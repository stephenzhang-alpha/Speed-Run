# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""LR question-type interleaving study option.

Interleaving mixes different LR question types within a session (…weaken,
assumption, flaw, weaken…) instead of *blocking* (all weaken, then all
assumption). Cognitive-science motivation: interleaved practice trains
discrimination between superficially-similar problem types and improves transfer
to new items, at the cost of feeling harder in the moment.

The points-at-stake queue chooses *which* cards to study; this controls their
*order*. It's a toggle (``lsat:interleave_lr`` in collection config); the pure
ordering functions below are shared by the app and the ablation harness.
"""

from __future__ import annotations

from typing import TypeVar

_T = TypeVar("_T")


def _bucket(items: list[tuple[_T, str]]) -> tuple[list[str], dict[str, list[_T]]]:
    order: list[str] = []
    buckets: dict[str, list[_T]] = {}
    for payload, qtype in items:
        if qtype not in buckets:
            buckets[qtype] = []
            order.append(qtype)
        buckets[qtype].append(payload)
    return order, buckets


def blocked_order(items: list[tuple[_T, str]]) -> list[_T]:
    """Group by question type (all of one type before the next)."""
    order, buckets = _bucket(items)
    return [payload for qtype in order for payload in buckets[qtype]]


def interleaved_order(items: list[tuple[_T, str]]) -> list[_T]:
    """Round-robin across question types so consecutive cards differ in type
    for as long as multiple types still have cards left."""
    order, buckets = _bucket(items)
    idx = {qtype: 0 for qtype in order}
    remaining = sum(len(b) for b in buckets.values())
    result: list[_T] = []
    while remaining:
        for qtype in order:
            if idx[qtype] < len(buckets[qtype]):
                result.append(buckets[qtype][idx[qtype]])
                idx[qtype] += 1
                remaining -= 1
    return result


# Confusable LR question-type clusters (SPOV 1 / A2). The interleaving
# meta-analysis (Brunmair & Richter 2019, g=0.42) shows the benefit GROWS with
# between-category similarity -- discriminative contrast only pays when the
# juxtaposed categories are genuinely confusable. These clusters group the stem
# families students actually mix up; interleaving *within* a cluster forces the
# discrimination that identification-first cards grade.
CONFUSABLE_CLUSTERS: list[list[str]] = [
    # "support the argument" family: which direction / how strong?
    [
        "lr.strengthen",
        "lr.assumption_necessary",
        "lr.assumption_sufficient",
        "lr.principle",
        "lr.weaken",
    ],
    # "what follows" family: entailment strength
    ["lr.inference_must_be_true", "lr.most_strongly_supported", "lr.cannot_be_true"],
    # "describe the argument" family: structure vs error vs role
    [
        "lr.flaw",
        "lr.method_of_reasoning",
        "lr.parallel_reasoning",
        "lr.parallel_flaw",
        "lr.role_in_argument",
        "lr.main_conclusion",
    ],
]

_CLUSTER_OF: dict[str, int] = {
    qtype: i for i, cluster in enumerate(CONFUSABLE_CLUSTERS) for qtype in cluster
}


def confusable_interleaved_order(items: list[tuple[_T, str]]) -> list[_T]:
    """Interleave types *within* confusable clusters (the evidence-strong form).

    Items are grouped by confusable cluster (types outside every cluster form
    their own group), then round-robined across types within each group, and the
    groups are chained in first-seen order. Adjacent items thus differ in type
    while staying confusable -- maximizing discriminative contrast instead of
    uniformly shuffling easily-separated types.
    """
    group_order: list[int | str] = []
    groups: dict[int | str, list[tuple[_T, str]]] = {}
    for payload, qtype in items:
        key: int | str = _CLUSTER_OF.get(qtype, qtype)
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append((payload, qtype))
    result: list[_T] = []
    for key in group_order:
        result.extend(interleaved_order(groups[key]))
    return result


def interleaving_degree(types: list[str]) -> float:
    """Fraction of adjacent pairs whose question types differ (0=blocked, ~1=fully
    interleaved). A measurable property of an actual study order."""
    if len(types) < 2:
        return 0.0
    diffs = sum(1 for a, b in zip(types, types[1:]) if a != b)
    return diffs / (len(types) - 1)
