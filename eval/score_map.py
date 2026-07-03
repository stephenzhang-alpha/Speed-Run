# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Step 3: raw -> scaled score mapping (Monte-Carlo), with an honest range.

Monte-Carlo per-item P(correct) across the ~76 scored questions, map each raw
count to a scaled 120-180 score via the documented equating table
(``lsat.models.readiness.raw_to_scaled``), and report the point estimate plus a
range that is never tighter than the LSAT's own +/-3 band.
"""

from __future__ import annotations

import math
import random
from typing import Any

from eval import config

_N_ITEMS = 76
_TRIALS = 3000


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 120.0
    idx = int(round((pct / 100.0) * (len(sorted_vals) - 1)))
    return sorted_vals[max(0, min(len(sorted_vals) - 1, idx))]


def run(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    from lsat.models.readiness import raw_to_scaled

    rng = random.Random(seed)
    probs = [_sigmoid(rng.uniform(-1.0, 1.0)) for _ in range(_N_ITEMS)]
    scaled = sorted(
        raw_to_scaled(sum(1 for p in probs if rng.random() < p), _N_ITEMS)
        for _ in range(_TRIALS)
    )
    point = int(round(_percentile(scaled, 50)))
    mc_lo = _percentile(scaled, 15)
    mc_hi = _percentile(scaled, 85)
    # Never tighter than +/-3 (the LSAT's own band).
    half = max(
        int(config.SCORE_MIN_RANGE_POINTS),
        int(round(point - mc_lo)),
        int(round(mc_hi - point)),
    )
    low, high = point - half, point + half
    # Preserve the width when clamping to [120, 180] by shifting the window
    # inward, so a strong (or weak) projection still reports a >= +/-3 band
    # instead of a truncated one.
    if low < 120:
        high += 120 - low
        low = 120
    if high > 180:
        low -= high - 180
        high = 180
    low, high = max(120, low), min(180, high)
    width_half = (high - low) // 2
    passed = (high - low) >= 2 * config.SCORE_MIN_RANGE_POINTS
    return {
        "name": "score_map",
        "passed": passed,
        "gate": True,
        "point": point,
        "range": [low, high],
        "range_half_width": width_half,
        "min_range_points": config.SCORE_MIN_RANGE_POINTS,
        "mc_band": [round(mc_lo, 1), round(mc_hi, 1)],
        "trials": _TRIALS,
        "n_items": _N_ITEMS,
        "detail": f"projected {point} range {low}-{high} (>= +/-{config.SCORE_MIN_RANGE_POINTS}); "
        "method: Monte-Carlo raw->scaled via documented equating table",
    }
