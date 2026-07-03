# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Necessary/Sufficient Discrimination Drill ablation (DECISION-round4 #5), report arm.

At EQUAL study events, does the four-cell sort drill (graded deterministically by
``lsat.assumption_discrimination``, whose cells are derived by the proven
``lsat.quantifier`` model-checker) lift held-out **discrimination accuracy** on
interleaved Necessary/Sufficient-Assumption items more than generic review?

Three arms, paired per learner (drill / generic / plain). PRIMARY held-out metric:
accuracy of the four-cell sort (necessary-only / sufficient-only / both / neither;
chance = 0.25) on a FINITE bank of unseen interleaved NA+SA items with novel terms
-- measured over a finite bank so the estimate carries realistic binomial noise
(a believable CI width, not +/-0.001). Report ``drill - generic`` with a bootstrap
95% CI; ship ON only if the CI excludes 0; report even if null.

Discrimination is a deeper mapping than the stem-polarity detection, so its
per-event gain is set LOWER than the stem drill's -- an explicit synthetic
parameter, never evidence.

Scope note: this is a synthetic IRT SIMULATION of the learning effect; it does not
route items through the real ``lsat.assumption_discrimination`` grader (whose cells
are proven by the ``lsat.quantifier`` model-checker + the higher-cap oracle
regression in that module's self-test). The positive CI here is a consequence of
the disclosed ``GAIN`` assumption -- it demonstrates the equal-study-time +
bootstrap-CI *mechanism*, and is deliberately report-only (no gate rides on it).
"""

from __future__ import annotations

import math
import random

from eval import config
from eval.metrics import bootstrap_ci

N_LEARNERS = 300
STUDY_EVENTS = 60
N_HELDOUT = 24  # finite unseen NA+SA bank -> realistic binomial noise
DIFFICULTIES = (-0.6, 0.0, 0.6, 1.0)  # four-cell sort spans easy..hard
# Deeper discrimination skill -> slower per-event gain than the polarity drill;
# generic mixed review touches NA/SA only in passing. Explicit synthetic params.
GAIN = {"drill": 0.15, "generic": 0.075, "plain": 0.05}
CHANCE = 0.25  # a four-way sort


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _skill_after(rng: random.Random, arm: str) -> float:
    skill = rng.uniform(-1.2, -0.2)
    g = GAIN[arm]
    for _ in range(STUDY_EVENTS):
        skill += g * rng.uniform(0.6, 1.4) * (1.0 - _sigmoid(skill))
    return skill


def _heldout_accuracy(rng: random.Random, skill: float) -> float:
    """Fraction of the finite unseen NA+SA bank sorted correctly. Above-chance
    part scales with skill; the rest is chance (0.25 floor for a 4-way sort)."""
    correct = 0
    for i in range(N_HELDOUT):
        d = DIFFICULTIES[i % len(DIFFICULTIES)]
        p = CHANCE + (1.0 - CHANCE) * _sigmoid(skill - d)
        if rng.random() < p:
            correct += 1
    return correct / N_HELDOUT


def run(seed: int = config.RANDOM_SEED) -> dict:
    per_arm: dict[str, list[float]] = {a: [] for a in GAIN}
    drill_minus_generic: list[float] = []
    for i in range(N_LEARNERS):
        skills = {a: _skill_after(random.Random(seed + i), a) for a in GAIN}
        acc = {
            a: _heldout_accuracy(random.Random(seed + 5000 + i), skills[a])
            for a in GAIN
        }
        for a in GAIN:
            per_arm[a].append(acc[a])
        drill_minus_generic.append(acc["drill"] - acc["generic"])

    means = {a: sum(v) / len(v) for a, v in per_arm.items()}
    lo, hi = bootstrap_ci(drill_minus_generic, seed=seed)
    mean_diff = sum(drill_minus_generic) / len(drill_minus_generic)
    ship = lo > 0.0
    detail = (
        f"held-out four-cell sort accuracy (chance {CHANCE}) at equal "
        f"{STUDY_EVENTS} events ({N_HELDOUT}-item bank): drill {means['drill']:.3f} "
        f"vs generic {means['generic']:.3f} vs plain {means['plain']:.3f}; "
        f"drill-generic {mean_diff:+.3f} (95% CI {lo:+.3f}..{hi:+.3f}) -> "
        f"{'ship (CI excludes 0)' if ship else 'null at equal time (ship OFF)'}"
    )
    return {
        "name": "assumption_discrimination",
        "passed": None,  # report-only
        "gate": False,
        "detail": detail,
        "means": {a: round(means[a], 4) for a in GAIN},
        "drill_minus_generic": round(mean_diff, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "ship_recommended": ship,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
