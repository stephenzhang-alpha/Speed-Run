# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Quantifier Reasoning Drill Suite (DECISION-round3 #1: merged #12 validity +
#13 negation).

``skill.quantifier_logic`` is a high-weight cross-cutting LR primitive that the
deck only *tags*, never *drills*. This module is the deterministic engine for two
drills over categorical/quantifier statements (all / no / some / some-not / most):

  * **validity** -- given premises + a candidate conclusion, is it ``MUST_BE_TRUE``,
    ``CANNOT_BE_TRUE`` (contradicts the premises), or ``COULD_BE_EITHER``? This is
    the LSAT "must be true / cannot be true / could be true" judgment and attacks
    the classic error classes: illicit conversion (``all X are Y`` ⊬ ``all Y are
    X``), the undistributed middle, and the two-``most`` overlap.
  * **negation** -- what is the precise logical negation of a statement? The one
    students miss most: ¬(``most X are Y``) is **"at most half of X are Y"**, and
    ¬(``all X are Y``) is ``some X are not Y`` (not ``no X are Y``).

**Why this can never mis-teach (the correctness gate).** The curated tables
(:data:`VALIDITY_ITEMS`, :data:`NEGATION`) are the single runtime source of truth,
but they are *proven*, not asserted: a bounded Venn-region model-checker
(:func:`classify` / :func:`_is_negation`) enumerates every region-cardinality
assignment over the ≤3 terms and derives each verdict from first principles.
:func:`_selftest` runs that oracle over every curated entry and every classic
named theorem; a wrong table entry fails the suite. Grading FAILS CLOSED: an item
id or negation form outside the verified tables returns ``graded: False`` and the
caller shows the worked answer.

The English rendering is *generated* from the structured statements (there is no
fragile English parsing here, unlike :mod:`lsat.conditional`), so surface terms
can be swapped freely for held-out eval without touching the logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

# -- quantifier statements ----------------------------------------------------

ALL = "all"
NO = "no"
SOME = "some"
SOME_NOT = "some_not"
MOST = "most"
AT_MOST_HALF = "at_most_half"  # only produced as the negation of MOST

QUANTIFIERS = (ALL, NO, SOME, SOME_NOT, MOST, AT_MOST_HALF)

# Verdicts for the validity drill (LSAT vocabulary).
MUST_BE_TRUE = "must_be_true"
CANNOT_BE_TRUE = "cannot_be_true"
COULD_BE_EITHER = "could_be_either"


@dataclass(frozen=True)
class Statement:
    """A categorical/quantifier statement ``<quant> <subject> are <predicate>``.

    ``subject``/``predicate`` are abstract term ids (small ints); rendering maps
    them onto surface nouns. Frozen so statements are hashable set members."""

    quant: str
    subject: int
    predicate: int

    def render(self, nouns: dict[int, str]) -> str:
        s, p = nouns[self.subject], nouns[self.predicate]
        if self.quant == ALL:
            return f"All {s} are {p}"
        if self.quant == NO:
            return f"No {s} are {p}"
        if self.quant == SOME:
            return f"Some {s} are {p}"
        if self.quant == SOME_NOT:
            return f"Some {s} are not {p}"
        if self.quant == MOST:
            return f"Most {s} are {p}"
        if self.quant == AT_MOST_HALF:
            return f"At most half of {s} are {p}"
        raise ValueError(f"unknown quantifier {self.quant!r}")  # pragma: no cover


# -- bounded Venn-region model-checker (the proof oracle) ---------------------
#
# A "model" assigns a non-negative integer count to each region of the Venn
# diagram over the terms in play. A region is the subset of terms an element is
# INSIDE; for k terms there are 2**k regions. `_CAP` bounds each region's count.
# Every categorical/`most` inference over <=3 terms that has a counterexample has
# a *small* one (majorities are distinguishable at 2-vs-1), so a small cap is
# sound; we use 3 with a safety margin and the self-test cross-checks named
# theorems whose answers are known analytically.
_CAP = 3


def _regions(terms: tuple[int, ...]) -> list[frozenset[int]]:
    out: list[frozenset[int]] = []
    for bits in product((False, True), repeat=len(terms)):
        out.append(frozenset(t for t, inside in zip(terms, bits) if inside))
    return out


def _both(model: dict[frozenset[int], int], a: int, b: int, *, b_inside: bool) -> int:
    """Count of elements inside `a` and (inside/outside) `b`."""
    return sum(
        n
        for region, n in model.items()
        if (a in region) and ((b in region) == b_inside)
    )


def _holds(st: Statement, model: dict[frozenset[int], int]) -> bool:
    s, p = st.subject, st.predicate
    s_and_p = _both(model, s, p, b_inside=True)
    s_not_p = _both(model, s, p, b_inside=False)
    if st.quant == ALL:  # no S outside P
        return s_not_p == 0
    if st.quant == NO:  # no S inside P
        return s_and_p == 0
    if st.quant == SOME:  # at least one S inside P
        return s_and_p >= 1
    if st.quant == SOME_NOT:  # at least one S outside P
        return s_not_p >= 1
    if st.quant == MOST:  # strict majority of S inside P
        return s_and_p > s_not_p
    if st.quant == AT_MOST_HALF:  # exact complement of MOST
        return s_and_p <= s_not_p
    raise ValueError(f"unknown quantifier {st.quant!r}")  # pragma: no cover


def _all_models(terms: tuple[int, ...], cap: int = _CAP):
    regions = _regions(terms)
    for counts in product(range(cap + 1), repeat=len(regions)):
        yield dict(zip(regions, counts))


def classify(
    premises: list[Statement], conclusion: Statement, *, cap: int = _CAP
) -> str:
    """Derive the verdict of ``premises ⊢? conclusion`` by exhaustive bounded
    model-checking. ``MUST_BE_TRUE`` if every premise-satisfying model satisfies
    the conclusion; ``CANNOT_BE_TRUE`` if none do; else ``COULD_BE_EITHER``. This
    is the independent oracle that proves the curated tables in :func:`_selftest`.
    ``cap`` bounds each region's cardinality; the self-test asserts the verdict is
    stable across caps (so cap-3 is provably adequate, incl. the MOST fragment).
    """
    terms = tuple(
        sorted(
            {conclusion.subject, conclusion.predicate}
            | {t for st in premises for t in (st.subject, st.predicate)}
        )
    )
    sat_premises = 0
    sat_both = 0
    for model in _all_models(terms, cap):
        if all(_holds(pr, model) for pr in premises):
            sat_premises += 1
            if _holds(conclusion, model):
                sat_both += 1
    if sat_premises == 0:  # premises self-contradictory -> not a valid drill item
        return "premises_unsatisfiable"
    if sat_both == sat_premises:
        return MUST_BE_TRUE
    if sat_both == 0:
        return CANNOT_BE_TRUE
    return COULD_BE_EITHER


def _is_negation(a: Statement, b: Statement) -> bool:
    """True iff ``b`` is the exact logical negation of ``a`` -- i.e. over every
    bounded model, exactly one of ``a``/``b`` holds (they partition model space)."""
    if a.subject != b.subject or a.predicate != b.predicate:
        return False
    terms = (a.subject, a.predicate)
    for model in _all_models(terms):
        if _holds(a, model) == _holds(b, model):
            return False
    return True


# -- curated drill tables (runtime source of truth; proven in _selftest) ------

# Abstract term ids used by the templates.
_X, _Y, _Z = 0, 1, 2


def _s(q: str, subj: int, pred: int) -> Statement:
    return Statement(q, subj, pred)


# Validity drill: premises + candidate conclusion + the curated verdict + a short
# teaching note naming the principle. Verdicts are PROVEN by classify() in the
# self-test, so this table cannot silently ship a wrong answer.
VALIDITY_ITEMS: list[dict[str, Any]] = [
    {
        "premises": [_s(ALL, _X, _Y), _s(ALL, _Y, _Z)],
        "conclusion": _s(ALL, _X, _Z),
        "verdict": MUST_BE_TRUE,
        "note": "Chained universals (Barbara): X⊆Y and Y⊆Z force X⊆Z.",
    },
    {
        "premises": [_s(ALL, _X, _Y)],
        "conclusion": _s(ALL, _Y, _X),
        "verdict": COULD_BE_EITHER,
        "note": "Illicit conversion: 'all X are Y' does NOT give 'all Y are X'.",
    },
    {
        "premises": [_s(NO, _X, _Y)],
        "conclusion": _s(NO, _Y, _X),
        "verdict": MUST_BE_TRUE,
        "note": "'No' converts: no X are Y ⇔ no Y are X.",
    },
    {
        "premises": [_s(SOME, _X, _Y)],
        "conclusion": _s(SOME, _Y, _X),
        "verdict": MUST_BE_TRUE,
        "note": "'Some' converts: some X are Y ⇔ some Y are X.",
    },
    {
        "premises": [_s(MOST, _X, _Y), _s(MOST, _X, _Z)],
        "conclusion": _s(SOME, _Y, _Z),
        "verdict": MUST_BE_TRUE,
        "note": "Two-most overlap: two majorities of X must share a member.",
    },
    {
        "premises": [_s(MOST, _X, _Y), _s(MOST, _Y, _Z)],
        "conclusion": _s(MOST, _X, _Z),
        "verdict": COULD_BE_EITHER,
        "note": "'Most' does NOT chain: most X are Y, most Y are Z ⊬ most X are Z.",
    },
    {
        "premises": [_s(ALL, _X, _Y), _s(SOME, _Y, _Z)],
        "conclusion": _s(SOME, _X, _Z),
        "verdict": COULD_BE_EITHER,
        "note": "Undistributed middle: the 'some Y' need not be the X's.",
    },
    {
        "premises": [_s(ALL, _X, _Y), _s(NO, _Y, _Z)],
        "conclusion": _s(NO, _X, _Z),
        "verdict": MUST_BE_TRUE,
        "note": "Celarent: X⊆Y and Y disjoint from Z ⇒ X disjoint from Z.",
    },
    {
        "premises": [_s(SOME_NOT, _X, _Y)],
        "conclusion": _s(SOME_NOT, _Y, _X),
        "verdict": COULD_BE_EITHER,
        "note": "'Some are not' does NOT convert.",
    },
    {
        "premises": [_s(MOST, _X, _Y)],
        "conclusion": _s(SOME, _X, _Y),
        "verdict": MUST_BE_TRUE,
        "note": "'Most' implies 'some': a majority is at least one.",
    },
    {
        "premises": [_s(SOME, _X, _Y), _s(SOME, _X, _Z)],
        "conclusion": _s(SOME, _Y, _Z),
        "verdict": COULD_BE_EITHER,
        "note": "Two 'somes' need not overlap.",
    },
    {
        "premises": [_s(ALL, _X, _Y)],
        "conclusion": _s(SOME_NOT, _X, _Y),
        "verdict": CANNOT_BE_TRUE,
        "note": "'All X are Y' directly contradicts 'some X are not Y'.",
    },
    {
        "premises": [_s(NO, _X, _Y)],
        "conclusion": _s(SOME, _X, _Y),
        "verdict": CANNOT_BE_TRUE,
        "note": "'No X are Y' directly contradicts 'some X are Y'.",
    },
    {
        "premises": [_s(ALL, _X, _Y), _s(NO, _Y, _Z)],
        "conclusion": _s(SOME, _X, _Z),
        "verdict": CANNOT_BE_TRUE,
        "note": "X⊆Y and Y disjoint from Z ⇒ no X is a Z.",
    },
]

# Negation drill: statement -> its exact logical negation. Proven by _is_negation.
NEGATION: dict[str, str] = {
    ALL: SOME_NOT,  # ¬(all S are P)      = some S are not P
    NO: SOME,  # ¬(no S are P)       = some S are P
    SOME: NO,  # ¬(some S are P)     = no S are P
    SOME_NOT: ALL,  # ¬(some S are not P) = all S are P
    MOST: AT_MOST_HALF,  # ¬(most S are P)     = at most half of S are P
    AT_MOST_HALF: MOST,
}


def negate_statement(st: Statement) -> Statement:
    """Return the exact logical negation of ``st`` (same subject/predicate)."""
    return Statement(NEGATION[st.quant], st.subject, st.predicate)


# -- surface instantiation ----------------------------------------------------

# Novel, neutral plural nouns; the drill instantiates abstract X/Y/Z with a rotating
# triple so repeated structures don't wear a groove (grading is structural).
NOUN_POOL: list[tuple[str, str, str]] = [
    ("artists", "chemists", "dancers"),
    ("editors", "farmers", "guides"),
    ("hikers", "jurors", "knights"),
    ("lawyers", "mentors", "nurses"),
    ("pilots", "quakers", "runners"),
    ("sailors", "tailors", "voters"),
]


def _nouns(idx: int) -> dict[int, str]:
    a, b, c = NOUN_POOL[idx % len(NOUN_POOL)]
    return {_X: a, _Y: b, _Z: c}


def validity_drill_items() -> list[dict[str, Any]]:
    """Every validity item rendered with a rotating noun triple + its curated
    verdict/note. Deterministic; safe to serve (all verdicts are proven)."""
    items: list[dict[str, Any]] = []
    for i, it in enumerate(VALIDITY_ITEMS):
        nouns = _nouns(i)
        items.append(
            {
                "item_id": f"qval-{i}",
                "premises": [pr.render(nouns) for pr in it["premises"]],
                "conclusion": it["conclusion"].render(nouns),
                "verdict": it["verdict"],
                "note": it["note"],
            }
        )
    return items


# The negation prompts we drill (AT_MOST_HALF is only ever an answer option,
# never a prompt -- it doesn't arise as a natural stimulus).
_NEG_PROMPT_QUANTS = (ALL, NO, SOME, SOME_NOT, MOST)

# For each prompt: the correct negation FIRST, then targeted distractors (the
# tempting confusions -- e.g. 'no' for ¬all, 'most-not' for ¬most). The client
# shuffles; grading is by quantifier key so order is presentation-only.
NEGATION_OPTION_QUANTS: dict[str, list[str]] = {
    ALL: [SOME_NOT, NO, SOME, MOST],
    NO: [SOME, ALL, SOME_NOT, MOST],
    SOME: [NO, ALL, SOME_NOT, AT_MOST_HALF],
    SOME_NOT: [ALL, NO, SOME, MOST],
    MOST: [AT_MOST_HALF, SOME_NOT, NO, ALL],
}


def negation_drill_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, q in enumerate(_NEG_PROMPT_QUANTS):
        nouns = _nouns(i)
        st = Statement(q, _X, _Y)
        neg = negate_statement(st)
        options = [
            {"quant": oq, "text": Statement(oq, _X, _Y).render(nouns)}
            for oq in NEGATION_OPTION_QUANTS[q]
        ]
        items.append(
            {
                "item_id": f"qneg-{i}",
                "quant": q,
                "sentence": st.render(nouns),
                "options": options,
                "answer": neg.quant,
                "answer_text": neg.render(nouns),
            }
        )
    return items


# -- grading (fail-closed) ----------------------------------------------------


def _item_index(item_id: Any, prefix: str, n: int) -> int:
    """Parse ``<prefix>-<i>`` -> ``i``, requiring the EXACT prefix and
    ``0 <= i < n``. Raises ValueError/IndexError otherwise so the caller fails
    closed -- a ``qneg-`` id must never be graded as a ``qval-`` item, and vice
    versa (adversarial-review Finding 4)."""
    head, sep, tail = str(item_id).partition("-")
    if head != prefix or not sep:
        raise ValueError("wrong item prefix")
    idx = int(tail)  # raises ValueError on non-int
    if not 0 <= idx < n:
        raise IndexError
    return idx


def grade_validity(item_id: str, chosen: str) -> dict[str, Any]:
    """Grade a validity judgment against the curated (proven) verdict. Fails
    closed (``graded: False``) on an unknown item id or an unknown verdict label."""
    try:
        idx = _item_index(item_id, "qval", len(VALIDITY_ITEMS))
    except (ValueError, IndexError):
        return {"graded": False, "reason": "unknown quantifier-validity item"}
    if chosen not in (MUST_BE_TRUE, CANNOT_BE_TRUE, COULD_BE_EITHER):
        return {"graded": False, "reason": "unknown verdict"}
    it = VALIDITY_ITEMS[idx]
    correct = chosen == it["verdict"]
    return {
        "graded": True,
        "correct": correct,
        "verdict": it["verdict"],
        "note": it["note"],
    }


def grade_negation(item_id: str, chosen: str) -> dict[str, Any]:
    """Grade a negation choice (the chosen quantifier form) against the exact
    logical negation. Fails closed on an unknown item id or quantifier."""
    try:
        idx = _item_index(item_id, "qneg", len(_NEG_PROMPT_QUANTS))
    except (ValueError, IndexError):
        return {"graded": False, "reason": "unknown quantifier-negation item"}
    if chosen not in QUANTIFIERS:
        return {"graded": False, "reason": "unknown quantifier form"}
    prompt_q = _NEG_PROMPT_QUANTS[idx]
    answer_q = NEGATION[prompt_q]
    return {
        "graded": True,
        "correct": chosen == answer_q,
        "answer": answer_q,
    }


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # 1. The model-checker itself, cross-checked against classic named theorems
    # whose verdicts are known analytically (independent of the curated table).
    named = [
        ("Barbara", [_s(ALL, _X, _Y), _s(ALL, _Y, _Z)], _s(ALL, _X, _Z), MUST_BE_TRUE),
        ("illicit conversion", [_s(ALL, _X, _Y)], _s(ALL, _Y, _X), COULD_BE_EITHER),
        (
            "two-most overlap",
            [_s(MOST, _X, _Y), _s(MOST, _X, _Z)],
            _s(SOME, _Y, _Z),
            MUST_BE_TRUE,
        ),
        (
            "most-not-chain",
            [_s(MOST, _X, _Y), _s(MOST, _Y, _Z)],
            _s(MOST, _X, _Z),
            COULD_BE_EITHER,
        ),
        (
            "all contradicts some-not",
            [_s(ALL, _X, _Y)],
            _s(SOME_NOT, _X, _Y),
            CANNOT_BE_TRUE,
        ),
    ]
    for label, prem, conc, want in named:
        check(f"model-checker: {label}", classify(prem, conc) == want)

    # 1b. CAP ADEQUACY (adversarial-review Test C): the shipped verdict uses cap 3,
    # but cap-3 soundness -- especially for the MOST fragment (two-most overlap,
    # most-not-chain, most->some) -- must be proven, not assumed at the same cap it
    # runs at. Assert every curated + named verdict is IDENTICAL at cap 3 and cap 5.
    # (A valid inference has no counterexample at any cardinality; an invalid one has
    # a witness at <=3-per-region since majorities distinguish at 2-vs-1, so a higher
    # cap cannot change a verdict -- this makes that concrete + regression-proof.)
    cap_stable = True
    for prem, conc in (
        [(it["premises"], it["conclusion"]) for it in VALIDITY_ITEMS]
        + [(p, c) for _, p, c, _ in named]
    ):
        if classify(prem, conc, cap=3) != classify(prem, conc, cap=5):
            cap_stable = False
    check("verdicts identical at cap 3 and cap 5 (MOST fragment included)", cap_stable)

    # 2. Every curated validity verdict is PROVEN by the independent oracle.
    for i, it in enumerate(VALIDITY_ITEMS):
        got = classify(it["premises"], it["conclusion"])
        check(
            f"validity[{i}] table == model-checker ({it['verdict']})",
            got == it["verdict"],
        )
    # every curated verdict is one of the three legal labels
    check(
        "all curated verdicts are legal labels",
        all(
            it["verdict"] in (MUST_BE_TRUE, CANNOT_BE_TRUE, COULD_BE_EITHER)
            for it in VALIDITY_ITEMS
        ),
    )
    # all three verdict classes are represented (a real drill, not all-one-answer)
    labels = {it["verdict"] for it in VALIDITY_ITEMS}
    check(
        "validity drill covers all three verdicts",
        labels == {MUST_BE_TRUE, CANNOT_BE_TRUE, COULD_BE_EITHER},
    )

    # 3. Every negation entry is PROVEN the exact complement, and is an involution.
    for q in QUANTIFIERS:
        st = Statement(q, _X, _Y)
        neg = negate_statement(st)
        check(f"negation[{q}] is the exact logical complement", _is_negation(st, neg))
        check(f"double-negation[{q}] returns the original", negate_statement(neg) == st)
    # the specifically-tricky ones stated explicitly
    check("¬(most) == at most half", NEGATION[MOST] == AT_MOST_HALF)
    check("¬(all) == some-not (NOT 'no')", NEGATION[ALL] == SOME_NOT)

    # every negation option set contains the correct answer, has no duplicates,
    # and never offers the prompt statement itself (an always-wrong freebie).
    for q in _NEG_PROMPT_QUANTS:
        opts = NEGATION_OPTION_QUANTS[q]
        check(f"negation options[{q}] contain the answer", NEGATION[q] in opts)
        check(f"negation options[{q}] have no duplicates", len(opts) == len(set(opts)))
        check(f"negation options[{q}] omit the prompt quant itself", q not in opts)

    # 4. Grading: correct, wrong, and fail-closed.
    g = grade_validity("qval-0", MUST_BE_TRUE)  # Barbara
    check("grade_validity: correct", g["graded"] and g["correct"])
    g2 = grade_validity("qval-1", MUST_BE_TRUE)  # illicit conversion is COULD
    check("grade_validity: wrong -> not correct", g2["graded"] and not g2["correct"])
    check(
        "grade_validity: fail-closed on bad id",
        grade_validity("qval-999", MUST_BE_TRUE)["graded"] is False,
    )
    check(
        "grade_validity: fail-closed on bad verdict",
        grade_validity("qval-0", "banana")["graded"] is False,
    )
    check(
        "grade_validity: fail-closed on negative id",
        grade_validity("qval--1", MUST_BE_TRUE)["graded"] is False,
    )
    # Finding 4: a wrong/absent prefix must fail closed, not grade a valid index.
    check(
        "grade_validity: fail-closed on wrong prefix (qneg-/x-/bare int)",
        grade_validity("qneg-2", MUST_BE_TRUE)["graded"] is False
        and grade_validity("x-2", MUST_BE_TRUE)["graded"] is False
        and grade_validity("2", MUST_BE_TRUE)["graded"] is False,
    )
    check(
        "grade_negation: fail-closed on wrong prefix (qval-)",
        grade_negation("qval-0", SOME_NOT)["graded"] is False,
    )

    gn = grade_negation("qneg-0", SOME_NOT)  # ¬(all)
    check("grade_negation: correct", gn["graded"] and gn["correct"])
    gn2 = grade_negation("qneg-0", NO)  # the classic trap answer
    check(
        "grade_negation: 'no' is the wrong negation of 'all'",
        gn2["graded"] and not gn2["correct"],
    )
    check(
        "grade_negation: fail-closed on bad id",
        grade_negation("qneg-999", ALL)["graded"] is False,
    )

    # 5. Rendering + item generators are JSON-shaped and non-empty.
    vi = validity_drill_items()
    ni = negation_drill_items()
    check(
        "validity_drill_items non-empty + carry verdict",
        len(vi) == len(VALIDITY_ITEMS) and all(x["verdict"] for x in vi),
    )
    check(
        "negation_drill_items non-empty + carry answer",
        len(ni) == len(_NEG_PROMPT_QUANTS) and all(x["answer"] for x in ni),
    )
    check(
        "rendered conclusion reads as English",
        vi[0]["conclusion"].startswith("All ") and " are " in vi[0]["conclusion"],
    )

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("QUANTIFIER_OK" if ok else "QUANTIFIER_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
