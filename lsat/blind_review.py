# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Blind-Review "Gap Map": the timed-vs-untimed 2x2 that separates a *pacing*
gap from a *knowledge* gap (DECISION.md section 3, Feature 4).

A "blind review" is an optional, untimed **second pass** over items already
answered under the clock. Because a blind pass is simply another
``PerformanceEvent`` for the same ``item_id`` -- stamped ``phase="blind"`` or
``"relaxed"`` (see :mod:`lsat.events`) -- joining the most-recent *timed* answer
with the most-recent *blind/relaxed* answer per item yields a per-skill 2x2:

===================  ===========================  ==============================
                     Blind correct                Blind wrong
===================  ===========================  ==============================
**Timed correct**    Mastered                     Fragile / Lucky (NOT mastery)
**Timed wrong**      Pressure / Technique         Knowledge gap
                     (-> pacing)                   (-> content)
===================  ===========================  ==============================

The map routes each skill to the fix it actually needs (pacing vs content) and
emits a de-shaming headline ("Untimed you're 88% on Weaken, timed 71% -- that
gap is pacing, not knowledge."). :func:`lucky_timed_items` is the honest-mastery
filter's target: items whose *timed* win was NOT reproduced under untimed review
(the top-right cell), so a lucky guess never masquerades as mastery.

Pure Python over the event log; JSON-serialisable output; abstains below a small
floor of paired items -- we never diagnose a skill from a handful of answers
(DECISION.md section 5.v). This is the read/analysis layer only: the reviewer's
timed/blind session toggle already lives in ``qt/aqt/lsat_performance.py``.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from lsat.events import PerformanceEvent, read_events
from lsat.taxonomy import load_taxonomy

if TYPE_CHECKING:
    from anki.collection import Collection

_MS_PER_DAY = 86_400_000.0
DEFAULT_HALF_LIFE_DAYS = 30.0

# Abstain floors: never diagnose from a handful of answers (DECISION.md 5.v).
MIN_PAIRED_ITEMS = 5  # overall: total items answered BOTH timed and blind/relaxed
MIN_PAIRED_PER_SKILL = 3  # per skill: before we name/route/headline that skill
_MIN_HEADLINE_GAP = 0.05  # a pacing headline needs at least this blind-minus-timed gap

_TIMED = "timed"
_BLIND_PHASES = ("blind", "relaxed")
_QUADRANTS = ("mastered", "fragile", "pressure", "knowledge")

# Fixed seed so the paired bootstrap CI is reproducible across calls (the number
# is shown to the learner; it must not jitter between renders).
_CI_SEED = 20260702


def _paired_bootstrap_ci(
    deltas: list[float],
    *,
    seed: int = _CI_SEED,
    n_boot: int = 1000,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of per-item paired deltas
    (blind_correct - timed_correct in {-1, 0, +1}). Same estimator as
    ``eval.metrics.bootstrap_ci`` but local, so runtime ``lsat`` code has no
    dependency on the ``eval`` harness. A gap whose CI excludes 0 is a *measured*
    pacing gap on the learner's OWN items, not a point estimate."""
    import random

    if not deltas:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(deltas)
    means: list[float] = []
    for _ in range(n_boot):
        means.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (lo, hi)


# -- join + classify ----------------------------------------------------------


def _classify(timed_correct: bool, blind_correct: bool) -> str:
    """The 2x2 cell for one item's (timed, blind) answer pair."""
    if timed_correct:
        return "mastered" if blind_correct else "fragile"
    return "pressure" if blind_correct else "knowledge"


def _join_by_item(
    events: list[PerformanceEvent],
) -> dict[str, tuple[PerformanceEvent, PerformanceEvent]]:
    """Per ``item_id``: (most-recent timed event, most-recent blind/relaxed event).

    ``read_events`` is HLC-sorted oldest -> newest, so the last event seen for
    each phase is the most recent. Only items that have BOTH a timed and a
    blind/relaxed answer are returned -- the 2x2 needs one of each.
    """
    latest_timed: dict[str, PerformanceEvent] = {}
    latest_blind: dict[str, PerformanceEvent] = {}
    for ev in events:
        if ev.phase == _TIMED:
            latest_timed[ev.item_id] = ev
        elif ev.phase in _BLIND_PHASES:
            latest_blind[ev.item_id] = ev
    return {
        item_id: (latest_timed[item_id], latest_blind[item_id])
        for item_id in latest_timed
        if item_id in latest_blind
    }


class _Cell:
    """A recency-weighted accumulator for one skill (or the overall total)."""

    __slots__ = ("counts", "w_sum", "w_timed_correct", "w_blind_correct", "deltas")

    def __init__(self) -> None:
        self.counts: dict[str, int] = {q: 0 for q in _QUADRANTS}
        self.w_sum = 0.0
        self.w_timed_correct = 0.0
        self.w_blind_correct = 0.0
        # per-item paired delta (blind - timed) in {-1, 0, +1}, for the bootstrap CI
        self.deltas: list[float] = []

    def add(
        self, quadrant: str, weight: float, timed_correct: bool, blind_correct: bool
    ) -> None:
        self.counts[quadrant] += 1
        self.w_sum += weight
        self.w_timed_correct += weight if timed_correct else 0.0
        self.w_blind_correct += weight if blind_correct else 0.0
        self.deltas.append(
            (1.0 if blind_correct else 0.0) - (1.0 if timed_correct else 0.0)
        )

    @property
    def n(self) -> int:
        return sum(self.counts.values())


def _summarize(cell: _Cell) -> dict[str, Any]:
    """Counts (raw), shares (count/total), and recency-weighted accuracies."""
    n = cell.n
    shares = {q: (cell.counts[q] / n if n else 0.0) for q in _QUADRANTS}
    timed_acc = cell.w_timed_correct / cell.w_sum if cell.w_sum > 0 else 0.0
    blind_acc = cell.w_blind_correct / cell.w_sum if cell.w_sum > 0 else 0.0
    paired_gap = sum(cell.deltas) / len(cell.deltas) if cell.deltas else 0.0
    ci_low, ci_high = _paired_bootstrap_ci(cell.deltas)
    return {
        "n": n,
        "counts": dict(cell.counts),
        "shares": shares,
        "timed_accuracy": timed_acc,
        "blind_accuracy": blind_acc,
        "gap": blind_acc - timed_acc,  # positive = you do better untimed (pacing gap)
        # the MEASURED paired gap (unweighted per-item blind-minus-timed) + its 95%
        # bootstrap CI. `gap_ci_excludes_0` -> the pacing gap is real, not noise.
        "paired_gap": paired_gap,
        "gap_ci_low": ci_low,
        "gap_ci_high": ci_high,
        "gap_ci_excludes_0": ci_low > 0.0 or ci_high < 0.0,
    }


def _route(counts: dict[str, int]) -> str:
    """Route a skill by its *misses*: more pressure than knowledge -> pacing."""
    if counts["pressure"] > counts["knowledge"]:
        return "pacing"
    if counts["knowledge"] > counts["pressure"]:
        return "content"
    return "mixed"


# -- skill names --------------------------------------------------------------


def _prettify(node_id: str) -> str:
    """Fallback display name if the taxonomy is unavailable (``lr.weaken`` ->
    ``Weaken``)."""
    leaf = node_id.split(".")[-1]
    return leaf.replace("_", " ").strip().title() or node_id


def _skill_names() -> dict[str, str]:
    """``node_id -> display name`` from the taxonomy (best-effort; empty on error
    so the compute layer never crashes on a missing/edited YAML)."""
    try:
        tax = load_taxonomy()
    except Exception:
        return {}
    names: dict[str, str] = {}
    for topic in tax.topics:
        names[topic.id] = topic.name
    for skill in tax.cross_cutting:
        names[skill.id] = skill.name
    return names


# -- routing + headline -------------------------------------------------------


def _routing_summary(skills: list[dict[str, Any]]) -> dict[str, Any]:
    ready = [s for s in skills if s["enough_evidence"]]
    pressure = [s["node_id"] for s in ready if s["route"] == "pacing"]
    knowledge = [s["node_id"] for s in ready if s["route"] == "content"]
    mixed = [s["node_id"] for s in ready if s["route"] == "mixed"]
    summary = (
        f"{len(pressure)} skill(s) pressure-dominated (route to pacing), "
        f"{len(knowledge)} knowledge-dominated (route to content)."
    )
    return {
        "pressure_dominated": pressure,
        "knowledge_dominated": knowledge,
        "mixed": mixed,
        "summary": summary,
    }


def _headline(skills: list[dict[str, Any]]) -> str:
    """One de-shaming sentence: name the biggest fixable *pacing* gap, else point
    at content -- never "you're too slow / bad at X"."""
    ready = [s for s in skills if s["enough_evidence"]]
    # A pacing headline requires a MEASURED gap: the point gap clears the floor AND
    # the paired bootstrap CI on the learner's own items excludes 0 (not noise).
    pacing = sorted(
        (
            s
            for s in ready
            if s["route"] == "pacing"
            and s["gap"] > _MIN_HEADLINE_GAP
            and s["gap_ci_excludes_0"]
        ),
        key=lambda s: s["gap"],
        reverse=True,
    )
    if pacing:
        s = pacing[0]
        return (
            f"Untimed you're {s['blind_accuracy']:.0%} on {s['name']}, "
            f"timed {s['timed_accuracy']:.0%} -- that gap is pacing, not knowledge "
            f"(95% CI on the paired gap {s['gap_ci_low']:+.0%}..{s['gap_ci_high']:+.0%}, "
            f"excludes 0)."
        )
    content = sorted(ready, key=lambda s: s["blind_accuracy"])
    content = [s for s in content if s["route"] == "content"]
    if content:
        s = content[0]
        return (
            f"On {s['name']} you're {s['blind_accuracy']:.0%} even untimed -- "
            f"that's content to shore up, and content gains stick."
        )
    return (
        "Your timed and untimed accuracy track closely so far -- "
        "no big pacing gap to exploit yet."
    )


# -- public API ---------------------------------------------------------------


def gap_map(
    col: Collection,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """The Blind-Review Gap Map: per-skill and overall 2x2, routing, headline.

    Joins the most-recent timed answer with the most-recent blind/relaxed answer
    per ``item_id`` and buckets each paired item into the four quadrants. Counts
    are raw; accuracies are recency-weighted (an answer's weight halves every
    ``half_life_days``, matching :func:`lsat.events.fold_recent_performance`).
    Returns a JSON-serialisable dict; ``available`` is False (with a note) below
    ``MIN_PAIRED_ITEMS`` paired items.
    """
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    half_life_ms = max(1.0, half_life_days * _MS_PER_DAY)
    paired = _join_by_item(read_events(col))

    base: dict[str, Any] = {
        "half_life_days": half_life_days,
        "floor": {
            "min_paired_items": MIN_PAIRED_ITEMS,
            "min_paired_per_skill": MIN_PAIRED_PER_SKILL,
        },
        "n_paired_items": len(paired),
    }
    if len(paired) < MIN_PAIRED_ITEMS:
        return {
            **base,
            "available": False,
            "overall": None,
            "skills": [],
            "routing": {
                "pressure_dominated": [],
                "knowledge_dominated": [],
                "mixed": [],
                "summary": "",
            },
            "headline": "",
            "note": (
                f"Not enough blind-review pairs yet "
                f"({len(paired)}/{MIN_PAIRED_ITEMS}). Do an untimed second pass "
                f"over timed items to build the Gap Map."
            ),
        }

    overall = _Cell()
    per_skill: dict[str, _Cell] = defaultdict(_Cell)
    for timed_ev, blind_ev in paired.values():
        quadrant = _classify(timed_ev.correct, blind_ev.correct)
        age_ms = max(0, now_ms - timed_ev.wall_ms)
        weight = 0.5 ** (age_ms / half_life_ms)
        overall.add(quadrant, weight, timed_ev.correct, blind_ev.correct)
        for node_id in timed_ev.node_ids or blind_ev.node_ids:
            per_skill[node_id].add(quadrant, weight, timed_ev.correct, blind_ev.correct)

    names = _skill_names()
    skills: list[dict[str, Any]] = []
    for node_id, cell in per_skill.items():
        enough = cell.n >= MIN_PAIRED_PER_SKILL
        skills.append(
            {
                "node_id": node_id,
                "name": names.get(node_id, _prettify(node_id)),
                "enough_evidence": enough,
                "route": _route(cell.counts) if enough else "insufficient",
                **_summarize(cell),
            }
        )
    skills.sort(key=lambda s: (-s["n"], s["node_id"]))

    return {
        **base,
        "available": True,
        "overall": _summarize(overall),
        "skills": skills,
        "routing": _routing_summary(skills),
        "headline": _headline(skills),
    }


def lucky_timed_items_from_events(events: list[PerformanceEvent]) -> set[str]:
    """Item ids whose latest *timed* answer was correct but latest *blind/relaxed*
    answer was wrong -- the Fragile/Lucky cell (pure; operates on an event list).

    These are the honest-mastery filter's target: a timed win not reproduced under
    untimed review is a lucky guess, and must NOT be credited as mastery. Used by
    :func:`lsat.events.fold_recent_performance` to drop such wins from the per-topic
    mastery that feeds the points-at-stake queue.
    """
    paired = _join_by_item(events)
    return {
        item_id
        for item_id, (timed_ev, blind_ev) in paired.items()
        if timed_ev.correct and not blind_ev.correct
    }


def lucky_timed_items(col: Collection) -> set[str]:
    """Item ids in the Fragile/Lucky cell for a collection (see
    :func:`lucky_timed_items_from_events`)."""
    return lucky_timed_items_from_events(read_events(col))


# -- self-test ----------------------------------------------------------------


def _json_ok(obj: Any) -> bool:
    """True iff ``obj`` round-trips through strict JSON (no NaN/Infinity)."""
    import json

    try:
        json.dumps(obj, allow_nan=False)
    except (ValueError, TypeError):
        return False
    return True


def _selftest() -> bool:  # noqa: PLR0915 (one linear scenario; clearer inline)
    """Engineer each 2x2 quadrant on a temp Collection and assert the map."""
    import os
    import sys
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in (os.path.join(root, "pylib"), os.path.join(root, "out", "pylib"), root):
        if path not in sys.path:
            sys.path.insert(0, path)

    from anki.collection import Collection
    from lsat.events import append_event

    now = 1_700_000_000_000
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    def add_pair(
        col: Collection,
        item_id: str,
        skill: str,
        timed_correct: bool,
        blind_correct: bool,
        timed_ms: int,
    ) -> None:
        append_event(
            col,
            item_id=item_id,
            skill_tags=[skill],
            correct=timed_correct,
            response_ms=timed_ms,
            phase="timed",
            now_ms=now,
        )
        append_event(
            col,
            item_id=item_id,
            skill_tags=[skill],
            correct=blind_correct,
            response_ms=150_000,
            phase="blind",
            now_ms=now,
        )

    tmp = tempfile.mkdtemp(prefix="br-selftest-")

    # (1) abstain below the paired-item floor -----------------------------------
    below = Collection(os.path.join(tmp, "below.anki2"))
    try:
        add_pair(below, "b1", "lr.weaken", False, True, 100_000)
        add_pair(below, "b2", "lr.weaken", True, True, 60_000)
        add_pair(below, "b3", "lr.weaken", False, False, 80_000)  # 3 pairs < floor(5)
        gm_below = gap_map(below, now_ms=now)
        check("abstains below the paired-item floor", gm_below["available"] is False)
        check("below-floor payload is JSON-safe", _json_ok(gm_below))
    finally:
        below.close()

    # (2) the full engineered scenario ------------------------------------------
    full = Collection(os.path.join(tmp, "full.anki2"))
    try:
        # Weaken: pressure-dominated (much better untimed) + two clean masteries.
        add_pair(full, "W1", "lr.weaken", False, True, 120_000)  # pressure
        add_pair(full, "W2", "lr.weaken", False, True, 110_000)  # pressure
        add_pair(full, "W3", "lr.weaken", False, True, 100_000)  # pressure
        add_pair(full, "W4", "lr.weaken", True, True, 60_000)  # mastered
        add_pair(full, "W5", "lr.weaken", True, True, 50_000)  # mastered
        # Necessary Assumption: knowledge-dominated + one lucky/fragile timed win.
        add_pair(full, "A1", "lr.assumption_necessary", False, False, 80_000)  # know.
        add_pair(full, "A2", "lr.assumption_necessary", False, False, 85_000)  # know.
        add_pair(full, "A3", "lr.assumption_necessary", True, False, 70_000)  # fragile

        gm = gap_map(full, now_ms=now)
        check("gap_map available at/above the floor", gm["available"] is True)
        check("counts all 8 paired items", gm["n_paired_items"] == 8)
        check(
            "overall 2x2 counts correct (mastered2/fragile1/pressure3/knowledge2)",
            gm["overall"]["counts"]
            == {"mastered": 2, "fragile": 1, "pressure": 3, "knowledge": 2},
        )
        check(
            "overall shares sum to 1.0",
            abs(sum(gm["overall"]["shares"].values()) - 1.0) < 1e-9,
        )

        by_id = {s["node_id"]: s for s in gm["skills"]}
        weaken = by_id["lr.weaken"]
        assumption = by_id["lr.assumption_necessary"]
        check(
            "a pressure item shows up as pressure (Weaken has 3)",
            weaken["counts"]["pressure"] == 3,
        )
        check(
            "Weaken is pressure-dominated -> routed to pacing",
            weaken["route"] == "pacing"
            and "lr.weaken" in gm["routing"]["pressure_dominated"],
        )
        check(
            "Necessary Assumption is knowledge-dominated -> routed to content",
            assumption["route"] == "content"
            and "lr.assumption_necessary" in gm["routing"]["knowledge_dominated"],
        )
        check(
            "Weaken blind_accuracy (100%) exceeds timed (40%)",
            abs(weaken["blind_accuracy"] - 1.0) < 1e-9
            and abs(weaken["timed_accuracy"] - 0.4) < 1e-9,
        )

        lucky = lucky_timed_items(full)
        check(
            "lucky_timed_items catches ONLY the fragile item A3",
            lucky == {"A3"},
        )

        check(
            "per-skill summary carries the paired-gap bootstrap CI",
            all(
                k in weaken
                for k in (
                    "paired_gap",
                    "gap_ci_low",
                    "gap_ci_high",
                    "gap_ci_excludes_0",
                )
            ),
        )
        check(
            "Weaken's pacing gap is MEASURED (paired CI excludes 0)",
            weaken["gap_ci_excludes_0"] is True and weaken["gap_ci_low"] > 0.0,
        )
        head = gm["headline"]
        check(
            "headline is a non-punitive pacing message citing the CI",
            isinstance(head, str) and "pacing" in head.lower() and "CI" in head,
        )
        check("gap_map payload is JSON-safe (allow_nan=False)", _json_ok(gm))
    finally:
        full.close()

    # (3) the join must use the MOST RECENT timed answer ------------------------
    recency = Collection(os.path.join(tmp, "recency.anki2"))
    try:
        append_event(
            recency,
            item_id="R",
            skill_tags=["lr.weaken"],
            correct=False,
            response_ms=90_000,
            phase="timed",
            now_ms=now,
        )
        append_event(  # a later, correcting timed pass over the same item
            recency,
            item_id="R",
            skill_tags=["lr.weaken"],
            correct=True,
            response_ms=40_000,
            phase="timed",
            now_ms=now,
        )
        append_event(
            recency,
            item_id="R",
            skill_tags=["lr.weaken"],
            correct=True,
            response_ms=150_000,
            phase="blind",
            now_ms=now,
        )
        joined = _join_by_item(read_events(recency))
        timed_ev, blind_ev = joined["R"]
        check(
            "join takes the most-recent timed (and blind) event",
            timed_ev.correct is True and blind_ev.correct is True,
        )
    finally:
        recency.close()

    ok = all(passed for _, passed in checks)
    print("BLIND_OK" if ok else "BLIND_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
