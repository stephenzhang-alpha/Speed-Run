# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Grounded misconception hypotheses (SPOV 2 / B4). [AI - optional]

When a review lands in the ``confident + wrong`` state, the app may show a
short hypothesis for *why* ("you may be treating a necessary condition as
sufficient"). Traceability rule: every hypothesis maps to a **label in the
documented taxonomy** (the ``skill.trap.*`` families and the ``flaw.*`` catalog
in ``lsat-taxonomy.yaml``, our encoding of the practitioner PowerScore/7Sage
error catalogs) -- never free-generated prose. The deterministic label->text
catalog below is the default and the AI-off path; an LLM may only *rephrase* a
catalog entry, and the rephrasing is fail-closed validated (label must survive,
no new content) with the deterministic text as fallback.

Fully removable: nothing else consumes hypotheses; with AI off the review flow
and every score are unaffected (the deterministic path needs no model at all).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lsat.ai.client import LLMClient, LLMUnavailable
from lsat.taxonomy import TRAP_FAMILY_LABELS, trap_family_to_node_id

if TYPE_CHECKING:
    from anki.collection import Collection

# Deterministic hypothesis catalog. Keys are taxonomy node ids (the traceable
# source labels); text states the *suspected habit*, framed fixably.
HYPOTHESIS_CATALOG: dict[str, str] = {
    # answer-choice trap families (skill.trap.*)
    "skill.trap.out_of_scope": (
        "You may be crediting answers that introduce considerations the "
        "argument never touches -- check each choice against the stated scope."
    ),
    "skill.trap.extreme_language": (
        "You may be accepting absolute wording (all / never / only) that is "
        "stronger than the argument can support."
    ),
    "skill.trap.reversal": (
        "You may be treating a necessary condition as sufficient (or reversing "
        "cause and effect) -- re-check which direction the claim runs."
    ),
    "skill.trap.half_right": (
        "You may be stopping at a choice whose first half matches and missing "
        "that its second half is unsupported."
    ),
    "skill.trap.irrelevant_comparison": (
        "You may be drawn to comparisons the argument does not need -- ask "
        "whether the comparison actually bears on the conclusion."
    ),
    # named flaw types (flaw.*)
    "flaw.causal": (
        "You may be reading a correlation (or a temporal sequence) as proof of "
        "causation without ruling out alternatives."
    ),
    "flaw.sampling": (
        "You may be generalizing from a sample without asking whether it "
        "represents the larger group."
    ),
    "flaw.necessary_sufficient_confusion": (
        "You may be treating a necessary condition as sufficient -- knowing B "
        "is required for A does not make B enough for A."
    ),
    "flaw.affirming_consequent": (
        "You may be affirming the consequent: from 'if A then B' and 'B', "
        "concluding 'A'."
    ),
    "flaw.denying_antecedent": (
        "You may be denying the antecedent: from 'if A then B' and 'not A', "
        "concluding 'not B'."
    ),
    "flaw.percentage_vs_number": (
        "You may be swapping percentages and raw counts -- a larger share is "
        "not a larger number unless the bases match."
    ),
    "flaw.equivocation": (
        "You may be letting a key term shift meaning between premise and conclusion."
    ),
    "flaw.circular": (
        "You may be accepting support that just restates the conclusion in "
        "different words."
    ),
}

# Gold set for the mapper (label -> keywords the hypothesis must contain).
# validate_hypotheses() must clear this before hypotheses are shown (B4's
# pre-viewing cutoff, mirroring the card checker's gold-set gate).
GOLD_CASES: list[tuple[str, list[str]]] = [
    ("skill.trap.reversal", ["necessary", "sufficient"]),
    ("skill.trap.extreme_language", ["absolute", "wording"]),
    ("skill.trap.out_of_scope", ["scope"]),
    ("skill.trap.half_right", ["half"]),
    ("skill.trap.irrelevant_comparison", ["comparison"]),
    ("flaw.causal", ["correlation", "causation"]),
    ("flaw.sampling", ["sample"]),
    ("flaw.necessary_sufficient_confusion", ["necessary", "sufficient"]),
    ("flaw.affirming_consequent", ["consequent"]),
    ("flaw.percentage_vs_number", ["percentages", "counts"]),
]
HYPOTHESIS_GOLD_PASS_MIN = 0.9


def hypothesis_for(note: Any, chosen: str) -> dict[str, Any] | None:
    """The grounded hypothesis for a confident miss on ``note`` picking
    ``chosen`` -- or ``None`` (render nothing) when no documented label applies.

    Label priority: the chosen distractor's trap family (the most specific
    diagnosis), then the item's first ``flaw.*`` tag. The returned dict carries
    the traceable ``source_label`` + human label + text; the UI must show the
    label with the text.
    """
    from lsat.grading import item_traps

    family = item_traps(note).get((chosen or "").strip().upper())
    if family:
        node_id = trap_family_to_node_id(family)
        if node_id in HYPOTHESIS_CATALOG:
            return {
                "text": HYPOTHESIS_CATALOG[node_id],
                "source_label": node_id,
                "label": TRAP_FAMILY_LABELS.get(family, family),
                "source": "lsat-taxonomy.yaml trap families (PowerScore/7Sage-style catalog)",
            }
    for tag in (note["skill_tags"] or "").split():
        if tag in HYPOTHESIS_CATALOG:
            return {
                "text": HYPOTHESIS_CATALOG[tag],
                "source_label": tag,
                "label": tag.split(".")[-1].replace("_", " "),
                "source": "lsat-taxonomy.yaml flaw_catalog (PowerScore/7Sage-style catalog)",
            }
    return None


_BANNED_NEW_CONTENT = re.compile(r"\d")


def rephrase_with_ai(
    hypothesis: dict[str, Any], client: LLMClient | None
) -> dict[str, Any]:
    """Optionally have an LLM rephrase the catalog text. Fail-closed: the
    rephrasing is used only if it keeps the label's key idea and adds no new
    content; otherwise (or with AI off / unavailable) the deterministic text
    stands. The source label is never AI-generated."""
    if client is None:
        return hypothesis
    base = hypothesis["text"]
    try:
        raw = client.complete(
            "You rewrite one sentence of study feedback. Keep the meaning, keep "
            "it to at most two sentences, add no new facts, no numbers.",
            f"Rewrite in a friendly, direct voice:\n{base}",
        ).strip()
    except LLMUnavailable:
        return hypothesis
    label_terms = [
        t for t in re.findall(r"[a-z]+", hypothesis["label"].lower()) if len(t) > 3
    ]
    ok = (
        0 < len(raw) <= 2 * len(base)
        and raw.count(".") <= 2
        and not _BANNED_NEW_CONTENT.search(raw)
        and (not label_terms or any(t in raw.lower() for t in label_terms))
    )
    if not ok:
        return hypothesis
    return {**hypothesis, "text": raw, "ai_rephrased": True}


def validate_hypotheses() -> dict[str, Any]:
    """Gold-set check on the deterministic mapper (run before display; the
    cutoff is pre-declared as ``HYPOTHESIS_GOLD_PASS_MIN``)."""
    passed = 0
    failures: list[str] = []
    for node_id, keywords in GOLD_CASES:
        text = HYPOTHESIS_CATALOG.get(node_id, "").lower()
        if text and all(k in text for k in keywords):
            passed += 1
        else:
            failures.append(node_id)
    rate = passed / len(GOLD_CASES) if GOLD_CASES else 0.0
    return {
        "n": len(GOLD_CASES),
        "passed": passed,
        "pass_rate": rate,
        "gate_passed": rate >= HYPOTHESIS_GOLD_PASS_MIN,
        "failures": failures,
    }


def hypotheses_for_open_misconceptions(
    col: Collection, *, client: LLMClient | None = None, limit: int = 5
) -> list[dict[str, Any]]:
    """Hypotheses for the currently-open confident misses (dashboard feed).

    Empty when the gold-set gate fails (nothing renders without a validated
    catalog) or when no misconception has a documented label. AI off = fully
    deterministic; AI on = optional rephrasing only.
    """
    if not validate_hypotheses()["gate_passed"]:
        return []
    from anki.notes import NoteId
    from lsat.misconceptions import misconception_stats

    stats = misconception_stats(col)
    if not stats.get("available"):
        return []
    out: list[dict[str, Any]] = []
    for rec in stats["misconceptions"]:
        if rec["status"] not in ("open", "relapsed"):
            continue
        try:
            note = col.get_note(NoteId(int(rec["item_id"])))
        except Exception:
            continue
        hyp = hypothesis_for(note, rec["chosen"])
        if hyp is None:
            continue
        out.append({**rephrase_with_ai(hyp, client), "item_id": rec["item_id"]})
        if len(out) >= limit:
            break
    return out


def _selftest() -> bool:
    import os
    import sys
    import tempfile

    sys.path[:0] = ["pylib", "out/pylib", "."]
    import anki.collection  # noqa: F401
    from anki.collection import Collection
    from anki.decks import DeckId
    from lsat.events import append_event
    from lsat.notetypes import LSAT_ITEM, ensure_notetypes, migrate_item_fields

    ok = True

    def check(name: str, cond: bool, extra: str = "") -> None:
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")

    gold = validate_hypotheses()
    check("gold set gate", gold["gate_passed"] is True, str(gold))

    col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
    try:
        ensure_notetypes(col)
        migrate_item_fields(col)
        nt = col.models.by_name(LSAT_ITEM)
        note = col.new_note(nt)
        note["stem"] = "Weaken?"
        note["choices"] = "(A) a\n(B) b\n(C) c"
        note["correct"] = "C"
        note["skill_tags"] = "lr.weaken flaw.causal"
        note["difficulty"] = "medium"
        note["distractor_traps"] = "B=extreme_language A=out_of_scope"
        col.add_note(
            note, DeckId(col.decks.add_normal_deck_with_name("LSAT::Practice").id)
        )

        hyp = hypothesis_for(note, "B")
        check(
            "trap label wins",
            hyp is not None
            and hyp["source_label"] == "skill.trap.extreme_language"
            and bool(hyp["text"]),
            str(hyp),
        )
        hyp_a = hypothesis_for(note, "D")  # unlabeled letter -> flaw tag fallback
        check(
            "flaw fallback",
            hyp_a is not None and hyp_a["source_label"] == "flaw.causal",
            str(hyp_a and hyp_a["source_label"]),
        )
        bare = col.new_note(nt)
        bare["stem"] = "x"
        bare["choices"] = "(A) a\n(B) b"
        bare["correct"] = "A"
        bare["skill_tags"] = "rc.inference"
        col.add_note(
            bare, DeckId(col.decks.add_normal_deck_with_name("LSAT::Practice").id)
        )
        check("no label -> None", hypothesis_for(bare, "B") is None)

        # AI-off end-to-end feed
        append_event(
            col,
            item_id=str(note.id),
            skill_tags=["lr.weaken"],
            correct=False,
            response_ms=2000,
            chosen="B",
            confidence="sure",
            phase="timed",
        )
        feed = hypotheses_for_open_misconceptions(col, client=None)
        check(
            "feed carries traceable label (AI off)",
            len(feed) == 1 and feed[0]["source_label"].startswith("skill.trap."),
            str(feed),
        )

        # fail-closed rephrasing: a client that violates the rules is rejected
        class BadClient:
            def complete(self, system: str, user: str, *, temperature: float = 0.0):
                return "Buy my course for $99!!! 12345"

        class OkClient:
            def complete(self, system: str, user: str, *, temperature: float = 0.0):
                return (
                    "Watch for absolute wording like all or never -- it is "
                    "usually stronger than the argument supports."
                )

        class DownClient:
            def complete(self, system: str, user: str, *, temperature: float = 0.0):
                raise LLMUnavailable("offline")

        base = hypothesis_for(note, "B")
        assert base is not None
        check(
            "bad rephrase rejected (falls back)",
            rephrase_with_ai(base, BadClient())["text"] == base["text"],
        )
        good = rephrase_with_ai(base, OkClient())
        check(
            "good rephrase accepted, label preserved",
            good.get("ai_rephrased") is True
            and good["source_label"] == base["source_label"],
        )
        check(
            "LLM down degrades silently",
            rephrase_with_ai(base, DownClient())["text"] == base["text"],
        )
    finally:
        col.close()

    print("HYPOTHESIS_OK" if ok else "HYPOTHESIS_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
