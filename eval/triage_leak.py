# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Time-Leak Diagnostic validity (DECISION-round3 #5), a report arm.

The Time-Leak read-out (:func:`lsat.triage.time_leak`) sums the time a learner
spent under the clock on items they ALSO miss untimed (a genuine gap, not a pace
problem) -- "reclaimable" seconds. It makes no learning-effect claim, so this arm
reports estimator validity on seeded synthetic learners with known per-item
ground truth:

  * RECOVERY -- on time-pressured learners with real unwinnable items, the
    estimated reclaimable seconds recover the truly-wasted time (mean estimate's
    bootstrap 95% CI excludes 0), and we report the recovery fraction.
  * FALSE-UNWINNABLE -- a truly WINNABLE item (high untimed ability) is flagged
    unwinnable at most ``TRIAGE_FALSE_UNWINNABLE_MAX`` of the time (the guard: a
    lone guess-confidence untimed miss doesn't confirm a gap).
  * NULL -- a not-time-pressured learner (timed ~= untimed accuracy) yields ~0
    reclaimable seconds (CI includes 0), so the diagnostic abstains rather than
    invent a leak.

Report-only (like ``eval/exam_schedule.py``). All inputs are seeded synthetic; the
real code path over the event log is exercised by ``lsat/triage.py``'s self-test.
"""

from __future__ import annotations

import random

from eval import config
from eval.metrics import bootstrap_ci

N_LEARNERS = 300
N_UNWINNABLE = 8  # truly-unwinnable items per pressured learner
N_WINNABLE = 12  # truly-winnable items (choke: high untimed, low timed)
UNWINNABLE_MS = 100_000  # ground it under the clock
WINNABLE_MS = 70_000
P_UNTIMED_UNWINNABLE = 0.15  # you miss it even untimed
P_UNTIMED_WINNABLE = 0.85  # you get it with time
P_TIMED_WINNABLE = 0.35  # but usually miss it under the clock
_GUESS = "guess"


def _classify_unwinnable(timed_correct, untimed_correct, untimed_conf) -> bool:
    """Mirror lsat.triage._confirmed_unwinnable."""
    if timed_correct or untimed_correct:
        return False
    return untimed_conf != _GUESS


def _pressured_learner(rng: random.Random) -> tuple[float, float, int]:
    """Return (estimated_reclaimable_s, true_wasted_s, n_false_unwinnable) for one
    time-pressured learner over their unwinnable + winnable items."""
    est = 0.0
    true_wasted = 0.0
    false_unwin = 0
    # truly-unwinnable items: all the time on them is genuinely wasted
    for _ in range(N_UNWINNABLE):
        true_wasted += UNWINNABLE_MS / 1000.0
        timed_c = rng.random() < 0.20  # rarely gets it timed
        untimed_c = rng.random() < P_UNTIMED_UNWINNABLE
        # a confident untimed miss (real gap) most of the time
        conf = "sure" if rng.random() < 0.8 else _GUESS
        if _classify_unwinnable(timed_c, untimed_c, conf):
            est += UNWINNABLE_MS / 1000.0
    # truly-winnable items: NOT wasted; a fluke untimed miss is usually a guess
    for _ in range(N_WINNABLE):
        timed_c = rng.random() < P_TIMED_WINNABLE
        untimed_c = rng.random() < P_UNTIMED_WINNABLE
        conf = _GUESS if rng.random() < 0.7 else "likely"  # fluke misses feel unsure
        if _classify_unwinnable(timed_c, untimed_c, conf):
            est += WINNABLE_MS / 1000.0
            false_unwin += 1
    return est, true_wasted, false_unwin


def _null_learner(rng: random.Random) -> float:
    """TRUE leak = 0: the learner gets everything with time (untimed always
    correct) and only some items timed (a pure pace gap, no genuine gaps). Every
    timed miss is winnable, so a valid detector returns ~0 reclaimable seconds.
    Returns the estimated reclaimable seconds (should be exactly 0)."""
    est = 0.0
    for _ in range(20):
        timed_c = rng.random() < 0.80  # misses some under the clock (pace only)
        untimed_c = True  # ...but gets them all with time -> nothing is unwinnable
        conf = "sure" if rng.random() < 0.7 else _GUESS
        if _classify_unwinnable(timed_c, untimed_c, conf):
            est += 80_000 / 1000.0
    return est


def run(seed: int = config.RANDOM_SEED) -> dict:
    rng = random.Random(seed)
    est_pressured: list[float] = []
    true_wasted: list[float] = []
    false_unwin = 0
    winnable_total = N_WINNABLE * N_LEARNERS
    for _ in range(N_LEARNERS):
        e, w, fu = _pressured_learner(rng)
        est_pressured.append(e)
        true_wasted.append(w)
        false_unwin += fu
    fp_rate = false_unwin / winnable_total

    est_null = [_null_learner(rng) for _ in range(N_LEARNERS)]

    lo, hi = bootstrap_ci(est_pressured, seed=seed)
    mean_est = sum(est_pressured) / len(est_pressured)
    mean_true = sum(true_wasted) / len(true_wasted)
    recovery = (mean_est / mean_true) if mean_true else 0.0

    null_mean = sum(est_null) / len(est_null)
    recovers = lo > 0.0
    fp_ok = fp_rate <= config.TRIAGE_FALSE_UNWINNABLE_MAX
    null_ok = null_mean < 1.0  # true-leak-0 learner -> ~0 reclaimable seconds
    ship = recovers and fp_ok and null_ok

    detail = (
        f"reclaimable seconds recover true wasted time: est {mean_est:.0f}s vs "
        f"true {mean_true:.0f}s (recovery {recovery:.0%}); 95% CI "
        f"{lo:.0f}-{hi:.0f}s {'excludes' if recovers else 'includes'} 0; "
        f"false-unwinnable {fp_rate:.3f} (max {config.TRIAGE_FALSE_UNWINNABLE_MAX}); "
        f"true-leak-0 null mean {null_mean:.1f}s -> "
        f"{'valid' if ship else 'NOT validated'}"
    )
    return {
        "name": "triage_leak",
        "passed": None,  # report-only
        "gate": False,
        "detail": detail,
        "recovery_fraction": round(recovery, 4),
        "ci_low_seconds": round(lo, 1),
        "ci_high_seconds": round(hi, 1),
        "false_unwinnable_rate": round(fp_rate, 4),
        "null_mean_seconds": round(null_mean, 2),
        "ship_recommended": bool(ship),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
