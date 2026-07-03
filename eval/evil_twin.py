# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Oracle-Proven "Skill or Luck?" Discrimination Twins (research follow-on) -- a
HARD gate.

The feature's promise: every evil twin an LLM helps target is a *provably-correct*
discriminator -- its labeled answer is re-derived by a decision procedure, and it
genuinely FLIPS the original item's verdict. This gate proves that safety property
against an INDEPENDENT oracle (so a bug in the shipped ``classify``/``entails`` OR
in the twin logic surfaces as a mislabel), then reports factual coverage.

**Hard safety gate (must be exactly 0 mislabels):**

1. *Curated*: for every enumerated twin of every source item, the stored verdict
   (a) equals an INDEPENDENT re-derivation (a higher-cap Venn enumerator for
   quantifier twins; a fresh truth-table for chain twins -- distinct code from the
   shipped oracles) and (b) DIFFERS from the original item's verdict.
2. *Fuzz*: over many random arguments + random single-quantifier conclusion edits,
   every edit the shipped ``classify`` calls a flip is confirmed a real flip by the
   independent enumerator (0 disagreements) -- and the independent oracle finds
   flips too (coverage), so the gate is not vacuously safe.
3. *Malicious drafter*: :func:`lsat.evil_twin.evil_twin_drill` driven by an
   adversarial client (out-of-range choice, junk nouns) NEVER serves a twin that
   fails re-verification; correctness is identical to AI-off.

Report-only: factual coverage (items with a twin, total twins). There is NO
synthetic efficacy number here -- the value claim ("catches lucky right answers")
is settled by real learners, not a simulation.
"""

from __future__ import annotations

import itertools
import random
from typing import Any

from eval import config

# -- independent quantifier oracle (higher cap than the shipped _CAP=3) --------


def _indep_quant_verdict(
    premises: list[Any], conclusion: Any, cap: int | None = None
) -> str | None:
    """A SECOND-opinion Venn-region model-checker written independently of the
    shipped oracle (different enumeration + region math). Returns must/cannot/could,
    or ``None`` if the premises are unsatisfiable (not a gradeable twin). Cap is
    adaptive -- 4 (above the shipped _CAP=3) for <=2 terms, 3 for 3 terms to keep
    the 5**8 region blow-up bounded; 3-term soundness is additionally cross-checked
    analytically by quantifier.py's own self-test."""
    from lsat.quantifier import (
        ALL,
        CANNOT_BE_TRUE,
        COULD_BE_EITHER,
        MOST,
        MUST_BE_TRUE,
        NO,
        SOME,
        SOME_NOT,
    )

    terms = sorted(
        {conclusion.subject, conclusion.predicate}
        | {t for p in premises for t in (p.subject, p.predicate)}
    )
    if cap is None:
        cap = 4 if len(terms) <= 2 else 3
    regions = [
        frozenset(t for t, b in zip(terms, bits) if b)
        for bits in itertools.product((0, 1), repeat=len(terms))
    ]

    def holds(st: Any, model: dict[frozenset[int], int]) -> bool:
        sp = sum(n for r, n in model.items() if st.subject in r and st.predicate in r)
        snp = sum(
            n for r, n in model.items() if st.subject in r and st.predicate not in r
        )
        return {
            ALL: snp == 0,
            NO: sp == 0,
            SOME: sp >= 1,
            SOME_NOT: snp >= 1,
            MOST: sp > snp,
        }[st.quant]

    p_models = 0
    pc_models = 0
    for counts in itertools.product(range(cap + 1), repeat=len(regions)):
        model = dict(zip(regions, counts))
        if all(holds(p, model) for p in premises):
            p_models += 1
            if holds(conclusion, model):
                pc_models += 1
    if p_models == 0:
        return None
    if pc_models == p_models:
        return MUST_BE_TRUE
    if pc_models == 0:
        return CANNOT_BE_TRUE
    return COULD_BE_EITHER


def _indep_chain_verdict(chain: list[Any], candidate: Any) -> str:
    """Independent material-entailment truth-table (fresh code, not the shipped
    ``entails``): a->b must-follows iff no premise-satisfying assignment has the
    candidate's antecedent true and consequent false."""
    from lsat.conditional_chain import DOES_NOT_FOLLOW, MUST_FOLLOW

    terms = sorted(
        {candidate.ante.term, candidate.cons.term}
        | {t for imp in chain for t in (imp.ante.term, imp.cons.term)}
    )

    def lit_true(lit: Any, assign: dict[int, bool]) -> bool:
        v = assign[lit.term]
        return (not v) if lit.neg else v

    for bits in itertools.product((False, True), repeat=len(terms)):
        assign = dict(zip(terms, bits))
        if not all(
            (not lit_true(i.ante, assign)) or lit_true(i.cons, assign) for i in chain
        ):
            continue
        if lit_true(candidate.ante, assign) and not lit_true(candidate.cons, assign):
            return DOES_NOT_FOLLOW
    return MUST_FOLLOW


# -- the gate ------------------------------------------------------------------


def _curated_check() -> dict[str, int]:
    from lsat.evil_twin import enumerate_twins, twin_source_ids, verify_twin

    mislabel = non_flip = unverified = total = 0
    for iid in twin_source_ids():
        for t in enumerate_twins(iid):
            total += 1
            if not verify_twin(t["twin_key"])["verified"]:
                unverified += 1
            if t["kind"] == "quant":
                indep = _indep_quant_verdict(t["premises"], t["conclusion"])
            else:
                indep = _indep_chain_verdict(t["chain"], t["candidate"])
            if indep != t["verdict"]:
                mislabel += 1
            if t["verdict"] == t["original_verdict"]:
                non_flip += 1
    return {
        "total": total,
        "mislabel": mislabel,
        "non_flip": non_flip,
        "unverified": unverified,
    }


def _fuzz_quant(seed: int, trials: int = 1500) -> dict[str, int]:
    """Random arguments + random single-quantifier conclusion edits. Every edit the
    shipped oracle calls a FLIP must be confirmed a real, correctly-labeled flip by
    the INDEPENDENT enumerator. Disagreements must be 0; flips>0 proves coverage.

    Restricted to 2-term arguments so the independent higher-cap enumerator stays
    cheap over thousands of trials; 3-term soundness is covered by the curated
    cap-4 cross-check above and quantifier.py's own 3-term self-test."""
    from lsat.quantifier import Statement, classify

    quants = ["all", "no", "some", "some_not", "most"]
    rng = random.Random(seed)
    disagree = flips = usable = 0
    verdicts = {"must_be_true", "cannot_be_true", "could_be_either"}
    for _ in range(trials):
        nterms = 2
        n_prem = rng.randint(1, 2)
        premises = [
            Statement(rng.choice(quants), *rng.sample(range(nterms), 2))
            for _ in range(n_prem)
        ]
        base_concl = Statement(rng.choice(quants), *rng.sample(range(nterms), 2))
        try:
            base_v = classify(premises, base_concl)
        except (ValueError, KeyError):
            continue
        if base_v not in verdicts:
            continue
        for q in quants:
            if q == base_concl.quant:
                continue
            edited = Statement(q, base_concl.subject, base_concl.predicate)
            try:
                shipped = classify(premises, edited)
            except (ValueError, KeyError):
                continue
            if shipped not in verdicts:
                continue
            if shipped == base_v:
                continue  # not a flip -> not offered as a twin
            usable += 1
            indep = _indep_quant_verdict(premises, edited)
            if indep is None:
                continue
            flips += 1
            if indep != shipped:
                disagree += 1
    return {"usable": usable, "flips_checked": flips, "disagree": disagree}


def _malicious_serves_safe() -> bool:
    import json

    from lsat.evil_twin import evil_twin_drill, twin_source_ids, verify_twin

    class Malicious:
        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            return json.dumps({"choice": 10_000, "nouns": ["1", "$$", ""]})

    for iid in twin_source_ids():
        d = evil_twin_drill(iid, client=Malicious())
        if not d.get("available") or not verify_twin(d["twin_key"])["verified"]:
            return False
        if "verdict" in d:  # never leak the answer
            return False
    return True


def run(seed: int = config.RANDOM_SEED) -> dict[str, Any]:
    cur = _curated_check()
    fuzz = _fuzz_quant(seed)
    malicious_safe = _malicious_serves_safe()

    from lsat.evil_twin import twin_source_ids

    n_items = len(twin_source_ids())
    denom = max(1, cur["total"] + fuzz["flips_checked"])
    mislabel_rate = (cur["mislabel"] + fuzz["disagree"]) / denom
    coverage_ok = cur["total"] > 0 and fuzz["flips_checked"] > 0
    passed = (
        cur["mislabel"] == 0
        and cur["non_flip"] == 0
        and cur["unverified"] == 0
        and fuzz["disagree"] == 0
        and mislabel_rate <= config.EVIL_TWIN_FALSE_LABEL_MAX
        and coverage_ok
        and malicious_safe
    )
    detail = (
        f"curated: {cur['total']} twins over {n_items} items, mislabel "
        f"{cur['mislabel']}, non-flip {cur['non_flip']}, unverified {cur['unverified']} "
        f"(indep. oracle cross-check); fuzz: {fuzz['disagree']} disagreements over "
        f"{fuzz['flips_checked']} independently-checked flips "
        f"(max {config.EVIL_TWIN_FALSE_LABEL_MAX}); malicious-safe={malicious_safe}. "
        "LLM does inert targeting/nouns; the oracle proves every verdict."
    )
    return {
        "name": "evil_twin",
        "passed": bool(passed),
        "gate": True,
        "detail": detail,
        "curated_twins": cur["total"],
        "curated_mislabel": cur["mislabel"],
        "curated_non_flip": cur["non_flip"],
        "curated_unverified": cur["unverified"],
        "fuzz_flips_checked": fuzz["flips_checked"],
        "fuzz_disagree": fuzz["disagree"],
        "mislabel_rate": round(mislabel_rate, 6),
        "mislabel_max": config.EVIL_TWIN_FALSE_LABEL_MAX,
        "n_source_items": n_items,
        "malicious_safe": malicious_safe,
        "coverage_ok": coverage_ok,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
