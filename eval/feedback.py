# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Elaborated-feedback ablation (DECISION-round2 #13), a report arm.

Three feedback styles, compared at **equal study TIME** (not equal item count),
because richer feedback costs seconds that could have bought more items -- the
honest trade the debate insisted on:

  * ``kr``   -- knowledge-of-result only (correct / incorrect). Cheapest per item.
  * ``kcr``  -- knowledge-of-correct-result + a single trap-family tip. This
                approximates the SHIPPED Feature 2 one-tap why-wrong.
  * ``ef``   -- the Elaborated Contrast Card (``lsat/contrast.py``): why the
                credited answer is credited + why the picked letter is a trap +
                the minimal edit. Richest, so it costs the most seconds/item and
                therefore does FEWER items in the same time.

Primary metric: held-out P(correct) on unseen same-trap-family items. We report
the **ef − kcr** difference with a bootstrap 95% CI over paired synthetic
learners; per the ruling the elaborated feedback should ship ONLY if that CI
excludes 0 at equal time. Reported either way (an honest negative is a result).

SIMULATION CAVEAT: synthetic learners; every rate is an explicit parameter below.
This proves the equal-time methodology, not a field effect. The chosen GAIN/COST
model an EF per-item advantage that survives the fewer-items time penalty, so this
run recommends ship; a larger time penalty or smaller gain gap would flip it to
the null branch (which is exactly why the decision is gated on the CI, not assumed).
"""

from __future__ import annotations

import math
import random

from eval import config
from eval.metrics import bootstrap_ci

# Equal study TIME budget per arm (seconds) and per-item feedback-reading cost.
# The budget is an exact multiple of every arm's cost (1680/12=140, /16=105,
# /20=84), so `int(budget/cost)` leaves no residual and each arm spends the SAME
# 1680s -- no rounding advantage to any arm (incl. the kcr comparison baseline).
TIME_BUDGET_S = 1680  # 28 min; divisible by all COST_S
COST_S = {"kr": 12.0, "kcr": 16.0, "ef": 20.0}  # ef reads a two-column contrast
# Per-reviewed-item ability gain (logit), with diminishing returns applied below.
# Richer feedback teaches more per item (elaborated feedback > KCR > KR), but the
# time budget lets the cheaper styles do more items -- the net is what we measure.
GAIN = {"kr": 0.10, "kcr": 0.15, "ef": 0.20}
N_LEARNERS = 400
DIFFICULTIES = (-1.0, 0.0, 1.0)
ARMS = ("kr", "kcr", "ef")
# Held-out items are UNSEEN same-trap items, so learned ability transfers only
# partially -- this keeps P(correct) off the ceiling and gives the effect honest
# spread (rather than everyone saturating at mastery).
TRANSFER = 0.6


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _simulate(seed: int, arm: str) -> float:
    """One synthetic learner through one feedback arm at equal study TIME.
    Returns held-out mean P(correct) on unseen same-trap items."""
    rng = random.Random(seed)
    ability = rng.uniform(-1.4, -0.2)
    n_items = int(TIME_BUDGET_S / COST_S[arm])
    g = GAIN[arm]
    for _ in range(n_items):
        # diminishing returns + per-item noise (a review is not uniformly useful).
        ability += g * rng.uniform(0.4, 1.6) * (1.0 - _sigmoid(ability))
    return sum(_sigmoid(TRANSFER * ability - d) for d in DIFFICULTIES) / len(
        DIFFICULTIES
    )


def run(seed: int = config.RANDOM_SEED) -> dict:
    per_arm: dict[str, list[float]] = {a: [] for a in ARMS}
    diffs_ef_kcr: list[float] = []
    for i in range(N_LEARNERS):
        # Paired: the same learner seed through every arm (isolates the feedback).
        vals = {a: _simulate(seed + i, a) for a in ARMS}
        for a in ARMS:
            per_arm[a].append(vals[a])
        diffs_ef_kcr.append(vals["ef"] - vals["kcr"])

    means = {a: sum(v) / len(v) for a, v in per_arm.items()}
    lo, hi = bootstrap_ci(diffs_ef_kcr, seed=seed)
    mean_diff = sum(diffs_ef_kcr) / len(diffs_ef_kcr)
    ship = lo > 0.0
    n_items = {a: int(TIME_BUDGET_S / COST_S[a]) for a in ARMS}
    detail = (
        f"held-out P(correct) at equal {TIME_BUDGET_S}s: "
        f"ef {means['ef']:.3f} ({n_items['ef']} items) vs "
        f"kcr {means['kcr']:.3f} ({n_items['kcr']} items) vs "
        f"kr {means['kr']:.3f} ({n_items['kr']} items); "
        f"ef-kcr {mean_diff:+.3f} (95% CI {lo:+.3f}..{hi:+.3f}) -> "
        f"{'ship (CI excludes 0)' if ship else 'null at equal time (CI includes 0) -- ship OFF'}"
    )
    return {
        "name": "feedback",
        "passed": None,  # report-only: an honest negative is a valid result
        "gate": False,
        "detail": detail,
        "means": {a: round(means[a], 4) for a in ARMS},
        "n_items_per_arm": n_items,
        "ef_minus_kcr": round(mean_diff, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "ship_recommended": ship,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
