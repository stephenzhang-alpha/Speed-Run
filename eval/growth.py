# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Mastery-Growth Panel gate (DECISION-round3 #2), a HARD gate.

The panel's only promise is *honest calibration*: it claims a per-skill direction
only when a bootstrap CI on the difficulty-matched early-vs-recent delta excludes
0. So the gate is a mechanics gate, not a learning-effect claim:

  * FALSE-DIRECTION arm -- on many true-no-change synthetic learners (recent
    accuracy == early accuracy), the panel must claim "improved"/"slipped" at most
    ``GROWTH_FALSE_DIRECTION_MAX`` of the time. This is the guarantee that the UI
    never fabricates progress out of noise.
  * DETECTION arm -- on many true-improvement learners, it must detect the rise at
    least ``GROWTH_DETECTION_MIN`` of the time (else the panel is honest but
    useless).

The panel ships ON only if BOTH hold. There is NO learning-effect claim here; any
engagement effect would need a separate pre-registered live-cohort arm (panel-on
vs panel-off at equal item quality). All inputs are seeded synthetic.
"""

from __future__ import annotations

import random

from eval import config
from lsat.growth import IMPROVED, SLIPPED, growth_for_skill

N_LEARNERS = 400
EVENTS = 80  # >= 2 * MIN_PER_WINDOW so a readout is attemptable
NULL_P = 0.7  # true-no-change accuracy
IMPROVE_FROM, IMPROVE_TO = 0.45, 0.82  # true-improvement early -> recent


def _history(n: int, p_early: float, p_recent: float, seed: int):
    rng = random.Random(seed)
    half = n // 2
    early = [(rng.random() < p_early, "medium") for _ in range(half)]
    recent = [(rng.random() < p_recent, "medium") for _ in range(half)]
    return early + recent


def _mix_drift(seed: int):
    """A pure difficulty-MIX DRIFT with NO real change: early mostly easy, recent
    mostly hard, same accuracy (NULL_P) in every band/window. A count-weighted
    pooled delta with no per-band floor fabricates a direction here (adversarial
    review Finding 1) -- this arm makes the gate exercise it, not just the clean
    single-band null."""
    rng = random.Random(seed)
    early = [(rng.random() < NULL_P, "easy") for _ in range(16)] + [
        (rng.random() < NULL_P, "hard") for _ in range(4)
    ]
    recent = [(rng.random() < NULL_P, "easy") for _ in range(4)] + [
        (rng.random() < NULL_P, "hard") for _ in range(16)
    ]
    return early + recent


def run(seed: int = config.RANDOM_SEED) -> dict:
    false_dir = 0
    mix_false = 0
    for i in range(N_LEARNERS):
        r = growth_for_skill(
            _history(EVENTS, NULL_P, NULL_P, seed + i), seed=seed + 7 + i
        )
        if r["status"] in (IMPROVED, SLIPPED):
            false_dir += 1
        m = growth_for_skill(_mix_drift(seed + 20_000 + i), seed=seed + 23 + i)
        if m["status"] in (IMPROVED, SLIPPED):
            mix_false += 1
    fp_rate = false_dir / N_LEARNERS
    mix_rate = mix_false / N_LEARNERS

    detected = 0
    for i in range(N_LEARNERS):
        r = growth_for_skill(
            _history(EVENTS, IMPROVE_FROM, IMPROVE_TO, seed + 10_000 + i),
            seed=seed + 13 + i,
        )
        if r["status"] == IMPROVED:
            detected += 1
    detect_rate = detected / N_LEARNERS

    passed = (
        fp_rate <= config.GROWTH_FALSE_DIRECTION_MAX
        and mix_rate <= config.GROWTH_FALSE_DIRECTION_MAX
        and detect_rate >= config.GROWTH_DETECTION_MIN
    )
    detail = (
        f"true-no-change false-direction {fp_rate:.3f}, difficulty-mix-drift "
        f"false-direction {mix_rate:.3f} (both max {config.GROWTH_FALSE_DIRECTION_MAX}); "
        f"true-improvement detection {detect_rate:.3f} "
        f"(min {config.GROWTH_DETECTION_MIN}) -> "
        f"{'panel ON' if passed else 'panel OFF (mechanics unmet)'}"
    )
    return {
        "name": "growth",
        "passed": bool(passed),
        "gate": True,
        "detail": detail,
        "false_direction_rate": round(fp_rate, 4),
        "mix_drift_false_direction_rate": round(mix_rate, 4),
        "detection_rate": round(detect_rate, 4),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
