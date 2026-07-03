# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Fatigue Curve — time-on-task accuracy decay (DECISION-round2 #10).

The LSAT is a ~3-hour, four-section stamina test; late-section accuracy decay is a
real, individual failure mode. No shipped signal captures session position
(Feature 4's Choke Index measures per-item time *pressure* — orthogonal). This
module measures how accuracy and speed change with **cumulative time-on-task
within a study session**.

**No schema migration.** Rather than add session fields to the event notetype, we
INFER sessions from the append-only event log's existing HLC wall timestamps: a
gap larger than :data:`SESSION_GAP_MS` starts a new session. Within a session each
event gets a cumulative-minutes-on-task from the session's first answer. We then
bin by cumulative minutes and report per-bin accuracy + median response time,
plus an OLS slope ("accuracy lost / 30 min").

Honest framing: this MEASURES a decrement; the diagnostic does not itself raise
scores, and whether a fatigue-aware model actually predicts better is the job of
``eval/fatigue.py``. Abstains below an evidence floor and never emits a fabricated
"stamina score". Only ``phase="timed"`` answers count (fatigue is about real
test-condition work).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lsat.events import read_events

if TYPE_CHECKING:
    from anki.collection import Collection
    from lsat.events import PerformanceEvent

SESSION_GAP_MS = 20 * 60 * 1000  # a >20-min gap between answers starts a new session
_MS_PER_MIN = 60_000.0
# Cumulative-minutes bins (upper edges); the last bin is "45+".
_BIN_EDGES = (10.0, 20.0, 30.0, 45.0)
_BIN_LABELS = ("0-10 min", "10-20 min", "20-30 min", "30-45 min", "45+ min")

MIN_TIMED_EVENTS = 20  # overall floor before we report a curve
MIN_SESSIONS = 3  # need a few sessions so the curve is not one sitting
MIN_BIN_EVENTS = 4  # a bin needs this many answers to be reported (else abstain)


def _sessions(events: list[PerformanceEvent]) -> list[list[PerformanceEvent]]:
    """Split HLC-ordered timed events into sessions by wall-clock gap."""
    timed = [e for e in events if e.phase == "timed"]
    timed.sort(key=lambda e: e.wall_ms)
    out: list[list[PerformanceEvent]] = []
    cur: list[PerformanceEvent] = []
    last_wall = None
    for e in timed:
        w = e.wall_ms
        if last_wall is not None and (w - last_wall) > SESSION_GAP_MS:
            out.append(cur)
            cur = []
        cur.append(e)
        last_wall = w
    if cur:
        out.append(cur)
    return out


def _bin_index(minutes: float) -> int:
    for i, edge in enumerate(_BIN_EDGES):
        if minutes < edge:
            return i
    return len(_BIN_EDGES)


def _median(xs: list[int]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _ols_slope(points: list[tuple[float, float]]) -> float | None:
    """Least-squares slope of y on x (per unit x), or None if degenerate."""
    n = len(points)
    if n < 2:
        return None
    mx = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    sxx = sum((p[0] - mx) ** 2 for p in points)
    if sxx <= 1e-12:
        return None
    sxy = sum((p[0] - mx) * (p[1] - my) for p in points)
    return sxy / sxx


def fatigue_curve(col: Collection, *, now_ms: int | None = None) -> dict[str, Any]:
    """Accuracy + response-time by cumulative minutes-on-task (JSON-safe).

    ``available`` is False (with a calm reason) below the evidence floors.
    Otherwise reports per-bin accuracy/median-RT/n, the number of sessions, and
    an OLS ``accuracy_slope_per_30min`` (negative = accuracy decays with time on
    task) with an honest note. Item difficulty is NOT regressed out here (that is
    the eval's validity job), so the curve is framed as a descriptive diagnostic.
    """
    _ = now_ms  # accepted for signature symmetry; the curve is not recency-weighted
    events = read_events(col)
    sessions = _sessions(events)
    n_timed = sum(len(s) for s in sessions)

    base: dict[str, Any] = {
        "available": False,
        "n_timed": n_timed,
        "n_sessions": len(sessions),
        "floor": {"min_timed": MIN_TIMED_EVENTS, "min_sessions": MIN_SESSIONS},
    }
    if n_timed < MIN_TIMED_EVENTS or len(sessions) < MIN_SESSIONS:
        return {
            **base,
            "reason": (
                f"Not enough timed study yet ({n_timed}/{MIN_TIMED_EVENTS} answers "
                f"across {len(sessions)}/{MIN_SESSIONS} sessions) to read a fatigue "
                "curve."
            ),
            "bins": [],
        }

    # Accumulate per-bin correctness + response times over all sessions.
    n_bins = len(_BIN_LABELS)
    correct = [0] * n_bins
    total = [0] * n_bins
    rts: list[list[int]] = [[] for _ in range(n_bins)]
    for session in sessions:
        start = session[0].wall_ms
        for e in session:
            minutes = max(0.0, (e.wall_ms - start) / _MS_PER_MIN)
            b = _bin_index(minutes)
            total[b] += 1
            correct[b] += 1 if e.correct else 0
            if e.response_ms > 0:
                rts[b].append(e.response_ms)

    bins: list[dict[str, Any]] = []
    slope_points: list[tuple[float, float]] = []
    centers = (5.0, 15.0, 25.0, 37.5, 55.0)  # representative minutes per bin
    for i in range(n_bins):
        if total[i] < MIN_BIN_EVENTS:
            continue
        acc = correct[i] / total[i]
        bins.append(
            {
                "label": _BIN_LABELS[i],
                "n": total[i],
                "accuracy": round(acc, 4),
                "median_response_ms": _median(rts[i]),
            }
        )
        slope_points.append((centers[i], acc))

    slope30 = _ols_slope(slope_points)
    slope30 = round(slope30 * 30.0, 4) if slope30 is not None else None
    if not bins:
        return {
            **base,
            "reason": "No time-on-task bin has enough answers yet.",
            "bins": [],
        }
    return {
        "available": True,
        "n_timed": n_timed,
        "n_sessions": len(sessions),
        "bins": bins,
        "accuracy_slope_per_30min": slope30,
        "note": (
            "Accuracy by cumulative minutes-on-task within a session"
            + (
                f"; about {abs(slope30):.0%} accuracy {'lost' if slope30 < 0 else 'gained'} "
                "per 30 min (descriptive -- item difficulty is not held constant here)."
                if slope30 is not None
                else " (not enough spread to fit a slope)."
            )
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

    col = Collection(os.path.join(tempfile.mkdtemp(prefix="fatigue-"), "c.anki2"))
    try:
        # Below floor -> abstain.
        check("abstains with no data", fatigue_curve(col)["available"] is False)

        # Build 4 sessions, each ~50 min, with accuracy decaying as minutes rise:
        # early answers mostly correct, late answers mostly wrong (a choke curve).
        day = 86_400_000
        base_wall = 1_700_000_000_000
        for s in range(4):
            sess_start = base_wall + s * day
            # 12 answers over ~55 minutes (5 min apart); accuracy falls with time.
            for i in range(12):
                minutes = i * 5
                correct = minutes < 25  # correct early, wrong late
                append_event(
                    col,
                    item_id=f"s{s}i{i}",
                    skill_tags=["lr.weaken"],
                    correct=correct,
                    response_ms=40_000 + minutes * 400,  # slower as fatigue sets in
                    phase="timed",
                    now_ms=sess_start + minutes * 60_000,
                )
        fc = fatigue_curve(col)
        check("available after enough sessions", fc["available"] is True)
        check("detected 4 sessions", fc["n_sessions"] == 4)
        check("reports multiple bins", len(fc["bins"]) >= 3)
        # accuracy should fall across bins (early high, late low)
        accs = [b["accuracy"] for b in fc["bins"]]
        check("accuracy decays across time-on-task bins", accs[0] > accs[-1])
        check(
            "slope is negative (accuracy lost per 30 min)",
            fc["accuracy_slope_per_30min"] < 0,
        )
        # response time should rise across bins
        rts = [b["median_response_ms"] for b in fc["bins"]]
        check("median RT rises with time on task", rts[-1] >= rts[0])
        check("json-safe", _json_ok(fc))

        # A single long session (not enough sessions) -> abstain.
        col2 = Collection(os.path.join(tempfile.mkdtemp(prefix="fatigue2-"), "c.anki2"))
        try:
            for i in range(30):
                append_event(
                    col2,
                    item_id=f"x{i}",
                    skill_tags=["lr.weaken"],
                    correct=True,
                    response_ms=40_000,
                    phase="timed",
                    now_ms=base_wall + i * 60_000,
                )
            check(
                "abstains below the session floor (1 session)",
                fatigue_curve(col2)["available"] is False,
            )
        finally:
            col2.close()
    finally:
        col.close()

    ok = all(p for _, p in checks)
    print("FATIGUE_OK" if ok else "FATIGUE_FAIL")
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
