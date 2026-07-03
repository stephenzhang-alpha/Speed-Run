# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Necessary/Sufficient Four-Cell Discrimination Drill (DECISION-round4 #5).

The single most-confused LR distinction: a **necessary** assumption is one the
argument cannot do without (negate it and the argument collapses), while a
**sufficient** assumption is one that, if added, *makes* the conclusion follow.
Students routinely pick a sufficient (too-strong) choice on a Necessary-Assumption
question and vice-versa. This drill has the learner sort a candidate statement
into one of four cells -- necessary-only / sufficient-only / both / neither --
over interleaved items, training the discrimination itself.

**Why it can't mis-teach.** The cell is DERIVED, not authored: it reuses the
bounded Venn model-checker proven correct in :mod:`lsat.quantifier`
(:func:`classify`) as an oracle over the categorical fragment:

    sufficient(A)  <=>  P + [A]            entails the conclusion   (MUST_BE_TRUE)
    necessary(A)   <=>  P + [not A]  makes the conclusion impossible (CANNOT_BE_TRUE)

The necessary side is literally the LSAT **negation test**. :func:`_selftest`
proves every curated cell with that oracle AND cross-checks the necessary side
against the equivalent entailment form (P + [conclusion] entails A). Grading fails
**closed**: a malformed item (premises that already contradict the conclusion, or
a candidate outside the categorical fragment) abstains rather than mis-sort.
"""

from __future__ import annotations

from typing import Any

from lsat.quantifier import (
    ALL,
    CANNOT_BE_TRUE,
    COULD_BE_EITHER,
    MUST_BE_TRUE,
    NO,
    SOME,
    Statement,
    classify,
    negate_statement,
)

NECESSARY_ONLY = "necessary_only"
SUFFICIENT_ONLY = "sufficient_only"
BOTH = "both"
NEITHER = "neither"
CELLS = (NECESSARY_ONLY, SUFFICIENT_ONLY, BOTH, NEITHER)

CELL_LABEL: dict[str, str] = {
    NECESSARY_ONLY: "Necessary, not sufficient",
    SUFFICIENT_ONLY: "Sufficient, not necessary",
    BOTH: "Both necessary and sufficient",
    NEITHER: "Neither",
}


def _sufficient(premises: list[Statement], conclusion: Statement, cand: Statement):
    """True/False, or None if the premises+candidate are self-contradictory."""
    verdict = classify([*premises, cand], conclusion)
    if verdict == "premises_unsatisfiable":
        return None
    return verdict == MUST_BE_TRUE


def _necessary(premises: list[Statement], conclusion: Statement, cand: Statement):
    """The LSAT negation test: assume NOT the candidate; is the conclusion now
    impossible? Returns True/False, or None if premises+not-candidate are
    self-contradictory (can't run the test)."""
    verdict = classify([*premises, negate_statement(cand)], conclusion)
    if verdict == "premises_unsatisfiable":
        return None
    return verdict == CANNOT_BE_TRUE


def classify_assumption(
    premises: list[Statement], conclusion: Statement, candidate: Statement
) -> dict[str, Any]:
    """Sort ``candidate`` into a four-cell (necessary/sufficient) label, or abstain.

    Returns ``{available: True, cell, sufficient, necessary}`` on a confident
    derivation, else ``{available: False, reason}`` (fail-closed)."""
    # Any statement outside the categorical fragment (an unknown quantifier) makes
    # the model-checker / negation raise; treat that as fail-closed abstain, not a
    # crash, so the "abstains outside the fragment" guarantee actually holds.
    try:
        gap = classify(premises, conclusion)
        # the argument must have a genuine GAP: the conclusion is neither already
        # entailed (nothing to assume) nor impossible (incoherent) given premises.
        # Only COULD_BE_EITHER is a real Necessary/Sufficient-Assumption argument.
        if gap != COULD_BE_EITHER:
            return {
                "available": False,
                "reason": "not a gap argument (conclusion already settled or impossible)",
            }
        suf = _sufficient(premises, conclusion, candidate)
        nec = _necessary(premises, conclusion, candidate)
    except (ValueError, KeyError):
        return {"available": False, "reason": "statement outside the categorical fragment"}
    if suf is None or nec is None:
        # suf is None: the candidate CONTRADICTS a premise (P + [A] unsatisfiable).
        # nec is None: the candidate is ENTAILED by the premises (P + [not A]
        # unsatisfiable), so the negation test is ill-defined. Either way it is not
        # a meaningful assumption to sort -> abstain rather than emit a shaky cell.
        return {
            "available": False,
            "reason": "candidate already contradicts or is entailed by the premises",
        }
    if nec and suf:
        cell = BOTH
    elif nec:
        cell = NECESSARY_ONLY
    elif suf:
        cell = SUFFICIENT_ONLY
    else:
        cell = NEITHER
    return {"available": True, "cell": cell, "sufficient": suf, "necessary": nec}


def grade_assumption(
    premises: list[Statement], conclusion: Statement, candidate: Statement, chosen: str
) -> dict[str, Any]:
    """Grade a learner's four-cell choice against the derived cell. Fails closed
    on an unclassifiable item or an unknown cell label."""
    parsed = classify_assumption(premises, conclusion, candidate)
    if not parsed.get("available"):
        return {"graded": False, **parsed}
    if chosen not in CELLS:
        return {"graded": False, "reason": "unknown cell"}
    return {
        "graded": True,
        "correct": chosen == parsed["cell"],
        "cell": parsed["cell"],
        "label": CELL_LABEL[parsed["cell"]],
        "necessary": parsed["necessary"],
        "sufficient": parsed["sufficient"],
    }


# -- curated drill items (structured; cells PROVEN by the model-checker) -------
_X, _Y, _Z = 0, 1, 2


def _s(q: str, subj: int, pred: int) -> Statement:
    return Statement(q, subj, pred)


# Each item: premises, conclusion, candidate, expected cell, teaching note.
# Interleaves necessary-leaning and sufficient-leaning stems (NA + SA practice).
DRILL_ITEMS: list[dict[str, Any]] = [
    {
        "premises": [_s(ALL, _X, _Y)],
        "conclusion": _s(ALL, _X, _Z),
        "candidate": _s(ALL, _Y, _Z),
        "cell": SUFFICIENT_ONLY,
        "note": "'All Y are Z' MAKES the conclusion follow, but the argument only "
        "needs the X-part of Y to be Z -- so it's sufficient, not necessary.",
    },
    {
        "premises": [_s(ALL, _X, _Y)],
        "conclusion": _s(SOME, _X, _Z),
        "candidate": _s(SOME, _Y, _Z),
        "cell": NECESSARY_ONLY,
        "note": "If some X are Z (and all X are Y) then some Y are Z -- so the "
        "argument needs it (necessary); but it alone doesn't force 'some X are Z'.",
    },
    {
        "premises": [],
        "conclusion": _s(NO, _Y, _X),
        "candidate": _s(NO, _X, _Y),
        "cell": BOTH,
        "note": "'No X are Y' and 'No Y are X' are equivalent (conversion) -- each "
        "is both necessary and sufficient for the other.",
    },
    {
        "premises": [_s(ALL, _X, _Y)],
        "conclusion": _s(ALL, _X, _Z),
        "candidate": _s(SOME, _X, _Y),
        "cell": NEITHER,
        "note": "'Some X are Y' is already implied-ish and does nothing for the "
        "X->Z link -- neither necessary nor sufficient.",
    },
    {
        "premises": [_s(ALL, _Y, _Z)],
        "conclusion": _s(ALL, _X, _Z),
        "candidate": _s(ALL, _X, _Y),
        "cell": SUFFICIENT_ONLY,
        "note": "Adding 'all X are Y' chains with 'all Y are Z' to force the "
        "conclusion (sufficient); but X could reach Z another way, so not necessary.",
    },
    {
        "premises": [],
        "conclusion": _s(SOME, _Y, _X),
        "candidate": _s(SOME, _X, _Y),
        "cell": BOTH,
        "note": "'Some X are Y' converts to 'some Y are X' -- equivalent, so both.",
    },
    {
        "premises": [_s(ALL, _X, _Y)],
        "conclusion": _s(NO, _X, _Z),
        "candidate": _s(NO, _Y, _Z),
        "cell": SUFFICIENT_ONLY,
        "note": "'No Y are Z' with 'all X are Y' forces 'no X are Z' (sufficient); "
        "but the argument could hold with some non-X Y being Z, so not necessary.",
    },
    {
        "premises": [],
        "conclusion": _s(SOME, _X, _Z),
        "candidate": _s(ALL, _X, _Y),
        "cell": NEITHER,
        "note": "'All X are Y' is about Y, irrelevant to the X->Z existence claim.",
    },
]

# neutral surface nouns for rendering; the STRUCTURE is what's graded
_NOUNS: list[tuple[str, str, str]] = [
    ("artists", "chemists", "dancers"),
    ("editors", "farmers", "guides"),
    ("hikers", "jurors", "knights"),
    ("lawyers", "mentors", "nurses"),
]


def drill_items() -> list[dict[str, Any]]:
    """The curated NA/SA discrimination drills, rendered with rotating nouns +
    their derived cell. Deterministic; safe to serve (every cell is proven)."""
    out: list[dict[str, Any]] = []
    for i, it in enumerate(DRILL_ITEMS):
        a, b, c = _NOUNS[i % len(_NOUNS)]
        nouns = {_X: a, _Y: b, _Z: c}
        parsed = classify_assumption(it["premises"], it["conclusion"], it["candidate"])
        out.append(
            {
                "item_id": f"nsq-{i}",
                "premises": [p.render(nouns) for p in it["premises"]],
                "conclusion": it["conclusion"].render(nouns),
                "candidate": it["candidate"].render(nouns),
                "cell": parsed.get("cell"),
                "note": it["note"],
            }
        )
    return out


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # every curated cell is PROVEN by the model-checker oracle
    for i, it in enumerate(DRILL_ITEMS):
        parsed = classify_assumption(it["premises"], it["conclusion"], it["candidate"])
        check(
            f"item[{i}] derived cell == curated ({it['cell']})",
            parsed.get("available") and parsed.get("cell") == it["cell"],
        )
        # Consistency check (NOT independent assurance): necessary via the negation
        # test <=> P+[conclusion] entails the candidate. These are a logical
        # tautology (P∧¬A⊨¬C ⟺ P∧C⊨A), so this only catches an implementation slip
        # in ONE path, never a shared definitional error -- the independent guard is
        # the higher-cap oracle regression below (adversarial-review Finding 3).
        if parsed.get("available"):
            equiv = classify([*it["premises"], it["conclusion"]], it["candidate"])
            nec_via_entailment = equiv == MUST_BE_TRUE
            check(
                f"item[{i}] negation-test == entailment form (consistency)",
                parsed["necessary"] == nec_via_entailment,
            )

    # all four cells represented (a real discrimination drill)
    cells = {it["cell"] for it in DRILL_ITEMS}
    check("drill covers all four cells", cells == set(CELLS))

    # grading: correct, wrong, fail-closed
    it0 = DRILL_ITEMS[0]
    g = grade_assumption(
        it0["premises"], it0["conclusion"], it0["candidate"], it0["cell"]
    )
    check("grade: correct", g["graded"] and g["correct"])
    wrong = NEITHER if it0["cell"] != NEITHER else BOTH
    g2 = grade_assumption(it0["premises"], it0["conclusion"], it0["candidate"], wrong)
    check("grade: wrong -> not correct", g2["graded"] and not g2["correct"])
    check(
        "grade: fail-closed on unknown cell",
        grade_assumption(it0["premises"], it0["conclusion"], it0["candidate"], "x")[
            "graded"
        ]
        is False,
    )

    # fail-closed on a self-contradictory argument (premises force NOT conclusion)
    bad = classify_assumption([_s(NO, _X, _Y)], _s(SOME, _X, _Y), _s(ALL, _X, _Z))
    check("fail-closed on incoherent premises->conclusion", bad["available"] is False)

    # fail-closed (not crash) on a statement outside the categorical fragment
    # (adversarial-review Finding 4): an unknown quantifier must ABSTAIN.
    oof = classify_assumption(
        [_s(ALL, _X, _Y)], _s(ALL, _X, _Z), Statement("frobnicate", _X, _Z)
    )
    check("fail-closed (no crash) outside the fragment", oof["available"] is False)

    # drill_items carries the derived cell
    check(
        "drill_items non-empty + carry cell",
        len(drill_items()) == len(DRILL_ITEMS)
        and all(d.get("cell") for d in drill_items()),
    )

    # REGRESSION (independent oracle): over many random small categorical
    # arguments, classify_assumption must NEVER emit a cell that disagrees with an
    # INDEPENDENT higher-cardinality-cap enumerator (a bug in the shared checker or
    # the necessary/sufficient formalization would show up as a wrong cell). It may
    # abstain more often (fail-closed) -- only a non-abstaining DISAGREEMENT fails.
    import itertools
    import random

    from lsat.quantifier import MOST, SOME_NOT

    ocap = 4  # independent, higher than the shipped _CAP=3

    def _oholds(st: Statement, model: dict) -> bool:
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

    def _omodels(terms: tuple[int, ...]):
        rs = [
            frozenset(t for t, b in zip(terms, bits) if b)
            for bits in itertools.product((0, 1), repeat=len(terms))
        ]
        for counts in itertools.product(range(ocap + 1), repeat=len(rs)):
            yield dict(zip(rs, counts))

    def _oracle(prem, concl, cand):
        terms = (0, 1)
        P = [m for m in _omodels(terms) if all(_oholds(p, m) for p in prem)]
        PC = [m for m in P if _oholds(concl, m)]
        if not P or len(PC) in (0, len(P)):
            return None  # unsat premises or no gap -> shipped should abstain
        PA = [m for m in P if _oholds(cand, m)]
        suf = len(PA) > 0 and all(_oholds(concl, m) for m in PA)
        nec = all(_oholds(cand, m) for m in PC)
        return (
            BOTH
            if nec and suf
            else NECESSARY_ONLY
            if nec
            else SUFFICIENT_ONLY
            if suf
            else NEITHER
        )

    quants = [ALL, NO, SOME, SOME_NOT, MOST]
    rng = random.Random(2024)
    wrong_cell = 0
    checked = 0

    def _rs():
        a, b = rng.sample([0, 1], 2)
        return Statement(rng.choice(quants), a, b)

    for _ in range(200):  # bounded: keep the self-test snappy (the review's oracle
        # already ran exhaustively at higher cap); this is a gross-breakage guard.
        prem = [_rs()] if rng.random() < 0.6 else []
        concl, cand = _rs(), _rs()
        got = classify_assumption(prem, concl, cand)
        o = _oracle(prem, concl, cand)
        if got.get("available") and o is not None:
            checked += 1
            if got["cell"] != o:
                wrong_cell += 1
    check(
        f"independent oracle: 0 wrong cells over {checked} classified random args",
        wrong_cell == 0,
    )

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("ASSUMPTION_OK" if ok else "ASSUMPTION_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
