# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Stem-Polarity Micro-Drill (DECISION-round4 #13).

The single highest-frequency *careless* LSAT error, cutting across every LR type:
an ``EXCEPT`` / ``LEAST`` / negated stem inverts the task, and under time pressure
the test-taker reverts to the prepotent task (find the weakener) instead of the
inverted one (find the one that does NOT weaken). Spaced retrieval automatizes the
stem -> task-polarity mapping so the correct attentional set is retrieved
automatically (Monsell 2003 task-set reconfiguration; Shiffrin & Schneider 1977 /
Logan 1988 automatization; Roediger & Karpicke 2006 testing effect).

This module is the deterministic engine: :func:`classify_stem` maps a question
stem to its **polarity** (direct / except / least / negated) + the derived search
instruction, and **fails closed** on any ambiguous stem (two conflicting markers,
or nothing recognizable). Grading is exact-match against the polarity; a mis-grade
would train the wrong attentional set, so the classifier is narrow and the drill
only ever serves the curated, self-test-pinned :data:`DRILL_STEMS`. The optional
``base_task`` hint is seeded from the taxonomy ``stem_cues`` (best-effort context,
never graded).
"""

from __future__ import annotations

import re
from typing import Any

DIRECT = "direct"
EXCEPT = "except"
LEAST = "least"
NEGATED = "negated"
POLARITIES = (DIRECT, EXCEPT, LEAST, NEGATED)

# The derived search instruction the learner should hold for each polarity.
INSTRUCTION: dict[str, str] = {
    DIRECT: "Find the ONE choice that does it — the other four don't.",
    EXCEPT: "Four choices DO it; pick the one that does NOT (EXCEPT inverts the task).",
    LEAST: "Pick the choice that does it the LEAST — the other four do it more.",
    NEGATED: "The stem is negated: pick the choice for which it does NOT hold.",
}

# Markers. EXCEPT/LEAST are (by LSAT convention) capitalized, but we match
# case-insensitively on a word boundary. The negation marker is deliberately
# HIGH-PRECISION: a bare "not" is far too common in a stem's *content* ("the plan
# will not succeed") to treat as a task inversion, so we match only reliable
# task-negation phrasings (the CANNOT-be-true family, "does not <task-verb>", and a
# negation inside the wh-question clause). A genuinely-negated stem in some other
# phrasing falls through to `direct` -- which is why the drill only serves the
# curated, self-test-pinned DRILL_STEMS rather than arbitrary item stems.
_EXCEPT_RE = re.compile(r"\bexcept\b", re.I)
# "at least" is a quantifier, not the LEAST-inversion marker -> exclude it.
_LEAST_RE = re.compile(r"(?<!at )\bleast\b", re.I)
_NEGATION_RE = re.compile(
    r"\b(?:cannot|can not|could not|must not) be (?:true|properly)"
    r"|\bdoes not (?:conform|follow|support|apply|hold|help|fit|serve)"
    # a negation in the wh-clause, but NOT "not only ... but" (a benign intensifier)
    r"|\bwhich one of the following (?:is|does|would|could|can) ?not(?!\s+only)\b",
    re.I,
)


def classify_stem(stem: str) -> dict[str, Any]:
    """Classify a stem's polarity + search instruction, or abstain.

    Returns ``{available: True, polarity, instruction, base_task}`` on a confident
    read, else ``{available: False, reason}``. Fail-closed: abstains when two
    distinct inversion markers co-occur (ambiguous) or the stem is empty."""
    s = (stem or "").strip()
    if not s:
        return {"available": False, "reason": "empty stem"}

    has_except = bool(_EXCEPT_RE.search(s))
    has_least = bool(_LEAST_RE.search(s))
    has_negation = bool(_NEGATION_RE.search(s))

    # Two distinct inversion markers -> we can't say which governs -> abstain.
    if sum([has_except, has_least, has_negation]) > 1:
        return {
            "available": False,
            "reason": "ambiguous: more than one inversion marker",
        }

    if has_except:
        polarity = EXCEPT
    elif has_least:
        polarity = LEAST
    elif has_negation:
        polarity = NEGATED
    else:
        polarity = DIRECT

    return {
        "available": True,
        "polarity": polarity,
        "instruction": INSTRUCTION[polarity],
        "base_task": _base_task(s),
    }


def _base_task(stem: str) -> str | None:
    """Best-effort base-task label from the taxonomy ``stem_cues`` (never graded;
    shown as context). Returns a display name or None if no cue matches."""
    try:
        from lsat.taxonomy import load_taxonomy

        tax = load_taxonomy()
    except Exception:
        return None
    low = stem.lower()
    for topic in getattr(tax, "topics", []):
        for cue in getattr(topic, "stem_cues", []) or []:
            # match on the cue with EXCEPT/LEAST stripped (they don't change the base)
            core = re.sub(r"\b(except|least)\b", "", cue, flags=re.I).strip()
            if core and core.lower() in low:
                return topic.name
    return None


def grade_stem_polarity(stem: str, chosen: str) -> dict[str, Any]:
    """Grade a learner's polarity call against the deterministic classifier.
    Fails closed (``graded: False``) on an unparseable stem or unknown polarity."""
    parsed = classify_stem(stem)
    if not parsed.get("available"):
        return {"graded": False, **parsed}
    if chosen not in POLARITIES:
        return {"graded": False, "reason": "unknown polarity"}
    return {
        "graded": True,
        "correct": chosen == parsed["polarity"],
        "polarity": parsed["polarity"],
        "instruction": parsed["instruction"],
        "base_task": parsed.get("base_task"),
    }


# Curated drill stems: a spread of polarity across LR base tasks. Each is pinned
# to its polarity in the self-test, so the drill never serves an item it would
# misclassify. Real LSAT phrasings (EXCEPT/LEAST capitalized as on the test).
DRILL_STEMS: list[tuple[str, str]] = [
    ("Which one of the following most weakens the argument?", DIRECT),
    ("Each of the following, if true, weakens the argument EXCEPT:", EXCEPT),
    ("Which one of the following most strengthens the argument?", DIRECT),
    ("All of the following support the conclusion EXCEPT:", EXCEPT),
    ("The argument is most vulnerable to criticism on the grounds that", DIRECT),
    ("Which one of the following the passage LEAST supports?", LEAST),
    (
        "Which one of the following, if true, would be LEAST helpful in "
        "evaluating the argument?",
        LEAST,
    ),
    (
        "If the statements above are true, which one of the following CANNOT be true?",
        NEGATED,
    ),
    (
        "Which one of the following is an assumption on which the argument depends?",
        DIRECT,
    ),
    (
        "The author would be most likely to agree with which one of the following?",
        DIRECT,
    ),
    ("Each of the following could be true EXCEPT:", EXCEPT),
    ("Which one of the following does NOT conform to the principle above?", NEGATED),
]


def drill_items() -> list[dict[str, Any]]:
    """The curated stem-polarity drills, each with its classified polarity +
    instruction. Deterministic; every entry classifies (never abstains)."""
    out: list[dict[str, Any]] = []
    for stem, _polarity in DRILL_STEMS:
        parsed = classify_stem(stem)
        out.append({"stem": stem, **parsed})
    return out


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # every curated stem classifies to its pinned polarity
    for stem, want in DRILL_STEMS:
        got = classify_stem(stem)
        check(
            f"[{want}] {stem[:48]}...",
            got.get("available") and got.get("polarity") == want,
        )

    # all four polarities are represented (a real drill, not one-answer)
    check(
        "drill covers all four polarities",
        {p for _, p in DRILL_STEMS} == set(POLARITIES),
    )

    # FAIL-CLOSED: ambiguous / empty stems abstain, never guess.
    for adversarial in [
        "Each of the following weakens the argument LEAST EXCEPT:",  # two markers
        "",
        "   ",
    ]:
        check(
            f"fail-closed abstain: {adversarial!r}",
            classify_stem(adversarial)["available"] is False,
        )

    # HIGH-PRECISION negation (adversarial review): a DIRECT stem whose *content*
    # contains "not" must NOT false-positive as negated -- these are direct
    # questions and must classify as `direct`, never `negated`.
    for content_not_stem in [
        "Which one of the following most supports the claim that the plan "
        "will not succeed?",
        "Which one of the following, if true, most strengthens the argument "
        "that the tax was not effective?",
        "The author is most likely to agree that the treaty is not binding on "
        "which one of the following grounds?",
    ]:
        got = classify_stem(content_not_stem)
        check(
            f"content 'not' does not trigger NEGATED: {content_not_stem[:40]}...",
            got.get("available") and got.get("polarity") == DIRECT,
        )

    # adversarial-review Finding 1: 'at least' is a quantifier, not the LEAST
    # marker; 'not only' is a benign intensifier, not a task negation. Both DIRECT.
    for direct_trap in [
        "Which one of the following is assumed by at least one of the premises?",
        "Which one of the following is not only supported but entailed by the passage?",
    ]:
        got = classify_stem(direct_trap)
        check(
            f"'at least'/'not only' stays DIRECT: {direct_trap[:36]}...",
            got.get("available") and got.get("polarity") == DIRECT,
        )

    # grading: correct, wrong, fail-closed
    g = grade_stem_polarity(
        "Each of the following weakens the argument EXCEPT:", EXCEPT
    )
    check("grade: correct", g["graded"] and g["correct"])
    g2 = grade_stem_polarity(
        "Each of the following weakens the argument EXCEPT:", DIRECT
    )
    check("grade: wrong -> not correct", g2["graded"] and not g2["correct"])
    check(
        "grade: fail-closed on ambiguous stem",
        grade_stem_polarity("weakens LEAST EXCEPT", EXCEPT)["graded"] is False,
    )
    check(
        "grade: fail-closed on unknown polarity",
        grade_stem_polarity("Which most weakens?", "banana")["graded"] is False,
    )

    # drill_items carries the classification
    check(
        "drill_items non-empty + carry polarity",
        len(drill_items()) == len(DRILL_STEMS)
        and all(d.get("polarity") for d in drill_items()),
    )

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("STEM_POLARITY_OK" if ok else "STEM_POLARITY_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
