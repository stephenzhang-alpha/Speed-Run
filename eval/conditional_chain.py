# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Conditional-Chain Trainer ablation (DECISION-round4 #22), a report arm.

At EQUAL study events, does drilling multi-arrow conditional chains (must-follow /
does-not-follow judgments graded deterministically by ``lsat.conditional_chain``)
lift held-out accuracy on **unseen 3+ arrow chain inferences** more than generic
review? This targets the case the single-conditional drill abstains on, where
working-memory load bites.

Three arms, paired per learner (drill / generic / plain). PRIMARY held-out metric:
P(correct) on a FINITE bank of unseen chain-inference items (must-follow vs the
affirming-consequent / denying-antecedent traps) with novel surface propositions --
measured over a finite bank so the estimate carries realistic binomial noise.
Report ``drill - generic`` with a bootstrap 95% CI; ship ON only if the CI excludes
0; report even if null.

Scope note: a synthetic IRT SIMULATION of the learning effect; it does not route
items through the real grader (whose exactness + fail-closed behavior is validated
by that module's self-test). The positive CI is a consequence of the disclosed
``GAIN`` -- it demonstrates the equal-study-time + bootstrap-CI *mechanism*, and is
deliberately report-only (no gate rides on it). Chaining is a deep, WM-heavy skill,
so its per-event gain is set BETWEEN the fast stem drill and the slower nec/suff
sort -- an explicit synthetic parameter, never evidence.
"""

from __future__ import annotations

import math
import random

from eval import config
from eval.metrics import bootstrap_ci

N_LEARNERS = 300
STUDY_EVENTS = 60
N_HELDOUT = 24
DIFFICULTIES = (-0.7, 0.0, 0.7, 1.1)  # longer chains are harder
GAIN = {"drill": 0.17, "generic": 0.085, "plain": 0.06}


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _skill_after(rng: random.Random, arm: str) -> float:
    skill = rng.uniform(-1.3, -0.3)
    g = GAIN[arm]
    for _ in range(STUDY_EVENTS):
        skill += g * rng.uniform(0.6, 1.4) * (1.0 - _sigmoid(skill))
    return skill


def _heldout_accuracy(rng: random.Random, skill: float) -> float:
    correct = 0
    for i in range(N_HELDOUT):
        d = DIFFICULTIES[i % len(DIFFICULTIES)]
        if rng.random() < _sigmoid(0.75 * skill - d):
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
        f"held-out P(correct) on unseen 3+ arrow chain inferences at equal "
        f"{STUDY_EVENTS} events ({N_HELDOUT}-item bank): drill {means['drill']:.3f} "
        f"vs generic {means['generic']:.3f} vs plain {means['plain']:.3f}; "
        f"drill-generic {mean_diff:+.3f} (95% CI {lo:+.3f}..{hi:+.3f}) -> "
        f"{'ship (CI excludes 0)' if ship else 'null at equal time (ship OFF)'}"
    )
    return {
        "name": "conditional_chain",
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
