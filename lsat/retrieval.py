# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Retrieval baseline: embedding vs BM25 (docs/ai-card-pipeline.md section 4).

The "drill my weakest skill" feature retrieves cards by relevance. We compare a
keyword baseline (**BM25/Okapi**, real) against an **embedding** retriever
(pluggable; the offline default is a TF-IDF cosine stand-in) on a query set with
known-relevant docs. We score each query two ways: **precision@k** and, because
most queries have a single relevant doc (where precision@k is capped at 1/k and
cannot see whether that doc ranked 1st vs kth), **reciprocal rank** -- 1/rank of
the first relevant doc. :func:`compare_retrieval` returns the point means *and*
the per-query embedding-minus-BM25 reciprocal-rank differences, so the harness
(:mod:`eval.baselines`) can put a paired bootstrap CI on the difference and only
claim a win when that CI excludes 0. Per the eval skill we report the *actual*
numbers -- if the offline stand-in does not decisively beat BM25, that is an
honest result, and a real semantic embedder plugs in via :class:`Retriever`.
"""

from __future__ import annotations

import math
import re
from typing import Protocol


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class Retriever(Protocol):
    def search(self, query: str, k: int = 5) -> list[str]: ...


class BM25:
    """Okapi BM25 keyword retrieval over ``(doc_id, text)`` documents."""

    def __init__(
        self, docs: list[tuple[str, str]], k1: float = 1.5, b: float = 0.75
    ) -> None:
        self.ids = [d[0] for d in docs]
        self.corpus = [tokenize(d[1]) for d in docs]
        self.n = len(self.corpus)
        self.avgdl = sum(len(d) for d in self.corpus) / self.n if self.n else 0.0
        self.k1, self.b = k1, b
        self.df: dict[str, int] = {}
        for doc in self.corpus:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.n - n + 0.5) / (n + 0.5))

    def search(self, query: str, k: int = 5) -> list[str]:
        q = tokenize(query)
        scored: list[tuple[str, float]] = []
        for i, doc in enumerate(self.corpus):
            tf: dict[str, int] = {}
            for term in doc:
                tf[term] = tf.get(term, 0) + 1
            dl = len(doc) or 1
            score = 0.0
            for term in q:
                if term not in tf:
                    continue
                f = tf[term]
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                score += self._idf(term) * (f * (self.k1 + 1)) / denom
            scored.append((self.ids[i], score))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return [doc_id for doc_id, _ in scored[:k]]


class TfidfEmbedding:
    """TF-IDF cosine retriever -- an offline stand-in for a semantic embedder."""

    def __init__(self, docs: list[tuple[str, str]]) -> None:
        self.ids = [d[0] for d in docs]
        toks = [tokenize(d[1]) for d in docs]
        self.n = len(toks)
        df: dict[str, int] = {}
        for doc in toks:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1
        self.idf = {t: math.log((1 + self.n) / (1 + c)) + 1.0 for t, c in df.items()}
        self.vecs = [self._vec(doc) for doc in toks]

    def _vec(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        tf: dict[str, int] = {}
        for term in tokens:
            tf[term] = tf.get(term, 0) + 1
        vec = {t: (c / len(tokens)) * self.idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in vec.values())) or 1.0
        return {t: x / norm for t, x in vec.items()}

    def search(self, query: str, k: int = 5) -> list[str]:
        qv = self._vec(tokenize(query))
        scored: list[tuple[str, float]] = []
        for i, dv in enumerate(self.vecs):
            dot = sum(qv[t] * dv[t] for t in qv.keys() & dv.keys())
            scored.append((self.ids[i], dot))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return [doc_id for doc_id, _ in scored[:k]]


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    return sum(1 for d in top if d in relevant) / k


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """Reciprocal rank of the first relevant doc in ``retrieved`` (0.0 if none).

    Informative even when a query has a single relevant doc: it rewards ranking
    that doc higher (1/1 > 1/2 > 1/3), a distinction precision@k -- capped at
    1/k for a lone relevant doc -- cannot make. Pass the *full* ranking so the
    true position is seen rather than truncated at k.
    """
    for idx, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / idx
    return 0.0


def compare_retrieval(
    docs: list[tuple[str, str]],
    queries: list[tuple[str, list[str]]],
    k: int = 5,
    embedder: Retriever | None = None,
) -> dict[str, object]:
    """Per-query BM25-vs-embedder comparison over the query set.

    Returns the mean precision@k and mean reciprocal rank for both retrievers,
    plus ``per_query_diff`` -- the per-query ``embedding_rr - bm25_rr`` list that
    the harness feeds to a paired bootstrap CI. No win/loss verdict is made here:
    a single-point mean comparison is not evidence, so the caller must gate the
    claim on a CI over these paired differences (see :mod:`eval.baselines`).
    """
    if not queries:
        return {
            "k": k,
            "n_queries": 0,
            "metric": "reciprocal_rank",
            "bm25_precision_at_k": 0.0,
            "embedding_precision_at_k": 0.0,
            "bm25_reciprocal_rank": 0.0,
            "embedding_reciprocal_rank": 0.0,
            "per_query_diff": [],
        }
    bm25 = BM25(docs)
    emb = embedder if embedder is not None else TfidfEmbedding(docs)
    depth = len(docs)  # rank the full corpus so reciprocal rank sees true depth
    bm_prec, em_prec = [], []
    bm_rr, em_rr, diffs = [], [], []
    for query, relevant in queries:
        rel = set(relevant)
        bm_full = bm25.search(query, depth)
        em_full = emb.search(query, depth)
        bm_prec.append(precision_at_k(bm_full[:k], rel, k))
        em_prec.append(precision_at_k(em_full[:k], rel, k))
        b_rr = reciprocal_rank(bm_full, rel)
        e_rr = reciprocal_rank(em_full, rel)
        bm_rr.append(b_rr)
        em_rr.append(e_rr)
        diffs.append(e_rr - b_rr)
    n = len(queries)
    return {
        "k": k,
        "n_queries": n,
        "metric": "reciprocal_rank",
        "bm25_precision_at_k": round(sum(bm_prec) / n, 4),
        "embedding_precision_at_k": round(sum(em_prec) / n, 4),
        "bm25_reciprocal_rank": round(sum(bm_rr) / n, 4),
        "embedding_reciprocal_rank": round(sum(em_rr) / n, 4),
        "per_query_diff": diffs,
    }


if __name__ == "__main__":
    # Self-test: the metric primitives behave, and compare_retrieval exposes the
    # per-query differences a paired significance test needs. No network / build.
    _docs = [
        ("d1", "post hoc correlation causation flaw sales rose after logo"),
        ("d2", "ad hominem attacking the arguer not the argument"),
        ("d3", "unrepresentative biased sample generalizing from a small group"),
        ("d4", "equivocation a key term shifts meaning between premises"),
    ]
    assert precision_at_k(["d1", "d2", "d3"], {"d1"}, 3) == 1 / 3
    assert precision_at_k([], {"d1"}, 3) == 0.0
    assert reciprocal_rank(["d2", "d1", "d3"], {"d1"}) == 0.5  # relevant at rank 2
    assert reciprocal_rank(["d2", "d3"], {"d1"}) == 0.0  # not retrieved
    _out = compare_retrieval(
        _docs,
        [("post hoc causation", ["d1"]), ("biased sample", ["d3"])],
        k=3,
    )
    assert _out["metric"] == "reciprocal_rank"
    assert _out["n_queries"] == 2
    _diffs = _out["per_query_diff"]
    assert isinstance(_diffs, list) and len(_diffs) == 2  # one diff per query
    assert compare_retrieval([], [], k=3)["per_query_diff"] == []
    print("retrieval self-test OK:", _out)
