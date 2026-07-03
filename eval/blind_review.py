# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Blind-Review routing-validity + honest-mastery eval (DECISION.md section 3,
Feature 4).

The Blind-Review Gap Map (:mod:`lsat.blind_review`) joins each item's most-recent
*timed* answer with its most-recent *blind/relaxed* answer and routes every skill
by its misses: more "pressure" (timed wrong, blind right) than "knowledge" (wrong
both ways) -> route to **pacing**; the reverse -> route to **content**. The same
join feeds the honest-mastery filter (:func:`lsat.events.fold_recent_performance`
with ``honest_mastery=True``), which DROPS a *lucky timed win* -- a timed-correct
answer the learner could not reproduce untimed -- so a guess never masquerades as
mastery in the points-at-stake queue.

This is a **report** on two validity questions, not a learning claim. On seeded
synthetic learners with a KNOWN ground-truth cause per skill we measure:

  (a) routing validity -- does the shipped routing recover the true cause? Each
      skill is generated as either "pressure" (high untimed ability, large pacing
      penalty) or "knowledge" (low ability both ways); we report the fraction of
      skills routed to the correct fix (pacing vs content) with a bootstrap CI.

  (b) honest mastery -- does dropping lucky timed wins improve held-out prediction?
      Learners guess more under the clock (timed-only lucky wins the untimed pass
      refutes); we fold per-skill mastery with the lucky-win drop ON vs OFF and
      score each against held-out future *untimed* answers (true ability). We
      report the Brier improvement with a bootstrap CI.

Everything is seeded and pure (no collection, no network); it reuses the shipped
join/classify/route helpers and the real lucky-win detector so the metric rests
on production code. It is REPORT-ONLY (no hard gate): the numbers validate the
mechanism on synthetic data, not a field result -- real paired reviews would
replace the generators unchanged.
"""

from __future__ import annotations

import math
import random
from typing import Any

from eval import config
from eval.metrics import bootstrap_ci
from lsat.blind_review import (
    MIN_PAIRED_PER_SKILL,
    _classify,
    _join_by_item,
    _route,
    lucky_timed_items_from_events,
)
from lsat.events import PerformanceEvent

# -- routing-validity generation ---------------------------------------------
N_LEARNERS_ROUTE = 120
N_SKILLS_ROUTE = 6
N_ITEMS_ROUTE = 14  # paired items per skill (well above MIN_PAIRED_PER_SKILL)
# "pressure": strong untimed ability, large pacing penalty -> timed collapses.
PRESSURE_ABILITY = (0.8, 1.8)
PRESSURE_PENALTY = (1.4, 2.4)
# "knowledge": weak both ways; the (small) penalty barely matters.
KNOWLEDGE_ABILITY = (-1.7, -0.6)
KNOWLEDGE_PENALTY = (0.0, 0.4)

# -- honest-mastery generation ------------------------------------------------
N_LEARNERS_HM = 140
N_SKILLS_HM = 5
N_TRAIN_HM = 16  # paired timed+blind training items per skill
N_HOLDOUT_HM = 12  # held-out future untimed answers per skill (true-ability probe)
KNOWLEDGE_PROB = (0.15, 0.85)  # per-skill P(truly knows an item), varied
GUESS_BLIND = 0.10  # untimed the learner reasons; small residual guess
GUESS_TIMED = 0.35  # under the clock they guess more -> lucky timed wins


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _ev(item_id: str, correct: bool, phase: str, node: str) -> PerformanceEvent:
    """A minimal synthetic event; the routing join reads phase/item_id/correct/
    node_ids (and list order for "most recent"), not the HLC, so a trivial stamp
    suffices."""
    return PerformanceEvent(
        note_id=0,
        item_id=item_id,
        node_ids=[node],
        correct=correct,
        response_ms=1,
        hlc="0000000000000:000000:d",
        device_id="d",
        phase=phase,
    )


def _honest_fold(
    events: list[PerformanceEvent], honest_mastery: bool
) -> dict[str, float]:
    """Per-node timed accuracy, mirroring ``lsat.events.fold_recent_performance``'s
    honest-mastery path inlined for purity.

    It restricts to the ``"timed"`` phase (the shipped default) and, when
    ``honest_mastery`` is set, drops a timed win whose item is a *lucky* win via
    the real :func:`lsat.blind_review.lucky_timed_items_from_events`. Recency
    weighting is omitted only because these synthetic events share one stamp
    (equal weight); the drop rule is the production rule verbatim.
    """
    lucky = lucky_timed_items_from_events(events) if honest_mastery else set()
    acc: dict[str, list[float]] = {}
    for e in events:
        if e.phase != "timed":
            continue
        if honest_mastery and e.correct and e.item_id in lucky:
            continue
        for node in e.node_ids:
            slot = acc.setdefault(node, [0.0, 0.0])
            slot[0] += 1.0 if e.correct else 0.0
            slot[1] += 1.0
    return {node: (c / t if t > 0 else 0.0) for node, (c, t) in acc.items()}


def _routing_validity(seed: int) -> dict[str, Any]:
    """Does the shipped routing recover each skill's KNOWN true cause?

    Generates ``N_SKILLS_ROUTE`` skills per learner, each truly "pressure" or
    "knowledge", builds paired timed+blind answers, and routes via the real
    join/classify/route helpers. Correct iff pressure->pacing and knowledge->
    content ("mixed" counts as a miss). Returns accuracy + bootstrap CI over the
    per-skill 0/1 indicators, plus the routing confusion counts.
    """
    rng = random.Random(seed)
    hits: list[float] = []
    confusion = {
        "pressure": {"pacing": 0, "content": 0, "mixed": 0},
        "knowledge": {"pacing": 0, "content": 0, "mixed": 0},
    }
    for learner in range(N_LEARNERS_ROUTE):
        for s in range(N_SKILLS_ROUTE):
            pressure = rng.random() < 0.5
            if pressure:
                ability = rng.uniform(*PRESSURE_ABILITY)
                penalty = rng.uniform(*PRESSURE_PENALTY)
            else:
                ability = rng.uniform(*KNOWLEDGE_ABILITY)
                penalty = rng.uniform(*KNOWLEDGE_PENALTY)
            node = f"lr.route_s{s}"
            events: list[PerformanceEvent] = []
            for i in range(N_ITEMS_ROUTE):
                diff = rng.uniform(-1.0, 1.0)
                p_untimed = _sigmoid(ability - diff)
                p_timed = _sigmoid(ability - diff - penalty)
                iid = f"L{learner}s{s}i{i}"
                events.append(_ev(iid, rng.random() < p_timed, "timed", node))
                events.append(_ev(iid, rng.random() < p_untimed, "blind", node))

            counts = {"mastered": 0, "fragile": 0, "pressure": 0, "knowledge": 0}
            for timed_ev, blind_ev in _join_by_item(events).values():
                counts[_classify(timed_ev.correct, blind_ev.correct)] += 1
            # Guard the shipped per-skill floor, exactly as gap_map does.
            enough = sum(counts.values()) >= MIN_PAIRED_PER_SKILL
            route = _route(counts) if enough else "mixed"

            cause = "pressure" if pressure else "knowledge"
            expected = "pacing" if pressure else "content"
            confusion[cause][route if route in ("pacing", "content") else "mixed"] += 1
            hits.append(1.0 if route == expected else 0.0)

    accuracy = sum(hits) / len(hits)
    lo, hi = bootstrap_ci(hits, seed)
    return {
        "accuracy": accuracy,
        "ci": (lo, hi),
        "confusion": confusion,
        "n_skills": len(hits),
    }


def _honest_mastery(seed: int) -> dict[str, Any]:
    """Does dropping lucky timed wins improve held-out next-answer prediction?

    For each learner-skill we fold per-skill mastery from the training answers
    with the lucky-win drop ON (honest) vs OFF, use that scalar as the predicted
    P(correct) for ``N_HOLDOUT_HM`` held-out future *untimed* answers (which
    reflect true ability), and score with the Brier score. Returns the mean Brier
    improvement (off - honest; positive = honest predicts better) with a bootstrap
    CI over the per-skill deltas, plus each arm's mean Brier.
    """
    rng = random.Random(seed)
    deltas: list[float] = []
    brier_honest: list[float] = []
    brier_off: list[float] = []
    for learner in range(N_LEARNERS_HM):
        events: list[PerformanceEvent] = []
        holdout: dict[str, list[float]] = {}
        for s in range(N_SKILLS_HM):
            k = rng.uniform(*KNOWLEDGE_PROB)
            node = f"lr.hm_s{s}"
            for i in range(N_TRAIN_HM):
                known = rng.random() < k
                iid = f"H{learner}s{s}i{i}"
                timed_correct = known or (rng.random() < GUESS_TIMED)
                blind_correct = known or (rng.random() < GUESS_BLIND)
                events.append(_ev(iid, timed_correct, "timed", node))
                events.append(_ev(iid, blind_correct, "blind", node))
            # Held-out future untimed answers ~ the learner's TRUE untimed ability.
            p_true = k + (1.0 - k) * GUESS_BLIND
            holdout[node] = [
                1.0 if rng.random() < p_true else 0.0 for _ in range(N_HOLDOUT_HM)
            ]

        mastery_honest = _honest_fold(events, honest_mastery=True)
        mastery_off = _honest_fold(events, honest_mastery=False)
        for node, ys in holdout.items():
            p_honest = mastery_honest.get(node, 0.0)
            p_off = mastery_off.get(node, 0.0)
            b_honest = sum((p_honest - y) ** 2 for y in ys) / len(ys)
            b_off = sum((p_off - y) ** 2 for y in ys) / len(ys)
            brier_honest.append(b_honest)
            brier_off.append(b_off)
            deltas.append(b_off - b_honest)

    improvement = sum(deltas) / len(deltas)
    lo, hi = bootstrap_ci(deltas, seed)
    return {
        "brier_improvement": improvement,
        "ci": (lo, hi),
        "brier_honest": sum(brier_honest) / len(brier_honest),
        "brier_off": sum(brier_off) / len(brier_off),
        "n_skills": len(deltas),
    }


def run(seed: int = config.RANDOM_SEED) -> dict[str, Any]:
    """Report-only: routing validity + honest-mastery lift on synthetic learners."""
    route = _routing_validity(seed)
    hm = _honest_mastery(seed + 7)  # decouple the two arms' RNG streams
    detail = (
        f"routing recovers the true cause {route['accuracy']:.2f} of the time "
        f"(95% CI {route['ci'][0]:.2f}-{route['ci'][1]:.2f}, n={route['n_skills']}); "
        f"honest-mastery drop improves held-out Brier by "
        f"{hm['brier_improvement']:+.4f} "
        f"(95% CI {hm['ci'][0]:+.4f}..{hm['ci'][1]:+.4f}: "
        f"{hm['brier_off']:.4f} -> {hm['brier_honest']:.4f}); "
        "SYNTHETIC learners -- validates the mechanism, not a field result."
    )
    return {
        "name": "blind_review",
        "passed": None,  # report-only: no pre-registered threshold, no hard gate
        "gate": False,
        "detail": detail,
        "routing_accuracy": round(route["accuracy"], 4),
        "routing_accuracy_ci": [round(route["ci"][0], 4), round(route["ci"][1], 4)],
        "routing_confusion": route["confusion"],
        "routing_n_skills": route["n_skills"],
        "honest_mastery_brier_improvement": round(hm["brier_improvement"], 4),
        "honest_mastery_ci": [round(hm["ci"][0], 4), round(hm["ci"][1], 4)],
        "honest_mastery_brier_off": round(hm["brier_off"], 4),
        "honest_mastery_brier_honest": round(hm["brier_honest"], 4),
        "honest_mastery_n_skills": hm["n_skills"],
        "params": {
            "route_learners": N_LEARNERS_ROUTE,
            "route_items_per_skill": N_ITEMS_ROUTE,
            "hm_learners": N_LEARNERS_HM,
            "hm_train_items": N_TRAIN_HM,
            "hm_holdout_items": N_HOLDOUT_HM,
            "guess_timed": GUESS_TIMED,
            "guess_blind": GUESS_BLIND,
        },
        "note": (
            "Seeded synthetic learners with a known ground-truth cause per skill; "
            "reuses the shipped join/classify/route helpers and the real lucky-win "
            "detector. Report-only -- real paired reviews replace the generators "
            "unchanged."
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
