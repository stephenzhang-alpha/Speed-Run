# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Confidence calibration + hypercorrection (DECISION section 3, Feature 3).

Two things over the same one-tap ``confidence`` the per-answer annotation store
now records with every graded answer ("sure"/"likely"/"guess", or "" = the tap
was skipped):

1. a **calibration instrument** -- *is the learner as right as they feel?* Each
   answer's stated confidence maps to a probability (:data:`CONF_TO_PROB`); we
   then report the learner's own reliability curve (stated vs actual accuracy),
   calibration error (ECE / Brier), resolution (AUC of stated confidence against
   correctness), an overconfidence index (mean stated_prob - mean accuracy)
   overall and per skill, and a ranked "sure-and-wrong" list.

2. a **hypercorrection controller** -- :func:`hypercorrection_boost` turns the
   recent high-confidence misses into a bounded, per-skill boost the review
   queue can consume, so the confident errors are re-tested first. Confident
   errors are corrected best (the hypercorrection effect, driven by surprise --
   Butterfield & Metcalfe 2001; Metcalfe 2017) but *relapse without a spaced
   re-test* (Butler, Fazio & Marsh 2011), so surfacing them for re-practice is
   the point.

Discipline (DECISION section 3c): we measure *this individual's* reliability
curve only, and never invoke the Dunning-Kruger *mechanism* (largely a
statistical artefact -- Gignac & Zajenkowski 2020). Unrated answers are skipped,
never imputed; every read abstains below an evidence floor or when the ratings
are degenerate (all one label -> resolution AUC is undefined). All scoring
metrics are reused verbatim from :mod:`eval.metrics` (nothing reimplemented).
"""

from __future__ import annotations

import math
import sys
import time
from typing import TYPE_CHECKING, Any

from eval.metrics import auc, brier, ece
from lsat.events import append_event, read_events

if TYPE_CHECKING:
    from anki.collection import Collection
    from lsat.events import PerformanceEvent

# One-tap confidence -> a stated probability of being correct. Module-level so
# the queue-weighting and dashboard consumers import the SAME mapping. An event
# whose confidence is "" (skipped/unrated) or is not a key here is SKIPPED for
# calibration: a missing rating is unknown, never imputed (DECISION section 5.vi).
CONF_TO_PROB: dict[str, float] = {"sure": 0.9, "likely": 0.7, "guess": 0.45}

# The labels treated as "high confidence" for hypercorrection: a miss on one of
# these is a genuine surprise (the high-ROI review target), unlike a wrong guess.
HIGH_CONFIDENCE = ("sure", "likely")

# Evidence floors (DECISION section 5.v: never "you're bad at X" from 4 points).
MIN_RATED_PER_SKILL = 5  # per-node overconfidence needs at least this many rated
SURE_AND_WRONG_LIMIT = 25  # cap the ranked confident-miss list (bounded output)

_MS_PER_DAY = 86_400_000.0


def _round(x: float, ndigits: int = 6) -> float:
    """JSON-safe float: finite and rounded (so no NaN/Inf can reach output)."""
    return round(x, ndigits) if math.isfinite(x) else 0.0


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _rated(events: list[PerformanceEvent]) -> list[PerformanceEvent]:
    """Events carrying a usable confidence label (unrated ones are skipped)."""
    return [e for e in events if e.confidence in CONF_TO_PROB]


def build_calibration(col: Collection, *, min_rated: int = 20) -> dict[str, Any]:
    """The calibration panel for a collection, as a JSON-safe dict.

    Returns ``{"available": False, "reason": ...}`` below ``min_rated`` rated
    answers or when the ratings are degenerate (all one label, so resolution is
    undefined). Otherwise reports ``n_rated``, the ``reliability`` curve, ``ece``,
    ``brier``, ``resolution_auc`` (AUC of stated_prob vs correct),
    ``overconfidence_index`` (mean stated_prob - mean accuracy), the ranked
    ``sure_and_wrong`` misses, and per-skill overconfidence in ``by_skill``.
    """
    rated = _rated(read_events(col))
    n_rated = len(rated)

    if n_rated < min_rated:
        return {
            "available": False,
            "reason": f"not enough confidence-rated answers ({n_rated}/{min_rated})",
            "n_rated": n_rated,
            "min_rated": min_rated,
        }

    labels_present = {e.confidence for e in rated}
    if len(labels_present) < 2:
        only = next(iter(labels_present))
        return {
            "available": False,
            "reason": (
                f"confidence ratings are degenerate (all '{only}'): "
                "resolution is undefined"
            ),
            "n_rated": n_rated,
            "min_rated": min_rated,
        }

    preds = [CONF_TO_PROB[e.confidence] for e in rated]
    ys = [1.0 if e.correct else 0.0 for e in rated]

    # Reliability curve: one row per confidence label actually used, in a stable
    # descending-confidence order (sure -> likely -> guess).
    reliability: list[dict[str, Any]] = []
    for label, stated in CONF_TO_PROB.items():
        group = [1.0 if e.correct else 0.0 for e in rated if e.confidence == label]
        if not group:
            continue
        reliability.append(
            {
                "confidence_label": label,
                "stated_prob": _round(stated),
                "actual_accuracy": _round(_mean(group)),
                "n": len(group),
            }
        )

    # Ranked confident misses: highest stated confidence first, then most recent.
    misses = sorted(
        (e for e in rated if not e.correct),
        key=lambda e: (CONF_TO_PROB[e.confidence], e.wall_ms),
        reverse=True,
    )
    sure_and_wrong = [
        {
            "item_id": e.item_id,
            "node_ids": list(e.node_ids),
            "confidence": e.confidence,
        }
        for e in misses[:SURE_AND_WRONG_LIMIT]
    ]

    # Per-skill overconfidence, abstaining per node below the evidence floor.
    node_acc: dict[str, list[float]] = {}
    node_conf: dict[str, list[float]] = {}
    for e in rated:
        p = CONF_TO_PROB[e.confidence]
        y = 1.0 if e.correct else 0.0
        for node_id in e.node_ids:
            node_acc.setdefault(node_id, []).append(y)
            node_conf.setdefault(node_id, []).append(p)
    by_skill: list[dict[str, Any]] = []
    for node_id, accs in node_acc.items():
        if len(accs) < MIN_RATED_PER_SKILL:
            continue
        mean_conf = _mean(node_conf[node_id])
        mean_acc = _mean(accs)
        by_skill.append(
            {
                "node_id": node_id,
                "n": len(accs),
                "mean_confidence": _round(mean_conf),
                "accuracy": _round(mean_acc),
                "overconfidence_index": _round(mean_conf - mean_acc),
            }
        )
    by_skill.sort(key=lambda d: d["overconfidence_index"], reverse=True)

    return {
        "available": True,
        "n_rated": n_rated,
        "reliability": reliability,
        "ece": _round(ece(preds, ys)),
        "brier": _round(brier(preds, ys)),
        "resolution_auc": _round(auc(preds, ys)),
        "overconfidence_index": _round(_mean(preds) - _mean(ys)),
        "sure_and_wrong": sure_and_wrong,
        "by_skill": by_skill,
    }


def hypercorrection_boost(
    col: Collection,
    *,
    cap: float = 0.5,
    half_life_days: float = 30.0,
    now_ms: int | None = None,
) -> dict[str, float]:
    """Per-node_id review boost in ``[0, cap]`` for high-confidence misses.

    A node's mass is the recency-weighted, confidence-weighted sum over its
    HIGH-confidence misses (``confidence in {"sure","likely"}`` AND not correct
    AND ``phase == "timed"``): each such miss contributes
    ``0.5 ** (age / half_life) * CONF_TO_PROB[confidence]``, so a recent "sure"
    miss outweighs an old "likely" one. Masses are normalised so the largest
    maps to ``cap`` (others proportionally), keeping the boost bounded and
    deterministic. Empty when there are no qualifying misses.

    This is consumed later by the queue weighting; it is intentionally a pure,
    side-effect-free read of the event log.
    """
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    half_life_ms = max(1.0, half_life_days * _MS_PER_DAY)

    mass: dict[str, float] = {}
    for e in read_events(col):
        if e.correct or e.phase != "timed" or e.confidence not in HIGH_CONFIDENCE:
            continue
        age_ms = max(0, now - e.wall_ms)
        contribution = (0.5 ** (age_ms / half_life_ms)) * CONF_TO_PROB[e.confidence]
        for node_id in e.node_ids:
            mass[node_id] = mass.get(node_id, 0.0) + contribution

    peak = max(mass.values(), default=0.0)
    if peak <= 0.0:
        return {}
    cap = max(0.0, cap)
    return {
        node_id: min(cap, max(0.0, _round(cap * (m / peak))))
        for node_id, m in mass.items()
    }


# -- self-test ----------------------------------------------------------------


def _ensure_anki_on_path() -> None:
    import os

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for rel in ("pylib", "out/pylib"):
        path = os.path.join(root, rel)
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def _selftest() -> bool:  # noqa: PLR0915 (a linear sequence of independent checks)
    """Synthetic end-to-end check against a temp collection. Prints PASS/FAIL."""
    import json
    import os
    import tempfile

    _ensure_anki_on_path()
    from anki.collection import Collection

    ok = True
    now_ms = 1_700_000_000_000  # fixed clock -> deterministic recency weighting

    def check(name: str, cond: object, extra: str = "") -> None:
        nonlocal ok
        passed = bool(cond)
        ok = ok and passed
        tail = f"  ({extra})" if extra else ""
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}{tail}")

    def check_json(name: str, obj: Any) -> None:
        try:
            json.dumps(obj, allow_nan=False)
            check(name, True)
        except (ValueError, TypeError) as exc:
            check(name, False, str(exc))

    def new_col() -> Collection:
        return Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))

    def seed(
        col: Collection,
        node_ids: list[str],
        label: str,
        n: int,
        n_correct: int,
        *,
        phase: str = "timed",
    ) -> None:
        for i in range(n):
            append_event(
                col,
                item_id=f"{label or 'unrated'}:{node_ids[0]}:{phase}:{i}",
                skill_tags=list(node_ids),
                correct=(i < n_correct),
                response_ms=4000,
                confidence=(label or None),
                phase=phase,
                now_ms=now_ms,
            )

    # 1) Well-calibrated learner: actual accuracy tracks stated confidence.
    col = new_col()
    try:
        seed(col, ["lr.strengthen"], "sure", 30, 27)  # 27/30 = 0.90
        seed(col, ["lr.strengthen"], "likely", 30, 21)  # 21/30 = 0.70
        seed(col, ["lr.strengthen"], "guess", 20, 9)  # 9/20 = 0.45
        rep = build_calibration(col)
        check("well-calibrated: available", rep["available"] is True)
        check(
            "well-calibrated: low ECE",
            rep["available"] and rep["ece"] <= 0.05,
            f"ece={rep.get('ece')}",
        )
        check(
            "well-calibrated: resolution_auc > 0.5",
            rep["available"] and rep["resolution_auc"] > 0.5,
            f"auc={rep.get('resolution_auc')}",
        )
        check_json("well-calibrated: json.dumps(allow_nan=False) ok", rep)
    finally:
        col.close()

    # 2) Overconfident learner: many "sure" misses; unrated answers ignored.
    col = new_col()
    try:
        seed(col, ["lr.weaken"], "sure", 30, 8)  # 8/30 correct
        seed(col, ["lr.weaken"], "likely", 20, 6)
        seed(col, ["lr.weaken"], "guess", 10, 4)
        seed(col, ["lr.weaken"], "", 15, 8)  # unrated -> must be skipped
        rep = build_calibration(col)
        check("overconfident: available", rep["available"] is True)
        check(
            "overconfident: unrated skipped (n_rated == 60)",
            rep.get("n_rated") == 60,
            f"n_rated={rep.get('n_rated')}",
        )
        check(
            "overconfident: overconfidence_index > 0",
            rep["available"] and rep["overconfidence_index"] > 0,
            f"oci={rep.get('overconfidence_index')}",
        )
        sw = rep.get("sure_and_wrong") or []
        check("overconfident: sure_and_wrong nonempty", bool(sw), f"n={len(sw)}")
        check(
            "overconfident: highest-confidence miss ranked first",
            bool(sw) and sw[0]["confidence"] == "sure",
        )
        bs = rep.get("by_skill") or []
        check(
            "overconfident: by_skill nonempty + top is overconfident",
            bool(bs) and bs[0]["overconfidence_index"] > 0,
            f"top={bs[:1]}",
        )
        check_json("overconfident: json.dumps(allow_nan=False) ok", rep)
    finally:
        col.close()

    # 3) Below the rated floor -> abstain (unrated events do not count).
    col = new_col()
    try:
        seed(col, ["lr.flaw"], "sure", 8, 6)
        seed(col, ["lr.flaw"], "likely", 6, 4)  # 14 rated, below default 20
        seed(col, ["lr.flaw"], "", 20, 10)  # unrated
        rep = build_calibration(col)
        check("below floor: available is False", rep["available"] is False)
        check(
            "below floor: has reason", bool(rep.get("reason")), str(rep.get("reason"))
        )
        check("below floor: n_rated == 14", rep.get("n_rated") == 14)
        check_json("below floor: json.dumps(allow_nan=False) ok", rep)
    finally:
        col.close()

    # 4) Degenerate ratings (all one label) -> abstain even above the floor.
    col = new_col()
    try:
        seed(col, ["lr.paradox"], "sure", 25, 13)  # >= floor but only one label
        rep = build_calibration(col)
        check("degenerate: available is False", rep["available"] is False)
        check(
            "degenerate: reason names it",
            "degenerate" in str(rep.get("reason", "")).lower(),
            str(rep.get("reason")),
        )
        check_json("degenerate: json.dumps(allow_nan=False) ok", rep)
    finally:
        col.close()

    # 5) Hypercorrection boost concentrates on the worst node; stays in [0, cap].
    col = new_col()
    try:
        seed(col, ["lr.weaken"], "sure", 20, 0)  # 20 timed sure misses (worst)
        seed(col, ["lr.flaw"], "likely", 5, 0)  # 5 timed likely misses
        seed(col, ["lr.strengthen"], "sure", 10, 10)  # all correct -> excluded
        seed(col, ["lr.reading_main_point"], "sure", 8, 0, phase="blind")  # not timed
        seed(col, ["lr.principle"], "guess", 8, 0)  # low confidence -> excluded
        boost = hypercorrection_boost(col, now_ms=now_ms)
        check("boost: nonempty", bool(boost), f"keys={sorted(boost)}")
        check(
            "boost: argmax is the most-confident-miss node",
            bool(boost) and max(boost, key=lambda k: boost[k]) == "lr.weaken",
        )
        check(
            "boost: max maps to cap (0.5)",
            abs(boost.get("lr.weaken", 0.0) - 0.5) < 1e-9,
            f"weaken={boost.get('lr.weaken')}",
        )
        check("boost: correct answers excluded", "lr.strengthen" not in boost)
        check("boost: non-timed phase excluded", "lr.reading_main_point" not in boost)
        check("boost: low-confidence excluded", "lr.principle" not in boost)
        check(
            "boost: every value within [0, cap]",
            all(0.0 <= v <= 0.5 for v in boost.values()),
            f"vals={sorted(round(v, 4) for v in boost.values())}",
        )
        check(
            "boost: weaker node ranks below the worst",
            boost.get("lr.flaw", 0.0) < boost.get("lr.weaken", 0.0),
        )
        small = hypercorrection_boost(col, cap=0.2, now_ms=now_ms)
        check(
            "boost: honours a custom cap",
            all(0.0 <= v <= 0.2 for v in small.values())
            and abs(small.get("lr.weaken", 0.0) - 0.2) < 1e-9,
        )
    finally:
        col.close()

    # 6) No qualifying misses -> empty boost.
    col = new_col()
    try:
        seed(col, ["lr.weaken"], "sure", 5, 5)  # all correct -> no misses
        check(
            "boost: empty when no high-confidence misses",
            hypercorrection_boost(col) == {},
        )
    finally:
        col.close()

    print("CALIB_OK" if ok else "CALIB_FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
