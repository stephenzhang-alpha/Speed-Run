# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Conditional-Chain Trainer (DECISION-round4 #22, deterministic).

The single-conditional drill (:mod:`lsat.conditional`) deliberately abstains on
compound/nested sentences, so it never touches the case where LSAT working-memory
load actually bites: **multi-arrow chains** ("If A then B; if B then C; ...") and
their contrapositives. This drill presents a chain of 3+ conditionals and asks
whether a candidate inference **must follow** or **does not follow** -- training
transitive chaining + the contrapositive, and the two classic errors (affirming
the consequent / denying the antecedent).

**Why it can't mis-teach.** Chains are STRUCTURED (implications over literals),
rendered to prose for display -- there is no fragile free-text parsing. Validity is
graded by **exact material entailment** (:func:`entails`): enumerate every boolean
assignment; ``a->b`` must-follows iff no premise-satisfying model has ``a`` true and
``b`` false. This is complete -- it catches the tautological-consequent and vacuous
cases that a pure reachability check misses. Reachability with contrapositive edges
(:func:`_reachable_entails`) is kept as the human-explainable chaining intuition and
is proven **sound** (never over-claims) against the exact grader over 500 random
chains in :func:`_selftest`; the curated verdicts are proven == the exact grader.
Grading fails **closed** on an unknown item.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

MUST_FOLLOW = "must_follow"
DOES_NOT_FOLLOW = "does_not_follow"
VERDICTS = (MUST_FOLLOW, DOES_NOT_FOLLOW)


@dataclass(frozen=True, slots=True)
class Lit:
    """A literal: a term id, possibly negated."""

    term: int
    neg: bool = False

    def negate(self) -> Lit:
        return Lit(self.term, not self.neg)


@dataclass(frozen=True, slots=True)
class Implication:
    ante: Lit
    cons: Lit

    def contrapositive(self) -> Implication:
        return Implication(self.cons.negate(), self.ante.negate())


def _edges(implications: list[Implication]) -> dict[Lit, set[Lit]]:
    """Directed edges for the implication graph: each ``a->b`` adds ``a->b`` AND
    its contrapositive ``not b -> not a``."""
    edges: dict[Lit, set[Lit]] = {}
    for imp in implications:
        for e in (imp, imp.contrapositive()):
            edges.setdefault(e.ante, set()).add(e.cons)
    return edges


def _reachable(edges: dict[Lit, set[Lit]], start: Lit) -> set[Lit]:
    seen: set[Lit] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt in edges.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def _reachable_entails(implications: list[Implication], candidate: Implication) -> bool:
    """A SOUND-but-incomplete fast check: ``b`` reachable from ``a`` in the
    implication+contrapositive graph. Reachability captures transitive chaining
    (the pedagogy we teach + explain), but it MISSES entailments that don't ride a
    path -- e.g. a consequent forced true as a fact (``a->b`` & ``not a -> b`` make
    b always true) or a vacuously-true candidate. So it never over-claims (proven
    in the self-test) but is not the grader; :func:`entails` is."""
    edges = _edges(implications)
    return candidate.cons in _reachable(edges, candidate.ante)


# -- exact grader: material entailment by truth-table enumeration -------------


def _terms(implications: list[Implication], candidate: Implication) -> list[int]:
    ts = {candidate.ante.term, candidate.cons.term}
    for imp in implications:
        ts.add(imp.ante.term)
        ts.add(imp.cons.term)
    return sorted(ts)


def _lit_true(lit: Lit, assign: dict[int, bool]) -> bool:
    v = assign[lit.term]
    return (not v) if lit.neg else v


def _first_counterexample(
    implications: list[Implication], candidate: Implication
) -> dict[int, bool] | None:
    """The shared enumeration behind :func:`entails` and :func:`counterexample`:
    return the FIRST assignment that satisfies every premise while making the
    candidate's antecedent true and its consequent false (a genuine countermodel),
    or ``None`` when no such assignment exists (i.e. the candidate is entailed)."""
    terms = _terms(implications, candidate)
    for bits in product((False, True), repeat=len(terms)):
        assign = dict(zip(terms, bits))
        if not all(
            (not _lit_true(i.ante, assign)) or _lit_true(i.cons, assign)
            for i in implications
        ):
            continue  # not a model of the premises
        if _lit_true(candidate.ante, assign) and not _lit_true(candidate.cons, assign):
            return assign  # counterexample: premises hold, ante true, cons false
    return None


def entails(implications: list[Implication], candidate: Implication) -> bool:
    """EXACT material entailment (the authoritative 'must follow' grader): premises
    ⊨ (ante -> cons)? True iff every assignment that satisfies all premises (each
    ``a->b`` as a material conditional) also satisfies ``(not ante) or cons`` -- i.e.
    there is no counterexample with the candidate's antecedent true and consequent
    false. Complete: it captures the tautological-consequent and vacuous cases that
    reachability misses."""
    return _first_counterexample(implications, candidate) is None


def counterexample(
    implications: list[Implication], candidate: Implication
) -> dict[int, bool] | None:
    """A concrete countermodel witnessing that ``candidate`` does NOT follow: a
    truth assignment (term id -> bool) satisfying every premise with the
    candidate's antecedent true and its consequent false. Returns ``None`` when the
    candidate is entailed (no such world exists). This is the same enumeration
    :func:`entails` runs, surfacing the witnessing world instead of just ``False`` --
    the uniquely convincing "here is a world where your premises all hold but your
    conclusion fails"."""
    return _first_counterexample(implications, candidate)


def render_world(assignment: dict[int, bool], props: list[str]) -> list[str]:
    """Render a countermodel :func:`counterexample` returned to prose lines, one per
    term in id order (e.g. ``"the alarm sounds = TRUE"``). A term outside ``props``
    falls back to ``p<id>``. JSON-safe (plain strings)."""
    lines: list[str] = []
    for term in sorted(assignment):
        name = props[term] if 0 <= term < len(props) else f"p{term}"
        lines.append(f"{name} = {'TRUE' if assignment[term] else 'FALSE'}")
    return lines


# -- curated drill chains (structured; verdicts proven by the oracle) ---------
# term ids 0..n; rendered to prose via a per-chain proposition list.

_A, _B, _C, _D, _E = 0, 1, 2, 3, 4


def _imp(a: int, b: int, *, na: bool = False, nb: bool = False) -> Implication:
    return Implication(Lit(a, na), Lit(b, nb))


# Each item: chain (implications), candidate, expected verdict, teaching note,
# and the proposition phrases for rendering (index = term id).
CHAIN_ITEMS: list[dict[str, Any]] = [
    {
        "chain": [_imp(_A, _B), _imp(_B, _C), _imp(_C, _D)],
        "candidate": _imp(_A, _D),
        "verdict": MUST_FOLLOW,
        "note": "Transitivity: A->B->C->D chains to A->D.",
        "props": [
            "the alarm sounds",
            "the guard is called",
            "the gate locks",
            "the log is updated",
        ],
    },
    {
        "chain": [_imp(_A, _B), _imp(_B, _C), _imp(_C, _D)],
        "candidate": _imp(_D, _A),
        "verdict": DOES_NOT_FOLLOW,
        "note": "Affirming the consequent: A->...->D does NOT give D->A.",
        "props": [
            "the alarm sounds",
            "the guard is called",
            "the gate locks",
            "the log is updated",
        ],
    },
    {
        "chain": [_imp(_A, _B), _imp(_B, _C), _imp(_C, _D)],
        "candidate": _imp(_D, _A, na=True, nb=True),  # not D -> not A
        "verdict": MUST_FOLLOW,
        "note": "Contrapositive of the whole chain: not D -> not A.",
        "props": [
            "the alarm sounds",
            "the guard is called",
            "the gate locks",
            "the log is updated",
        ],
    },
    {
        "chain": [_imp(_A, _B), _imp(_B, _C), _imp(_C, _D)],
        "candidate": _imp(_A, _D, na=True, nb=True),  # not A -> not D
        "verdict": DOES_NOT_FOLLOW,
        "note": "Denying the antecedent: not A does NOT give not D.",
        "props": [
            "the alarm sounds",
            "the guard is called",
            "the gate locks",
            "the log is updated",
        ],
    },
    {
        # a contrapositive-stated link: 'if not C then not B' == B->C
        "chain": [_imp(_A, _B), _imp(_C, _B, na=True, nb=True), _imp(_C, _D)],
        "candidate": _imp(_A, _D),
        "verdict": MUST_FOLLOW,
        "note": "'If not C then not B' is B->C; so A->B->C->D gives A->D.",
        "props": [
            "the bill passes",
            "the budget balances",
            "revenue rises",
            "the surplus grows",
        ],
    },
    {
        # branch: A->B, A->C, B->D ; C->D not stated
        "chain": [_imp(_A, _B), _imp(_A, _C), _imp(_B, _D)],
        "candidate": _imp(_C, _D),
        "verdict": DOES_NOT_FOLLOW,
        "note": "C shares a cause with B but nothing links C to D.",
        "props": [
            "the grant is approved",
            "the lab expands",
            "hiring starts",
            "output doubles",
        ],
    },
    {
        "chain": [_imp(_A, _B), _imp(_A, _C), _imp(_B, _D)],
        "candidate": _imp(_A, _D),
        "verdict": MUST_FOLLOW,
        "note": "A->B and B->D chain to A->D (the C branch is irrelevant).",
        "props": [
            "the grant is approved",
            "the lab expands",
            "hiring starts",
            "output doubles",
        ],
    },
    {
        # 4-hop with a contrapositive query mid-chain
        "chain": [_imp(_A, _B), _imp(_B, _C), _imp(_C, _D), _imp(_D, _E)],
        "candidate": _imp(_C, _A, na=True, nb=True),  # not C -> not A
        "verdict": MUST_FOLLOW,
        "note": "not C -> not B -> not A (contrapositive up the chain).",
        "props": ["A", "B", "C", "D", "E"],
    },
]


def _render_lit(lit: Lit, props: list[str]) -> str:
    p = props[lit.term]
    return f"not {p}" if lit.neg else p


def _render_imp(imp: Implication, props: list[str]) -> str:
    return f"If {_render_lit(imp.ante, props)}, then {_render_lit(imp.cons, props)}."


def drill_items() -> list[dict[str, Any]]:
    """The curated chain drills rendered to prose, each with its proven verdict.
    Deterministic; safe to serve (every verdict is oracle-proven in the self-test)."""
    out: list[dict[str, Any]] = []
    for i, it in enumerate(CHAIN_ITEMS):
        props = it["props"]
        out.append(
            {
                "item_id": f"chain-{i}",
                "premises": [_render_imp(imp, props) for imp in it["chain"]],
                "candidate": _render_imp(it["candidate"], props),
                "verdict": it["verdict"],
                "note": it["note"],
            }
        )
    return out


def grade_chain(item_id: str, chosen: str) -> dict[str, Any]:
    """Grade a must-follow / does-not-follow judgment against the curated (proven)
    verdict. Fails closed on an unknown item id or verdict."""
    try:
        head, sep, tail = str(item_id).partition("-")
        if head != "chain" or not sep:
            raise ValueError
        idx = int(tail)
        if not 0 <= idx < len(CHAIN_ITEMS):
            raise IndexError
    except (ValueError, IndexError):
        return {"graded": False, "reason": "unknown chain item"}
    if chosen not in VERDICTS:
        return {"graded": False, "reason": "unknown verdict"}
    it = CHAIN_ITEMS[idx]
    return {
        "graded": True,
        "correct": chosen == it["verdict"],
        "verdict": it["verdict"],
        "note": it["note"],
    }


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    import random

    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # 1. every curated verdict matches the EXACT grader; and for the must_follow
    # items the reachability explanation actually finds the path (so the taught
    # chaining/contrapositive story is valid for what we serve).
    for i, it in enumerate(CHAIN_ITEMS):
        exact = entails(it["chain"], it["candidate"])
        want = it["verdict"] == MUST_FOLLOW
        check(f"chain[{i}] exact grader == curated ({it['verdict']})", exact == want)
        if want:
            check(
                f"chain[{i}] reachability explains the must_follow",
                _reachable_entails(it["chain"], it["candidate"]),
            )

    # 2. both verdicts are represented (a real drill)
    check(
        "drill covers both verdicts",
        {it["verdict"] for it in CHAIN_ITEMS} == set(VERDICTS),
    )

    # 3. SOUNDNESS regression: reachability must NEVER over-claim vs the exact
    # grader (reachable => entailed) over random chains. It may under-claim (that is
    # exactly why reachability is not the grader) -- so we assert implication, not
    # equality.
    rng = random.Random(2024)
    unsound = 0
    for _ in range(500):
        nterms = rng.randint(3, 5)
        k = rng.randint(2, 4)
        impls = []
        for _ in range(k):
            a, b = rng.sample(range(nterms), 2)
            impls.append(_imp(a, b, na=rng.random() < 0.3, nb=rng.random() < 0.3))
        ca, cb = rng.sample(range(nterms), 2)
        cand = _imp(ca, cb, na=rng.random() < 0.3, nb=rng.random() < 0.3)
        if _reachable_entails(impls, cand) and not entails(impls, cand):
            unsound += 1  # reachability said yes but exact said no -> over-claim
    check(
        f"reachability is sound vs exact over 500 random chains ({unsound} over-claims)",
        unsound == 0,
    )

    # 3b. counterexample() agrees with entails() and returns a REAL countermodel:
    # for a does-not-follow candidate the witnessing world satisfies every premise
    # yet makes the candidate false; for a must-follow candidate it is None.
    for i, it in enumerate(CHAIN_ITEMS):
        cx = counterexample(it["chain"], it["candidate"])
        entailed = entails(it["chain"], it["candidate"])
        check(f"chain[{i}] counterexample is None iff entailed", (cx is None) == entailed)
        if cx is not None:
            premises_hold = all(
                (not _lit_true(imp.ante, cx)) or _lit_true(imp.cons, cx)
                for imp in it["chain"]
            )
            cand = it["candidate"]
            falsifies = _lit_true(cand.ante, cx) and not _lit_true(cand.cons, cx)
            check(f"chain[{i}] countermodel satisfies premises + falsifies candidate",
                  premises_hold and falsifies)
            world = render_world(cx, it["props"])
            check(f"chain[{i}] render_world: one line per assigned term",
                  len(world) == len(cx) and all(" = " in ln for ln in world))

    # 4. grading: correct, wrong, fail-closed
    g = grade_chain("chain-0", MUST_FOLLOW)
    check("grade: correct", g["graded"] and g["correct"])
    g2 = grade_chain("chain-0", DOES_NOT_FOLLOW)
    check("grade: wrong -> not correct", g2["graded"] and not g2["correct"])
    check(
        "grade: fail-closed on bad id",
        grade_chain("chain-999", MUST_FOLLOW)["graded"] is False,
    )
    check(
        "grade: fail-closed on bad prefix",
        grade_chain("x-0", MUST_FOLLOW)["graded"] is False,
    )
    check(
        "grade: fail-closed on bad verdict",
        grade_chain("chain-0", "banana")["graded"] is False,
    )

    # 5. drill_items shape
    di = drill_items()
    check(
        "drill_items non-empty + carry verdict + >=3-arrow chains",
        len(di) == len(CHAIN_ITEMS)
        and all(x["verdict"] for x in di)
        and all(len(x["premises"]) >= 3 for x in di),
    )

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("CHAIN_OK" if ok else "CHAIN_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
