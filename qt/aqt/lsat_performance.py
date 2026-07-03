# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Capture graded LSAT Item answers from the reviewer.

The ``LSAT Item`` card template posts the chosen multiple-choice letter via
``pycmd("lsatAnswer:<LETTER>")``. We intercept it through the
``webview_did_receive_js_message`` hook (so ``reviewer.py`` is untouched), grade
it against the note's ``correct`` field -- authoritative; the answer never
leaves Python and is not in the question template -- record the answer latency
(``card.time_taken``, the same millisecond source as ``revlog.time``), and
append an append-only ``PerformanceEvent`` (see :mod:`lsat.events`). The graded
result is returned to the page so it can highlight the chosen/correct options.

The ``lsat`` package is a sibling of ``qt``/``pylib`` and not on the app's
sys.path, so we add the repo root on first use (mirrors ``lsat_dashboard``).
"""

from __future__ import annotations

import os
import sys
from typing import Any

from aqt import gui_hooks

ANSWER_PREFIX = "lsatAnswer:"
TRAP_PREFIX = "lsatTrap:"
CLASSIFY_PREFIX = "lsatClassify:"
_registered = False

# The phase stamped onto answers logged from the reviewer: "timed" (default),
# "blind" (untimed second pass) or "relaxed" (untimed learning). Blind Review
# flips this with set_session_phase; the hook records it on each event so the
# Gap Map / honest-mastery fold can tell a real timed answer from a review pass.
_session_phase = "timed"


def set_session_phase(phase: str) -> None:
    """Set the phase applied to subsequently-logged answers."""
    global _session_phase
    _session_phase = (phase or "timed").strip().lower()


def current_phase() -> str:
    return _session_phase


def _ensure_lsat_on_path() -> None:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.append(root)


def _grade_trap(message: str, note: Any) -> tuple[bool, Any]:
    """Grade a ``lsatTrap:<LETTER>:<family>`` self-explanation tap (not logged)."""
    from lsat.grading import grade_trap

    letter, _, family = message[len(TRAP_PREFIX) :].partition(":")
    return (True, grade_trap(note, chosen=letter, family=family))


def _on_js_message(
    handled: tuple[bool, Any], message: str, context: Any
) -> tuple[bool, Any]:
    """Record a graded answer (``lsatAnswer:``), grade a trap tap
    (``lsatTrap:``) or the identification-first stage (``lsatClassify:``)."""
    if not message.startswith((ANSWER_PREFIX, TRAP_PREFIX, CLASSIFY_PREFIX)):
        return handled

    from aqt.reviewer import Reviewer

    if not isinstance(context, Reviewer):
        return handled
    card = context.card
    if card is None:
        return handled

    _ensure_lsat_on_path()
    from lsat.grading import grade_answer, grade_classify
    from lsat.notetypes import LSAT_ITEM

    note = card.note()
    notetype = note.note_type()
    if notetype is None or notetype["name"] != LSAT_ITEM:
        return handled

    if message.startswith(TRAP_PREFIX):
        return _grade_trap(message, note)

    if message.startswith(CLASSIFY_PREFIX):
        # Stage 1 of the identification-first card: grade the named type. Not
        # logged by itself -- the page carries it into the answer as `ident`.
        return (True, grade_classify(note, named=message[len(CLASSIFY_PREFIX) :]))

    # Payload is "<LETTER>" with optional ":conf=<label>" (sure/likely/guess)
    # and ":ident=<1|0>" (classify-stage grade) suffixes.
    payload = message[len(ANSWER_PREFIX) :].strip()
    identified = ""
    if ":ident=" in payload:
        payload, _, ident_part = payload.partition(":ident=")
        identified = ident_part.strip() if ident_part.strip() in ("0", "1") else ""
    confidence: str | None = None
    if ":conf=" in payload:
        letter_part, _, conf_part = payload.partition(":conf=")
        payload = letter_part
        confidence = conf_part.strip().lower() or None

    # Latency = time since the card was shown, the same quantity Anki writes to
    # revlog.time. Captured now (at the graded click), before the SR rating.
    try:
        response_ms = int(card.time_taken(capped=False))
    except Exception:
        response_ms = 0

    try:
        result = grade_answer(
            context.mw.col,
            note,
            chosen=payload,
            confidence=confidence,
            response_ms=response_ms,
            phase=current_phase(),
            identified=identified,
        )
    except Exception as exc:
        # Never break review flow on a logging error; surface it to the page.
        return (True, {"error": str(exc)})
    return (True, result)


def register_lsat_performance() -> None:
    """Subscribe the answer-capture handler (idempotent)."""
    global _registered
    if _registered:
        return
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
    _registered = True
