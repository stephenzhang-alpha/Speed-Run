# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Conditional Translation Drill ablation (DECISION-round2 #19), a report arm.

At EQUAL study events, does drilling conditional translation (the faded
sufficient->necessary + contrapositive drill, graded deterministically by
``lsat.conditional``) lift held-out accuracy on **conditional-dependent LR items**
more than generic review?

Three arms, paired per learner:
  * drill   -- targeted conditional-translation practice (efficient skill gain);
  * generic -- ordinary mixed review that only touches conditional logic in passing;
  * plain   -- vanilla review (no targeting or interleaving).

Held-out metric: P(correct) on unseen conditional-tagged LR items (necessary /
sufficient assumption, must-be-true, parallel, principle) = a function of the
learner's conditional-logic skill. Report ``drill - generic`` with a bootstrap
95% CI. Honest single-digit ceiling; report even if null. The per-event gain
advantage of the drill is an EXPLICIT parameter, not evidence -- synthetic.
"""

from __future__ import annotations

import math
import random

from eval import config
from eval.metrics import bootstrap_ci

N_LEARNERS = 300
STUDY_EVENTS = 60  # equal events per arm
DIFFICULTIES = (-1.0, 0.0, 1.0)
# Per-event conditional-logic skill gain (logit), diminishing. The targeted drill
# is more efficient per event than incidental generic review; plain is the least
# targeted. Explicit parameters (not measured).
GAIN = {"drill": 0.16, "generic": 0.09, "plain": 0.07}


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _simulate(seed: int, arm: str) -> float:
    rng = random.Random(seed)
    skill = rng.uniform(-1.6, -0.4)  # start weak at conditional logic
    g = GAIN[arm]
    for _ in range(STUDY_EVENTS):
        skill += g * rng.uniform(0.6, 1.4) * (1.0 - _sigmoid(skill))
    # Held-out conditional-tagged LR items; partial transfer keeps it off the ceiling.
    return sum(_sigmoid(0.7 * skill - d) for d in DIFFICULTIES) / len(DIFFICULTIES)


def run(seed: int = config.RANDOM_SEED) -> dict:
    per_arm: dict[str, list[float]] = {a: [] for a in GAIN}
    drill_minus_generic: list[float] = []
    for i in range(N_LEARNERS):
        vals = {a: _simulate(seed + i, a) for a in GAIN}
        for a in GAIN:
            per_arm[a].append(vals[a])
        drill_minus_generic.append(vals["drill"] - vals["generic"])

    means = {a: sum(v) / len(v) for a, v in per_arm.items()}
    lo, hi = bootstrap_ci(drill_minus_generic, seed=seed)
    mean_diff = sum(drill_minus_generic) / len(drill_minus_generic)
    ship = lo > 0.0
    detail = (
        f"held-out P(correct) on conditional-tagged LR items at equal "
        f"{STUDY_EVENTS} events: drill {means['drill']:.3f} vs generic "
        f"{means['generic']:.3f} vs plain {means['plain']:.3f}; drill-generic "
        f"{mean_diff:+.3f} (95% CI {lo:+.3f}..{hi:+.3f}) -> "
        f"{'ship (CI excludes 0)' if ship else 'null at equal time (ship the drill OFF)'}"
    )
    return {
        "name": "conditional",
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
