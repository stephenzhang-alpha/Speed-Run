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
    # A width-only check is tautological: the +/-3 floor above guarantees
    # (high-low) >= 2*SCORE_MIN_RANGE_POINTS for ANY mapping, so it can never fail
    # and never exercises the shipped raw_to_scaled. Gate on what the floor does NOT
    # guarantee, so a broken mapping (constant, inverted, or off-scale) is caught:
    #  - responsive:  more correct answers must yield a strictly higher score;
    #  - in_scale:    every score (endpoints, point, and the reported band) in 120-180;
    #  - band_ok:     the Monte-Carlo band brackets the point (not inverted);
    #  - width_ok:    the reported range still honors the >= +/-3 floor.
    # Check the WHOLE mapping, not just the endpoints: every additional correct
    # answer must not lower the score (non-decreasing), and more-correct must beat
    # fewer-correct overall (strict at the ends). Non-decreasing (rather than
    # strictly increasing everywhere) tolerates legitimate plateaus in the equating
    # table while still catching a middle dip / inversion an endpoints-only check missed.
    scores_by_raw = [raw_to_scaled(r, _N_ITEMS) for r in range(_N_ITEMS + 1)]
    lo_score, hi_score = scores_by_raw[0], scores_by_raw[-1]

    def _responsive(scores: list[float]) -> bool:
        return scores[0] < scores[-1] and all(
            a <= b for a, b in zip(scores, scores[1:])
        )

    responsive = _responsive(scores_by_raw)
    in_scale = all(120 <= s <= 180 for s in (point, low, high, lo_score, hi_score))
    band_ok = mc_lo <= point <= mc_hi
    width_ok = (high - low) >= 2 * config.SCORE_MIN_RANGE_POINTS
    passed = responsive and in_scale and band_ok and width_ok
    # Committed gate-teeth: a constant or inverted equating table must FAIL the
    # responsive check (so a reviewer sees the gate is not vacuous, from the snapshot).
    _const = _responsive([150.0] * (_N_ITEMS + 1))
    _inverted = _responsive([180.0 - (s - 120.0) for s in scores_by_raw])
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
        "endpoints": [lo_score, hi_score],
        "n_monotone_checks": _N_ITEMS,
        # negative controls: broken equating tables that MUST fail `responsive`.
        "controls": {
            "shipped_responsive": responsive,
            "constant_responsive": _const,
            "inverted_responsive": _inverted,
        },
        "detail": f"projected {point} range {low}-{high} (>= +/-{config.SCORE_MIN_RANGE_POINTS}); "
        f"endpoints {lo_score}->{hi_score}; gate-teeth: constant & inverted equating "
        f"tables both fail responsive ({_const}, {_inverted}), shipped passes ({responsive}); "
        "method: Monte-Carlo raw->scaled via documented equating table",
    }
