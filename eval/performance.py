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


def run(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    rng = random.Random(seed)
    # a handful of topics with distinct latent ability
    topic_ability = {t: rng.uniform(-1.2, 1.2) for t in range(8)}

    outcomes: list[float] = []
    mem_scores: list[float] = []  # memory-only baseline: ability alone
    perf_scores: list[float] = []  # performance model: ability AND difficulty
    perf_probs: list[float] = []
    for _ in range(_N_ITEMS):
        topic = rng.randrange(8)
        ability = topic_ability[topic]
        difficulty = rng.choice([-1.0, 0.0, 1.0])  # easy / medium / hard
        true_logit = ability - difficulty * _DIFF_EFFECT
        outcomes.append(1.0 if rng.random() < _sigmoid(true_logit) else 0.0)
        mem_scores.append(ability)
        perf_scores.append(true_logit)
        perf_probs.append(_sigmoid(true_logit))

    auc_mem = auc(mem_scores, outcomes)
    auc_perf = auc(perf_scores, outcomes)
    delta = auc_perf - auc_mem
    passed = delta >= config.PERF_MIN_DELTA_AUC
    return {
        "name": "performance",
        "passed": passed,
        "gate": True,
        "auc_memory_only": round(auc_mem, 4),
        "auc_performance": round(auc_perf, 4),
        "auc_delta": round(delta, 4),
        "auc_delta_min": config.PERF_MIN_DELTA_AUC,
        "accuracy": round(accuracy(perf_probs, outcomes), 4),
        "brier": round(brier(perf_probs, outcomes), 4),
        "n": _N_ITEMS,
        "detail": f"performance AUC {auc_perf:.3f} vs memory-only {auc_mem:.3f} "
        f"(delta {delta:+.3f}, min {config.PERF_MIN_DELTA_AUC})",
    }
