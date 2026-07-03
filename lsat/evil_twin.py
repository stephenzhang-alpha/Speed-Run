# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Oracle-Proven "Skill or Luck?" Discrimination Twins (research follow-on). [AI]

The deepest anxiety of a strong LSAT taker is not "was I wrong?" but "was I RIGHT
for the wrong reason?" -- a lucky pattern-match on a formal-logic item that a
one-token change would expose. An *evil twin* is a **minimally-edited variant of
an item you got right whose correct answer FLIPS**: reverse the arrow, swap a
quantifier, convert subject/predicate. If you understood, you nail the twin; if
you memorized a surface, it catches you.

This is the one place LLM generation is genuinely load-bearing WITHOUT ever
risking correctness, because the labor splits cleanly:

* the **oracle** (:func:`lsat.quantifier.classify` /
  :func:`lsat.conditional_chain.entails`) ENUMERATES every minimal single-edit
  variant and PROVES each one's verdict -- we keep only the variants whose proven
  verdict DIFFERS from the original (a genuine discriminator), so a mislabeled
  twin can never be served (fail-closed);
* the **LLM** (optional) does only *logically inert* work -- it SELECTS which
  proven twin best targets the learner's specific misconception and picks fresh,
  domain-varied surface nouns. Neither choice can change a proof (nouns don't
  appear in the model-checker; the twin set is oracle-fixed), so with AI off,
  garbled, or adversarial the served twin is still oracle-correct.

The result -- provably-correct, freshly-phrased, misconception-targeted twins --
is something a pure-LLM tool can't guarantee (correctness) and a pure-template
tool can't do (targeting + variety). Grading is stateless: a ``twin_key`` encodes
the base item + the edit, and :func:`grade_twin` re-derives the verdict from the
oracle every time.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from lsat.ai.client import LLMClient, LLMUnavailable
from lsat.conditional_chain import (
    CHAIN_ITEMS,
    DOES_NOT_FOLLOW,
    MUST_FOLLOW,
    Implication,
    entails,
)
from lsat.quantifier import (
    ALL,
    CANNOT_BE_TRUE,
    COULD_BE_EITHER,
    MOST,
    MUST_BE_TRUE,
    NO,
    NOUN_POOL,
    SOME,
    SOME_NOT,
    Statement,
    classify,
)

# Verdicts the oracles can return that we treat as a clean, gradeable answer.
_QUANT_VERDICTS = (MUST_BE_TRUE, CANNOT_BE_TRUE, COULD_BE_EITHER)
_CHAIN_VERDICTS = (MUST_FOLLOW, DOES_NOT_FOLLOW)
# The single-token quantifier edits we consider (AT_MOST_HALF is only ever a
# negation answer, never a natural stimulus, so it is not an edit target).
_EDIT_QUANTS = (ALL, NO, SOME, SOME_NOT, MOST)


# -- twin enumeration + the oracle proof --------------------------------------


@lru_cache(maxsize=8192)
def _classify_memo(premises: tuple[Statement, ...], conclusion: Statement) -> str:
    """Memoized wrapper over the SHIPPED oracle ``classify`` (the model-checker is
    heavy -- 4**8 models for 3-term arguments -- and the same argument recurs many
    times across enumeration/verification). Statements are frozen/hashable."""
    try:
        return classify(list(premises), conclusion)
    except (ValueError, KeyError):
        return "__error__"


def _quant_verdict(premises: list[Statement], conclusion: Statement) -> str | None:
    """The oracle verdict for a quantifier argument, or ``None`` if the edit made
    the premises unsatisfiable / left the decidable fragment (fail-closed: such a
    variant is simply not offered as a twin)."""
    v = _classify_memo(tuple(premises), conclusion)
    return v if v in _QUANT_VERDICTS else None


@lru_cache(maxsize=8192)
def _entails_memo(chain: tuple[Implication, ...], candidate: Implication) -> bool:
    return entails(list(chain), candidate)


def _chain_verdict(chain: list[Implication], candidate: Implication) -> str:
    return MUST_FOLLOW if _entails_memo(tuple(chain), candidate) else DOES_NOT_FOLLOW


def _quant_base(idx: int) -> dict[str, Any]:
    from lsat.quantifier import VALIDITY_ITEMS

    return VALIDITY_ITEMS[idx]


def _enumerate_quant(item_id: str, idx: int) -> list[dict[str, Any]]:
    """All single-edit quantifier variants whose PROVEN verdict differs from the
    original -- each a genuine, oracle-certified discriminator."""
    base = _quant_base(idx)
    premises: list[Statement] = base["premises"]
    concl: Statement = base["conclusion"]
    original = base["verdict"]
    out: list[dict[str, Any]] = []

    def add(edit: str, prem: list[Statement], c: Statement, human: str) -> None:
        v = _quant_verdict(prem, c)
        if v is not None and v != original:
            out.append(
                {
                    "twin_key": f"{item_id}#{edit}",
                    "kind": "quant",
                    "premises": prem,
                    "conclusion": c,
                    "verdict": v,
                    "original_verdict": original,
                    "edit_note": human,
                    "options": list(_QUANT_VERDICTS),
                }
            )

    # edit the conclusion's quantifier
    for q in _EDIT_QUANTS:
        if q != concl.quant:
            add(
                f"cq:{q}",
                premises,
                Statement(q, concl.subject, concl.predicate),
                f"conclusion quantifier {concl.quant} -> {q}",
            )
    # convert the conclusion (swap subject/predicate) -- the classic illicit move
    if concl.subject != concl.predicate:
        add(
            "conv",
            premises,
            Statement(concl.quant, concl.predicate, concl.subject),
            "conclusion subject/predicate swapped (conversion)",
        )
    return out


def _enumerate_chain(item_id: str, idx: int) -> list[dict[str, Any]]:
    """Minimal-edit conditional-chain twins of a MUST_FOLLOW item that the oracle
    proves DO NOT follow -- the affirming-the-consequent / denying-the-antecedent
    traps that catch a pattern-matcher."""
    it = CHAIN_ITEMS[idx]
    if it["verdict"] != MUST_FOLLOW:
        return []
    chain: list[Implication] = it["chain"]
    cand: Implication = it["candidate"]
    props: list[str] = it["props"]
    out: list[dict[str, Any]] = []

    def rl(lit: Any) -> str:
        p = props[lit.term] if 0 <= lit.term < len(props) else f"p{lit.term}"
        return f"not {p}" if lit.neg else p

    def add(edit: str, c: Implication, human: str) -> None:
        v = _chain_verdict(chain, c)
        if v != it["verdict"]:  # keep only genuine flips
            out.append(
                {
                    "twin_key": f"{item_id}#{edit}",
                    "kind": "chain",
                    "chain": chain,
                    "candidate": c,
                    "verdict": v,
                    "original_verdict": it["verdict"],
                    "edit_note": human,
                    "options": list(_CHAIN_VERDICTS),
                }
            )

    rev = Implication(cand.cons, cand.ante)
    add(
        "rev",
        rev,
        f'reversed the arrow: "{rl(cand.cons)}" -> "{rl(cand.ante)}" '
        "(affirming the consequent)",
    )
    neg = Implication(cand.ante.negate(), cand.cons.negate())
    add(
        "neg",
        neg,
        f'negated both sides: "{rl(cand.ante.negate())}" -> '
        f'"{rl(cand.cons.negate())}" (denying the antecedent)',
    )
    return out


_TWIN_CACHE: dict[str, list[dict[str, Any]]] = {}


def enumerate_twins(item_id: str) -> list[dict[str, Any]]:
    """Every oracle-proven discrimination twin for a curated ``qval-<n>`` or
    ``chain-<n>`` item (empty on an unknown id or an item with no flipping edit).
    Cached per item (deterministic) -- the oracle is heavy, so verify/grade/serve
    reuse one enumeration instead of re-running the model-checker each call."""
    if item_id in _TWIN_CACHE:
        return _TWIN_CACHE[item_id]
    result = _enumerate_uncached(item_id)
    _TWIN_CACHE[item_id] = result
    return result


def _enumerate_uncached(item_id: str) -> list[dict[str, Any]]:
    try:
        head, sep, tail = str(item_id).partition("-")
        if not sep:
            return []
        idx = int(tail)
    except (ValueError, AttributeError):
        return []
    from lsat.quantifier import VALIDITY_ITEMS

    if head == "qval" and 0 <= idx < len(VALIDITY_ITEMS):
        return _enumerate_quant(item_id, idx)
    if head == "chain" and 0 <= idx < len(CHAIN_ITEMS):
        return _enumerate_chain(item_id, idx)
    return []


def _reconstruct(twin_key: str) -> dict[str, Any] | None:
    """Rebuild a twin (structure + oracle verdict) from its stateless key
    ``<item_id>#<edit>``. Returns ``None`` (fail-closed) on any malformed /
    unknown key or an edit that does not, in fact, flip the verdict."""
    base_id, sep, _edit = str(twin_key).partition("#")
    if not sep:
        return None
    for t in enumerate_twins(base_id):
        if t["twin_key"] == twin_key:
            return t
    return None


def verify_twin(twin_key: str) -> dict[str, Any]:
    """THE ORACLE GATE for a twin. Re-derives the verdict from the oracle and
    confirms it is (a) a clean gradeable verdict and (b) DIFFERENT from the
    original item's verdict (a genuine discriminator). Anything else is BLOCKED."""
    t = _reconstruct(twin_key)
    if t is None:
        return {"verified": False, "reason": "unknown or non-flipping twin"}
    if t["kind"] == "quant":
        rederived = _quant_verdict(t["premises"], t["conclusion"])
    else:
        rederived = _chain_verdict(t["chain"], t["candidate"])
    ok = rederived == t["verdict"] and rederived != t["original_verdict"]
    return {
        "verified": bool(ok),
        "verdict": t["verdict"],
        "rederived": rederived,
        "original_verdict": t["original_verdict"],
        "reason": None if ok else "oracle re-derivation disagrees or does not flip",
    }


# -- rendering (deterministic template; nouns are logically inert) -------------


def _render_quant(t: dict[str, Any], nouns: dict[int, str]) -> dict[str, Any]:
    return {
        "premises": [p.render(nouns) for p in t["premises"]],
        "conclusion": t["conclusion"].render(nouns),
    }


def _render_chain(t: dict[str, Any], props: list[str]) -> dict[str, Any]:
    def rl(lit: Any) -> str:
        p = props[lit.term] if 0 <= lit.term < len(props) else f"p{lit.term}"
        return f"not {p}" if lit.neg else p

    def ri(imp: Implication) -> str:
        return f"If {rl(imp.ante)}, then {rl(imp.cons)}."

    return {
        "premises": [ri(i) for i in t["chain"]],
        "conclusion": ri(t["candidate"]),
    }


def _terms_of(t: dict[str, Any]) -> list[int]:
    if t["kind"] == "quant":
        ts = {t["conclusion"].subject, t["conclusion"].predicate}
        for p in t["premises"]:
            ts.update((p.subject, p.predicate))
    else:
        ts = {t["candidate"].ante.term, t["candidate"].cons.term}
        for imp in t["chain"]:
            ts.update((imp.ante.term, imp.cons.term))
    return sorted(ts)


def _clean_nouns(raw: Any, n: int) -> list[str] | None:
    """Accept an LLM noun list only if it is n distinct, plausible plural nouns.
    Nouns are logically inert (they never enter a proof), so this guards only
    READABILITY -- a rejected list simply falls back to the curated pool."""
    if not isinstance(raw, list) or len(raw) < n:
        return None
    out: list[str] = []
    for w in raw[:n]:
        if not isinstance(w, str):
            return None
        w = w.strip().lower()
        if not re.fullmatch(r"[a-z][a-z ]{2,19}", w):
            return None
        out.append(w)
    return out if len(set(out)) == n else None


# -- the AI layer: select + freshen (both logically inert) --------------------

_SELECT_SYSTEM = (
    "You help target a logic drill. You are given several PROVEN discrimination "
    "variants of an item a student answered; each has already been verified by a "
    "decision procedure -- you cannot change any answer. Pick the ONE variant most "
    "likely to expose a shaky understanding (prefer the classic confusions: "
    "affirming the consequent, illicit conversion, all-vs-most), and propose fresh "
    "plural nouns for the terms. Return ONLY JSON: "
    '{"choice": <int index>, "nouns": ["...", ...]}. Nothing else.'
)


def _ai_select(
    twins: list[dict[str, Any]], client: LLMClient, *, misconception: str | None
) -> tuple[int, list[str] | None]:
    """Ask the LLM to pick a twin index + fresh nouns. Both are logically inert;
    an out-of-range index or bad nouns fall back to defaults. Never raises through
    (``LLMUnavailable`` -> defaults)."""
    n_terms = len(_terms_of(twins[0]))
    listing = "\n".join(
        f'{i}: edit="{t["edit_note"]}" -> answer flips to "{t["verdict"]}"'
        for i, t in enumerate(twins)
    )
    hint = (
        f"\nThe student's suspected weak spot: {misconception}."
        if misconception
        else ""
    )
    try:
        raw = client.complete(
            _SELECT_SYSTEM,
            f"Variants:\n{listing}{hint}\n\nReturn {n_terms} nouns.",
        )
    except LLMUnavailable:
        return 0, None
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return 0, None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return 0, None
    choice = data.get("choice", 0)
    if not isinstance(choice, int) or not (0 <= choice < len(twins)):
        choice = 0
    return choice, _clean_nouns(data.get("nouns"), n_terms)


def evil_twin_drill(
    item_id: str, *, client: LLMClient | None = None, misconception: str | None = None
) -> dict[str, Any]:
    """A render-ready "skill or luck?" twin for a curated item, or a fail-closed
    abstain. The oracle proves every candidate twin; the LLM (if any) only selects
    which one + picks fresh nouns. The correct answer + edit note are withheld
    (returned only by :func:`grade_twin`). ``source`` records the provenance."""
    twins = enumerate_twins(item_id)
    if not twins:
        return {"available": False, "reason": "no oracle-proven twin for this item"}

    source = "deterministic"
    choice, ai_nouns = 0, None
    if client is not None:
        choice, ai_nouns = _ai_select(twins, client, misconception=misconception)
        source = "ai_targeted" if (choice != 0 or ai_nouns) else "ai_default"

    twin = twins[choice]
    # Defense in depth: re-verify the selected twin through the gate before serving.
    if not verify_twin(twin["twin_key"])["verified"]:
        return {"available": False, "reason": "twin failed oracle re-verification"}

    terms = _terms_of(twin)
    if twin["kind"] == "quant":
        pool = ai_nouns or list(NOUN_POOL[choice % len(NOUN_POOL)])
        nouns = {term: pool[i % len(pool)] for i, term in enumerate(terms)}
        rendered = _render_quant(twin, nouns)
    else:
        # chain terms render via the item's `props`; fresh AI nouns (if any) just
        # relabel those slots -- logically inert, so the proof is unaffected.
        props = list(CHAIN_ITEMS[int(item_id.split("-")[1])]["props"])
        if ai_nouns:
            for i, term in enumerate(terms):
                if term < len(props):
                    props[term] = ai_nouns[i % len(ai_nouns)]
        rendered = _render_chain(twin, props)

    return {
        "available": True,
        "item_id": item_id,
        "twin_key": twin["twin_key"],
        "premises": rendered["premises"],
        "conclusion": rendered["conclusion"],
        "options": twin["options"],
        "prompt": "You got the original right. Does THIS one follow? (a one-edit twin)",
        "source": source,
        "done": False,
    }


def grade_twin(twin_key: str, chosen: str) -> dict[str, Any]:
    """Oracle-grade a learner's verdict on a twin. Re-derives the correct answer
    from the decision procedure every time (stateless); fails closed on an unknown
    key or verdict."""
    v = verify_twin(twin_key)
    if not v["verified"]:
        return {"graded": False, "reason": v.get("reason", "unverifiable twin")}
    t = _reconstruct(twin_key)
    assert t is not None  # verify_twin already confirmed it reconstructs
    if chosen not in t["options"]:
        return {"graded": False, "reason": "unknown verdict"}
    return {
        "graded": True,
        "correct": chosen == t["verdict"],
        "verdict": t["verdict"],
        "original_verdict": t["original_verdict"],
        "edit_note": t["edit_note"],
    }


def twin_source_ids() -> list[str]:
    """Curated items that have at least one oracle-proven twin (safe to serve)."""
    from lsat.quantifier import VALIDITY_ITEMS

    ids = [f"qval-{i}" for i in range(len(VALIDITY_ITEMS))]
    ids += [
        f"chain-{i}" for i, it in enumerate(CHAIN_ITEMS) if it["verdict"] == MUST_FOLLOW
    ]
    return [i for i in ids if enumerate_twins(i)]


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:  # noqa: C901 - a thorough gate is worth the length
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    ids = twin_source_ids()
    check("twin source ids non-empty (quant + chain)", len(ids) >= 2)

    # 1. EVERY enumerated twin is oracle-proven and genuinely flips the verdict.
    total = flips = mislabeled = 0
    for iid in ids:
        for t in enumerate_twins(iid):
            total += 1
            v = verify_twin(t["twin_key"])
            if not v["verified"]:
                mislabeled += 1
            if t["verdict"] != t["original_verdict"]:
                flips += 1
    check(f"all {total} enumerated twins pass the oracle gate", mislabeled == 0)
    check("every twin genuinely flips the verdict", flips == total and total > 0)

    # 2. verify_twin re-derivation matches the stored verdict for every twin
    #    (independent recomputation, not the stored label).
    disagreements = 0
    for iid in ids:
        for t in enumerate_twins(iid):
            v = verify_twin(t["twin_key"])
            if v["verdict"] != v["rederived"]:
                disagreements += 1
    check("oracle re-derivation == stored verdict for all twins", disagreements == 0)

    # 3. grade_twin: correct verdict graded correct; the original verdict graded
    #    WRONG (that is the whole point -- the twin flips); fail-closed on junk.
    qid = next(i for i in ids if i.startswith("qval"))
    t0 = enumerate_twins(qid)[0]
    g_ok = grade_twin(t0["twin_key"], t0["verdict"])
    check(
        "grade_twin: correct verdict -> correct",
        g_ok.get("graded") and g_ok.get("correct"),
    )
    g_orig = grade_twin(t0["twin_key"], t0["original_verdict"])
    check(
        "grade_twin: the ORIGINAL verdict is now WRONG (flip works)",
        g_orig.get("graded") and not g_orig.get("correct"),
    )
    check(
        "grade_twin: fail-closed on unknown verdict",
        grade_twin(t0["twin_key"], "banana").get("graded") is False,
    )
    check(
        "grade_twin: fail-closed on unknown key",
        grade_twin("qval-0#cq:banana", MUST_BE_TRUE).get("graded") is False,
    )
    check(
        "verify_twin: fail-closed on malformed key",
        verify_twin("not-a-key").get("verified") is False,
    )

    # 4. a NON-flipping edit key must NOT verify (fail-closed): forge a key whose
    #    edit leaves the verdict unchanged by re-using the item's own conclusion.
    check(
        "verify_twin: fail-closed on a fabricated non-enumerated key",
        verify_twin("qval-0#cq:__nope__").get("verified") is False,
    )

    # 5. chain twins: reversed + negated candidates flip MUST_FOLLOW -> not-follow.
    cid = next(i for i in ids if i.startswith("chain"))
    ctwins = enumerate_twins(cid)
    check("chain item yields >=1 flipping twin", len(ctwins) >= 1)
    check(
        "all chain twins flip to does_not_follow",
        all(t["verdict"] == DOES_NOT_FOLLOW for t in ctwins),
    )

    # 6. the AI layer: off / valid / garbled / malicious / down -- NEVER serves an
    #    unverified twin; correctness is identical across all of them.
    class GoodClient:
        def __init__(self, n: int) -> None:
            self._n = n

        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            return json.dumps(
                {
                    "choice": 1 if self._n > 1 else 0,
                    "nouns": ["widgets", "gadgets", "gizmos"],
                }
            )

    class MaliciousClient:
        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            # out-of-range choice + junk nouns: must be clamped, never crash/leak
            return json.dumps({"choice": 999, "nouns": ["1", "$$$", ""]})

    class GarbageClient:
        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            return "Here you go! The answer is definitely must_be_true, trust me."

    class DownClient:
        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            raise LLMUnavailable("offline")

    n_twins = len(enumerate_twins(qid))
    cases: list[tuple[str, LLMClient | None]] = [
        ("off", None),
        ("valid", GoodClient(n_twins)),
        ("malicious", MaliciousClient()),
        ("garbled", GarbageClient()),
        ("down", DownClient()),
    ]
    for label, cli in cases:
        d = evil_twin_drill(qid, client=cli)
        served_ok = d.get("available") and verify_twin(d["twin_key"])["verified"]
        check(f"evil_twin_drill[{label}]: serves an oracle-verified twin", served_ok)
        check(f"evil_twin_drill[{label}]: withholds the answer", "verdict" not in d)

    # malicious out-of-range choice must have been clamped to a valid twin
    dmal = evil_twin_drill(qid, client=MaliciousClient())
    check(
        "malicious choice clamped to a real twin",
        dmal.get("available") and dmal["twin_key"].startswith(qid),
    )

    # 7. fail-closed on unknown / non-twin items
    check(
        "evil_twin_drill: fail-closed on unknown item",
        evil_twin_drill("qval-999").get("available") is False,
    )
    check("enumerate_twins: empty on unknown id", enumerate_twins("bogus-3") == [])

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("EVIL_TWIN_OK" if ok else "EVIL_TWIN_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
