# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Framework-agnostic grading for LSAT Item answers.

Shared by the desktop reviewer hook (``qt/aqt/lsat_performance.py``, driven by
``pycmd``) and the mobile HTTP endpoints (``qt/aqt/lsat_web.py``). Keeping the
logic here guarantees a mobile answer produces the *same* append-only
``PerformanceEvent`` a desktop answer would -- the two front-ends differ only in
how they obtain the note + arguments.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anki.collection import Collection

# Choices are stored one per line as "(A) text"; parse them the same way the
# Item card template's JS does (line-anchored so "(A)" inside prose is ignored).
_CHOICE_RE = re.compile(
    r"(?:^|\n)[ \t]*\(([A-E])\)[ \t]*(.*?)(?=\n[ \t]*\([A-E]\)|$)", re.DOTALL
)


def parse_choices(text: str) -> list[dict[str, str]]:
    """Parse the ``choices`` field into ``[{letter, text}]`` (blanks dropped)."""
    out: list[dict[str, str]] = []
    for m in _CHOICE_RE.finditer(text or ""):
        body = m.group(2).strip()
        if body:
            out.append({"letter": m.group(1), "text": body})
    return out


def item_traps(note: Any) -> dict[str, str]:
    """The item's per-distractor trap map (empty if unlabeled/legacy)."""
    try:
        spec = note["distractor_traps"] or ""
    except KeyError:
        return {}
    from lsat.error_patterns import parse_distractor_traps

    return parse_distractor_traps(spec)


def item_qtype(note: Any) -> str:
    """The item's primary question-type node id (first ``lr.*``/``rc.*`` tag),
    or "" when it has none (no classify stage for such items)."""
    for node_id in (note["skill_tags"] or "").split():
        if node_id.startswith(("lr.", "rc.")):
            return node_id
    return ""


def grade_classify(note: Any, *, named: str) -> dict[str, Any]:
    """Grade the identification-first stage (SPOV 1 / A2): did the student name
    the item's question type correctly *before* solving it?

    Pure -- the classify grade is NOT logged on its own; the front-end carries
    it into :func:`grade_answer` (``identified``) so one event holds both stage
    grades. Returns ``{classify_correct, actual_type, actual_label}``.
    """
    from lsat.taxonomy import load_taxonomy

    actual = item_qtype(note)
    named = (named or "").strip()
    correct = bool(actual) and named == actual
    label = ""
    if actual:
        try:
            label = load_taxonomy().topic_by_id(actual).name
        except KeyError:
            label = actual
    return {"classify_correct": correct, "actual_type": actual, "actual_label": label}


def grade_answer(
    col: Collection,
    note: Any,
    *,
    chosen: str,
    confidence: str | None,
    response_ms: int,
    phase: str,
    identified: str = "",
) -> dict[str, Any]:
    """Grade a chosen letter, append the graded event, and report the result.

    Returns ``{correct, correct_letter, has_traps, contrast}``. ``has_traps`` says
    whether the chosen distractor has a trap label, so the UI only offers the trap
    tap when it can grade + give feedback. ``contrast`` is the deterministic
    Elaborated-Contrast payload (DECISION-round2 #13) shown on a MISS -- why the
    credited answer is credited + why the picked letter is a trap; it abstains
    (``available: False``) when nothing is documented, and is ``None`` on a
    correct answer. ``identified`` carries the classify-stage grade ("1"/"0";
    "" = none) onto the same event.
    """
    from lsat.events import append_event

    chosen = (chosen or "").strip().upper()
    correct_letter = (note["correct"] or "").strip().upper()
    is_correct = bool(chosen) and chosen == correct_letter
    node_ids = (note["skill_tags"] or "").split()

    append_event(
        col,
        item_id=str(note.id),
        skill_tags=node_ids,
        correct=is_correct,
        response_ms=max(0, int(response_ms or 0)),
        chosen=chosen,
        confidence=confidence,
        phase=phase or "timed",
        identified=identified,
    )
    # Elaborated feedback is a learning-from-errors moment: only built on a miss.
    contrast: dict[str, Any] | None = None
    if not is_correct:
        from lsat.contrast import build_contrast

        contrast = build_contrast(note, chosen)
    return {
        "correct": is_correct,
        "correct_letter": correct_letter,
        "has_traps": chosen in item_traps(note),
        "contrast": contrast,
    }


def grade_trap(note: Any, *, chosen: str, family: str) -> dict[str, Any]:
    """Grade a "which trap is (X)?" tap against the item's authoritative labels."""
    from lsat.taxonomy import TRAP_FAMILY_LABELS

    actual = item_traps(note).get((chosen or "").strip().upper())
    return {
        "trap_correct": bool(actual) and (family or "").strip().lower() == actual,
        "actual_family": actual,
        "actual_label": TRAP_FAMILY_LABELS.get(actual or ""),
    }
