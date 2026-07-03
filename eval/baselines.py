# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Beat-the-baseline: embedding retrieval vs BM25 (docs/ai-card-pipeline.md section 4).

Builds a corpus + query set from the gold set and compares an embedding
retriever against BM25. A single-point mean comparison is not evidence, so we
score each query with reciprocal rank, take the per-query embedding-minus-BM25
differences, and put a paired bootstrap 95% CI on the mean difference. We only
set ``embedding_wins`` when that CI *excludes 0*; otherwise the report states,
honestly, that the two are not statistically distinguishable on this query set
and that a real semantic embedder would be needed to win decisively. This is a
report-only step (no hard gate). A real embedder plugs into
:func:`lsat.retrieval.compare_retrieval` via its ``embedder`` arg.
"""

from __future__ import annotations

from typing import Any


def _ensure_repo_on_path() -> None:
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


def run() -> dict[str, Any]:
    _ensure_repo_on_path()
    from collections import defaultdict

    from eval.config import RANDOM_SEED
    from eval.metrics import bootstrap_ci
    from lsat.ai.gold_set import load_gold_set
    from lsat.retrieval import compare_retrieval

    gold = load_gold_set()
    docs = [
        (item["id"], f"{item['question']} {item['answer']} {item['principle']}")
        for item in gold
    ]
    by_skill: dict[str, list[str]] = defaultdict(list)
    for item in gold:
        by_skill[item["skill"]].append(item["id"])
    # queries phrase the skill in words (a light paraphrase of the doc content)
    queries = [
        (skill.replace(".", " ").replace("_", " "), ids)
        for skill, ids in by_skill.items()
    ]

    result = compare_retrieval(docs, queries, k=3)

    # Paired significance: bootstrap a 95% CI on the mean per-query difference
    # (embedding reciprocal rank - BM25 reciprocal rank). Claim a win ONLY when
    # the CI excludes 0 -- a point-estimate lead is not, by itself, a real win.
    raw_diffs = result.pop("per_query_diff", [])
    diffs: list[float] = list(raw_diffs) if isinstance(raw_diffs, list) else []
    ci_low, ci_high = bootstrap_ci(diffs, seed=RANDOM_SEED)
    mean_diff = sum(diffs) / len(diffs) if diffs else 0.0
    embedding_wins = ci_low > 0.0

    metric = result.get("metric", "reciprocal_rank")
    k = result.get("k")
    em_rr = result.get("embedding_reciprocal_rank")
    bm_rr = result.get("bm25_reciprocal_rank")
    em_p = result.get("embedding_precision_at_k")
    bm_p = result.get("bm25_precision_at_k")
    ci_str = f"[{round(ci_low, 4)}, {round(ci_high, 4)}]"
    if embedding_wins:
        detail = (
            f"embedding beats BM25: {metric} {em_rr} vs {bm_rr} (P@{k} {em_p} vs "
            f"{bm_p}); paired bootstrap 95% CI on mean diff {ci_str} excludes 0 "
            f"-- statistically distinguishable on this query set."
        )
    else:
        detail = (
            f"NOT statistically distinguishable on this query set: {metric} "
            f"{em_rr} vs {bm_rr} (P@{k} {em_p} vs {bm_p}); paired bootstrap 95% CI "
            f"on mean diff {ci_str} includes 0 -- an honest negative. A real "
            f"semantic embedder (not this lexical TF-IDF stand-in) would be needed "
            f"to win decisively."
        )

    result.update(
        {
            "mean_diff": round(mean_diff, 4),
            "ci_low": round(ci_low, 4),
            "ci_high": round(ci_high, 4),
            "embedding_wins": embedding_wins,
            "detail": detail,
        }
    )
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
