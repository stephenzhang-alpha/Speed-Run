# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Exam-Day Retrievability Targeting (DECISION-round2 #7).

Students have a FIXED test date and finite hours; the shipped points-at-stake
queue and ZPD selector are blind to *when* the exam is. This module reallocates
the SAME review minutes toward being retrievable ON test day:

- the learner sets an ``exam_date`` once (a shared collection-config key -- the
  single owner of the exam-date cluster);
- :func:`deadline_desired_retention` gives a deadline-adjusted target retention
  DR(d): a low floor when the exam is far, ramping up in the final ~3 weeks (a
  cram-taper toward high test-day retrievability);
- :func:`project_examday_retrievability` projects each card's FSRS retrievability
  forward to exam day via the power forgetting curve;
- :func:`build_consolidation_queue` surfaces the cards whose *projected exam-day*
  retrievability sits below DR(d), ranked by ``exam_weight * (DR - projected_R)``,
  with a hard daily cap, and flags cards whose next due date lands AFTER the exam.

**Honest framing.** This is a scheduling *reallocation*, not new learning: the
claim (measured in ``eval/exam_schedule.py``) is ~3-6 scaled points from spending
the same minutes better, and it can be net-zero for a learner who already studies
daily -- that null case is reported. The module ABSTAINS (degrades to the normal
queue) when there is no exam date or too little FSRS memory state to project.

Pure Python over FSRS data the engine already stores; no Rust, no proto.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lsat.taxonomy import TAG_SEP, Taxonomy, load_taxonomy

if TYPE_CHECKING:
    from anki.collection import Collection

EXAM_DATE_CONFIG_KEY = "lsat:exam_date"  # stored as epoch milliseconds (UTC)
_MS_PER_DAY = 86_400_000.0

# FSRS-5 power forgetting curve R(t) = (1 + FACTOR * t/S)^DECAY, t and S in days.
FSRS5_DECAY = -0.5
FSRS5_FACTOR = 19.0 / 81.0  # = 0.9**(1/DECAY) - 1

# Deadline-adjusted desired-retention ramp (a cram-taper toward test day).
DR_FLOOR = 0.80  # far from the exam: hold a modest floor (avoid over-reviewing)
DR_PEAK = 0.94  # in the last day or two: aim high for test-day retrievability
DR_RAMP_DAYS = 21  # start ramping ~3 weeks out (Cepeda-style spacing ridgeline)

DEFAULT_DAILY_CAP = 60  # never balloon the day's reviews (anti-burnout hard cap)
MIN_CARDS_WITH_STATE = 10  # abstain below this many cards carrying FSRS state


# -- exam date config ---------------------------------------------------------


def set_exam_date(col: Collection, epoch_ms: int | None) -> None:
    """Set (or clear, with ``None``) the exam date. Stored in synced config."""
    if epoch_ms is None:
        col.set_config(EXAM_DATE_CONFIG_KEY, None)
    else:
        col.set_config(EXAM_DATE_CONFIG_KEY, int(epoch_ms))


def get_exam_date(col: Collection) -> int | None:
    val = col.get_config(EXAM_DATE_CONFIG_KEY, None)
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def days_until_exam(col: Collection, *, now_ms: int | None = None) -> int | None:
    """Whole days from now until the exam (0 = today/past), or None if unset."""
    exam = get_exam_date(col)
    if exam is None:
        return None
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    return max(0, int((exam - now) // _MS_PER_DAY))


# -- pure retrievability model ------------------------------------------------


def deadline_desired_retention(days_until: int) -> float:
    """Target retention for a card given days remaining (DR floor -> peak ramp)."""
    if days_until <= 1:
        return DR_PEAK
    if days_until >= DR_RAMP_DAYS:
        return DR_FLOOR
    frac = (DR_RAMP_DAYS - days_until) / float(DR_RAMP_DAYS - 1)
    return DR_FLOOR + frac * (DR_PEAK - DR_FLOOR)


def project_examday_retrievability(
    stability: float, days_until: int, decay: float = FSRS5_DECAY
) -> float:
    """Projected FSRS retrievability on exam day for a card with the given
    stability (days), assuming no further review. In ``(0, 1]``."""
    if stability <= 0:
        return 0.0
    t = max(0, days_until)
    return float((1.0 + FSRS5_FACTOR * t / stability) ** decay)


# -- consolidation queue ------------------------------------------------------


@dataclass(frozen=True)
class ConsolidationCard:
    card_id: int
    node_id: str
    exam_weight: float
    stability: float
    projected_r: float
    gap: float  # DR - projected_r  (>0 means it needs consolidation)
    priority: float  # exam_weight * gap
    due_after_exam: bool


def _tag_weight_map(tax: Taxonomy) -> dict[str, float]:
    """``taxonomy tag -> exam/study weight`` for scored types + cross-cutting."""
    out: dict[str, float] = {}
    for t in tax.question_types:
        out[t.tag] = t.exam_weight
    for s in tax.cross_cutting:
        out[s.tag] = s.study_weight
    return out


def _card_exam_weight(tags: list[str], weights: dict[str, float]) -> tuple[str, float]:
    """The max-weight taxonomy tag on a card (node_id, weight); ("", 0) if none."""
    best_id, best_w = "", 0.0
    for tag in tags:
        w = weights.get(tag)
        if w is not None and w > best_w:
            best_w = w
            best_id = tag
    return best_id, best_w


def build_consolidation_queue(
    col: Collection,
    *,
    taxonomy: Taxonomy | None = None,
    now_ms: int | None = None,
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> dict[str, Any]:
    """The exam-day consolidation queue for a collection (JSON-safe).

    Abstains (``available: False``) when no exam date is set or too few cards
    carry FSRS memory state to project. Otherwise ranks LSAT-tagged review cards
    whose projected exam-day retrievability is below the deadline target
    DR(days), by ``exam_weight * (DR - projected_R)``, capped at ``daily_cap``.
    """

    tax = taxonomy or load_taxonomy()
    days = days_until_exam(col, now_ms=now_ms)
    base: dict[str, Any] = {
        "available": False,
        "days_until_exam": days,
        "daily_cap": daily_cap,
    }
    if days is None:
        return {**base, "reason": "No exam date set.", "queue": []}

    dr = deadline_desired_retention(days)
    weights = _tag_weight_map(tax)
    root = next(iter(weights), "lsat::x").split(TAG_SEP)[0] if weights else "lsat"

    # One joined scan of LSAT-tagged review cards: id, tags, stability, due.
    # stability lives in the card's FSRS memory state (data blob); we read it via
    # the same extractor family the memory model uses, but need the raw value, so
    # we pull it from the deserialised card below in one pass.
    from lsat.models.memory import _tag_ancestors

    node_tags = set(weights)
    rows = col.db.all(
        "select c.id, n.tags, c.due, c.odue from cards c, notes n "
        "where c.nid = n.id and c.type = 2 and n.tags like ?",
        f"%{root}{TAG_SEP}%",
    )
    candidates: list[ConsolidationCard] = []
    n_with_state = 0
    timing = col._backend.sched_timing_today()
    for cid, tags, due, odue in rows:
        matched: set[str] = set()
        for token in tags.split():
            for anc in _tag_ancestors(token.lower()):
                if anc in node_tags:
                    matched.add(anc)
        if not matched:
            continue
        card = col.get_card(cid)
        state = card.memory_state
        if state is None or state.stability <= 0:
            continue
        n_with_state += 1
        node_id, weight = _card_exam_weight(sorted(matched), weights)
        projected = project_examday_retrievability(state.stability, days)
        gap = dr - projected
        # due is in days since collection creation for review cards; a card whose
        # next due lands after the exam won't be seen again before test day.
        due_day = odue if odue and odue != 0 else due
        due_after_exam = due_day > timing.days_elapsed + days
        if gap > 0:
            candidates.append(
                ConsolidationCard(
                    card_id=int(cid),
                    node_id=node_id,
                    exam_weight=round(weight, 6),
                    stability=round(float(state.stability), 4),
                    projected_r=round(projected, 4),
                    gap=round(gap, 4),
                    priority=round(weight * gap, 6),
                    due_after_exam=bool(due_after_exam),
                )
            )

    if n_with_state < MIN_CARDS_WITH_STATE:
        return {
            **base,
            "reason": (
                f"Not enough FSRS memory state yet ({n_with_state}/"
                f"{MIN_CARDS_WITH_STATE} cards) to project exam-day retention."
            ),
            "queue": [],
        }

    candidates.sort(key=lambda c: (c.priority, c.card_id), reverse=True)
    capped = candidates[:daily_cap]
    return {
        "available": True,
        "days_until_exam": days,
        "desired_retention": round(dr, 4),
        "daily_cap": daily_cap,
        "n_below_target": len(candidates),
        "n_due_after_exam": sum(1 for c in candidates if c.due_after_exam),
        "queue": [
            {
                "card_id": c.card_id,
                "node_id": c.node_id,
                "exam_weight": c.exam_weight,
                "projected_r": c.projected_r,
                "gap": c.gap,
                "priority": c.priority,
                "due_after_exam": c.due_after_exam,
            }
            for c in capped
        ],
        "note": (
            f"{days} day(s) to exam; target retention {dr:.0%}. "
            f"{len(candidates)} card(s) project below target"
            + (
                f", {sum(1 for c in candidates if c.due_after_exam)} not due again "
                "before the exam"
                if any(c.due_after_exam for c in candidates)
                else ""
            )
            + f". Showing the top {len(capped)} to consolidate today."
        ),
    }


def exam_schedule_summary(
    col: Collection, *, now_ms: int | None = None
) -> dict[str, Any]:
    """Compact dashboard summary: days-to-exam + consolidation count (or abstain)."""
    q = build_consolidation_queue(col, now_ms=now_ms)
    return {
        "available": q["available"],
        "days_until_exam": q.get("days_until_exam"),
        "desired_retention": q.get("desired_retention"),
        "n_below_target": q.get("n_below_target", 0),
        "n_due_after_exam": q.get("n_due_after_exam", 0),
        "reason": q.get("reason"),
        "note": q.get("note"),
    }


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # DR ramp: floor far out, peak near, monotic non-decreasing toward the exam.
    check(
        "DR floor when far (>=21d)",
        abs(deadline_desired_retention(30) - DR_FLOOR) < 1e-9,
    )
    check("DR peak on exam day", abs(deadline_desired_retention(0) - DR_PEAK) < 1e-9)
    ramp = [deadline_desired_retention(d) for d in range(21, 0, -1)]
    check(
        "DR ramps up as the exam approaches",
        all(a <= b + 1e-9 for a, b in zip(ramp, ramp[1:])),
    )
    check(
        "DR stays within [floor, peak]",
        all(DR_FLOOR - 1e-9 <= v <= DR_PEAK + 1e-9 for v in ramp),
    )

    # Forgetting curve: R decreases with time, increases with stability, R(0)=1.
    check("R(t=0) == 1", abs(project_examday_retrievability(50, 0) - 1.0) < 1e-9)
    check(
        "R decreases over time",
        project_examday_retrievability(50, 5) > project_examday_retrievability(50, 30),
    )
    check(
        "R higher for more stable card",
        project_examday_retrievability(200, 20)
        > project_examday_retrievability(20, 20),
    )
    check(
        "R in (0,1] for a stable card at 30d",
        0.0 < project_examday_retrievability(50, 30) <= 1.0,
    )
    check(
        "zero stability -> R 0 (abstain)", project_examday_retrievability(0, 10) == 0.0
    )

    # Collection-level: abstain with no exam date, then build a queue.
    import os
    import sys
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (os.path.join(root, "pylib"), os.path.join(root, "out", "pylib"), root):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        from anki.collection import Collection
    except Exception as exc:  # anki not importable here -> pure checks only
        print(f"  [SKIP] collection checks: {exc}")
        ok = all(p for _, p in checks)
        print("EXAM_SCHEDULE_OK" if ok else "EXAM_SCHEDULE_FAIL")
        return ok

    col = Collection(os.path.join(tempfile.mkdtemp(prefix="exam-"), "c.anki2"))
    try:
        now = 1_700_000_000_000
        check(
            "abstains with no exam date",
            build_consolidation_queue(col, now_ms=now)["available"] is False,
        )
        set_exam_date(col, now + int(14 * _MS_PER_DAY))
        check("days_until_exam ~ 14", days_until_exam(col, now_ms=now) == 14)
        q = build_consolidation_queue(col, now_ms=now)
        # No LSAT cards with FSRS state yet -> abstain on thin state.
        check(
            "abstains on thin FSRS state",
            q["available"] is False and "memory state" in (q.get("reason") or ""),
        )
        check("summary is json-safe", _json_ok(exam_schedule_summary(col, now_ms=now)))
    finally:
        col.close()

    ok = all(p for _, p in checks)
    print("EXAM_SCHEDULE_OK" if ok else "EXAM_SCHEDULE_FAIL")
    return ok


def _json_ok(obj: Any) -> bool:
    import json

    try:
        json.dumps(obj, allow_nan=False)
    except (ValueError, TypeError):
        return False
    return True


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
