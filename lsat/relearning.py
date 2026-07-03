# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Mandatory spaced re-test of confident-wrong items (SPOV 2 / B3).

Surfacing a confident miss once and showing feedback is the *incomplete*
intervention: corrected high-confidence errors return as the correction fades,
and they return more often than low-confidence ones (Butler, Fazio & Marsh
2011). A retrieval test after corrective feedback blocks that return (Metcalfe
& Miele 2014). So every open misconception (see :mod:`lsat.misconceptions`)
owes a graded re-test a few days out -- spaced, so the re-test is itself a
retrieval event rather than an immediate re-read.

:func:`schedule_retests` reschedules the item's cards via the normal scheduler
(``set_due_date``), so re-tests ride the ordinary review queue, stay undoable,
and never bypass FSRS. A card already due sooner is left alone. Re-testing the
*same* item is the evidence-backed core (it blocks the specific error); fresh
same-trap items additionally enter through the trap boost in the queue.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lsat.misconceptions import open_misconception_items

if TYPE_CHECKING:
    from anki.collection import Collection

# Days until the owed re-test (documented in the README; "spaced" per
# Butler/Fazio/Marsh -- late enough to be a retrieval test, soon enough that
# the correction has not fully faded).
RETEST_DELAY_DAYS = 2


def retest_candidates(col: Collection) -> list[dict[str, Any]]:
    """The open/relapsed misconception items and their card ids + due dates."""
    from anki.notes import NoteId

    out: list[dict[str, Any]] = []
    today = col.sched.today
    for item_id in open_misconception_items(col):
        try:
            note = col.get_note(NoteId(int(item_id)))
        except Exception:
            continue  # event references an item deleted since
        for card_id in note.card_ids():
            card = col.get_card(card_id)
            out.append(
                {
                    "item_id": item_id,
                    "card_id": int(card_id),
                    "due_in_days": (card.due - today) if card.type == 2 else None,
                }
            )
    return out


def schedule_retests(
    col: Collection, *, delay_days: int = RETEST_DELAY_DAYS
) -> dict[str, Any]:
    """Pull every owed re-test to at most ``delay_days`` from today.

    Only review cards farther out than ``delay_days`` are moved (a card already
    due sooner will be re-tested anyway; new/learning cards are already in the
    day's flow). Returns a JSON-safe summary. Idempotent: a second call finds
    nothing left to move.
    """
    from anki.cards import CardId

    to_move: list[CardId] = []
    items: set[str] = set()
    for cand in retest_candidates(col):
        due_in = cand["due_in_days"]
        if due_in is not None and due_in > delay_days:
            to_move.append(CardId(cand["card_id"]))
            items.add(str(cand["item_id"]))
    if to_move:
        # "N!" resets the interval to exactly N days; plain "N" keeps the ease.
        col.sched.set_due_date(to_move, str(delay_days))
    return {
        "scheduled": len(to_move),
        "items": sorted(items),
        "delay_days": delay_days,
    }


def _selftest() -> bool:
    import os
    import sys
    import tempfile

    sys.path[:0] = ["pylib", "out/pylib", "."]
    import anki.collection  # noqa: F401
    from anki.collection import Collection
    from anki.decks import DeckId
    from lsat.events import append_event
    from lsat.notetypes import LSAT_ITEM, ensure_notetypes

    ok = True

    def check(name: str, cond: bool, extra: str = "") -> None:
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")

    col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
    try:
        ensure_notetypes(col)
        deck = DeckId(col.decks.add_normal_deck_with_name("LSAT::Practice").id)
        nt = col.models.by_name(LSAT_ITEM)
        note = col.new_note(nt)
        note["stem"] = "Weaken?"
        note["choices"] = "(A) a\n(B) b\n(C) c"
        note["correct"] = "C"
        note["skill_tags"] = "lr.weaken"
        note["difficulty"] = "medium"
        col.add_note(note, deck)

        # Make its card a review card due far in the future (raw SQL like the
        # models' tests do), then log a confident miss -> open misconception.
        card_id = note.card_ids()[0]
        far_due = col.sched.today + 30
        col.db.execute(
            "update cards set type=2, queue=2, due=?, ivl=30 where id=?",
            far_due,
            card_id,
        )
        append_event(
            col,
            item_id=str(note.id),
            skill_tags=["lr.weaken"],
            correct=False,
            response_ms=4000,
            chosen="B",
            confidence="sure",
            phase="timed",
        )

        cands = retest_candidates(col)
        check("candidate found", len(cands) == 1 and cands[0]["due_in_days"] == 30)

        res = schedule_retests(col)
        check("rescheduled 1", res["scheduled"] == 1, str(res))
        card = col.get_card(card_id)
        check(
            "due pulled to <= delay",
            (card.due - col.sched.today) <= RETEST_DELAY_DAYS,
            f"due_in={card.due - col.sched.today}",
        )
        res2 = schedule_retests(col)
        check("idempotent", res2["scheduled"] == 0, str(res2))

        # Undo still works (set_due_date is a normal undoable op).
        check("undo available", col.undo_status().undo != "")

        # Resolution clears the debt: a later correct answer -> no candidates.
        append_event(
            col,
            item_id=str(note.id),
            skill_tags=["lr.weaken"],
            correct=True,
            response_ms=3000,
            chosen="C",
            confidence="likely",
            phase="timed",
        )
        check("resolved -> no candidates", retest_candidates(col) == [])
    finally:
        col.close()

    print("RELEARNING_OK" if ok else "RELEARNING_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
