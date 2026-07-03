# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Time-Leak Diagnostic (DECISION-round3 #5): reclaimable-seconds triage read-out.

Over items answered BOTH timed and untimed (blind/relaxed), classify each miss:

  * **winnable** -- missed timed but gotten untimed. Time spent here can pay off
    with better pacing (a choke, not a leak); NOT reclaimable.
  * **unwinnable** -- missed timed AND missed untimed *with confidence* (not a lone
    guess). You don't have it even with unlimited time, so the time you spent
    grinding it under the clock is **reclaimable** -- the leak the LSAT triage
    skill (guess-and-move-on) exists to plug.

The read-out sums reclaimable seconds and reports them WITH a bootstrap 95% CI. It
is strictly descriptive -- it never promises a point/score gain (a diagnostic does
not raise scores). It leads with an abstain path when there is no blind pass yet
("need a blind pass first"), abstains below a paired-item floor, and returns ~0
(CI includes 0) for a learner who is not time-pressured -- exactly the honest null.

Mirrors :mod:`lsat.pacing`'s structure (abstain floors, JSON-safe payloads,
``_selftest``). No Rust/proto/schema.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from lsat.events import read_events
from lsat.pacing import _pair_by_item, _prettify, _skill_names

if TYPE_CHECKING:
    from anki.collection import Collection

MIN_TRIAGE_PAIRS = 8  # paired (timed+untimed) items before any read-out
TRIAGE_BOOTSTRAP_N = 600
TRIAGE_SEED = 1234
_GUESS = "guess"  # a lone untimed miss marked "guess" does NOT confirm unwinnable

_FRAMING = (
    "Reclaimable = time spent under the clock on items you also missed untimed "
    "(a genuine gap, not a pace problem) -- seconds a guess-and-move-on triage "
    "would return to winnable items. Descriptive only: it measures time, never a "
    "promised score gain."
)


def _confirmed_unwinnable(timed_correct: bool, untimed_ev: Any) -> bool:
    """A miss is 'unwinnable' when it was wrong timed AND wrong untimed, and the
    untimed miss was not a lone guess (confidence 'sure'/'likely'/unrated confirms
    a real gap; a pure guess is too uncertain to brand the item unwinnable)."""
    if timed_correct or untimed_ev.correct:
        return False
    return (untimed_ev.confidence or "").strip().lower() != _GUESS


def _bootstrap_mean_ci(values: list[float], seed: int) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(TRIAGE_BOOTSTRAP_N):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(0.025 * TRIAGE_BOOTSTRAP_N)]
    hi = means[min(TRIAGE_BOOTSTRAP_N - 1, int(0.975 * TRIAGE_BOOTSTRAP_N))]
    return (lo, hi)


def time_leak(col: Collection, *, now_ms: int | None = None) -> dict[str, Any]:
    """Per-skill and overall reclaimable-seconds read-out. JSON-safe. Abstains
    with an explicit reason when there is no blind pass, too few paired items, or
    no measurable leak (CI on per-item reclaimable seconds includes 0)."""
    events = read_events(col)
    has_untimed = any(e.phase in ("blind", "relaxed") for e in events)
    pairs = _pair_by_item(events)

    base: dict[str, Any] = {
        "floor": {"min_pairs": MIN_TRIAGE_PAIRS},
        "n_pairs": len(pairs),
        "framing": _FRAMING,
    }
    if not has_untimed:
        return {
            **base,
            "available": False,
            "overall": None,
            "skills": [],
            "headline": "",
            "reason": "Need a blind pass first -- blind-review some items untimed "
            "so a miss can be labelled winnable (pace) vs unwinnable (gap).",
        }
    if len(pairs) < MIN_TRIAGE_PAIRS:
        return {
            **base,
            "available": False,
            "overall": None,
            "skills": [],
            "headline": "",
            "reason": "Not enough items answered both timed and untimed yet.",
        }

    # per-pair reclaimable seconds (0 unless the miss is a confirmed gap)
    per_item: list[float] = []
    n_unwinnable = n_winnable = 0
    skill_reclaim: dict[str, list[float]] = {}
    skill_unwin: dict[str, int] = {}
    for _item_id, (timed_ev, untimed_ev) in pairs.items():
        unwinnable = _confirmed_unwinnable(timed_ev.correct, untimed_ev)
        winnable = (not timed_ev.correct) and untimed_ev.correct
        secs = (timed_ev.response_ms / 1000.0) if unwinnable else 0.0
        per_item.append(secs)
        if unwinnable:
            n_unwinnable += 1
        if winnable:
            n_winnable += 1
        for node_id in timed_ev.node_ids:
            skill_reclaim.setdefault(node_id, []).append(secs)
            if unwinnable:
                skill_unwin[node_id] = skill_unwin.get(node_id, 0) + 1

    total_reclaimable_s = sum(per_item)
    mean_lo, mean_hi = _bootstrap_mean_ci(per_item, TRIAGE_SEED)
    n = len(per_item)
    # scale the per-item mean CI up to a total-seconds CI over the paired set
    total_ci_low = mean_lo * n
    total_ci_high = mean_hi * n
    # a leak is "measurable" only when the per-item reclaimable-seconds CI excludes 0
    measurable = mean_lo > 0.0

    names = _skill_names()
    skills = []
    for node_id, secs_list in sorted(skill_reclaim.items()):
        total = sum(secs_list)
        skills.append(
            {
                "node_id": node_id,
                "name": names.get(node_id, _prettify(node_id)),
                "reclaimable_seconds": round(total, 1),
                "n_unwinnable": skill_unwin.get(node_id, 0),
                "n_pairs": len(secs_list),
            }
        )
    skills.sort(key=lambda s: s["reclaimable_seconds"], reverse=True)

    if measurable and n_unwinnable > 0:
        mins = total_reclaimable_s / 60.0
        headline = (
            f"About {mins:.1f} min went to {n_unwinnable} item(s) you also missed "
            f"untimed -- reclaimable by triaging those sooner (95% CI "
            f"{total_ci_low / 60.0:.1f}-{total_ci_high / 60.0:.1f} min). "
            f"{n_winnable} other miss(es) were winnable with time (pace, not gap)."
        )
    else:
        headline = (
            "No measurable time leak -- your timed misses are mostly winnable with "
            "time, not items you'd miss untimed too."
        )

    return {
        **base,
        "available": True,
        "measurable_leak": bool(measurable and n_unwinnable > 0),
        "overall": {
            "reclaimable_seconds": round(total_reclaimable_s, 1),
            "reclaimable_ci_low": round(max(0.0, total_ci_low), 1),
            "reclaimable_ci_high": round(total_ci_high, 1),
            "n_unwinnable": n_unwinnable,
            "n_winnable": n_winnable,
            "n_pairs": n,
        },
        "skills": skills,
        "headline": headline,
    }


# -- self-test ----------------------------------------------------------------


def _json_ok(obj: Any) -> bool:
    import json

    try:
        json.dumps(obj, allow_nan=False)
        return True
    except (TypeError, ValueError):
        return False


def _selftest() -> bool:
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

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    def pair(
        col, item_id, skill, timed_correct, untimed_correct, timed_ms, untimed_conf=""
    ):
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
            correct=untimed_correct,
            response_ms=150_000,
            phase="blind",
            confidence=untimed_conf,
            now_ms=now,
        )

    tmp = tempfile.mkdtemp(prefix="triage-selftest-")

    # (1) no blind pass -> "need a blind pass first"
    nb = Collection(os.path.join(tmp, "nb.anki2"))
    try:
        for i in range(10):
            append_event(
                nb,
                item_id=f"t{i}",
                skill_tags=["lr.flaw"],
                correct=False,
                response_ms=90_000,
                phase="timed",
                now_ms=now,
            )
        r = time_leak(nb, now_ms=now)
        check(
            "abstains with 'need a blind pass first'",
            r["available"] is False and "blind pass" in r["reason"],
        )
        check("no-blind payload JSON-safe", _json_ok(r))
    finally:
        nb.close()

    # (2) below the paired floor -> abstain
    few = Collection(os.path.join(tmp, "few.anki2"))
    try:
        for i in range(3):
            pair(few, f"p{i}", "lr.flaw", False, False, 90_000)
        r = time_leak(few, now_ms=now)
        check("abstains below the paired floor", r["available"] is False)
    finally:
        few.close()

    # (3) a real leak: 6 unwinnable (wrong timed+untimed, ~90s each) + 4 winnable
    leak = Collection(os.path.join(tmp, "leak.anki2"))
    try:
        for i in range(6):  # unwinnable: wrong both, confident untimed miss
            pair(leak, f"u{i}", "lr.flaw", False, False, 90_000, untimed_conf="sure")
        for i in range(4):  # winnable: wrong timed, right untimed
            pair(leak, f"w{i}", "lr.flaw", False, True, 80_000)
        r = time_leak(leak, now_ms=now)
        ov = r["overall"]
        check("leak available", r["available"] is True)
        check(
            "counts 6 unwinnable + 4 winnable",
            ov["n_unwinnable"] == 6 and ov["n_winnable"] == 4,
        )
        check(
            "reclaimable seconds = 6 * 90s = 540s",
            abs(ov["reclaimable_seconds"] - 540.0) < 1e-6,
        )
        check("measurable leak flagged (CI excludes 0)", r["measurable_leak"] is True)
        check("reclaimable CI lower bound > 0", ov["reclaimable_ci_low"] > 0.0)
        check("headline reports reclaimable minutes", "reclaimable" in r["headline"])
        check("leak payload JSON-safe (allow_nan=False)", _json_ok(r))
    finally:
        leak.close()

    # (4) not time-pressured null: all winnable (wrong timed, right untimed) OR
    # right timed -> no unwinnable items -> reclaimable ~0, no measurable leak
    null = Collection(os.path.join(tmp, "null.anki2"))
    try:
        for i in range(10):
            pair(null, f"n{i}", "lr.flaw", i % 2 == 0, True, 70_000)
        r = time_leak(null, now_ms=now)
        check("null: no measurable leak", r["measurable_leak"] is False)
        check(
            "null: reclaimable seconds ~ 0",
            abs(r["overall"]["reclaimable_seconds"]) < 1e-6,
        )
        check("null payload JSON-safe", _json_ok(r))
    finally:
        null.close()

    # (5) a lone GUESS untimed miss does not brand an item unwinnable
    guess = Collection(os.path.join(tmp, "guess.anki2"))
    try:
        for i in range(8):
            pair(guess, f"g{i}", "lr.flaw", False, False, 90_000, untimed_conf="guess")
        r = time_leak(guess, now_ms=now)
        check(
            "lone guess untimed misses are NOT counted unwinnable",
            r["overall"]["n_unwinnable"] == 0,
        )
    finally:
        guess.close()

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("TRIAGE_OK" if ok else "TRIAGE_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
