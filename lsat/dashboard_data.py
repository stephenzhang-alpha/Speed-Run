# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Assemble the LSAT dashboard payload (JSON-serialisable dict).

The desktop dashboard renders three honestly-bounded scores plus a coverage map.
Today only the **memory** score is a real local model (PRD section 5.1); the
**performance** and **readiness** scores abstain with the honesty contract
(PRD section 5.3) until those models and enough graded evidence exist -- the
readiness widget literally cannot render a number until the give-up rule holds.

This module is pure Python + the local models; it never touches the network.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from lsat.models.memory import TopicMemory, compute_memory
from lsat.models.performance import (
    PerformanceModel,
    PerfTopic,
    fit_performance_model,
    performance_summary,
)
from lsat.models.readiness import build_readiness
from lsat.primitives import primitive_coverage
from lsat.taxonomy import Taxonomy, load_taxonomy

if TYPE_CHECKING:
    from anki.collection import Collection


def _topic_dict(t: TopicMemory) -> dict[str, Any]:
    return {
        "node_id": t.node_id,
        "name": t.name,
        "tag": t.tag,
        "kind": t.kind,
        "n_cards": t.n_cards,
        "n_reviews": t.n_reviews,
        "memory": t.memory,
        "low": t.low,
        "high": t.high,
        "enough_evidence": t.enough_evidence,
        "note": t.note,
    }


def _weighted_overall(
    question_types: list[TopicMemory], tax: Taxonomy
) -> dict[str, Any]:
    """Exam-weighted mean memory over the displayed question types (a summary)."""
    displayed = [
        t for t in question_types if t.enough_evidence and t.memory is not None
    ]
    if not displayed:
        return {
            "memory": None,
            "low": None,
            "high": None,
            "displayed_topics": 0,
            "note": "Not enough evidence yet -- review more cards to show a memory score.",
        }
    exam_weight = {t.id: t.exam_weight for t in tax.question_types}
    weights = [max(exam_weight.get(t.node_id, 0.0), 1e-9) for t in displayed]
    total = sum(weights)

    def wmean(values: list[float]) -> float:
        return sum(w * v for w, v in zip(weights, values)) / total

    return {
        "memory": wmean([t.memory for t in displayed]),  # type: ignore[misc]
        "low": wmean([t.low for t in displayed]),  # type: ignore[misc]
        "high": wmean([t.high for t in displayed]),  # type: ignore[misc]
        "displayed_topics": len(displayed),
        "note": f"Exam-weighted across {len(displayed)} topics with enough evidence.",
    }


def _best_next_to_study(
    question_types: list[TopicMemory], tax: Taxonomy
) -> dict[str, Any] | None:
    """The single highest-value topic to study: fewest cards, then highest weight."""
    if not question_types:
        return None
    exam_weight = {t.id: t.exam_weight for t in tax.question_types}
    best = min(
        question_types, key=lambda t: (t.n_cards, -exam_weight.get(t.node_id, 0.0))
    )
    return {"node_id": best.node_id, "name": best.name, "n_cards": best.n_cards}


def _perf_topic_dict(t: PerfTopic) -> dict[str, Any]:
    return {
        "node_id": t.node_id,
        "name": t.name,
        "tag": t.tag,
        "n_events": t.n_events,
        "n_correct": t.n_correct,
        "p": t.p,
        "low": t.low,
        "high": t.high,
        "enough_evidence": t.enough_evidence,
        "note": t.note,
    }


def _performance_panel(
    model: PerformanceModel, tax: Taxonomy, min_events: int
) -> dict[str, Any]:
    """The performance panel: per-topic P(correct) +/- interval, or abstaining."""
    topics = performance_summary(model, tax, min_events)
    panel: dict[str, Any] = {
        "topics": [_perf_topic_dict(t) for t in topics],
        "n_events": model.n_events,
        "calibration": model.calibration,
    }
    by_id = {p.node_id: p for p in topics}
    exam_weight = {t.id: t.exam_weight for t in tax.question_types}
    scored: list[tuple[float, float, float, float]] = []
    for node_id, pt in by_id.items():
        if (
            pt.enough_evidence
            and pt.p is not None
            and pt.low is not None
            and pt.high is not None
        ):
            scored.append(
                (max(exam_weight.get(node_id, 0.0), 1e-9), pt.p, pt.low, pt.high)
            )
    if not scored:
        panel["available"] = False
        panel["overall"] = None
        panel["note"] = "Answer graded LSAT items (multiple choice) to build this."
        return panel
    wsum = sum(w for w, _, _, _ in scored) or 1.0
    panel["available"] = True
    panel["overall"] = {
        "p": sum(w * p for w, p, _, _ in scored) / wsum,
        "low": sum(w * lo for w, _, lo, _ in scored) / wsum,
        "high": sum(w * hi for w, _, _, hi in scored) / wsum,
        "displayed_topics": len(scored),
    }
    panel["note"] = (
        f"P(correct) on new exam-style items, from {model.n_events} graded answers."
    )
    return panel


def _safe(label: str, fn: Any) -> dict[str, Any]:
    """Run an insight builder, degrading to an abstaining panel on any error so
    a single model never breaks the whole dashboard."""
    try:
        return fn()
    except Exception as exc:  # defensive: insights are best-effort
        return {"available": False, "reason": f"{label} unavailable: {exc}"}


def _fatigue_curve(col: Collection) -> dict[str, Any]:
    """Accuracy vs cumulative time-on-task (DECISION-round2 #10)."""
    from lsat.fatigue import fatigue_curve

    return fatigue_curve(col)


def _exam_schedule_summary(col: Collection) -> dict[str, Any]:
    """Days-to-exam + consolidation count (DECISION-round2 #7), or an abstain
    shape when no exam date is set / too little FSRS state to project."""
    from lsat.exam_schedule import exam_schedule_summary

    return exam_schedule_summary(col)


def _adherence_status(col: Collection) -> dict[str, Any]:
    """If-Then plan + adherence (DECISION-round2 #4), or abstain when no plan."""
    from lsat.adherence import adherence_status

    return adherence_status(col)


def _growth_panel(col: Collection) -> dict[str, Any]:
    """Mastery-Growth panel (DECISION-round3 #2): CI-gated, difficulty-matched,
    self-referential per-skill progress; abstains per skill until its CI excludes
    0 (mechanism gated by the ``growth`` hard eval)."""
    from lsat.growth import compute_growth

    return compute_growth(col)


def _answer_change_ledger(col: Collection) -> dict[str, Any]:
    """First-Instinct Ledger (DECISION-round4 #17): the learner's own net
    wrong->right vs right->wrong answer changes on timed sections, CI-gated;
    abstains below the min-changes floor (mechanism gated by ``answer_change``)."""
    from lsat.answer_change import compute_answer_change

    return compute_answer_change(col)


def _time_leak(col: Collection) -> dict[str, Any]:
    """Reclaimable-seconds triage read-out (DECISION-round3 #5), or an abstain
    shape when there is no blind pass / too few paired items / no measurable leak."""
    from lsat.triage import time_leak

    return time_leak(col)


def _misconception_panel(col: Collection) -> dict[str, Any]:
    """B2 four-state counts + resolution ledger, with B4's grounded hypotheses
    (deterministic label->text; AI off) attached to the open misses."""
    from lsat.ai.misconception import hypotheses_for_open_misconceptions
    from lsat.misconceptions import misconception_stats

    stats = misconception_stats(col)
    if stats.get("available"):
        stats["hypotheses"] = hypotheses_for_open_misconceptions(col, client=None)
    return stats


def _insights(col: Collection) -> dict[str, Any]:
    """The novel, evidence-based LSAT panels (see research/debate/DECISION.md).

    Each reads the per-answer annotation store (chosen/confidence/phase) and
    abstains honestly until it has enough evidence.
    """
    from lsat import blind_review, error_patterns, pacing
    from lsat.models import calibration, fluency

    return {
        "calibration": _safe("calibration", lambda: calibration.build_calibration(col)),
        "traps": _safe("traps", lambda: error_patterns.trap_fingerprint(col)),
        "gap_map": _safe("gap_map", lambda: blind_review.gap_map(col)),
        # Within-item paired Choke Index with a bootstrap CI (DECISION-round2 #24);
        # carries the old unpaired aggregate as a labelled low-confidence fallback.
        "choke": _safe("choke", lambda: pacing.paired_choke_index(col)),
        "pacing": _safe("pacing", lambda: pacing.pacing_stats(col)),
        # Rush-Error Detector (DECISION-round3 #21): fast answers disproportionately
        # more wrong than the learner's own slower ones (CI-gated, per-baseline).
        "rush": _safe("rush", lambda: pacing.rush_errors(col)),
        # Time-Leak Diagnostic (DECISION-round3 #5): reclaimable seconds spent on
        # items missed even untimed (a gap, not a pace problem), reported with a CI.
        "time_leak": _safe("time_leak", lambda: _time_leak(col)),
        "fluency": _safe("fluency", lambda: fluency.fluency_status(col)),
        # Fatigue Curve (DECISION-round2 #10): accuracy vs cumulative minutes
        # on task, sessions inferred from event timestamps (no schema change).
        "fatigue": _safe("fatigue", lambda: _fatigue_curve(col)),
        # SPOV 2 / B2+B4: confidence x correctness states, the misconception
        # ledger (with re-test debts), and grounded hypotheses for open misses.
        "misconceptions": _safe("misconceptions", lambda: _misconception_panel(col)),
    }


def build(col: Collection, taxonomy: Taxonomy | None = None) -> dict[str, Any]:
    """Build the dashboard payload for a collection.

    The whole assembly runs inside a single :func:`events_cache` window (the
    memory/performance/readiness models and all seven insight panels each read
    the graded-event log, so one parse serves them all) and a
    :func:`deck_nodes_cache` window (primitive coverage is computed for both the
    readiness give-up gate and the coverage panel from one LSAT-note scan). Both
    turn repeated full scans into one (PRD section 13 dashboard-refresh budget);
    no note is written during a build, so neither cache can go stale.
    """
    from lsat.events import events_cache
    from lsat.primitives import deck_nodes_cache

    with events_cache(col), deck_nodes_cache(col):
        return _build(col, taxonomy)


def _build(col: Collection, taxonomy: Taxonomy | None = None) -> dict[str, Any]:
    tax = taxonomy or load_taxonomy()
    report = compute_memory(col, tax)
    question_types = [t for t in report.topics if t.kind == "question_type"]
    model = fit_performance_model(col, tax)

    # Coverage counts GRADED ITEMS per question type -- the quantity the YAML
    # threshold (min_graded_items_to_count) and the readiness give-up gate both use
    # -- not reviewed drill-card count (t.n_cards). Counting cards diverged from the
    # readiness payload on the same dashboard and read ~0% for a fully-graded deck
    # (the starter deck seeds ~1 drill card per type, so n_cards >= min_items was
    # unreachable regardless of graded volume).
    min_items = tax.coverage.min_graded_items_to_count

    def _graded_count(t: Any) -> int:
        return model.counts.get(t.node_id, (0, 0))[0]

    covered = [t for t in question_types if _graded_count(t) >= min_items]
    coverage_pct = (
        round(100.0 * len(covered) / len(question_types), 1) if question_types else 0.0
    )

    best_next = _best_next_to_study(question_types, tax)
    performance = _performance_panel(model, tax, min_items)
    readiness = build_readiness(col, tax, model, best_next)

    return {
        "exam": tax.exam,
        "format_as_of": tax.format_as_of,
        "generated_at": int(time.time()),
        # Exam-Day Retrievability Targeting (DECISION-round2 #7): days-to-exam +
        # consolidation count, or an abstain shape when no exam date is set (cheap
        # -- it returns before scanning cards when there is no date).
        "exam_schedule": _safe("exam_schedule", lambda: _exam_schedule_summary(col)),
        # If-Then study plan adherence (DECISION-round2 #4): the plan + completion
        # inferred from the event log, or an abstain shape when no plan is set.
        "adherence": _safe("adherence", lambda: _adherence_status(col)),
        # Mastery-Growth panel (DECISION-round3 #2): self-referential, CI-gated,
        # difficulty-matched per-skill progress; abstains until the CI excludes 0.
        "growth": _safe("growth", lambda: _growth_panel(col)),
        # First-Instinct Ledger (DECISION-round4 #17): the learner's own
        # answer-change net on timed sections, CI-gated; abstains below the floor.
        "answer_change": _safe("answer_change", lambda: _answer_change_ledger(col)),
        "give_up": {"min_reviews_per_topic": report.min_reviews_for_display},
        "scores": {
            "memory": {
                "overall": _weighted_overall(question_types, tax),
                "topics": [_topic_dict(t) for t in report.topics],
            },
            "performance": performance,
            "readiness": readiness,
        },
        "insights": _insights(col),
        "coverage": {
            "pct": coverage_pct,
            "covered": len(covered),
            "total": len(question_types),
            "min_items": min_items,
            "basis": tax.coverage.basis,
            # A3: taxonomy coverage by reasoning-primitive family (deck-based).
            "primitives": _safe("primitives", lambda: primitive_coverage(col, tax)),
            "topics": [
                {
                    "node_id": t.node_id,
                    "name": t.name,
                    "n_graded": _graded_count(t),
                    "n_cards": t.n_cards,
                    "covered": _graded_count(t) >= min_items,
                }
                for t in question_types
            ],
        },
    }
