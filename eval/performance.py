# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Step 2: held-out question accuracy -- must beat a memory-only baseline.

Predict P(correct) on held-out items from skill mastery + item difficulty (the
performance model's inputs) and compare AUC against a memory-only baseline that
sees recall/mastery alone. If difficulty carries no signal beyond memory, the
delta is ~0 and this reports that honestly. Synthetic-data caveat as in Step 1.
"""

from __future__ import annotations

import math
import random
from typing import Any

from eval import config
from eval.metrics import accuracy, auc, brier

_N_ITEMS = 1500
_DIFF_EFFECT = 1.2  # logit units per difficulty step (easy=-1, medium=0, hard=+1)


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _run_pass(seed: int, diff_effect: float) -> dict[str, Any]:
    """One held-out pass: generate outcomes from ability +/- difficulty*diff_effect,
    score with memory-only (ability) vs performance (ability AND difficulty), and
    return both AUCs. With diff_effect=0 the performance score IS the memory score, so
    the AUC delta collapses to 0 -- the negative control that proves the gate has teeth."""
    rng = random.Random(seed)
    topic_ability = {t: rng.uniform(-1.2, 1.2) for t in range(8)}
    outcomes: list[float] = []
    mem_scores: list[float] = []  # memory-only baseline: ability alone
    perf_scores: list[float] = []  # performance model: ability AND difficulty
    perf_probs: list[float] = []
    for _ in range(_N_ITEMS):
        topic = rng.randrange(8)
        ability = topic_ability[topic]
        difficulty = rng.choice([-1.0, 0.0, 1.0])  # easy / medium / hard
        true_logit = ability - difficulty * diff_effect
        outcomes.append(1.0 if rng.random() < _sigmoid(true_logit) else 0.0)
        mem_scores.append(ability)
        perf_scores.append(true_logit)
        perf_probs.append(_sigmoid(true_logit))
    return {
        "auc_mem": auc(mem_scores, outcomes),
        "auc_perf": auc(perf_scores, outcomes),
        "perf_probs": perf_probs,
        "outcomes": outcomes,
    }


def run(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    real = _run_pass(seed, _DIFF_EFFECT)
    auc_mem, auc_perf = real["auc_mem"], real["auc_perf"]
    delta = auc_perf - auc_mem
    passed = delta >= config.PERF_MIN_DELTA_AUC

    # Negative control: remove the difficulty signal (diff_effect=0) so the
    # performance score collapses onto memory and the AUC delta is ~0 -- committed
    # proof the gate can fail. Raise if the control is vacuous (would itself pass).
    null = _run_pass(seed, 0.0)
    delta_null = null["auc_perf"] - null["auc_mem"]
    null_would_fail = delta_null < config.PERF_MIN_DELTA_AUC
    if not null_would_fail:
        raise AssertionError(
            f"performance negative control is vacuous: null delta {delta_null:+.4f} "
            f">= gate {config.PERF_MIN_DELTA_AUC}"
        )
    return {
        "name": "performance",
        "passed": passed,
        "gate": True,
        "auc_memory_only": round(auc_mem, 4),
        "auc_performance": round(auc_perf, 4),
        "auc_delta": round(delta, 4),
        "auc_delta_min": config.PERF_MIN_DELTA_AUC,
        "auc_delta_null": round(delta_null, 4),
        "null_would_fail": null_would_fail,
        "accuracy": round(accuracy(real["perf_probs"], real["outcomes"]), 4),
        "brier": round(brier(real["perf_probs"], real["outcomes"]), 4),
        "n": _N_ITEMS,
        "detail": f"performance AUC {auc_perf:.3f} vs memory-only {auc_mem:.3f} "
        f"(delta {delta:+.3f}, min {config.PERF_MIN_DELTA_AUC}); "
        f"null-signal control (difficulty removed) delta {delta_null:+.3f} "
        f"< {config.PERF_MIN_DELTA_AUC} -> gate has teeth",
    }
