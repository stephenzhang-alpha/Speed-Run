# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The leakage check (7e): a hard gate.

Scan everything used for training/generation (the train split) for any held-out
item or near-copy, via THREE lexical signals (ANY flagged pair fails the build):

1. **normalized exact/substring match** -- catches verbatim reuse;
2. **lexical tf-idf cosine** >= ``LEAK_COSINE_MAX`` -- catches token-overlap
   near-copies (bag-of-words, so word reordering does not evade it);
3. **character-n-gram (shingle) Jaccard** >= ``LEAK_FUZZY_MAX`` -- catches
   *reworded* near-copies that the token-exact cosine misses because it does not
   stem (e.g. "companies increases" vs "company increased" share the stems but
   not the tokens; the tf-idf cosine collapses on that, the shingle overlap does
   not).

**Honest limit (was mislabeled "embedding cosine"):** these are all *lexical*.
A fully-synonymized paraphrase that shares no word stems ("cutting costs boosts
earnings" vs "lowering prices increases revenue") evades every lexical signal;
catching that needs a real *semantic* embedder. :func:`_semantic_sim` is the
pluggable hook (returns ``None`` = unavailable offline) where one drops in --
identical to how ``lsat.retrieval`` leaves its embedder pluggable. The detector
self-test (:func:`detector_self_test`) proves the "clean" result is trustworthy:
it plants a verbatim copy, a reworded near-copy the shingle path must catch, and
an unrelated item that must NOT be flagged.
"""

from __future__ import annotations

import math
import re
from typing import Any

from eval import config
from lsat.retrieval import tokenize


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _shingles(text: str, n: int = 4) -> set[str]:
    """Character n-grams over the normalized text -- robust to word reordering
    and to the morphological variants the token-exact cosine cannot see."""
    s = re.sub(r"\s+", " ", _normalize(text))
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _semantic_sim(a_text: str, b_text: str) -> float | None:
    """Pluggable semantic-similarity hook. Returns ``None`` when no semantic
    embedder is available (the offline default), so the scan falls back to the
    lexical signals. Wire a real sentence embedder here to catch fully-reworded
    paraphrases that share no word stems (the one case lexical signals miss)."""
    return None


def _idf(docs: list[list[str]]) -> dict[str, float]:
    n = len(docs)
    df: dict[str, int] = {}
    for doc in docs:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1
    return {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}


def _vec(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    raw = {t: (c / len(tokens)) * idf.get(t, 0.0) for t, c in tf.items()}
    norm = math.sqrt(sum(v * v for v in raw.values())) or 1.0
    return {t: v / norm for t, v in raw.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(a[t] * b[t] for t in a.keys() & b.keys())


def _scan(
    corpus: list[tuple[str, str]], heldout: list[tuple[str, str]]
) -> list[dict[str, Any]]:
    corpus_norm = [(cid, _normalize(text)) for cid, text in corpus]
    all_tokens = [tokenize(text) for _, text in corpus] + [
        tokenize(text) for _, text in heldout
    ]
    idf = _idf(all_tokens)
    corpus_vecs = [
        (cid, _vec(tokenize(text), idf), _shingles(text)) for cid, text in corpus
    ]
    flagged: list[dict[str, Any]] = []
    for hid, htext in heldout:
        hnorm = _normalize(htext)
        hvec = _vec(tokenize(htext), idf)
        hsh = _shingles(htext)
        for (cid, cnorm), (_, cvec, csh), (_, ctext) in zip(
            corpus_norm, corpus_vecs, corpus
        ):
            exact = hnorm == cnorm or hnorm in cnorm or cnorm in hnorm
            cos = _cosine(hvec, cvec)
            fuzzy = _jaccard(hsh, csh)
            sem = _semantic_sim(htext, ctext)
            reason = None
            if exact:
                reason = "normalized_match"
            elif cos >= config.LEAK_COSINE_MAX:
                reason = "cosine"
            elif fuzzy >= config.LEAK_FUZZY_MAX:
                reason = "fuzzy_shingle"
            elif sem is not None and sem >= config.LEAK_COSINE_MAX:
                reason = "semantic"
            if reason is not None:
                flagged.append(
                    {
                        "heldout": hid,
                        "train": cid,
                        "cosine": round(cos, 3),
                        "fuzzy": round(fuzzy, 3),
                        "reason": reason,
                    }
                )
    return flagged


# Controlled detector fixtures: same argument (a) verbatim, (b) reworded with
# morphological variants + reordering (token-disjoint enough that the tf-idf
# cosine misses it -- only the shingle path catches it), and (c) an unrelated
# item that must NOT trip any signal.
_SELFTEST_ORIGINAL = (
    "The advertising firm concluded that lowering prices increases total revenue "
    "because sales volume rose after the last discount."
)
_SELFTEST_REWORD = (
    "Because sales volumes rose following the previous discounts, the ad firms "
    "concluded that lowering the price increases the total revenues."
)
_SELFTEST_UNRELATED = (
    "A marine biologist observed that migratory seabirds navigate across open "
    "ocean using the Earth's magnetic field and polarized light."
)


def detector_self_test() -> dict[str, Any]:
    """Prove the scanner catches near-copies AND does not over-flag.

    Three planted cases: a verbatim copy (must be caught, exact), a reworded
    near-copy (must be caught -- and by the shingle path, since the tf-idf cosine
    stays below its threshold on the morphological rewording), and an unrelated
    item (must NOT be flagged). A "clean" scan is only trustworthy if all three
    hold."""
    train = [("orig", _SELFTEST_ORIGINAL)]
    verbatim = _scan(train, [("copy", _SELFTEST_ORIGINAL)])
    reworded = _scan(train, [("reword", _SELFTEST_REWORD)])
    unrelated = _scan(train, [("other", _SELFTEST_UNRELATED)])

    verbatim_ok = len(verbatim) >= 1 and verbatim[0]["reason"] == "normalized_match"
    # The reworded copy must be caught, and specifically it must be the shingle
    # path that catches it (proving the fuzzy detector adds real coverage over the
    # token-exact cosine, which by construction stays below its own threshold).
    reworded_ok = len(reworded) >= 1 and reworded[0]["reason"] == "fuzzy_shingle"
    unrelated_ok = len(unrelated) == 0
    ok = verbatim_ok and reworded_ok and unrelated_ok
    return {
        "ok": ok,
        "verbatim_caught": verbatim_ok,
        "reworded_caught_by_shingle": reworded_ok,
        "unrelated_not_flagged": unrelated_ok,
        "reworded_cosine": reworded[0]["cosine"] if reworded else None,
        "reworded_fuzzy": reworded[0]["fuzzy"] if reworded else None,
    }


def run(split: dict[str, str] | None = None, **_kwargs: Any) -> dict[str, Any]:
    from eval.split import make_split
    from lsat.ai.gold_set import load_gold_set

    items = load_gold_set()
    if split is None:
        split = make_split(items)
    docs = {
        it["id"]: f"{it['question']} {it['answer']} {it['principle']}" for it in items
    }
    train = [(i, docs[i]) for i in split if split[i] == "train"]
    heldout = [(i, docs[i]) for i in split if split[i] == "heldout"]

    flagged = _scan(train, heldout)
    passed = len(flagged) == 0

    st = detector_self_test()
    self_test_ok = st["ok"]

    return {
        "name": "leakage",
        "passed": passed and self_test_ok,
        "gate": True,
        "flagged": flagged,
        "n_flagged": len(flagged),
        "cosine_threshold": config.LEAK_COSINE_MAX,
        "fuzzy_threshold": config.LEAK_FUZZY_MAX,
        "detector_self_test_ok": self_test_ok,
        "detector_self_test": st,
        "n_train": len(train),
        "n_heldout": len(heldout),
        "detail": f"{len(flagged)} leak(s) in {len(train)}x{len(heldout)} pairs; "
        f"detector self-test {'OK' if self_test_ok else 'FAILED'} "
        f"(verbatim+reworded caught, unrelated clean)",
    }
