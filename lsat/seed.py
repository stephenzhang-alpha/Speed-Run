# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Seed the default, ORIGINAL, taxonomy-tagged LSAT decks (SPOV 1 / A1).

SPOV 1 defines the knowledge base as three reasoning-primitive families, each a
first-class deck (subdecks of ``LSAT::Drills``) so coverage, scheduling, and
analytics can slice by them:

- ``LSAT::Drills::Diction``        -- precise connective/term meanings.
- ``LSAT::Drills::Logic``          -- formal rules + the named-fallacy catalog.
- ``LSAT::Drills::Question Types`` -- LR/RC question-type identification (A2).

plus ``LSAT::Practice`` for the graded multiple-choice items (the performance
signal). The card content lives in :mod:`lsat.deck_content`; this module handles
deck creation, family routing, tagging, and idempotency. A card's destination
deck is derived from its ``primitive_type`` (the family of its first skill), so
the family a card teaches and the deck it lands in can never drift apart.

All content is original (authored for this project), never copied from LSAC
PrepTests or other copyrighted material (PRD section 16). Each note is tagged
with hierarchical ``lsat::`` tags derived from the taxonomy node ids, and also
stores the machine-readable node ids in its ``skill_tags`` field.

Run as a script against a collection:

    out/pyenv/bin/python -m lsat.seed --collection /path/to/collection.anki2

or call :func:`seed_deck` with an already-open ``Collection`` (e.g. from the
desktop add-on). Seeding is idempotent: it is skipped if the collection has
already been seeded, unless ``force=True``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lsat.deck_content import SEED_CARDS, SEED_ITEMS
from lsat.notetypes import (
    LSAT_CARD,
    LSAT_ITEM,
    ensure_notetypes,
    migrate_card_fields,
    migrate_item_fields,
)
from lsat.taxonomy import (
    PRIMITIVE_DICTION,
    PRIMITIVE_LOGIC,
    PRIMITIVE_QTYPE,
    load_taxonomy,
    node_id_to_tag,
    primitive_type_of_node,
)

if TYPE_CHECKING:
    from anki.collection import Collection
    from anki.decks import DeckId

DRILLS_DECK = "LSAT::Drills"
# The three reasoning-primitive families (SPOV 1 / A1) are first-class subdecks
# of Drills: studying "LSAT::Drills" studies all three, while each family can be
# browsed/scheduled on its own. Creating any subdeck also creates the Drills
# parent that the AI pipeline promotes generated cards into (ai/pipeline.py).
DICTION_DECK = "LSAT::Drills::Diction"
LOGIC_DECK = "LSAT::Drills::Logic"
QTYPE_DECK = "LSAT::Drills::Question Types"
PRACTICE_DECK = "LSAT::Practice"
# primitive family -> deck name; kept in sync with lsat.taxonomy's families.
FAMILY_DECKS = {
    PRIMITIVE_DICTION: DICTION_DECK,
    PRIMITIVE_LOGIC: LOGIC_DECK,
    PRIMITIVE_QTYPE: QTYPE_DECK,
}
SEED_MARKER_TAG = "lsat::seed"
SEEDED_CONFIG_KEY = "lsat:seeded"


def _tags_for(skill_ids: list[str]) -> list[str]:
    return [node_id_to_tag(s) for s in skill_ids] + [SEED_MARKER_TAG]


def _add_cards(col: Collection, deck_ids: dict[str, DeckId]) -> dict[str, int]:
    """Add every drill card, routing each to its primitive family's deck.

    Returns a ``{family: count}`` breakdown. The card's family is derived from
    its first skill (``primitive_type_of_node``), which also sets the note's
    ``primitive_type`` field -- so a card is always filed under the family it
    actually teaches.
    """
    notetype = col.models.by_name(LSAT_CARD)
    assert notetype is not None
    tax = load_taxonomy()
    per_family: dict[str, int] = {family: 0 for family in deck_ids}
    for spec in SEED_CARDS:
        primary = spec["skills"][0]
        family = primitive_type_of_node(primary)
        note = col.new_note(notetype)
        note["front"] = spec["front"]
        note["back"] = spec["back"]
        note["explanation"] = spec.get("explanation", "")
        note["skill_tags"] = " ".join(spec["skills"])
        note["source_id"] = spec.get("source_id", "original")
        note["source_quote"] = spec.get("source_quote", "")
        # A1: exactly one primitive family per card, derived from the primary
        # skill; topic_weight is that skill's exam/study weight at seed time.
        note["primitive_type"] = family
        note["topic_weight"] = f"{tax.weight_of_node(primary):.3f}"
        note.tags = _tags_for(spec["skills"])
        col.add_note(note, deck_ids[family])
        per_family[family] += 1
    return per_family


def _add_items(col: Collection, deck_id: DeckId) -> int:
    notetype = col.models.by_name(LSAT_ITEM)
    assert notetype is not None
    for spec in SEED_ITEMS:
        note = col.new_note(notetype)
        note["stem"] = spec["stem"]
        note["choices"] = spec["choices"]
        note["correct"] = spec["correct"]
        note["skill_tags"] = " ".join(spec["skills"])
        note["difficulty"] = spec.get("difficulty", "medium")
        note["source_id"] = spec.get("source_id", "original")
        note["source_quote"] = spec.get("source_quote", "")
        # Per-distractor trap labels power the Distractor-Reasoning Engine. The
        # field exists because migrate_item_fields runs before seeding; only set
        # it when the spec supplies labels so legacy items stay blank.
        traps = spec.get("distractor_traps", "")
        if traps:
            note["distractor_traps"] = traps
        note.tags = _tags_for(spec["skills"])
        col.add_note(note, deck_id)
    return len(SEED_ITEMS)


def seed_deck(col: Collection, *, force: bool = False) -> dict:
    """Ensure notetypes exist and add the default tagged decks. Idempotent."""
    if not force and col.get_config(SEEDED_CONFIG_KEY, False):
        return {
            "seeded": False,
            "reason": "already seeded (pass force=True to re-seed)",
        }

    from anki.decks import DeckId

    ensure_notetypes(col)
    # Field migrations are idempotent; older collections gain the A1 primitive
    # fields + the Item distractor_traps field before (re-)seeding writes them.
    migrate_card_fields(col)
    migrate_item_fields(col)
    # Create the three family subdecks (this also creates the LSAT::Drills
    # parent) plus the graded Practice deck.
    deck_ids: dict[str, DeckId] = {
        family: DeckId(col.decks.add_normal_deck_with_name(name).id)
        for family, name in FAMILY_DECKS.items()
    }
    practice_deck_id = DeckId(col.decks.add_normal_deck_with_name(PRACTICE_DECK).id)

    # Replace rather than accumulate: drop any previously-seeded notes (marked
    # with SEED_MARKER_TAG) so re-seeding is idempotent instead of appending a
    # fresh duplicate copy each time.
    prior = list(col.find_notes(f"tag:{SEED_MARKER_TAG}"))
    if prior:
        col.remove_notes(prior)

    per_family = _add_cards(col, deck_ids)
    n_items = _add_items(col, practice_deck_id)

    col.set_config(SEEDED_CONFIG_KEY, True)
    return {
        "seeded": True,
        "removed": len(prior),
        "cards": sum(per_family.values()),
        "cards_by_family": per_family,
        "items": n_items,
        "decks": [*FAMILY_DECKS.values(), PRACTICE_DECK],
    }


def _ensure_anki_on_path() -> None:
    """Make the dev `anki` package importable (mirrors tools/run.py)."""
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("pylib", "out/pylib"):
        path = os.path.join(root, rel)
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Seed the default tagged LSAT decks.")
    parser.add_argument(
        "--collection",
        required=True,
        help="path to a .anki2 collection (created if it does not exist)",
    )
    parser.add_argument(
        "--force", action="store_true", help="re-seed even if already seeded"
    )
    args = parser.parse_args(argv)

    _ensure_anki_on_path()
    import os

    from anki.collection import Collection

    # Honour the documented "created if it does not exist": make sure the parent
    # directory is present so opening a fresh collection does not raise a raw
    # SQLite "unable to open database file" error.
    os.makedirs(os.path.dirname(os.path.abspath(args.collection)), exist_ok=True)
    col = Collection(args.collection)
    try:
        result = seed_deck(col, force=args.force)
    finally:
        col.close()
    print(result)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
