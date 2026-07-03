# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Quantifier Reasoning Drill ablation (DECISION-round3 #1), a report arm.

At EQUAL study events, does drilling quantifier reasoning (the validity +
negation drills graded deterministically by ``lsat.quantifier``) lift held-out
accuracy on **quantifier-inference / negation judgments** more than generic
review?

Three arms, paired per learner:
  * drill   -- targeted quantifier practice (efficient skill gain);
  * generic -- ordinary mixed review that only touches quantifier logic in passing;
  * plain   -- vanilla review (no targeting).

PRIMARY held-out metric: P(correct) on unseen quantifier judgments instantiated
with **novel surface terms** (the transfer-relevant form). SECONDARY: speeded
accuracy at a matched median RT -- automaticity's real payoff (fluency lets the
learner apply the rule under time pressure, not merely when unhurried). Report
``drill - generic`` with a bootstrap 95% CI. Honest single-digit ceiling; report
even if null. Per-event skill gain is an EXPLICIT synthetic parameter, not
evidence. The far-transfer arms (full quantifier-tagged LR items;
Necessary-Assumption items) are NOT modeled here -- they ship OFF until their own
field CI excludes 0.
"""

from __future__ import annotations

import math
import random

from eval import config
from eval.metrics import bootstrap_ci

N_LEARNERS = 300
STUDY_EVENTS = 60  # equal events per arm
DIFFICULTIES = (-1.0, 0.0, 1.0)
# Per-event quantifier-logic skill gain (logit), diminishing. The targeted drill
# is more efficient per event than incidental generic review; plain is least
# targeted. Explicit parameters (not measured).
GAIN = {"drill": 0.16, "generic": 0.09, "plain": 0.07}
# Under time pressure, higher automaticity (proxied by accumulated skill) converts
# more of the untimed accuracy into speeded accuracy. The drill's edge should show
# up MORE under speed -- that is the automaticity claim, tested as the secondary.
SPEED_PENALTY = 0.55  # logit haircut applied to ability when answering fast


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _skill_after(seed: int, arm: str) -> float:
    rng = random.Random(seed)
    skill = rng.uniform(-1.6, -0.4)  # start weak at quantifier logic
    g = GAIN[arm]
    for _ in range(STUDY_EVENTS):
        skill += g * rng.uniform(0.6, 1.4) * (1.0 - _sigmoid(skill))
    return skill


def _accuracy(skill: float, *, speeded: bool) -> float:
    # Held-out judgments with NOVEL terms; partial transfer keeps it off the
    # ceiling. Speeded answers apply a fixed ability haircut (fluency gap).
    ability = 0.7 * skill - (SPEED_PENALTY if speeded else 0.0)
    return sum(_sigmoid(ability - d) for d in DIFFICULTIES) / len(DIFFICULTIES)


def run(seed: int = config.RANDOM_SEED) -> dict:
    per_arm: dict[str, list[float]] = {a: [] for a in GAIN}
    per_arm_speeded: dict[str, list[float]] = {a: [] for a in GAIN}
    drill_minus_generic: list[float] = []
    speeded_drill_minus_generic: list[float] = []
    for i in range(N_LEARNERS):
        skills = {a: _skill_after(seed + i, a) for a in GAIN}
        unt = {a: _accuracy(skills[a], speeded=False) for a in GAIN}
        spd = {a: _accuracy(skills[a], speeded=True) for a in GAIN}
        for a in GAIN:
            per_arm[a].append(unt[a])
            per_arm_speeded[a].append(spd[a])
        drill_minus_generic.append(unt["drill"] - unt["generic"])
        speeded_drill_minus_generic.append(spd["drill"] - spd["generic"])

    means = {a: sum(v) / len(v) for a, v in per_arm.items()}
    speeded_means = {a: sum(v) / len(v) for a, v in per_arm_speeded.items()}
    lo, hi = bootstrap_ci(drill_minus_generic, seed=seed)
    slo, shi = bootstrap_ci(speeded_drill_minus_generic, seed=seed)
    mean_diff = sum(drill_minus_generic) / len(drill_minus_generic)
    speeded_diff = sum(speeded_drill_minus_generic) / len(speeded_drill_minus_generic)
    ship = lo > 0.0
    detail = (
        f"held-out P(correct) on quantifier judgments (novel terms) at equal "
        f"{STUDY_EVENTS} events: drill {means['drill']:.3f} vs generic "
        f"{means['generic']:.3f} vs plain {means['plain']:.3f}; drill-generic "
        f"{mean_diff:+.3f} (95% CI {lo:+.3f}..{hi:+.3f}) -> "
        f"{'ship (CI excludes 0)' if ship else 'null at equal time (ship the drill OFF)'}; "
        f"SECONDARY speeded drill-generic {speeded_diff:+.3f} "
        f"(95% CI {slo:+.3f}..{shi:+.3f})"
    )
    return {
        "name": "quantifier",
        "passed": None,  # report-only
        "gate": False,
        "detail": detail,
        "means": {a: round(means[a], 4) for a in GAIN},
        "speeded_means": {a: round(speeded_means[a], 4) for a in GAIN},
        "drill_minus_generic": round(mean_diff, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "speeded_drill_minus_generic": round(speeded_diff, 4),
        "speeded_ci_low": round(slo, 4),
        "speeded_ci_high": round(shi, 4),
        "ship_recommended": ship,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
