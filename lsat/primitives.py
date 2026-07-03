# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Taxonomy coverage by reasoning-primitive family (SPOV 1 / A3).

The knowledge base is three primitive families -- ``diction`` (precise
connective/term meanings), ``logic`` (formal rules + named fallacies) and
``qtype`` (the question-type taxonomy with its prescribed attack). This module
measures how much of each family the *deck* actually covers, so the dashboard
can show taxonomy coverage per family and the readiness give-up rule can abstain
when the deck is genuinely incomplete (a deck that drills vocabulary hard but
never covers Necessary Assumption must not read as "ready").

A node counts as covered when at least one LSAT Card or LSAT Item carries it in
``skill_tags`` -- deck coverage, deliberately distinct from the *graded-item*
coverage used elsewhere (give-up "covered question types" needs >= N graded
answers; this asks the weaker question "does the deck even teach it?").
"""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from lsat.notetypes import LSAT_CARD, LSAT_ITEM
from lsat.taxonomy import (
    PRIMITIVE_DICTION,
    PRIMITIVE_LOGIC,
    PRIMITIVE_QTYPE,
    Taxonomy,
)

if TYPE_CHECKING:
    from anki.collection import Collection

# The logic family's non-flaw members (formal-rule cross-cutting skills).
_LOGIC_SKILLS = ("skill.conditional_logic", "skill.quantifier_logic")

# Per-build cache for the full LSAT-note scan (mirrors lsat.events.events_cache):
# a dashboard build calls primitive_coverage twice (once in the readiness give-up
# gate, once in the coverage panel), each scanning every LSAT_CARD/LSAT_ITEM note.
# Opening deck_nodes_cache around the build parses that set once. Safe only for a
# read-only window (no card/item note is added mid-build).
_DECK_NODES_CACHE: contextvars.ContextVar[tuple[int, set[str]] | None] = (
    contextvars.ContextVar("lsat_deck_nodes_cache", default=None)
)


@contextlib.contextmanager
def deck_nodes_cache(col: Collection) -> Iterator[set[str]]:
    """Open a read-only window in which :func:`deck_node_ids` scans once."""
    existing = _DECK_NODES_CACHE.get()
    if existing is not None and existing[0] == id(col):
        yield existing[1]
        return
    nodes = _deck_node_ids_uncached(col)
    token = _DECK_NODES_CACHE.set((id(col), nodes))
    try:
        yield nodes
    finally:
        _DECK_NODES_CACHE.reset(token)


def family_denominators(tax: Taxonomy) -> dict[str, set[str]]:
    """The full taxonomy node set per primitive family (the denominators)."""
    return {
        PRIMITIVE_DICTION: set(tax.diction),
        PRIMITIVE_LOGIC: set(tax.flaw_catalog) | set(_LOGIC_SKILLS),
        PRIMITIVE_QTYPE: {t.id for t in tax.question_types},
    }


def deck_node_ids(col: Collection) -> set[str]:
    """Every taxonomy node id carried by any card or item in the deck.

    Returns the cached scan inside a :func:`deck_nodes_cache` window, else scans
    fresh."""
    cached = _DECK_NODES_CACHE.get()
    if cached is not None and cached[0] == id(col):
        return cached[1]
    return _deck_node_ids_uncached(col)


def _deck_node_ids_uncached(col: Collection) -> set[str]:
    nodes: set[str] = set()
    for name in (LSAT_CARD, LSAT_ITEM):
        if col.models.by_name(name) is None:
            continue
        for nid in col.find_notes(f'note:"{name}"'):
            note = col.get_note(nid)
            try:
                nodes.update((note["skill_tags"] or "").split())
            except KeyError:
                continue
    return nodes


def primitive_coverage(col: Collection, tax: Taxonomy) -> dict[str, Any]:
    """Per-family + overall deck coverage of the primitive taxonomy.

    Returns ``{families: {name: {covered, total, pct, missing}}, overall_pct}``
    where ``pct`` is 0-100 and ``missing`` lists up to 5 uncovered node ids so
    the dashboard can say *what* is missing, not just how much.
    """
    have = deck_node_ids(col)
    families: dict[str, Any] = {}
    covered_total = 0
    node_total = 0
    for family, nodes in family_denominators(tax).items():
        covered = sorted(n for n in nodes if n in have)
        missing = sorted(n for n in nodes if n not in have)
        families[family] = {
            "covered": len(covered),
            "total": len(nodes),
            "pct": round(100.0 * len(covered) / len(nodes), 1) if nodes else 0.0,
            "missing": missing[:5],
        }
        covered_total += len(covered)
        node_total += len(nodes)
    return {
        "families": families,
        "overall_pct": (
            round(100.0 * covered_total / node_total, 1) if node_total else 0.0
        ),
        "basis": "deck (>=1 card or item tagging the node)",
    }
