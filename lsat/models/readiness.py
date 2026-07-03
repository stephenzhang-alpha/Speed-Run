# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Readiness model: a projected 120-180 LSAT score with an honest range.

PRD section 5.3 / section 12 step 3. We Monte-Carlo the ~76-question scored mix
(50 LR + 26 RC, weighted by the taxonomy), drawing per-item correctness from the
performance model, sum to a raw score, map raw -> scaled via a *documented
equating-style table* (a labelled approximation -- LSAC equates per form with no
fixed formula), and report the resulting distribution.

Two hard rules from the PRD are enforced here, not left to the UI:

- **Give-up rule (section 5.4):** no number until ALL hold -- >=150 graded items,
  >=60% LR question-type coverage + >=1 graded item in every RC type, >=40 timed
  items, and held-out calibration ECE below the taxonomy threshold. Otherwise we
  return the abstaining shape (what's missing + the best next thing to study).
- **Honesty contract (section 5.3):** the range is never tighter than +/-3 (the
  LSAT's own band), and a number is emitted ONLY when all eight required display
  fields are populated. Any gap falls back to abstaining -- never a bare guess.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Any

from lsat.events import read_events
from lsat.models.performance import PerformanceModel
from lsat.models.projections import append_projection, track_record
from lsat.taxonomy import Taxonomy

if TYPE_CHECKING:
    from anki.collection import Collection

DEFAULT_TRIALS = 2000
DEFAULT_SEED = 1234

# Documented equating-style approximation (PRD section 18.2): fraction of raw
# items correct -> representative scaled score. Monotonic; interpolated linearly.
# This is a labelled approximation, NOT a precise per-form conversion.
_EQUATING_ANCHORS: list[tuple[float, float]] = [
    (0.00, 120.0),
    (0.20, 125.0),
    (0.35, 132.0),
    (0.50, 143.0),
    (0.62, 151.0),
    (0.72, 157.0),
    (0.80, 162.0),
    (0.88, 167.0),
    (0.94, 172.0),
    (0.98, 176.0),
    (1.00, 180.0),
]


def raw_to_scaled(raw: int, total: int) -> float:
    """Map a raw correct count to a scaled 120-180 score (documented approx.)."""
    if total <= 0:
        return 120.0
    frac = max(0.0, min(1.0, raw / total))
    anchors = _EQUATING_ANCHORS
    for i in range(1, len(anchors)):
        f0, s0 = anchors[i - 1]
        f1, s1 = anchors[i]
        if frac <= f1:
            span = f1 - f0
            t = 0.0 if span <= 0 else (frac - f0) / span
            return s0 + t * (s1 - s0)
    return anchors[-1][1]


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 120.0
    idx = int(round((pct / 100.0) * (len(sorted_values) - 1)))
    return sorted_values[max(0, min(len(sorted_values) - 1, idx))]


def _difficulty_pool(col: Collection) -> list[str]:
    from lsat.models.performance import _difficulty_map

    pool = list(_difficulty_map(col).values())
    return pool or ["medium"]


def _weighted_choice(
    rng: random.Random, items: list, weights: list[float], total: float
):
    r = rng.random() * total
    upto = 0.0
    for item, w in zip(items, weights):
        upto += w
        if r <= upto:
            return item
    return items[-1]


def _student_overconfidence(col: Collection) -> float | None:
    """The student's measured overconfidence index (mean stated confidence -
    actual accuracy) from the one-tap ratings, or None while unmeasurable."""
    from lsat.models.calibration import build_calibration

    cal = build_calibration(col)
    if not cal.get("available"):
        return None
    value = cal.get("overconfidence_index")
    return float(value) if value is not None else None


def give_up_status(
    col: Collection, tax: Taxonomy, model: PerformanceModel
) -> dict[str, Any]:
    """Evaluate the give-up gates (PRD section 5.4 + D3).

    Beyond the original four: abstain when the *student's* measured
    overconfidence is too high to trust a point estimate (enforced only once
    calibration is measurable -- we cannot call an unmeasured student
    miscalibrated), and when the deck covers too little of the primitive
    taxonomy (A3 -- a vocabulary-only deck must not read as "ready").
    """
    gu = tax.give_up.readiness
    events = read_events(col)
    n_graded = len(events)
    n_timed = sum(1 for e in events if e.response_ms > 0)

    min_cov = tax.coverage.min_graded_items_to_count
    lr_qts = [t for t in tax.question_types if t.section == "lr"]
    rc_qts = [t for t in tax.question_types if t.section == "rc"]
    lr_covered = [t for t in lr_qts if model.counts.get(t.id, (0, 0))[0] >= min_cov]
    lr_cov = len(lr_covered) / len(lr_qts) if lr_qts else 0.0
    rc_missing = [t for t in rc_qts if model.counts.get(t.id, (0, 0))[0] < 1]
    all_qts = tax.question_types
    covered_all = [t for t in all_qts if model.counts.get(t.id, (0, 0))[0] >= min_cov]
    coverage_pct = 100.0 * len(covered_all) / len(all_qts) if all_qts else 0.0
    ece = model.calibration.get("ece")
    overconfidence = _student_overconfidence(col)

    from lsat.primitives import primitive_coverage

    prim_pct = primitive_coverage(col, tax)["overall_pct"] / 100.0

    ok_graded = n_graded >= gu.min_graded_performance_items
    ok_lr = lr_cov >= gu.min_lr_question_type_coverage
    ok_rc = not rc_missing
    ok_timed = n_timed >= gu.min_timed_items
    ok_calib = ece is not None and ece <= gu.max_heldout_calibration_ece
    # Only enforceable once measurable; underconfidence never blocks.
    ok_student = (
        overconfidence is None or overconfidence <= gu.max_student_overconfidence
    )
    ok_prim = prim_pct >= gu.min_primitive_coverage

    missing: list[str] = []
    if not ok_graded:
        missing.append(
            f"{gu.min_graded_performance_items}+ graded performance items "
            f"(have {n_graded})"
        )
    if not ok_lr:
        missing.append(
            f"{int(gu.min_lr_question_type_coverage * 100)}%+ LR question-type "
            f"coverage (have {lr_cov * 100:.0f}%)"
        )
    if not ok_rc:
        missing.append(
            f"1+ graded item in every RC question type "
            f"({len(rc_qts) - len(rc_missing)}/{len(rc_qts)})"
        )
    if not ok_timed:
        missing.append(f"{gu.min_timed_items}+ timed items (have {n_timed})")
    if not ok_calib:
        have = "n/a" if ece is None else f"{ece:.3f}"
        missing.append(
            f"held-out calibration ECE at or below {gu.max_heldout_calibration_ece} "
            f"(have {have})"
        )
    if not ok_student:
        missing.append(
            f"student overconfidence at or below {gu.max_student_overconfidence:+.2f} "
            f"(measured {overconfidence:+.2f} -- confident answers are outrunning "
            "accuracy, so a point estimate would overstate readiness)"
        )
    if not ok_prim:
        missing.append(
            f"{int(gu.min_primitive_coverage * 100)}%+ of the primitive taxonomy "
            f"covered by the deck (have {prim_pct * 100:.0f}%)"
        )

    return {
        "passed": ok_graded
        and ok_lr
        and ok_rc
        and ok_timed
        and ok_calib
        and ok_student
        and ok_prim,
        "missing": missing,
        "n_graded": n_graded,
        "n_timed": n_timed,
        "lr_coverage": lr_cov,
        "coverage_pct": coverage_pct,
        "ece": ece,
        "student_overconfidence": overconfidence,
        "primitive_coverage_pct": round(prim_pct * 100.0, 1),
    }


def monte_carlo(
    col: Collection,
    tax: Taxonomy,
    model: PerformanceModel,
    *,
    trials: int = DEFAULT_TRIALS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any] | None:
    """Monte-Carlo the scored mix -> raw -> scaled distribution + range (>=+/-3)."""
    rng = random.Random(seed)
    diff_pool = _difficulty_pool(col)

    # Precompute the per-section question-type mix and cache P(correct) per
    # (node, difficulty) so the inner trial loop is cheap.
    sections: list[tuple[list, list[float], float, int]] = []
    total_items = 0
    p_cache: dict[tuple[str, str], float] = {}
    for section in tax.sections:
        qts = [t for t in tax.question_types if t.section == section.id]
        if not qts:
            continue
        weights = [max(t.within_section_weight, 1e-9) for t in qts]
        sections.append((qts, weights, sum(weights), section.scored_questions_estimate))
        total_items += section.scored_questions_estimate
        for t in qts:
            for diff in set(diff_pool):
                p_cache[(t.id, diff)] = model.predict(t.id, diff, 0.0)
    if total_items <= 0:
        return None

    scaled: list[float] = []
    for _ in range(trials):
        raw = 0
        for qts, weights, total_w, n_items in sections:
            for _ in range(n_items):
                node = _weighted_choice(rng, qts, weights, total_w)
                diff = rng.choice(diff_pool)
                if rng.random() < p_cache[(node.id, diff)]:
                    raw += 1
        scaled.append(raw_to_scaled(raw, total_items))

    scaled.sort()
    point = int(round(_percentile(scaled, 50)))
    lo = _percentile(scaled, 15)
    hi = _percentile(scaled, 85)
    # Never tighter than the LSAT's own +/-3 band (PRD section 2.1 / 5.3). Work in
    # integer points so rounding cannot shrink the reported width below +/-3.
    half = max(
        int(tax.readiness.min_range_points),
        int(round(point - lo)),
        int(round(hi - point)),
    )
    low = point - half
    high = point + half
    # Preserve the width when clamping to [120, 180]: shift the window inward
    # rather than truncating one side (which would report a sub-+/-3 range).
    if low < 120:
        high += 120 - low
        low = 120
    if high > 180:
        low -= high - 180
        high = 180
    return {
        "point": point,
        "low": max(120, low),
        "high": min(180, high),
        "trials": trials,
        "n_items": total_items,
    }


def widen_for_miscalibration(
    proj: dict[str, Any], overconfidence: float | None, points_per_unit: float
) -> tuple[dict[str, Any], int]:
    """D2: widen the projected range as a function of measured miscalibration.

    Rule (documented in the YAML + docs/models.md): ``extra_half_width =
    round(points_per_unit * max(0, overconfidence_index))``. A student whose
    confident answers outrun their accuracy is *less* ready than raw accuracy
    implies, so the band grows; underconfidence never narrows it, and an
    unmeasured student widens by nothing (the give-up gate handles trust).
    Clamping to [120, 180] shifts the window inward, preserving width.
    """
    extra = (
        0
        if overconfidence is None
        else int(round(points_per_unit * max(0.0, overconfidence)))
    )
    if extra <= 0:
        return proj, 0
    low = proj["low"] - extra
    high = proj["high"] + extra
    if low < 120:
        high += 120 - low
        low = 120
    if high > 180:
        low -= high - 180
        high = 180
    return {**proj, "low": max(120, low), "high": min(180, high)}, extra


def _confidence(n_graded: int, coverage_pct: float, half_width: float) -> list[str]:
    if coverage_pct >= 80 and n_graded >= 300 and half_width <= 4:
        level = "high"
    elif coverage_pct >= 65 and n_graded >= 200:
        level = "medium"
    else:
        level = "low"
    reason = (
        f"{level} -- {coverage_pct:.0f}% coverage, {n_graded} graded items, "
        f"range ±{half_width:.0f}"
    )
    return [level, reason]


def _top_reasons(model: PerformanceModel, tax: Taxonomy, min_events: int) -> list[str]:
    displayed = [
        (t, model.predict(t.id, "medium", 0.0))
        for t in tax.question_types
        if model.counts.get(t.id, (0, 0))[0] >= min_events
    ]
    if not displayed:
        return []
    ranked = sorted(displayed, key=lambda tp: tp[1], reverse=True)
    reasons: list[str] = []
    for t, p in ranked[:2]:
        reasons.append(f"{t.name}: strong at {p * 100:.0f}% (lifting the projection)")
    for t, p in ranked[-2:]:
        if all(t.id != rt.id for rt, _ in ranked[:2]):
            reasons.append(f"{t.name}: weak at {p * 100:.0f}% (pulling it down)")
    return reasons


def build_readiness(
    col: Collection,
    tax: Taxonomy,
    model: PerformanceModel,
    best_next: dict[str, Any] | None,
    *,
    trials: int = DEFAULT_TRIALS,
    seed: int = DEFAULT_SEED,
    now_ms: int | None = None,
    log: bool = True,
) -> dict[str, Any]:
    """Assemble the readiness panel: a full honesty-contract payload or abstain."""
    base = {
        "min_range_points": tax.readiness.min_range_points,
        "required_fields": list(tax.readiness.required_display_fields),
    }

    def abstain(reason: str, missing: list[str]) -> dict[str, Any]:
        return {
            **base,
            "available": False,
            "reason": reason,
            "missing": missing,
            "best_next_to_study": best_next,
        }

    status = give_up_status(col, tax, model)
    if not status["passed"]:
        return abstain("Not enough evidence yet to project a score.", status["missing"])

    coverage_pct = status["coverage_pct"]

    proj = monte_carlo(col, tax, model, trials=trials, seed=seed)
    if proj is None:
        return abstain(
            "Not enough evidence yet to project a score.",
            ["no scored question types configured"],
        )

    # D2: a miscalibrated student gets a wider band (rule in the YAML).
    proj, widened_by = widen_for_miscalibration(
        proj,
        status.get("student_overconfidence"),
        tax.readiness.widen_points_per_overconfidence,
    )

    half_width = (proj["high"] - proj["low"]) / 2.0
    reasons = _top_reasons(model, tax, tax.coverage.min_graded_items_to_count)
    fields: dict[str, Any] = {
        "point_estimate": proj["point"],
        "range": [proj["low"], proj["high"]],
        "percent_covered": coverage_pct,
        "confidence": _confidence(status["n_graded"], coverage_pct, half_width),
        "last_updated": int(time.time()),
        "top_reasons": reasons,
        "best_next_to_study": best_next,
        "past_projection_track_record": track_record(col, now_ms=now_ms),
    }

    # Honesty contract hard gate: never render a number with a missing field.
    incomplete = [
        key
        for key, value in fields.items()
        if value is None or (key == "top_reasons" and not value)
    ]
    if incomplete:
        return abstain(
            "Readiness inputs incomplete.",
            [f"missing readiness field: {key}" for key in incomplete],
        )

    if log:
        append_projection(
            col,
            point=proj["point"],
            low=proj["low"],
            high=proj["high"],
            coverage_pct=coverage_pct,
            n_graded=status["n_graded"],
            now_ms=now_ms,
        )

    return {
        **base,
        "available": True,
        **fields,
        "trials": proj["trials"],
        # D2 transparency: how much miscalibration widened the band (points per
        # side), and the measured index it came from.
        "range_widened_by_miscalibration": widened_by,
        "student_overconfidence": status.get("student_overconfidence"),
    }
