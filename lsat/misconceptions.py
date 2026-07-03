# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Confidence x correctness state classification (SPOV 2 / B2).

Every graded review resolves to exactly one state:

- ``mastery``        confident + correct
- ``misconception``  confident + wrong  (danger zone; highest review value)
- ``fragile``        unsure + correct   (lucky; keep in rotation)
- ``honest_gap``     unsure + wrong     (plain knowledge gap; relearn source)
- ``unrated``        no confidence tap  (cannot classify without the signal)

Classification uses TIMED events only, matching the honest-mastery fold (a
relaxed second pass says nothing about exam-state knowledge).

Because corrected high-confidence errors *return* unless re-tested (Butler,
Fazio & Marsh 2011; the re-test blocks the return, Metcalfe & Miele 2014), each
misconception also carries a **resolution status** derived from later events on
the same item:

- ``open``      no later graded test -- the mandatory spaced re-test is owed
- ``resolved``  the most recent later test was answered correctly
- ``relapsed``  a correct answer was followed by another confident miss (the
                error returned; it is re-flagged, never silently trusted)

``lsat/relearning.py`` consumes the ``open`` set to schedule re-tests; the
dashboard consumes the counts.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from lsat.events import PerformanceEvent, read_events

if TYPE_CHECKING:
    from anki.collection import Collection

# One-tap confidence labels treated as "confident" (matches the
# hypercorrection boost in lsat/models/calibration.py).
CONFIDENT_LABELS = frozenset({"sure", "likely"})
UNSURE_LABELS = frozenset({"guess"})

STATE_MASTERY = "mastery"
STATE_MISCONCEPTION = "misconception"
STATE_FRAGILE = "fragile"
STATE_HONEST_GAP = "honest_gap"
STATE_UNRATED = "unrated"
STATES = (
    STATE_MASTERY,
    STATE_MISCONCEPTION,
    STATE_FRAGILE,
    STATE_HONEST_GAP,
    STATE_UNRATED,
)


def classify_event(confidence: str, correct: bool) -> str:
    """Map one review's (pre-answer confidence, correctness) to its state."""
    conf = (confidence or "").strip().lower()
    if conf in CONFIDENT_LABELS:
        return STATE_MASTERY if correct else STATE_MISCONCEPTION
    if conf in UNSURE_LABELS:
        return STATE_FRAGILE if correct else STATE_HONEST_GAP
    return STATE_UNRATED


def _resolution(item_events: list[PerformanceEvent], last: int) -> str:
    """Resolution status of the item's latest confident miss (index ``last``).

    ``resolved`` -- a later test exists and the most recent one was correct.
    ``relapsed`` -- the latest miss is the *return* of an error that had already
    been corrected once (an earlier confident miss followed by a correct
    answer), the exact failure mode Butler/Fazio/Marsh warn about.
    ``open`` -- otherwise: the spaced re-test is still owed.
    """
    later = item_events[last + 1 :]  # already HLC-ordered oldest -> newest
    if later:
        return "resolved" if later[-1].correct else "open"
    for i in range(last):
        event = item_events[i]
        if classify_event(event.confidence, event.correct) == STATE_MISCONCEPTION:
            if any(e.correct for e in item_events[i + 1 : last]):
                return "relapsed"
    return "open"


def misconception_stats(col: Collection, *, min_events: int = 1) -> dict[str, Any]:
    """Per-topic + overall state counts and the misconception ledger.

    JSON-safe. ``available`` is False until at least ``min_events`` timed
    events exist. Misconceptions are keyed per item: the *latest* confident
    miss on an item defines one ledger entry with its resolution status.
    """
    events = [e for e in read_events(col) if e.phase == "timed"]
    if len(events) < min_events:
        return {
            "available": False,
            "reason": f"no graded timed reviews yet (need {min_events}+)",
            "states": {s: 0 for s in STATES},
        }

    states = {s: 0 for s in STATES}
    by_topic: dict[str, dict[str, int]] = defaultdict(lambda: {s: 0 for s in STATES})
    by_item: dict[str, list[PerformanceEvent]] = defaultdict(list)
    for event in events:
        state = classify_event(event.confidence, event.correct)
        states[state] += 1
        for node_id in event.node_ids:
            by_topic[node_id][state] += 1
        by_item[event.item_id].append(event)

    ledger: list[dict[str, Any]] = []
    resolution = {"open": 0, "resolved": 0, "relapsed": 0}
    for item_id, item_events in by_item.items():
        miss_idx = [
            i
            for i, e in enumerate(item_events)
            if classify_event(e.confidence, e.correct) == STATE_MISCONCEPTION
        ]
        if not miss_idx:
            continue
        last = miss_idx[-1]
        status = _resolution(item_events, last)
        resolution[status] += 1
        ledger.append(
            {
                "item_id": item_id,
                "node_ids": item_events[last].node_ids,
                "chosen": item_events[last].chosen,
                "confidence": item_events[last].confidence,
                "hlc": item_events[last].hlc,
                "status": status,
            }
        )

    n_classified = len(events) - states[STATE_UNRATED]
    headline = None
    if resolution["open"] or resolution["relapsed"]:
        owed = resolution["open"] + resolution["relapsed"]
        headline = (
            f"{owed} confident miss(es) still need a spaced re-test -- "
            "corrected errors return unless re-tested."
        )
    return {
        "available": True,
        "n_events": len(events),
        "n_classified": n_classified,
        "states": states,
        "by_topic": {k: dict(v) for k, v in sorted(by_topic.items())},
        "misconceptions": sorted(ledger, key=lambda r: str(r["hlc"])),
        "resolution": resolution,
        "headline": headline,
    }


def open_misconception_items(col: Collection) -> list[str]:
    """Item ids whose latest confident miss is still open/relapsed -- the set
    owed a mandatory spaced re-test (consumed by ``lsat/relearning.py``)."""
    stats = misconception_stats(col)
    if not stats.get("available"):
        return []
    return [
        str(rec["item_id"])
        for rec in stats["misconceptions"]
        if rec["status"] in ("open", "relapsed")
    ]


def _selftest() -> bool:
    import os
    import sys
    import tempfile

    sys.path[:0] = ["pylib", "out/pylib", "."]
    import anki.collection  # noqa: F401
    from anki.collection import Collection
    from lsat.events import append_event
    from lsat.notetypes import ensure_notetypes

    ok = True

    def check(name: str, cond: bool, extra: str = "") -> None:
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")

    # pure classifier
    check("sure+correct=mastery", classify_event("sure", True) == STATE_MASTERY)
    check(
        "likely+wrong=misconception",
        classify_event("likely", False) == STATE_MISCONCEPTION,
    )
    check("guess+correct=fragile", classify_event("guess", True) == STATE_FRAGILE)
    check("guess+wrong=honest_gap", classify_event("guess", False) == STATE_HONEST_GAP)
    check("unrated", classify_event("", True) == STATE_UNRATED)

    col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
    try:
        ensure_notetypes(col)
        check("abstains empty", misconception_stats(col)["available"] is False)

        def ev(item, correct, conf, phase="timed"):
            append_event(
                col,
                item_id=item,
                skill_tags=["lr.weaken"],
                correct=correct,
                response_ms=1000,
                chosen="B" if not correct else "C",
                confidence=conf,
                phase=phase,
            )

        ev("i_open", False, "sure")  # misconception, never re-tested -> open
        ev("i_resolved", False, "sure")  # misconception ...
        ev("i_resolved", True, "likely")  # ... then corrected -> resolved
        ev("i_relapse", False, "sure")  # misconception ...
        ev("i_relapse", True, "likely")  # ... corrected ...
        ev("i_relapse", False, "sure")  # ... NEW confident miss = new ledger entry
        ev("i_mastery", True, "sure")  # mastery
        ev("i_fragile", True, "guess")  # fragile
        ev("i_gap", False, "guess")  # honest gap
        ev("i_unrated", True, "")  # unrated
        ev("i_blind", False, "sure", phase="blind")  # excluded (not timed)

        stats = misconception_stats(col)
        check("available", stats["available"] is True)
        s = stats["states"]
        check(
            "state counts",
            # mastery: i_resolved + i_relapse corrections + i_mastery = 3
            s[STATE_MASTERY] == 3
            and s[STATE_MISCONCEPTION] == 4
            and s[STATE_FRAGILE] == 1
            and s[STATE_HONEST_GAP] == 1
            and s[STATE_UNRATED] == 1,
            str(s),
        )
        check(
            "every timed event classified once",
            sum(s.values()) == stats["n_events"],
        )
        by_status = {r["item_id"]: r["status"] for r in stats["misconceptions"]}
        check(
            "ledger statuses",
            by_status
            == {"i_open": "open", "i_resolved": "resolved", "i_relapse": "relapsed"},
            str(by_status),
        )
        check(
            "open set for relearning",
            set(open_misconception_items(col)) == {"i_open", "i_relapse"},
        )
        check(
            "per-topic counts present",
            stats["by_topic"]["lr.weaken"][STATE_MISCONCEPTION] == 4,
        )
        import json

        json.dumps(stats, allow_nan=False)
        check("JSON-safe", True)
    finally:
        col.close()

    print("MISCONCEPTIONS_OK" if ok else "MISCONCEPTIONS_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
