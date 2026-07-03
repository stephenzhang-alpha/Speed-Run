# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""If-Then Study Plan adherence eval (DECISION-round2 #4), a report arm.

**Mechanics/plumbing check ONLY.** This does NOT prove the feature works -- the
adherence lift is held UNPROVEN until a live-cohort A/B. It demonstrates the
equal-comparison methodology on synthetic learners:

  * PRIMARY -- 14-day planned-session completion rate, plan vs no-plan, paired per
    learner; the bootstrap 95% CI on the rate difference is reported (an
    implementation-intention lift is an EXPLICIT parameter, not evidence).
  * GUARDRAIL (the honest anti-double-count) -- per-item ACCURACY is drawn from
    the same distribution regardless of plan (a plan changes whether you show up,
    not how well you reason), so its plan-vs-no-plan CI must INCLUDE 0. If it did
    not, the sim would be smuggling a score claim into an adherence feature.

Synthetic; every rate is explicit. Report-only (no hard gate).
"""

from __future__ import annotations

import random

from eval import config
from eval.metrics import bootstrap_ci

N_LEARNERS = 400
WINDOW_DAYS = 14
# Implementation-intention lift on the daily show-up probability (an EXPLICIT
# modelling parameter loosely scaled from the literature's medium-large d; NOT a
# measured result). The plan raises adherence, capped at 1.0.
PLAN_LIFT = 0.15


def run(seed: int = config.RANDOM_SEED) -> dict:
    rng = random.Random(seed)
    completion_diffs: list[float] = []
    accuracy_diffs: list[float] = []
    plan_rates: list[float] = []
    noplan_rates: list[float] = []
    for _ in range(N_LEARNERS):
        base_p = rng.uniform(0.30, 0.70)  # this learner's baseline daily-study prob
        plan_p = min(1.0, base_p + PLAN_LIFT)
        # Paired 14-day completion under each regime (independent day draws).
        plan_done = sum(1 for _ in range(WINDOW_DAYS) if rng.random() < plan_p)
        noplan_done = sum(1 for _ in range(WINDOW_DAYS) if rng.random() < base_p)
        pr, npr = plan_done / WINDOW_DAYS, noplan_done / WINDOW_DAYS
        plan_rates.append(pr)
        noplan_rates.append(npr)
        completion_diffs.append(pr - npr)
        # GUARDRAIL: accuracy is independent of the plan -- same distribution, two
        # independent draws -> the difference should straddle 0 (no cannibalization).
        acc_ability = rng.uniform(0.45, 0.85)
        a_plan = sum(1 for _ in range(20) if rng.random() < acc_ability) / 20
        a_noplan = sum(1 for _ in range(20) if rng.random() < acc_ability) / 20
        accuracy_diffs.append(a_plan - a_noplan)

    comp_mean = sum(completion_diffs) / len(completion_diffs)
    comp_lo, comp_hi = bootstrap_ci(completion_diffs, seed=seed)
    acc_mean = sum(accuracy_diffs) / len(accuracy_diffs)
    acc_lo, acc_hi = bootstrap_ci(accuracy_diffs, seed=seed + 1)

    completion_lift = comp_lo > 0.0
    guardrail_ok = acc_lo <= 0.0 <= acc_hi  # accuracy CI must include 0
    detail = (
        f"MECHANICS ONLY (unproven until a live cohort): planned-completion rate "
        f"plan {sum(plan_rates) / len(plan_rates):.2f} vs no-plan "
        f"{sum(noplan_rates) / len(noplan_rates):.2f}; diff {comp_mean:+.3f} "
        f"(95% CI {comp_lo:+.3f}..{comp_hi:+.3f}, excludes 0={completion_lift}); "
        f"guardrail accuracy diff {acc_mean:+.3f} (95% CI {acc_lo:+.3f}..{acc_hi:+.3f}, "
        f"includes 0={guardrail_ok} -> no score cannibalization)"
    )
    return {
        "name": "adherence",
        "passed": None,  # report-only; the real claim needs a live A/B
        "gate": False,
        "detail": detail,
        "completion_diff": round(comp_mean, 4),
        "completion_ci": [round(comp_lo, 4), round(comp_hi, 4)],
        "completion_lift_ci_excludes_0": completion_lift,
        "accuracy_diff": round(acc_mean, 4),
        "accuracy_ci": [round(acc_lo, 4), round(acc_hi, 4)],
        "guardrail_no_cannibalization": guardrail_ok,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
