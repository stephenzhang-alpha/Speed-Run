# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Rush-Error Detector estimator-validity gate (DECISION-round3 #21).

The Rush-Error read-out (:func:`lsat.pacing.rush_errors`) flags a timed miss that
lands under half the learner's OWN careful (untimed) median RT. The claim is
*estimator validity*, not a learning effect, so the gate has two teeth:

  * SENSITIVITY -- on learners with a planted rush penalty (fast answers are less
    accurate), the per-baseline detector flags the problem >= ``RUSH_DETECT_MIN``.
  * SPECIFICITY + BEATS-NAIVE -- on **naturally fast but accurate** learners (short
    RTs, no penalty -- the exact confound a naive absolute-clock threshold trips
    on), the per-baseline detector's false-flag rate stays <= ``RUSH_FALSE_FLAG_MAX``
    AND is strictly below a naive absolute-threshold detector's. This is why the
    per-learner baseline exists.

The estimator's decision rule is simulated directly here (as in
``eval/choke_validity.py``); the real code path over the event log is exercised by
``lsat/pacing.py``'s self-test. All inputs are seeded synthetic.
"""

from __future__ import annotations

import math
import random
import statistics

from eval import config

N_LEARNERS = 300
N_UNTIMED = 12  # careful-pace baseline answers per learner
# Detection (power) is measured at a MATURE per-skill data volume (~72 timed
# answers ~= three practice sections): the CI-gated flag deliberately abstains on
# thin data, so on a handful of answers it neither detects nor false-flags -- the
# honest failure mode. The false-flag arm below holds at ANY volume (it is
# CI-gated), which is the property that actually matters for not misleading users.
N_TIMED = 72
RUSH_FRAC = 0.5  # fraction of timed items answered fast
FAST_FRAC = 0.5  # detector: fast = rt < FAST_FRAC * baseline median (mirrors pacing.py)
EXCESS_MARGIN = 0.15  # per-baseline flag: fast error rate >= 15pp above non-fast
MIN_SIDE = 5  # min fast AND non-fast answers to compute an excess (mirrors pacing.py)
BOOT_N = 600  # bootstrap resamples for the excess CI (mirrors pacing.py)
NAIVE_RATE = 0.10  # naive flag: fast-and-wrong COUNT share above this (baseline-blind)
NAIVE_ABS_MS = 45_000  # a naive absolute fast threshold (baseline-blind)

# Planted-rush population: normal pace, real penalty on the rushed items.
PLANTED = {"median_ms": 90_000, "p_careful": 0.75, "penalty": 0.35}
# Naturally-fast null: short RTs, accurate, NO penalty -- the naive-killer confound.
FAST_NULL = {"median_ms": 18_000, "p_careful": 0.85, "penalty": 0.0}


def _simulate(rng: random.Random, spec: dict) -> tuple[float, list[tuple[float, bool]]]:
    med = spec["median_ms"]
    p_careful = spec["p_careful"]
    p_rush = p_careful - spec["penalty"]
    untimed = [rng.lognormvariate(math.log(med), 0.3) for _ in range(N_UNTIMED)]
    baseline = statistics.median(untimed)
    timed: list[tuple[float, bool]] = []
    for _ in range(N_TIMED):
        if rng.random() < RUSH_FRAC:
            rt = 0.3 * med * rng.uniform(0.7, 1.3)
            correct = rng.random() < p_rush
        else:
            rt = med * rng.uniform(0.8, 1.2)
            correct = rng.random() < p_careful
        timed.append((rt, correct))
    return baseline, timed


def _excess_flag(
    timed: list[tuple[float, bool]], threshold_ms: float, rng: random.Random
) -> bool:
    """Per-baseline rule (mirrors lsat.pacing._rush_fold): flag when fast answers
    are MATERIALLY (>= EXCESS_MARGIN) and SIGNIFICANTLY (bootstrap CI on the excess
    excludes 0) more wrong than non-fast, given enough of each side."""
    fast = [c for rt, c in timed if rt < threshold_ms]
    slow = [c for rt, c in timed if rt >= threshold_ms]
    nf, ns = len(fast), len(slow)
    if nf < MIN_SIDE or ns < MIN_SIDE:
        return False
    fast_err = sum(1 for c in fast if not c) / nf
    slow_err = sum(1 for c in slow if not c) / ns
    if (fast_err - slow_err) < EXCESS_MARGIN:
        return False
    diffs: list[float] = []
    for _ in range(BOOT_N):
        fe = sum(not fast[rng.randrange(nf)] for _ in range(nf)) / nf
        se = sum(not slow[rng.randrange(ns)] for _ in range(ns)) / ns
        diffs.append(fe - se)
    diffs.sort()
    return diffs[int(0.025 * BOOT_N)] > 0.0


def _naive_count_flag(timed: list[tuple[float, bool]]) -> bool:
    """The naive baseline-blind detector: flag when the fast-and-wrong COUNT share
    (against an absolute clock) exceeds NAIVE_RATE. This is what the per-learner
    baseline must beat -- it has no notion of the learner's own pace."""
    if not timed:
        return False
    rate = sum(1 for rt, c in timed if rt < NAIVE_ABS_MS and not c) / len(timed)
    return rate >= NAIVE_RATE


def run(seed: int = config.RANDOM_SEED) -> dict:
    rng = random.Random(seed)

    # SENSITIVITY: planted-rush learners should be flagged by the per-baseline rule.
    detected = 0
    for _ in range(N_LEARNERS):
        baseline, timed = _simulate(rng, PLANTED)
        if _excess_flag(timed, FAST_FRAC * baseline, rng):
            detected += 1
    detect_rate = detected / N_LEARNERS

    # SPECIFICITY on naturally-fast-but-accurate learners: per-baseline vs naive.
    base_false = 0
    naive_false = 0
    for _ in range(N_LEARNERS):
        baseline, timed = _simulate(rng, FAST_NULL)
        if _excess_flag(timed, FAST_FRAC * baseline, rng):
            base_false += 1
        if _naive_count_flag(timed):
            naive_false += 1
    base_false_rate = base_false / N_LEARNERS
    naive_false_rate = naive_false / N_LEARNERS

    passed = (
        detect_rate >= config.RUSH_DETECT_MIN
        and base_false_rate <= config.RUSH_FALSE_FLAG_MAX
        and base_false_rate < naive_false_rate
    )
    detail = (
        f"planted-rush detection {detect_rate:.3f} (min {config.RUSH_DETECT_MIN}); "
        f"naturally-fast false-flag: per-baseline {base_false_rate:.3f} "
        f"(max {config.RUSH_FALSE_FLAG_MAX}) vs naive absolute-clock "
        f"{naive_false_rate:.3f} -> "
        f"{'valid (beats naive)' if passed else 'INVALID'}"
    )
    return {
        "name": "rush",
        "passed": bool(passed),
        "gate": True,
        "detail": detail,
        "detection_rate": round(detect_rate, 4),
        "baseline_false_flag": round(base_false_rate, 4),
        "naive_false_flag": round(naive_false_rate, 4),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
