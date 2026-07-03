# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Stem-Polarity Micro-Drill ablation (DECISION-round4 #13), a report arm.

At EQUAL study events, does drilling stem polarity (EXCEPT / LEAST / negated,
graded deterministically by ``lsat.stem_polarity``) lift held-out accuracy on
**unseen inverted-stem items** more than generic review?

Three arms, paired per learner (drill / generic / plain). PRIMARY held-out metric:
P(correct) on a finite bank of unseen EXCEPT/LEAST/negated items instantiated with
novel surface tasks -- measured over a FINITE bank so the estimate carries the
realistic binomial noise a razor-thin deterministic mean would hide (this is why
the CI here is a believable width, not +/-0.001). SECONDARY: speeded accuracy
(the automatization payoff -- an automatic stem->task-set mapping is resource-
independent, so it survives the fatigue/time-pressure moment the lapse strikes).

Report ``drill - generic`` with a bootstrap 95% CI; ship the drill ON only if the
CI excludes 0; report even if null. Per-event skill gain is an EXPLICIT synthetic
parameter, not evidence -- and it is set HIGHER than the reasoning-drill evals
because polarity detection is a narrow mapping that automatizes fast.

Scope note: this is a synthetic IRT SIMULATION of the learning effect; it does not
route items through the real ``lsat.stem_polarity`` classifier (whose determinism +
fail-closed behavior is validated by that module's own self-test). The positive CI
here is therefore a consequence of the disclosed ``GAIN`` assumption -- it
demonstrates the equal-study-time + bootstrap-CI *mechanism*, and would be replaced
by a live cohort. It is deliberately report-only (no gate rides on it).
"""

from __future__ import annotations

import math
import random

from eval import config
from eval.metrics import bootstrap_ci

N_LEARNERS = 300
STUDY_EVENTS = 60
N_HELDOUT = 24  # finite unseen-stem bank -> realistic binomial noise on each learner
DIFFICULTIES = (-0.8, 0.0, 0.8)
# Polarity detection is a narrow, automatizable mapping, so the targeted drill
# gains FAST per event (higher than the reasoning drills); generic review touches
# it only incidentally. Explicit synthetic parameters, not evidence.
GAIN = {"drill": 0.22, "generic": 0.10, "plain": 0.07}
SPEED_PENALTY = 0.5  # ability haircut when answering under time pressure


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _skill_after(rng: random.Random, arm: str) -> float:
    skill = rng.uniform(-1.4, -0.3)  # start weak at catching inverted stems
    g = GAIN[arm]
    for _ in range(STUDY_EVENTS):
        skill += g * rng.uniform(0.6, 1.4) * (1.0 - _sigmoid(skill))
    return skill


def _heldout_accuracy(rng: random.Random, skill: float, *, speeded: bool) -> float:
    """Fraction correct over a FINITE unseen-stem bank (binomial noise), so the
    per-learner estimate has realistic variance."""
    ability = 0.8 * skill - (SPEED_PENALTY if speeded else 0.0)
    correct = 0
    for i in range(N_HELDOUT):
        d = DIFFICULTIES[i % len(DIFFICULTIES)]
        if rng.random() < _sigmoid(ability - d):
            correct += 1
    return correct / N_HELDOUT


def run(seed: int = config.RANDOM_SEED) -> dict:
    per_arm: dict[str, list[float]] = {a: [] for a in GAIN}
    drill_minus_generic: list[float] = []
    speeded_diff: list[float] = []
    for i in range(N_LEARNERS):
        # a fresh RNG per learner keeps arms paired on the same skill draws + bank
        skills = {}
        for a in GAIN:
            skills[a] = _skill_after(random.Random(seed + i), a)
        unt = {}
        spd = {}
        for a in GAIN:
            unt[a] = _heldout_accuracy(
                random.Random(seed + 5000 + i), skills[a], speeded=False
            )
            spd[a] = _heldout_accuracy(
                random.Random(seed + 9000 + i), skills[a], speeded=True
            )
            per_arm[a].append(unt[a])
        drill_minus_generic.append(unt["drill"] - unt["generic"])
        speeded_diff.append(spd["drill"] - spd["generic"])

    means = {a: sum(v) / len(v) for a, v in per_arm.items()}
    lo, hi = bootstrap_ci(drill_minus_generic, seed=seed)
    slo, shi = bootstrap_ci(speeded_diff, seed=seed)
    mean_diff = sum(drill_minus_generic) / len(drill_minus_generic)
    speeded_mean = sum(speeded_diff) / len(speeded_diff)
    ship = lo > 0.0
    detail = (
        f"held-out P(correct) on unseen inverted-stem items at equal "
        f"{STUDY_EVENTS} events ({N_HELDOUT}-item bank): drill {means['drill']:.3f} "
        f"vs generic {means['generic']:.3f} vs plain {means['plain']:.3f}; "
        f"drill-generic {mean_diff:+.3f} (95% CI {lo:+.3f}..{hi:+.3f}) -> "
        f"{'ship (CI excludes 0)' if ship else 'null at equal time (ship OFF)'}; "
        f"SECONDARY speeded drill-generic {speeded_mean:+.3f} "
        f"(95% CI {slo:+.3f}..{shi:+.3f})"
    )
    return {
        "name": "stem_polarity",
        "passed": None,  # report-only
        "gate": False,
        "detail": detail,
        "means": {a: round(means[a], 4) for a in GAIN},
        "drill_minus_generic": round(mean_diff, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "speeded_drill_minus_generic": round(speeded_mean, 4),
        "ship_recommended": ship,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
