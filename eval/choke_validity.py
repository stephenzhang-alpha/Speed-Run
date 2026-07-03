# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Choke-Index diagnostic-validity eval (DECISION-round2 #24).

The shipped unpaired Choke Index subtracts timed accuracy from untimed accuracy
over *different item pools*, so a difficulty mismatch between the items a learner
happened to answer timed vs untimed shows up as a spurious "choke." The paired
within-item estimator (``lsat.pacing.paired_choke_index``) instead uses only
items answered BOTH ways, takes the per-item delta, and bootstraps a 95% CI --
raising a flag only when the CI lower bound > 0.

This is a **report + gate** on the estimator's validity, not a learning claim. On
seeded synthetic learners with a KNOWN ground-truth pressure penalty we check:

  (a) CI coverage -- the paired CI covers the true per-student mean delta at least
      ``CHOKE_CI_COVERAGE_MIN`` of the time (a nominal-95% property); and
  (b) false positives -- when the true penalty is 0 but the timed pool is harder
      than the untimed pool, the paired estimator flags "choke" at most
      ``CHOKE_FALSE_POSITIVE_MAX`` of the time, and demonstrably LESS often than
      the unpaired aggregate (which is fooled by the difficulty confound).

Everything is seeded and pure (no collection, no network).
"""

from __future__ import annotations

import math
import random

from eval import config
from lsat.events import PerformanceEvent
from lsat.pacing import MIN_CONFIDENT_FLAG_ITEMS, _pair_by_item, _paired_estimate

_NODE = "lr.weaken"


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _ev(item_id: str, correct: bool, phase: str) -> PerformanceEvent:
    """A minimal synthetic event; the paired estimator reads phase/item_id/correct
    (and list order for "most recent"), not the HLC, so a trivial stamp suffices."""
    return PerformanceEvent(
        note_id=0,
        item_id=item_id,
        node_ids=[_NODE],
        correct=correct,
        response_ms=1,
        hlc="0000000000000:000000:d",
        device_id="d",
        phase=phase,
    )


def _paired_deltas(events: list[PerformanceEvent]) -> list[int]:
    paired = _pair_by_item(events)
    return [
        (1 if b.correct else 0) - (1 if t.correct else 0) for t, b in paired.values()
    ]


def _student_events(
    rng: random.Random, n_items: int, penalty_logit: float, ability: float = 0.4
) -> tuple[list[PerformanceEvent], float]:
    """A learner who answered ``n_items`` both timed and untimed, with a per-item
    pressure penalty ``penalty_logit`` (0 = no choke). Returns (events, true mean
    delta = mean_i[P(untimed correct) - P(timed correct)])."""
    events: list[PerformanceEvent] = []
    true = 0.0
    for i in range(n_items):
        diff = rng.uniform(-1.0, 1.0)
        p_un = _sigmoid(ability - diff)
        p_ti = _sigmoid(ability - diff - penalty_logit)
        true += p_un - p_ti
        iid = f"it{i}"
        events.append(_ev(iid, rng.random() < p_ti, "timed"))
        events.append(_ev(iid, rng.random() < p_un, "blind"))
    return events, true / n_items


# Validate at the OPERATING floor -- the fewest paired items at which the product
# raises a *confident* choke flag (lsat.pacing.MIN_CONFIDENT_FLAG_ITEMS) -- so the
# CI-coverage guarantee is tested where it actually matters, not at a comfortable
# large n. (The percentile bootstrap under-covers below this floor, which is why
# the product does not flag there.)
def _ci_coverage(
    seed: int, trials: int = 300, n_items: int = MIN_CONFIDENT_FLAG_ITEMS
) -> float:
    rng = random.Random(seed)
    penalties = [0.0, 0.5, 1.0]
    covered = 0
    for t in range(trials):
        events, true_delta = _student_events(rng, n_items, penalties[t % 3])
        est = _paired_estimate(_paired_deltas(events), seed=seed + t)
        if est["ci_low"] <= true_delta <= est["ci_high"]:
            covered += 1
    return covered / trials


def _false_positive_rates(
    seed: int, trials: int = 300, n_overlap: int = 24, n_only: int = 24
) -> tuple[float, float]:
    """Penalty=0 with difficulty-mismatched pools: overlap items are medium, the
    timed-only pool is HARD and the untimed-only pool is EASY. Returns
    (paired_flag_rate, unpaired_flag_rate)."""
    rng = random.Random(seed + 991)
    paired_fp = 0
    unpaired_fp = 0
    for _ in range(trials):
        events: list[PerformanceEvent] = []
        # overlap items answered BOTH ways (medium difficulty, no real choke)
        for i in range(n_overlap):
            diff = rng.uniform(-0.4, 0.4)
            p = _sigmoid(0.4 - diff)
            events.append(_ev(f"ov{i}", rng.random() < p, "timed"))
            events.append(_ev(f"ov{i}", rng.random() < p, "blind"))
        # timed-only HARD items (drag timed accuracy down)
        p_hard = _sigmoid(0.4 - 1.6)
        for i in range(n_only):
            events.append(_ev(f"th{i}", rng.random() < p_hard, "timed"))
        # untimed-only EASY items (pull untimed accuracy up)
        p_easy = _sigmoid(0.4 + 1.6)
        for i in range(n_only):
            events.append(_ev(f"ue{i}", rng.random() < p_easy, "blind"))

        est = _paired_estimate(_paired_deltas(events), seed=seed)
        if est["flag"]:
            paired_fp += 1

        # Unpaired aggregate = mean(untimed correct) - mean(timed correct) over the
        # WHOLE mismatched pool, flagged like the shipped estimator (> 0.05).
        timed = [e.correct for e in events if e.phase == "timed"]
        untimed = [e.correct for e in events if e.phase in ("blind", "relaxed")]
        un_acc = sum(untimed) / len(untimed)
        ti_acc = sum(timed) / len(timed)
        if (un_acc - ti_acc) > 0.05:
            unpaired_fp += 1
    return paired_fp / trials, unpaired_fp / trials


def run(seed: int = config.RANDOM_SEED) -> dict:
    coverage = _ci_coverage(seed)
    paired_fp, unpaired_fp = _false_positive_rates(seed)
    passed = (
        coverage >= config.CHOKE_CI_COVERAGE_MIN
        and paired_fp <= config.CHOKE_FALSE_POSITIVE_MAX
        and unpaired_fp > paired_fp
    )
    detail = (
        f"paired CI coverage {coverage:.2f} (min {config.CHOKE_CI_COVERAGE_MIN}); "
        f"false-positive under difficulty-mismatched pools: paired {paired_fp:.2f} "
        f"(max {config.CHOKE_FALSE_POSITIVE_MAX}) vs unpaired {unpaired_fp:.2f}"
    )
    return {
        "name": "choke_validity",
        "passed": passed,
        "gate": True,
        "detail": detail,
        "ci_coverage": round(coverage, 4),
        "false_positive_paired": round(paired_fp, 4),
        "false_positive_unpaired": round(unpaired_fp, 4),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
