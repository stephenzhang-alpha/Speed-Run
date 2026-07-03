# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Fatigue Curve validity eval (DECISION-round2 #10), a report arm.

Does modelling cumulative time-on-task actually PREDICT better? We generate
synthetic study sessions where accuracy decays with minutes-on-task (a per-learner
fatigue slope) AND items vary in difficulty (so we can check difficulty is not the
confound). We fit two predictors on the first two-thirds of each session and score
them on the HELD-OUT last third (where fatigue bites):

  * blind   -- ability (training accuracy) + item difficulty only; position-blind.
  * fatigue -- blind + a training-fit cumulative-minutes term.

Metric: pooled ROC AUC on held-out late-session items; report ``fatigue - blind``
dAUC with a bootstrap 95% CI over learners. The signal is called real only if
dAUC >= FATIGUE_MIN_DELTA_AUC with the CI excluding 0 (else the diagnostic
abstains, per lsat/fatigue.py). Synthetic; every rate is explicit.
"""

from __future__ import annotations

import math
import random

from eval import config
from eval.metrics import auc

N_LEARNERS = 300
SESSION_LEN = 18  # answers per session
DIFFS = (-1.0, 0.0, 1.0)


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _learner(rng: random.Random) -> list[dict]:
    """One session: items with a difficulty, a minutes-on-task, and an outcome
    drawn from sigmoid(ability - difficulty - fatigue*minutes)."""
    ability = rng.uniform(0.3, 1.3)
    fatigue = rng.uniform(0.01, 0.05)  # logit accuracy lost per minute (true decay)
    items = []
    for i in range(SESSION_LEN):
        minutes = i * 3.0  # ~3 min/item
        d = rng.choice(DIFFS)
        p = _sigmoid(ability - d - fatigue * minutes)
        items.append(
            {"minutes": minutes, "d": d, "y": 1.0 if rng.random() < p else 0.0}
        )
    return items


def _fit_and_score(items: list[dict]) -> tuple[list[float], list[float], list[float]]:
    """Held out every 3rd item (so held-out spans the whole session's minutes
    range, not just the tail) and train on the rest; return
    (blind_preds, fatigue_preds, ys) on the held-out items. This tests whether
    modelling time-on-task improves prediction of the within-session decline."""
    train = [t for i, t in enumerate(items) if i % 3 != 2]
    test = [t for i, t in enumerate(items) if i % 3 == 2]
    if not train or not test:
        return [], [], []
    base = sum(t["y"] for t in train) / len(train)  # ability proxy (training acc)
    # OLS slope of y on minutes over training (probability space) -> fatigue term.
    mm = sum(t["minutes"] for t in train) / len(train)
    sxx = sum((t["minutes"] - mm) ** 2 for t in train)
    b = (
        sum((t["minutes"] - mm) * (t["y"] - base) for t in train) / sxx
        if sxx > 1e-9
        else 0.0
    )
    blind, fat, ys = [], [], []
    for t in test:
        diff_adj = -0.12 * t["d"]  # harder items (d=+1) score lower, both models
        blind.append(base + diff_adj)
        fat.append(base + diff_adj + b * (t["minutes"] - mm))
        ys.append(t["y"])
    return blind, fat, ys


def _pooled_auc(learners: list[list[dict]], which: int) -> float:
    preds: list[float] = []
    ys: list[float] = []
    for items in learners:
        b, f, y = _fit_and_score(items)
        preds.extend(f if which == 1 else b)
        ys.extend(y)
    return auc(preds, ys) if preds else 0.5


def run(seed: int = config.RANDOM_SEED) -> dict:
    rng = random.Random(seed)
    learners = [_learner(rng) for _ in range(N_LEARNERS)]
    blind_auc = _pooled_auc(learners, 0)
    fatigue_auc = _pooled_auc(learners, 1)
    delta = fatigue_auc - blind_auc

    # Bootstrap over learners for a CI on the dAUC.
    boot = random.Random(seed + 7)
    deltas = []
    n = len(learners)
    for _ in range(400):
        sample = [learners[boot.randrange(n)] for _ in range(n)]
        deltas.append(_pooled_auc(sample, 1) - _pooled_auc(sample, 0))
    deltas.sort()
    lo = deltas[int(0.025 * len(deltas))]
    hi = deltas[min(len(deltas) - 1, int(0.975 * len(deltas)))]
    real = delta >= config.FATIGUE_MIN_DELTA_AUC and lo > 0.0
    detail = (
        f"held-out within-session AUC: fatigue-aware {fatigue_auc:.3f} vs "
        f"position-blind {blind_auc:.3f}; dAUC {delta:+.3f} "
        f"(95% CI {lo:+.3f}..{hi:+.3f}; min {config.FATIGUE_MIN_DELTA_AUC}) -> "
        f"{'signal is real' if real else 'abstain (below threshold or CI includes 0)'}"
    )
    return {
        "name": "fatigue",
        "passed": None,  # report-only
        "gate": False,
        "detail": detail,
        "blind_auc": round(blind_auc, 4),
        "fatigue_auc": round(fatigue_auc, 4),
        "delta_auc": round(delta, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "signal_real": real,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
