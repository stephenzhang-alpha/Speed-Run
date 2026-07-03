# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Conditional Translation Drill (DECISION-round2 #19).

``skill.conditional_logic`` is the taxonomy's highest-weight (0.9) cross-cutting
LR primitive, and today it is only *tagged* on cards, never *drilled* as a formal
skill. This module is the deterministic engine for a translation drill: turn an
English conditional into its ``sufficient -> necessary`` arrow and its
contrapositive, and grade a learner's identification of those parts.

**Grading is fully deterministic (no LLM) and FAIL-CLOSED.** A mis-graded
conditional would teach the *wrong* rule, so :func:`parse_conditional` recognizes
only a fixed, unit-tested set of connective forms (if/then, only if, unless,
no/all/only, requires, sufficient/necessary for) applied to a *single, simple*
conditional. It **hard-abstains** in two ways: (1) no rule matches, and (2) a rule
matches but a captured clause still contains a connective or relative pronoun --
the signature of a compound ("... if and only if ..."), nested ("if S, then N,
unless M") or relative-clause ("every dog that is trained is calm") sentence whose
flat split can't be trusted (see :data:`_CLAUSE_AMBIGUOUS`). On either abstain the
caller shows the worked answer rather than grading. The parser is deliberately
narrow: it prefers a false *abstain* over a confident wrong arrow. The phrasing
table below is the single source of truth; :func:`_selftest` pins each curated
sentence's exact arrow AND asserts the adversarial forms abstain.

Formal rules encoded:
- ``if S, then N`` / ``if S, N``            -> S -> N
- ``S only if N``                           -> S -> N   (only if marks the necessary)
- ``S unless N`` / ``unless N, S``          -> not N -> S   (unless == if not)
- ``no S are N``                            -> S -> not N
- ``all/every S are N``                     -> S -> N
- ``only S are N`` / ``only S can N``       -> N -> S   (only marks the necessary)
- ``S requires N``                          -> S -> N
- ``N is required/necessary for S``         -> S -> N
- ``S is sufficient for N``                 -> S -> N
Contrapositive of ``A -> B`` is ``not B -> not A``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Term:
    text: str
    negated: bool = False

    def negate(self) -> Term:
        return Term(self.text, not self.negated)

    def render(self) -> str:
        return f"not ({self.text})" if self.negated else self.text


@dataclass(frozen=True)
class Conditional:
    sufficient: Term
    necessary: Term

    @property
    def arrow(self) -> str:
        return f"{self.sufficient.render()} -> {self.necessary.render()}"

    def contrapositive(self) -> Conditional:
        # A -> B  <=>  not B -> not A
        return Conditional(self.necessary.negate(), self.sufficient.negate())


def _clean(clause: str) -> str:
    """Trim a clause to its core predicate and canonicalize to lowercase (so the
    rendered arrow is case-stable; grading compares via _norm_term regardless)."""
    c = clause.strip().strip(",.;:").strip().lower()
    c = re.sub(r"^(that|then)\s+", "", c)
    return c.strip()


# A captured clause that STILL contains a connective or a (dangling) relative
# pronoun is the tell-tale of a bad split: the greedy `(.+?)` anchored on the
# first copula/connective will happily match compound ("... if and only if ..."),
# nested ("if you study, then you pass, unless ...") or relative-clause
# ("every dog THAT IS trained is calm") sentences and return a *wrong* arrow.
# The drill would then teach the wrong rule, so we treat any such clause as
# unparseable and abstain -- this is what makes the parser genuinely fail-closed,
# not merely on total non-matches. (Curated DRILL_SENTENCES contain none of these
# words in their clauses; the self-test pins that + the adversarial abstains.)
_CLAUSE_AMBIGUOUS = re.compile(
    r"\b(if|then|unless|and|or|iff|that|who|whom|which|whose|either|neither|both)\b",
    re.I,
)


# Ordered (pattern, builder) rules. The FIRST match wins, so more-specific forms
# (e.g. "only if", "no ... unless") precede the general "if". Each builder returns
# a Conditional or None (None -> keep trying / abstain). Groups are the raw
# clauses; _clean normalizes them.
def _build(suff: str, nec: str, *, suff_neg: bool = False, nec_neg: bool = False):
    s, n = _clean(suff), _clean(nec)
    if not s or not n:
        return None
    # Fail-closed: a residual connective/relative pronoun means the flat split
    # can't be trusted -> abstain rather than emit a confidently-wrong arrow.
    if _CLAUSE_AMBIGUOUS.search(s) or _CLAUSE_AMBIGUOUS.search(n):
        return None
    return Conditional(Term(s, suff_neg), Term(n, nec_neg))


_RULES: list[tuple[re.Pattern[str], Any]] = [
    # "no S are/is N" -> S -> not N   (before "all"/"only")
    (
        re.compile(r"^no\s+(.+?)\s+(?:are|is)\s+(.+)$", re.I),
        lambda m: _build(m.group(1), m.group(2), nec_neg=True),
    ),
    # "unless N, S" (group1=N, group2=S) -> not N -> S
    (
        re.compile(r"^unless\s+(.+?),\s+(.+)$", re.I),
        lambda m: _build(m.group(1), m.group(2), suff_neg=True),
    ),
    # "S unless N" (group1=S, group2=N) -> not N -> S
    (
        re.compile(r"^(.+?)\s+unless\s+(.+)$", re.I),
        lambda m: _build(m.group(2), m.group(1), suff_neg=True),
    ),
    # "if S, then N" / "if S then N" / "if S, N"
    (
        re.compile(r"^if\s+(.+?)(?:,\s*then\s+|\s+then\s+|,\s*)(.+)$", re.I),
        lambda m: _build(m.group(1), m.group(2)),
    ),
    # "S only if N" -> S -> N
    (
        re.compile(r"^(.+?)\s+only\s+if\s+(.+)$", re.I),
        lambda m: _build(m.group(1), m.group(2)),
    ),
    # "only S are/is/can N" -> N -> S
    (
        re.compile(r"^only\s+(.+?)\s+(?:are|is|can)\s+(.+)$", re.I),
        lambda m: _build(m.group(2), m.group(1)),
    ),
    # "all/every S are/is N" -> S -> N
    (
        re.compile(r"^(?:all|every|each)\s+(.+?)\s+(?:are|is)\s+(.+)$", re.I),
        lambda m: _build(m.group(1), m.group(2)),
    ),
    # "N is required/necessary for S" -> S -> N
    (
        re.compile(r"^(.+?)\s+is\s+(?:required|necessary)\s+for\s+(.+)$", re.I),
        lambda m: _build(m.group(2), m.group(1)),
    ),
    # "S is sufficient for N" -> S -> N
    (
        re.compile(r"^(.+?)\s+is\s+sufficient\s+for\s+(.+)$", re.I),
        lambda m: _build(m.group(1), m.group(2)),
    ),
    # "S requires N" -> S -> N
    (
        re.compile(r"^(.+?)\s+requires\s+(.+)$", re.I),
        lambda m: _build(m.group(1), m.group(2)),
    ),
]


def parse_conditional(sentence: str) -> dict[str, Any]:
    """Parse an English conditional into its arrow + contrapositive, or abstain.

    Returns ``{available: True, sufficient, necessary, arrow, contrapositive}`` on
    a confident parse, else ``{available: False, reason}`` (the caller shows the
    worked answer instead of grading -- fail-closed, never mis-teach).
    """
    s = (sentence or "").strip().rstrip(".")
    for pattern, builder in _RULES:
        m = pattern.match(s)
        if not m:
            continue
        cond = builder(m)
        if cond is None:
            continue
        contra = cond.contrapositive()
        return {
            "available": True,
            "sufficient": cond.sufficient.render(),
            "necessary": cond.necessary.render(),
            "arrow": cond.arrow,
            "contrapositive": contra.arrow,
        }
    return {
        "available": False,
        "reason": "Could not confidently translate this conditional; showing the worked answer.",
    }


def _norm_term(text: str) -> str:
    """Normalize a term for fuzzy comparison (lowercase, drop punctuation, negation
    markers preserved as a leading 'not')."""
    t = (text or "").strip().lower().strip(".,;:").strip()
    t = re.sub(r"^not\s*\(?\s*", "not ", t)
    t = t.rstrip(")")
    return re.sub(r"\s+", " ", t)


def grade_conditional(
    sentence: str, *, sufficient: str, necessary: str
) -> dict[str, Any]:
    """Grade a learner's sufficient/necessary identification against the canonical
    parse. Hard-abstains (``graded: False``) when the sentence is unparseable, so
    the drill never marks an answer against an uncertain key."""
    parsed = parse_conditional(sentence)
    if not parsed.get("available"):
        return {"graded": False, **parsed}
    want_s = _norm_term(parsed["sufficient"])
    want_n = _norm_term(parsed["necessary"])
    got_s = _norm_term(sufficient)
    got_n = _norm_term(necessary)
    suff_ok = got_s == want_s
    nec_ok = got_n == want_n
    return {
        "graded": True,
        "correct": suff_ok and nec_ok,
        "sufficient_correct": suff_ok,
        "necessary_correct": nec_ok,
        "sufficient": parsed["sufficient"],
        "necessary": parsed["necessary"],
        "arrow": parsed["arrow"],
        "contrapositive": parsed["contrapositive"],
    }


# Curated drill sentences -- clean, unambiguous conditionals across every
# connective form the parser handles. Every one is asserted to parse in the
# self-test, so the drill never has to serve an item it would abstain on.
DRILL_SENTENCES = [
    "If it rains, then the match is postponed.",
    "If the alarm sounds, the building is evacuated.",
    "The loan is approved only if the credit check passes.",
    "The flight departs unless the weather worsens.",
    "Unless the fee is paid, the account is suspended.",
    "No mammals are cold-blooded.",
    "All triangles are polygons.",
    "Every senator is an adult.",
    "Only citizens are eligible.",
    "Admission requires a valid ticket.",
    "A quorum is necessary for a vote.",
    "A signature is sufficient for consent.",
]


def drill_items() -> list[dict[str, Any]]:
    """The curated conditional-translation drills, each with its canonical parse
    (sentence + sufficient/necessary/arrow/contrapositive). Deterministic; safe to
    serve because every entry parses (never abstains)."""
    return [{"sentence": s, **parse_conditional(s)} for s in DRILL_SENTENCES]


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    def arrow(s: str) -> str:
        p = parse_conditional(s)
        return p["arrow"] if p.get("available") else "ABSTAIN"

    def contra(s: str) -> str:
        p = parse_conditional(s)
        return p["contrapositive"] if p.get("available") else "ABSTAIN"

    # if/then
    check(
        "if/then",
        arrow("If it rains, then the game is cancelled")
        == "it rains -> the game is cancelled",
    )
    check(
        "if/comma (no then)",
        arrow("If she studies, she passes") == "she studies -> she passes",
    )
    check(
        "contrapositive of if/then",
        contra("If it rains, then the game is cancelled")
        == "not (the game is cancelled) -> not (it rains)",
    )
    # only if -> necessary
    check("only if", arrow("You win only if you play") == "you win -> you play")
    # unless == if not
    check(
        "S unless N",
        arrow("The picnic happens unless it rains")
        == "not (it rains) -> the picnic happens",
    )
    check(
        "unless N, S",
        arrow("Unless it rains, the picnic happens")
        == "not (it rains) -> the picnic happens",
    )
    # no / all / only
    check("no S are N", arrow("No cats are dogs") == "cats -> not (dogs)")
    check("all S are N", arrow("All dogs are mammals") == "dogs -> mammals")
    check("every S is N", arrow("Every prime is odd") == "prime -> odd")
    check(
        "only S are N -> N->S",
        arrow("Only members are admitted") == "admitted -> members",
    )
    # requires / necessary / sufficient
    check("S requires N", arrow("Entry requires a ticket") == "entry -> a ticket")
    check(
        "N necessary for S",
        arrow("A ticket is necessary for entry") == "entry -> a ticket",
    )
    check(
        "S sufficient for N",
        arrow("A ticket is sufficient for entry") == "a ticket -> entry",
    )
    # ordering: "no ... " must not be eaten by "all"; "only if" not by "only"
    check(
        "only-if beats only",
        arrow("You pass only if you study") == "you pass -> you study",
    )
    # abstain on the unparseable
    check(
        "abstains on a non-conditional",
        parse_conditional("The sky is blue and grass is green")["available"] is False,
    )
    check("abstains on empty", parse_conditional("")["available"] is False)

    # FAIL-CLOSED regression guard: sentences a greedy flat split would MIS-parse
    # (compound / nested / relative-clause) must ABSTAIN, never emit a wrong arrow.
    for adversarial in [
        "Every dog that is trained is calm",
        "All employees who are late are fined",
        "No plan that is risky is approved",
        "You pass if and only if you study",
        "If you study, then you pass, unless you oversleep",
        "A ticket is necessary and sufficient for entry",
        "If it rains and it is cold, then the game is cancelled",
        "The loan is approved only if the check passes and the deposit clears",
    ]:
        check(
            f"fail-closed abstain: {adversarial!r}",
            parse_conditional(adversarial)["available"] is False,
        )

    # grading: correct, partial, and abstain
    g = grade_conditional(
        "If it rains, then the game is cancelled",
        sufficient="it rains",
        necessary="the game is cancelled",
    )
    check("grade: fully correct", g["graded"] and g["correct"])
    g2 = grade_conditional(
        "If it rains, then the game is cancelled",
        sufficient="it rains",
        necessary="the game continues",
    )
    check(
        "grade: necessary wrong -> not correct",
        g2["graded"] and not g2["correct"] and g2["sufficient_correct"],
    )
    g3 = grade_conditional("The sky is blue", sufficient="x", necessary="y")
    check("grade: abstains (fail-closed) on unparseable", g3["graded"] is False)

    # every curated drill sentence must parse to its EXACT documented arrow --
    # not merely `available`, so a future edit that mis-parses a curated sentence
    # (the latent hazard: a wrong-rule drill shipping with the suite green) fails.
    expected_arrows = {
        "If it rains, then the match is postponed.": "it rains -> the match is postponed",
        "If the alarm sounds, the building is evacuated.": "the alarm sounds -> the building is evacuated",
        "The loan is approved only if the credit check passes.": "the loan is approved -> the credit check passes",
        "The flight departs unless the weather worsens.": "not (the weather worsens) -> the flight departs",
        "Unless the fee is paid, the account is suspended.": "not (the fee is paid) -> the account is suspended",
        "No mammals are cold-blooded.": "mammals -> not (cold-blooded)",
        "All triangles are polygons.": "triangles -> polygons",
        "Every senator is an adult.": "senator -> an adult",
        "Only citizens are eligible.": "eligible -> citizens",
        "Admission requires a valid ticket.": "admission -> a valid ticket",
        "A quorum is necessary for a vote.": "a vote -> a quorum",
        "A signature is sufficient for consent.": "a signature -> consent",
    }
    check(
        "every DRILL_SENTENCES entry is pinned in expected_arrows",
        set(expected_arrows) == set(DRILL_SENTENCES),
    )
    check(
        "all curated drill sentences parse to their exact documented arrow",
        all(arrow(s) == expected_arrows[s] for s in DRILL_SENTENCES),
    )
    check(
        "drill_items carries the parsed key", all(d.get("arrow") for d in drill_items())
    )

    # contrapositive is self-inverse (double contrapositive == original arrow)
    check(
        "double-contrapositive returns to the original",
        Conditional(Term("A"), Term("B")).contrapositive().contrapositive().arrow
        == "A -> B",
    )

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("CONDITIONAL_OK" if ok else "CONDITIONAL_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
