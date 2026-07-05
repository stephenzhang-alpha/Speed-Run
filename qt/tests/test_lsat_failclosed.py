# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Anki for LSAT: regression guards for the fail-CLOSED grading contract.

Two fail-open bugs (found by the debug hunt): grade_answer used to log a permanent
false MISS for an item with no answer key, and submit_conditional accepted a
negative/out-of-range drill index via Python negative indexing. Both must now
ABSTAIN (graded:false, nothing logged) like every sibling grader. These paths run
BEFORE any collection write, so they're exercised without opening a collection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


class _FakeNote:
    """Minimal Anki-note stand-in: dict field access + an id (enough for the
    abstain paths, which never touch the collection)."""

    def __init__(self, fields: dict[str, str], note_id: int = 1) -> None:
        self._f = fields
        self.id = note_id

    def __getitem__(self, key: str) -> str:
        return self._f.get(key, "")


_CHOICES = "(A) first choice\n(B) second choice\n(C) third choice"


def test_grade_answer_abstains_on_empty_answer_key() -> None:
    from lsat.grading import grade_answer

    note = _FakeNote({"correct": "", "choices": _CHOICES, "skill_tags": ""})
    # col is None: the abstain path must return before ever appending an event.
    res = grade_answer(
        None, note, chosen="A", confidence="sure", response_ms=100, phase="timed"
    )
    assert res["graded"] is False, "must not grade an item with no answer key"
    assert res["correct"] is False and res["correct_letter"] == ""


def test_grade_answer_abstains_on_whitespace_answer_key() -> None:
    from lsat.grading import grade_answer

    note = _FakeNote({"correct": "   ", "choices": _CHOICES, "skill_tags": ""})
    res = grade_answer(
        None, note, chosen="B", confidence=None, response_ms=0, phase="timed"
    )
    assert res["graded"] is False


def test_grade_answer_abstains_on_answer_key_not_in_choices() -> None:
    from lsat.grading import grade_answer

    # correct points to (F), which is not among the parsed choices -> ungradeable.
    note = _FakeNote({"correct": "F", "choices": _CHOICES, "skill_tags": ""})
    res = grade_answer(
        None, note, chosen="A", confidence="likely", response_ms=50, phase="timed"
    )
    assert res["graded"] is False


def test_grade_answer_abstains_on_empty_choice() -> None:
    from lsat.grading import grade_answer

    note = _FakeNote({"correct": "A", "choices": _CHOICES, "skill_tags": ""})
    res = grade_answer(
        None, note, chosen="", confidence="guess", response_ms=0, phase="timed"
    )
    assert res["graded"] is False, "no valid choice selected must not grade"


def test_submit_conditional_rejects_negative_index() -> None:
    from lsat import api

    # 'cond--1' parses to idx=-1; without a bounds guard Python negative indexing
    # would resolve to a real sentence and grade against it. Must fail closed.
    res = api.submit_conditional(None, item_id="cond--1", sufficient="x", necessary="y")
    assert res.get("graded") is False


def test_submit_conditional_rejects_out_of_range_index() -> None:
    from lsat import api

    res = api.submit_conditional(None, item_id="cond-999999")
    assert res.get("graded") is False


def test_submit_conditional_rejects_non_numeric_index() -> None:
    from lsat import api

    res = api.submit_conditional(None, item_id="cond-abc")
    assert res.get("graded") is False
