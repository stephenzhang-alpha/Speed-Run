# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The paraphrase test (7d / C2): card recall vs accuracy on reworded items.

Report-only (not a hard gate). This is how SPOV 1's central claim is proven or
falsified: take >= 30 cards, two exam-style items each testing the same idea in
new words, and compare recall on the card against accuracy on the reworded
items. The GAP is the deliverable, not a passing grade -- if recall and
reworded-accuracy are essentially equal (CI includes 0), the performance model
is merely echoing the memory model and "the bridge" does not exist; we say so
plainly either way.

Reported **per topic** as well as overall (transfer varies by question type),
and complemented by ``eval/transfer.py``, which grades the same question as a
*surface-distance curve* (Barnett & Ceci 2002: never a single far-transfer
number). Synthetic learners here; the per-topic transfer penalties are
documented, adjustable assumptions.
"""

from __future__ import annotations

import random
from typing import Any

from eval import config
from eval.metrics import bootstrap_ci

_N_CARDS = 30
_ITEMS_PER_CARD = 2
# Modeled recognition->application drop per topic (set 0 for none). Types whose
# prescribed attack is more mechanical (conditional chains) transfer better
# than judgment-heavy ones -- an assumption the harness makes visible.
_TOPIC_PENALTIES: dict[str, float] = {
    "lr.weaken": 0.18,
    "lr.strengthen": 0.16,
    "lr.flaw": 0.15,
    "lr.assumption_necessary": 0.17,
    "lr.inference_must_be_true": 0.10,
    "lr.parallel_reasoning": 0.20,
}


def run(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    rng = random.Random(seed)
    topics = list(_TOPIC_PENALTIES)
    per_topic: dict[str, dict[str, list[float]]] = {
        t: {"recall": [], "acc": []} for t in topics
    }
    per_card_gap: list[float] = []

    for i in range(_N_CARDS):
        topic = topics[i % len(topics)]
        penalty = _TOPIC_PENALTIES[topic]
        recall = rng.uniform(0.75, 0.97)  # they know the card
        applied = max(0.0, recall - penalty + rng.uniform(-0.08, 0.08))
        hits = sum(1 for _ in range(_ITEMS_PER_CARD) if rng.random() < applied)
        acc = hits / _ITEMS_PER_CARD
        per_topic[topic]["recall"].append(recall)
        per_topic[topic]["acc"].append(acc)
        per_card_gap.append(recall - acc)

    n = _N_CARDS
    mean_recall = sum(sum(v["recall"]) for v in per_topic.values()) / n
    mean_acc = sum(sum(v["acc"]) for v in per_topic.values()) / n
    gap = mean_recall - mean_acc
    lo, hi = bootstrap_ci(per_card_gap, seed)

    topic_rows = {
        t: {
            "n_cards": len(v["recall"]),
            "recall": round(sum(v["recall"]) / len(v["recall"]), 3),
            "accuracy": round(sum(v["acc"]) / len(v["acc"]), 3),
            "gap": round(
                sum(v["recall"]) / len(v["recall"]) - sum(v["acc"]) / len(v["acc"]), 3
            ),
        }
        for t, v in per_topic.items()
        if v["recall"]
    }
    # Honest verdict either way: a CI excluding 0 = a real recognition ->
    # application gap; a CI including 0 = performance is echoing memory.
    if lo > 0:
        verdict = "real recognition->application gap (bridge needed and measured)"
    else:
        verdict = (
            "gap indistinguishable from 0 -- performance model may be echoing "
            "the memory model; reported honestly"
        )
    return {
        "name": "paraphrase",
        "passed": None,  # report-only
        "gate": False,
        "card_recall": round(mean_recall, 3),
        "reworded_item_accuracy": round(mean_acc, 3),
        "gap": round(gap, 3),
        "gap_ci": [round(lo, 3), round(hi, 3)],
        "n_cards": n,
        "items_per_card": _ITEMS_PER_CARD,
        "per_topic": topic_rows,
        "verdict": verdict,
        "detail": f"card recall {mean_recall:.2f} vs reworded-item accuracy "
        f"{mean_acc:.2f} -> gap {gap:+.2f} (95% CI {lo:+.2f}..{hi:+.2f}) over "
        f"{n} cards x{_ITEMS_PER_CARD}; per-topic gaps "
        f"{min(r['gap'] for r in topic_rows.values()):+.2f}.."
        f"{max(r['gap'] for r in topic_rows.values()):+.2f}; "
        "distance-graded companion: transfer step",
    }
