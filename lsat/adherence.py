# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""If-Then Study Plan + adherence (DECISION-round2 #4).

A study app lives or dies on ADHERENCE -- showing up is the biggest real-world
determinant of score gain, and NONE of the shipped features (they all assume the
session already happened) touch it. Implementation intentions -- a single
"If <cue>, then I will <behaviour>" plan -- are one of the best-attested
behaviour-change levers (Gollwitzer; medium-large d).

This module stores ONE if-then plan in collection config and reports adherence
**inferred from the existing graded-event log** -- no new notetype, no new synced
record, no new sync path: "did you study today" is just "was there a timed answer
today", so the append-only event log already carries it.

**Locked constraints (DECISION-round2 §#4, non-negotiable):** the surface is a
single daily cue + a one-tap start; **no streak counters and no loss-aversion**
mechanics (they invite the exact gaming/shaming the honesty discipline forbids);
after >= 2 missed planned days a *neutral* re-plan prompt (never a shame message).

**Honest claim:** a behavioural adherence lift only. There is NO score claim from
the plan itself; any score effect is just the mechanical value of extra practice
and must not be double-counted against the study features. The synthetic-log eval
(``eval/adherence.py``) is a mechanics/plumbing check ONLY -- the adherence claim
is held UNPROVEN until a live-cohort CI excludes 0.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anki.collection import Collection

PLAN_CONFIG_KEY = "lsat:study_plan"
_MS_PER_DAY = 86_400_000
DEFAULT_WINDOW_DAYS = 14
REPLAN_MISSED_DAYS = 2  # >= this many consecutive missed planned days -> re-plan nudge


@dataclass(frozen=True)
class Plan:
    cue: str  # e.g. "8am" / "after breakfast"
    habit: str  # the anchor habit, e.g. "coffee"
    place: str  # e.g. "at my desk"
    n_cards: int  # the daily target
    created_ms: int


def if_then_string(plan: Plan) -> str:
    """The single implementation-intention sentence the cue restates. Renders
    gracefully whether the plan has all three trigger parts or just a cue."""
    trigger = plan.cue
    if plan.habit:
        trigger = f"{trigger} after {plan.habit}" if trigger else f"after {plan.habit}"
    if plan.place:
        trigger = f"{trigger} {plan.place}".strip()
    return f"If {trigger}, then I will do {plan.n_cards} LSAT cards."


def set_plan(
    col: Collection,
    *,
    cue: str,
    habit: str,
    place: str,
    n_cards: int,
    now_ms: int | None = None,
) -> Plan:
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    plan = Plan(
        cue=cue.strip(),
        habit=habit.strip(),
        place=place.strip(),
        n_cards=max(1, int(n_cards)),
        created_ms=now,
    )
    col.set_config(
        PLAN_CONFIG_KEY,
        {
            "cue": plan.cue,
            "habit": plan.habit,
            "place": plan.place,
            "n_cards": plan.n_cards,
            "created_ms": plan.created_ms,
        },
    )
    return plan


def clear_plan(col: Collection) -> None:
    col.set_config(PLAN_CONFIG_KEY, None)


def get_plan(col: Collection) -> Plan | None:
    data = col.get_config(PLAN_CONFIG_KEY, None)
    if not isinstance(data, dict):
        return None
    try:
        return Plan(
            cue=str(data.get("cue", "")),
            habit=str(data.get("habit", "")),
            place=str(data.get("place", "")),
            n_cards=max(1, int(data.get("n_cards", 1))),
            created_ms=int(data.get("created_ms", 0)),
        )
    except (TypeError, ValueError):
        return None


def _study_days(col: Collection) -> dict[int, int]:
    """``UTC-day-index -> count of timed graded answers that day`` from the log."""
    from lsat.events import read_events

    by_day: dict[int, int] = {}
    for e in read_events(col):
        if e.phase != "timed":
            continue
        day = e.wall_ms // _MS_PER_DAY
        by_day[day] = by_day.get(day, 0) + 1
    return by_day


def adherence_status(
    col: Collection,
    *,
    now_ms: int | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    """Adherence read-out inferred from the graded-event log (JSON-safe).

    ``available`` is False (no plan) until a plan is set -- adherence is only
    meaningful against an intention. With a plan it reports the if-then sentence,
    active days + completed days (>= the daily target) in the window, days since
    last study, and a NEUTRAL re-plan flag after >= ``REPLAN_MISSED_DAYS``
    consecutive missed days. No streaks, no shaming (DECISION-round2 §#4).
    """
    plan = get_plan(col)
    if plan is None:
        return {"available": False, "reason": "No study plan set."}

    now = now_ms if now_ms is not None else int(time.time() * 1000)
    today = now // _MS_PER_DAY
    by_day = _study_days(col)
    window = [today - i for i in range(window_days)]
    active_days = sum(1 for d in window if by_day.get(d, 0) > 0)
    completed_days = sum(1 for d in window if by_day.get(d, 0) >= plan.n_cards)

    studied_days = [d for d, n in by_day.items() if n > 0]
    last_active_days_ago = (today - max(studied_days)) if studied_days else None

    # Consecutive missed days ending today (today counts as missed only once it
    # has begun and no study yet -- we count from yesterday backwards + today).
    missed_streak = 0
    for d in [today - i for i in range(window_days)]:
        if by_day.get(d, 0) > 0:
            break
        missed_streak += 1
    needs_replan = missed_streak >= REPLAN_MISSED_DAYS

    return {
        "available": True,
        "if_then": if_then_string(plan),
        "n_cards_target": plan.n_cards,
        "window_days": window_days,
        "active_days": active_days,
        "completed_days": completed_days,
        "last_active_days_ago": last_active_days_ago,
        "consecutive_missed_days": missed_streak,
        "needs_replan": needs_replan,
        # A calm, non-shaming line the UI can show verbatim.
        "note": (
            f"You've hit your {plan.n_cards}-card plan on {completed_days} of the "
            f"last {window_days} days"
            + (" -- want to re-plan a cue that fits better?" if needs_replan else ".")
        ),
    }


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    import os
    import sys
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (os.path.join(root, "pylib"), os.path.join(root, "out", "pylib"), root):
        if p not in sys.path:
            sys.path.insert(0, p)
    from anki.collection import Collection
    from lsat.events import append_event

    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    col = Collection(os.path.join(tempfile.mkdtemp(prefix="adh-"), "c.anki2"))
    try:
        now = 1_700_000_000_000
        day = _MS_PER_DAY
        check(
            "abstains with no plan",
            adherence_status(col, now_ms=now)["available"] is False,
        )

        plan = set_plan(
            col, cue="8am", habit="coffee", place="at my desk", n_cards=10, now_ms=now
        )
        check(
            "if_then sentence reads right",
            "then I will do 10 LSAT cards" in if_then_string(plan),
        )
        check("get_plan round-trips", get_plan(col).n_cards == 10)

        # Study on days 0 (today), 1, 3 ago: day0 = 12 cards (completed), day1 = 5
        # (active not completed), day3 = 10 (completed). days 2 + 4..13 = missed.
        def study(days_ago: int, n: int) -> None:
            ts = now - days_ago * day
            for i in range(n):
                append_event(
                    col,
                    item_id=f"d{days_ago}i{i}",
                    skill_tags=["lr.weaken"],
                    correct=True,
                    response_ms=1000,
                    phase="timed",
                    now_ms=ts,
                )

        # Append oldest-first: the HLC clock is monotonic, so out-of-order
        # appends would bump earlier events' walls forward (real usage is
        # chronological, so day-bucketing from the HLC wall is faithful there).
        study(3, 10)
        study(1, 5)
        study(0, 12)
        st = adherence_status(col, now_ms=now)
        check("available with a plan", st["available"] is True)
        check("active_days = 3 (days 0,1,3)", st["active_days"] == 3)
        check("completed_days = 2 (>=10 on days 0 and 3)", st["completed_days"] == 2)
        check("last_active = 0 (studied today)", st["last_active_days_ago"] == 0)
        check("no re-plan (studied today)", st["needs_replan"] is False)
        check("json-safe", _json_ok(st))

        # A lapsed learner: last study 3 days ago -> 3 consecutive missed -> re-plan.
        col2 = Collection(os.path.join(tempfile.mkdtemp(prefix="adh2-"), "c.anki2"))
        try:
            set_plan(
                col2,
                cue="8am",
                habit="coffee",
                place="at my desk",
                n_cards=5,
                now_ms=now,
            )
            for i in range(6):
                append_event(
                    col2,
                    item_id=f"x{i}",
                    skill_tags=["lr.weaken"],
                    correct=True,
                    response_ms=1000,
                    phase="timed",
                    now_ms=now - 3 * day,
                )
            st2 = adherence_status(col2, now_ms=now)
            check(
                "lapsed: 3 consecutive missed days", st2["consecutive_missed_days"] == 3
            )
            check("lapsed: neutral re-plan flag set", st2["needs_replan"] is True)
            check(
                "lapsed: note is non-shaming",
                "re-plan" in st2["note"] and "bad" not in st2["note"].lower(),
            )
        finally:
            col2.close()
    finally:
        col.close()

    ok = all(p for _, p in checks)
    print("ADHERENCE_OK" if ok else "ADHERENCE_FAIL")
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
