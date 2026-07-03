# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Elaborated Contrast Card (DECISION-round2 #13): the post-miss two-column
"why the credited answer is credited / why the one you picked is a trap" feedback.

This upgrades the shipped Feature 2 one-tap why-wrong (knowledge-of-correct-result
+ a single trap-family tip) into true **elaborated feedback** (EF): on a miss we
show, side by side,

  LEFT  -- a deterministic "why-credited" clause keyed to the item's question type
           (the reusable judgment the credited answer exercises); and
  RIGHT -- the trap family of the letter the student actually picked, plus a
           one-line **minimal edit** (what in the argument/choice would have to be
           different for that trap to be the credited answer).

**AI-off by design.** Every clause is a fixed, documented catalog entry keyed to a
real taxonomy node -- there is NO model call at feedback time, so it carries none
of the AI-grading honesty risk. :func:`validate_contrast_catalog` is the gold-set
gate: it refuses to let a clause reference a node id that is not in the taxonomy.
:func:`build_contrast` **abstains** (``available: False``) whenever the item's
question type has no documented clause AND the chosen letter has no trap label, so
we never fabricate an explanation.

The measured claim is honest and time-matched: elaborated feedback buys at most a
small held-out gain over knowledge-of-correct-result, and ONLY if the eval arm's
CI excludes 0 -- see ``eval/feedback.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lsat.grading import item_qtype, item_traps
from lsat.taxonomy import TRAP_FAMILY_LABELS

if TYPE_CHECKING:
    from lsat.taxonomy import Taxonomy

# Per-question-type "why the credited answer is credited": the prescribed judgment
# for that stem. Keys MUST be taxonomy question-type node ids (gold-set-gated).
WHY_CREDITED: dict[str, str] = {
    # Logical Reasoning
    "lr.weaken": "The credited answer most directly undermines the link between the argument's evidence and its conclusion.",
    "lr.strengthen": "The credited answer most directly shores up the link between the evidence and the conclusion.",
    "lr.assumption_necessary": "The credited answer states something the argument must take for granted -- negate it and the argument falls apart.",
    "lr.assumption_sufficient": "The credited answer, if added as a premise, is enough to make the conclusion follow.",
    "lr.flaw": "The credited answer names the exact reasoning error the argument commits, in the abstract.",
    "lr.inference_must_be_true": "The credited answer must be true given the stimulus -- it follows with no extra assumptions.",
    "lr.most_strongly_supported": "The credited answer is the choice the stimulus best supports, even if not proven outright.",
    "lr.principle": "The credited answer matches the broad rule the argument applies (or that governs the case).",
    "lr.parallel_reasoning": "The credited answer reproduces the argument's logical structure, regardless of topic.",
    "lr.parallel_flaw": "The credited answer commits the same reasoning error as the stimulus, regardless of topic.",
    "lr.method_of_reasoning": "The credited answer describes how the argument proceeds, not whether it is right.",
    "lr.main_conclusion": "The credited answer is the point the rest of the argument is offered to support.",
    "lr.role_in_argument": "The credited answer describes the function the referenced claim plays in the argument.",
    "lr.point_at_issue": "The credited answer is the claim the two speakers would actually disagree (or agree) about.",
    "lr.paradox": "The credited answer explains how both surprising facts can be true at once, without denying either.",
    "lr.evaluate": "The credited answer raises the question whose answer would most change how good the argument is.",
    "lr.cannot_be_true": "The credited answer is the one the stimulus rules out -- it cannot be true if the stimulus is.",
    # Reading Comprehension
    "rc.inference": "The credited answer follows from the passage without adding outside information.",
    "rc.specific_detail": "The credited answer restates what the passage explicitly says at the cited point.",
    "rc.main_point_purpose": "The credited answer captures the passage's overall point/purpose, not one local detail.",
    "rc.function_role": "The credited answer says why the author included the referenced material, not just what it says.",
    "rc.attitude_tone": "The credited answer matches the author's expressed stance -- no stronger, no weaker.",
    "rc.strengthen_weaken_rc": "The credited answer bears on the specific claim the question targets, not the passage at large.",
    "rc.structure_organization": "The credited answer describes how the passage is built, section by section.",
    "rc.application_analogy": "The credited answer transfers the passage's principle to a genuinely parallel new case.",
    "rc.comparative_dual_passage": "The credited answer states the actual relationship between the two passages' claims.",
}

# What each trap family's chosen distractor would need for it to be *credited* --
# the "minimal edit" that names why it is only a trap. Keys are trap families.
TRAP_MINIMAL_EDIT: dict[str, str] = {
    "out_of_scope": "it would be credited only if the argument were actually about that -- it reaches beyond the stimulus.",
    "extreme_language": "soften its absolute wording (all / never / only / must) to what the stimulus actually supports.",
    "reversal": "flip its conditional or causal direction -- as written it runs the relationship backwards.",
    "half_right": "the first half fits, but the unsupported second half is what makes it wrong.",
    "irrelevant_comparison": "the groups it compares would have to be the ones the argument is actually about.",
}

# Short "fixable habit" tips per family (kept in sync with error_patterns._FAMILY_TIPS).
_FAMILY_TIP: dict[str, str] = {
    "out_of_scope": "check each choice stays inside the argument's scope",
    "extreme_language": "slow down on absolute words like all / never / only",
    "reversal": "confirm the conditional or causal direction before committing",
    "half_right": "reject choices that are only partly supported",
    "irrelevant_comparison": "make sure any compared groups are actually relevant",
}


def validate_contrast_catalog(tax: Taxonomy) -> list[str]:
    """Gold-set gate: return the list of catalog keys that are NOT real taxonomy
    question-type nodes (empty list = catalog is clean). A non-empty result means
    a clause would reference a node the taxonomy does not define -- a drift bug."""
    qt_ids = {t.id for t in tax.question_types}
    return sorted(k for k in WHY_CREDITED if k not in qt_ids)


def build_contrast(note: Any, chosen: str) -> dict[str, Any]:
    """Deterministic post-miss contrast for one graded item + chosen letter.

    Returns ``{"available": True, "why_credited": ..., "trap": {...}}`` with only
    the documented parts present, or ``{"available": False}`` when neither the
    question type nor the chosen letter has a documented clause (abstain -- never
    fabricate). No model call; safe with AI off.
    """
    qtype = item_qtype(note)
    why = WHY_CREDITED.get(qtype)
    family = item_traps(note).get((chosen or "").strip().upper())

    if why is None and family is None:
        return {"available": False}

    out: dict[str, Any] = {"available": True}
    if why is not None:
        out["why_credited"] = why
    if family is not None:
        out["trap"] = {
            "family": family,
            "label": TRAP_FAMILY_LABELS.get(family, family),
            "tip": _FAMILY_TIP.get(
                family, "review why that choice is built to attract you"
            ),
            "minimal_edit": TRAP_MINIMAL_EDIT.get(
                family, "it does not actually answer what the question asks."
            ),
        }
    return out


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    import os
    import sys
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (os.path.join(root, "pylib"), os.path.join(root, "out", "pylib"), root):
        if p not in sys.path:
            sys.path.insert(0, p)

    from anki.collection import Collection
    from anki.decks import DeckId
    from lsat.notetypes import LSAT_ITEM, ensure_notetypes, migrate_item_fields
    from lsat.taxonomy import load_taxonomy

    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    tax = load_taxonomy()
    check(
        "catalog is gold-set clean (all keys are taxonomy nodes)",
        validate_contrast_catalog(tax) == [],
    )
    check(
        "every LR + RC question type has a why-credited clause",
        all(t.id in WHY_CREDITED for t in tax.question_types),
    )

    path = os.path.join(tempfile.mkdtemp(prefix="contrast-"), "c.anki2")
    col = Collection(path)
    try:
        ensure_notetypes(col)
        migrate_item_fields(col)
        did = DeckId(col.decks.add_normal_deck_with_name("C::Items").id)
        nt = col.models.by_name(LSAT_ITEM)
        assert nt is not None
        note = col.new_note(nt)
        note["stem"] = "stem"
        note["choices"] = "(A) a\n(B) b\n(C) c\n(D) d\n(E) e"
        note["correct"] = "C"
        note["skill_tags"] = "lr.weaken flaw.causal"
        note["difficulty"] = "medium"
        note["distractor_traps"] = "A=extreme_language B=out_of_scope"
        col.add_note(note, did)

        c = build_contrast(note, "A")  # extreme_language trap on a Weaken item
        check("contrast available on a labelled miss", c["available"] is True)
        check(
            "why-credited keyed to the question type (Weaken)",
            "undermines" in c.get("why_credited", ""),
        )
        check(
            "trap side names the chosen letter's family",
            c["trap"]["family"] == "extreme_language",
        )
        check("trap side carries a minimal-edit", bool(c["trap"]["minimal_edit"]))
        check("json-safe", _json_ok(c))

        # A letter with no trap label but a known qtype -> still shows why-credited.
        c2 = build_contrast(note, "D")
        check(
            "shows why-credited even when the chosen letter is unlabelled",
            c2["available"] is True and "why_credited" in c2 and "trap" not in c2,
        )

        # An item whose qtype has no clause AND an unlabelled letter -> abstain.
        note2 = col.new_note(nt)
        note2["stem"] = "s"
        note2["choices"] = "(A) a\n(B) b"
        note2["correct"] = "A"
        note2["skill_tags"] = "skill.diction.only_if"  # not a question type
        note2["difficulty"] = "medium"
        note2["distractor_traps"] = ""
        col.add_note(note2, did)
        check(
            "abstains when nothing is documented",
            build_contrast(note2, "B")["available"] is False,
        )
    finally:
        col.close()

    ok = all(p for _, p in checks)
    print("CONTRAST_OK" if ok else "CONTRAST_FAIL")
    return ok


def _json_ok(obj: Any) -> bool:
    import json

    try:
        json.dumps(obj, allow_nan=False)
    except (ValueError, TypeError):
        return False
    return True


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
