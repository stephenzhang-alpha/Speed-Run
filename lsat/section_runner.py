# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Timed Section Runner persistence (DECISION-round4 #17).

Captures a full timed-section attempt as an append-only ``LSAT SectionAttempt``
note (cards suspended; syncs under the same HLC-merge rules as PerformanceEvents).
The per-question trajectory is stored as JSON; :mod:`lsat.answer_change` reads it
to compute the First-Instinct Ledger (net wrong->right vs right->wrong changes).

A trajectory is a list of per-question records; the fields the diagnostic needs:
``reached`` (did the clock allow an answer), ``changed`` (first answer != final),
``first_correct`` / ``final_correct``. Extra UI fields (dwell_ms, flagged, visit
order) are stored verbatim and ignored by the diagnostic.

This is persistence + a reader only -- no learning claim, no scoring. The runner
UI (a SvelteKit route) and the diagnostic live elsewhere.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from lsat.notetypes import LSAT_SECTION_ATTEMPT, ensure_notetypes

if TYPE_CHECKING:
    from anki.collection import Collection
    from anki.notes import NoteId

SECTIONS_DECK = "LSAT::Sections"

# Answer-change categories (kept in sync with lsat.answer_change).
_WR = "wr"  # wrong -> right
_RW = "rw"  # right -> wrong
_WW = "ww"  # wrong -> wrong


def record_section_attempt(
    col: Collection, *, trajectory: list[dict[str, Any]], now_ms: int | None = None
) -> NoteId:
    """Append one timed-section attempt. ``trajectory`` is the per-question record
    list; it is stored as JSON on a new suspended note. Returns the note id."""
    from anki.decks import DeckId
    from lsat.events import _next_hlc, device_id

    ensure_notetypes(col)
    notetype = col.models.by_name(LSAT_SECTION_ATTEMPT)
    assert notetype is not None
    deck_id = DeckId(col.decks.add_normal_deck_with_name(SECTIONS_DECK).id)

    dev = device_id(col)
    hlc = _next_hlc(col, dev, now_ms=now_ms)

    note = col.new_note(notetype)
    note["trajectory"] = json.dumps(list(trajectory), separators=(",", ":"))
    note["n_questions"] = str(len(trajectory))
    note["started_at_hlc"] = hlc
    note["device_id"] = dev
    col.add_note(note, deck_id)
    col.sched.suspend_cards(list(note.card_ids()))
    return note.id


def _classify_change(first_correct: bool, final_correct: bool) -> str | None:
    """Category for a CHANGED question, or None if it isn't a real change
    (both-correct is impossible for a changed answer, so it is ignored)."""
    if final_correct and not first_correct:
        return _WR
    if first_correct and not final_correct:
        return _RW
    if not first_correct and not final_correct:
        return _WW
    return None


def read_answer_changes(col: Collection) -> tuple[list[str], int]:
    """Read every recorded section attempt and return
    ``(change_categories, n_sections)`` where ``change_categories`` is the flat
    list of ``wr``/``rw``/``ww`` over all REACHED, CHANGED questions. Robust to a
    missing notetype or a malformed trajectory (those are skipped)."""
    if col.models.by_name(LSAT_SECTION_ATTEMPT) is None:
        return ([], 0)
    changes: list[str] = []
    n_sections = 0
    for nid in col.find_notes(f'note:"{LSAT_SECTION_ATTEMPT}"'):
        note = col.get_note(nid)
        n_sections += 1
        try:
            traj = json.loads(note["trajectory"] or "[]")
        except (ValueError, KeyError):
            continue
        if not isinstance(traj, list):
            continue
        for q in traj:
            if not isinstance(q, dict):
                continue
            if not q.get("reached", True) or not q.get("changed"):
                continue
            # require BOTH graded-correctness keys -- an ungradeable question (item
            # not found at submit time) is left without them and must not be
            # miscounted as wrong->wrong.
            if "first_correct" not in q or "final_correct" not in q:
                continue
            cat = _classify_change(
                bool(q.get("first_correct")), bool(q.get("final_correct"))
            )
            if cat is not None:
                changes.append(cat)
    return (changes, n_sections)


def section_stats(col: Collection) -> dict[str, Any]:
    """Light aggregate over recorded sections for the dashboard: attempt count,
    total reached/unreached, and the answer-change split (JSON-safe)."""
    if col.models.by_name(LSAT_SECTION_ATTEMPT) is None:
        return {"n_sections": 0, "n_reached": 0, "n_unreached": 0}
    n_sections = n_reached = n_unreached = 0
    for nid in col.find_notes(f'note:"{LSAT_SECTION_ATTEMPT}"'):
        note = col.get_note(nid)
        n_sections += 1
        try:
            traj = json.loads(note["trajectory"] or "[]")
        except (ValueError, KeyError):
            continue
        for q in traj if isinstance(traj, list) else []:
            if isinstance(q, dict):
                if q.get("reached", True):
                    n_reached += 1
                else:
                    n_unreached += 1
    return {
        "n_sections": n_sections,
        "n_reached": n_reached,
        "n_unreached": n_unreached,
    }


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:
    import os
    import sys
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in (os.path.join(root, "pylib"), os.path.join(root, "out", "pylib"), root):
        if path not in sys.path:
            sys.path.insert(0, path)

    from anki.collection import Collection

    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    tmp = tempfile.mkdtemp(prefix="section-selftest-")
    col = Collection(os.path.join(tmp, "c.anki2"))
    now = 1_700_000_000_000
    try:
        # empty collection -> no changes, no sections
        ch, ns = read_answer_changes(col)
        check("empty: no changes, no sections", ch == [] and ns == 0)

        # a section: q0 reached+changed wrong->right; q1 reached+changed right->wrong;
        # q2 reached, unchanged (skip); q3 unreached (skip); q4 changed wrong->wrong.
        traj = [
            {
                "index": 0,
                "reached": True,
                "changed": True,
                "first_correct": False,
                "final_correct": True,
            },
            {
                "index": 1,
                "reached": True,
                "changed": True,
                "first_correct": True,
                "final_correct": False,
            },
            {
                "index": 2,
                "reached": True,
                "changed": False,
                "first_correct": True,
                "final_correct": True,
            },
            {
                "index": 3,
                "reached": False,
                "changed": False,
                "first_correct": False,
                "final_correct": False,
            },
            {
                "index": 4,
                "reached": True,
                "changed": True,
                "first_correct": False,
                "final_correct": False,
            },
        ]
        record_section_attempt(col, trajectory=traj, now_ms=now)
        ch, ns = read_answer_changes(col)
        check("one section recorded", ns == 1)
        check(
            "changes classified (wr, rw, ww) from reached+changed only",
            sorted(ch) == sorted([_WR, _RW, _WW]),
        )

        # cards are suspended (logged, never studied)
        nid = list(col.find_notes(f'note:"{LSAT_SECTION_ATTEMPT}"'))[0]
        cards = [col.get_card(cid) for cid in col.get_note(nid).card_ids()]
        from anki.consts import QUEUE_TYPE_SUSPENDED

        check(
            "attempt cards are suspended",
            all(c.queue == QUEUE_TYPE_SUSPENDED for c in cards),
        )

        # section_stats aggregates reached/unreached
        st = section_stats(col)
        check(
            "section_stats: 1 section, 4 reached, 1 unreached",
            st["n_sections"] == 1 and st["n_reached"] == 4 and st["n_unreached"] == 1,
        )

        # malformed trajectory is skipped, not crashed
        note = col.new_note(col.models.by_name(LSAT_SECTION_ATTEMPT))
        note["trajectory"] = "not json"
        note["n_questions"] = "0"
        from anki.decks import DeckId

        col.add_note(
            note, DeckId(col.decks.add_normal_deck_with_name(SECTIONS_DECK).id)
        )
        ch2, ns2 = read_answer_changes(col)
        check(
            "malformed trajectory skipped (no crash)",
            ns2 == 2 and sorted(ch2) == sorted([_WR, _RW, _WW]),
        )

        # end-to-end: the ledger reads these changes
        from lsat.answer_change import compute_answer_change

        led = compute_answer_change(col)
        check(
            "compute_answer_change reads sections",
            led["n_sections"] == 2 and led["n_changes"] == 3,
        )
    finally:
        col.close()

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("SECTION_RUNNER_OK" if ok else "SECTION_RUNNER_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
