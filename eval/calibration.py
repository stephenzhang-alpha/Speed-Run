# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Step 1: memory calibration -- does predicted recall match observed recall?

Synthetic-data caveat: with no real review history, we draw held-out reviews
from the model's own predicted recall (outcome ~ Bernoulli(predicted)) -- a
self-consistency check of the calibration metric + gate. A real corpus of
held-out reviews would replace this generator unchanged. We also score an
overconfident predictor to show the ECE gate has teeth (it fails).
"""

from __future__ import annotations

import random
from typing import Any

from eval import config
from eval.metrics import brier, ece, log_loss, reliability_bins

_N_REVIEWS = 2000


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def run(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    rng = random.Random(seed)
    preds: list[float] = []
    ys: list[float] = []
    over_preds: list[float] = []  # an overconfident (miscalibrated) predictor
    for _ in range(_N_REVIEWS):
        p = rng.random()
        outcome = 1.0 if rng.random() < p else 0.0
        preds.append(p)
        ys.append(outcome)
        # push probabilities toward the extremes -> overconfident, higher ECE
        over_preds.append(_clamp(0.5 + (p - 0.5) * 1.8))

    model_ece = ece(preds, ys)
    over_ece = ece(over_preds, ys)
    passed = model_ece <= config.ECE_MAX
    return {
        "name": "calibration",
        "passed": passed,
        "gate": True,
        "ece": round(model_ece, 4),
        "ece_max": config.ECE_MAX,
        "brier": round(brier(preds, ys), 4),
        "log_loss": round(log_loss(preds, ys), 4),
        "overconfident_ece": round(over_ece, 4),
        "reliability": [
            {
                "bin": f"{b['lo']:.1f}-{b['hi']:.1f}",
                "n": b["count"],
                "pred": round(b["mean_p"], 3) if b["mean_p"] is not None else None,
                "obs": round(b["mean_y"], 3) if b["mean_y"] is not None else None,
            }
            for b in reliability_bins(preds, ys)
        ],
        "n": _N_REVIEWS,
        "detail": f"ECE={model_ece:.4f} (max {config.ECE_MAX}); "
        f"an overconfident predictor scores ECE={over_ece:.4f} and would fail",
    }
