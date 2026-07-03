# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Exam-Day Retrievability Targeting eval (DECISION-round2 #7), a report arm.

At EQUAL review count, does allocating reviews by the deadline-aware
desired-retention ramp (consolidate the cards that would decay below target by
exam day, weighted by exam weight) beat a fixed-retention baseline (review
whatever is below 0.9 today, exam date ignored)? Metric: weighted mean projected
retrievability ON exam day.

Two pre-registered arms plus the honest null:
  * deadline  -- rank by exam_weight * (DR(days_left) - projected_examday_R)
  * fixed     -- rank by (0.9 - current_R)   [the exam-blind baseline]
  * null      -- a learner with enough daily budget to review EVERY card daily;
                 the two policies then converge (no benefit) -- reported so the
                 effect is not overstated.

Reallocation, not new learning: the same number of reviews is spent either way.
Synthetic; every rate is an explicit parameter.
"""

from __future__ import annotations

import random

from eval import config
from eval.metrics import bootstrap_ci
from lsat.exam_schedule import (
    deadline_desired_retention,
    project_examday_retrievability,
)

N_CARDS = 60
DAYS = 28
DAILY_BUDGET = 4  # genuinely scarce (~2 reviews/card total) -> timing matters
NULL_DAILY_BUDGET = N_CARDS  # enough to review everything daily -> policies tie
GROWTH = 1.45  # stability multiplier on a successful review (kept modest)
MAX_STABILITY = 120.0
N_LEARNERS = 300
_INIT_STABILITY = (1.0, 4.0)  # start low so cards can decay below target


def _weighted_examday_score(cards: list[dict], days_left_at_end: int = 0) -> float:
    """Weighted mean projected exam-day retrievability over the cards."""
    wsum = sum(c["w"] for c in cards) or 1.0
    total = 0.0
    for c in cards:
        elapsed = days_left_at_end + (DAYS - c["last"])  # days from last review to exam
        total += c["w"] * project_examday_retrievability(c["s"], max(0, elapsed))
    return total / wsum


def _examday_r(stability: float, last_review_day: int) -> float:
    return project_examday_retrievability(stability, max(0, DAYS - last_review_day))


def _simulate(seed: int, policy: str, daily_budget: int) -> float:
    """Both policies spend EXACTLY ``daily_budget`` reviews every day (equal
    review count). They differ only in WHICH cards they spend them on:
      * deadline -- the SHIPPED consolidation ranking (lsat.exam_schedule.
                    build_consolidation_queue): exam_weight * (DR(days_left) -
                    projected_examday_R), so this eval validates the actual
                    heuristic, not a metric-optimizing greedy;
      * fixed    -- exam-blind: refresh the cards most decayed right now.
    """
    rng = random.Random(seed)
    cards = [
        {"w": rng.uniform(0.2, 1.0), "s": rng.uniform(*_INIT_STABILITY), "last": 0}
        for _ in range(N_CARDS)
    ]
    budget = min(daily_budget, N_CARDS)
    for t in range(1, DAYS + 1):
        days_left = DAYS - t
        if policy == "deadline":
            # SHIPPED ranking: exam_weight * (deadline target - projected exam-day R).
            dr = deadline_desired_retention(days_left)

            def key(c: dict, _dr: float = dr) -> float:
                return c["w"] * max(0.0, _dr - _examday_r(c["s"], c["last"]))
        else:  # fixed: review whatever is most decayed NOW (exam date ignored)

            def key(c: dict) -> float:
                return -project_examday_retrievability(c["s"], t - c["last"])

        ranked = sorted(cards, key=key, reverse=True)
        for c in ranked[:budget]:  # always spend the full budget (equal reviews)
            c["s"] = min(MAX_STABILITY, c["s"] * GROWTH)
            c["last"] = t
    return _weighted_examday_score(cards)


def run(seed: int = config.RANDOM_SEED) -> dict:
    deadline_vals, fixed_vals, null_diffs = [], [], []
    diffs = []
    for i in range(N_LEARNERS):
        d = _simulate(seed + i, "deadline", DAILY_BUDGET)
        f = _simulate(seed + i, "fixed", DAILY_BUDGET)
        deadline_vals.append(d)
        fixed_vals.append(f)
        diffs.append(d - f)
        # null: same learner, both policies with budget >= N -> should tie
        nd = _simulate(seed + i, "deadline", NULL_DAILY_BUDGET)
        nf = _simulate(seed + i, "fixed", NULL_DAILY_BUDGET)
        null_diffs.append(nd - nf)

    mean_d = sum(deadline_vals) / len(deadline_vals)
    mean_f = sum(fixed_vals) / len(fixed_vals)
    mean_diff = sum(diffs) / len(diffs)
    lo, hi = bootstrap_ci(diffs, seed=seed)
    null_mean = sum(null_diffs) / len(null_diffs)
    null_lo, null_hi = bootstrap_ci(null_diffs, seed=seed)
    wins = lo > 0.0
    detail = (
        f"weighted exam-day retrievability at equal reviews ({DAILY_BUDGET}/day x "
        f"{DAYS}d, {N_CARDS} cards): deadline {mean_d:.3f} vs fixed {mean_f:.3f}; "
        f"delta {mean_diff:+.3f} (95% CI {lo:+.3f}..{hi:+.3f})"
        f"{' -> deadline-aware wins' if wins else ' (CI includes 0)'}; "
        f"daily-studier null delta {null_mean:+.3f} "
        f"(95% CI {null_lo:+.3f}..{null_hi:+.3f})"
    )
    return {
        "name": "exam_schedule",
        "passed": None,  # report-only
        "gate": False,
        "detail": detail,
        "deadline_mean": round(mean_d, 4),
        "fixed_mean": round(mean_f, 4),
        "delta": round(mean_diff, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "deadline_wins": wins,
        "daily_studier_null_delta": round(null_mean, 4),
        "daily_studier_null_ci": [round(null_lo, 4), round(null_hi, 4)],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
