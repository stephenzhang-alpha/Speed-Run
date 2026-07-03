# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The generation pipeline: generate -> check -> stage -> gate -> promote.

Generated cards enter a **staging** area first. They are promoted into the live
deck only when BOTH hold (docs/ai-card-pipeline.md section 6): every promoted card's
``verdict == CORRECT_USEFUL`` AND the batch clears the quality gate
(pass-rate/wrong-rate from ``eval/config.py``). If the AI is unavailable or its
output is unparseable, the batch is skipped and existing (human) cards keep
serving -- the review loop never blocks (graceful degradation, section 5).

``run_batch`` is pure (no collection) so the generate/check/gate logic is
testable in isolation; ``stage_and_promote`` performs the Anki-side moves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lsat.ai.checker import PASS_VERDICT, VERDICT_ORDER, check_card
from lsat.ai.client import LLMClient, LLMUnavailable
from lsat.ai.generator import Card, generate_cards

if TYPE_CHECKING:
    from anki.collection import Collection

try:
    from eval.config import CARD_CHECK_PASS_RATE_MIN, CARD_CHECK_WRONG_RATE_MAX
except Exception:  # pragma: no cover - eval pkg always present in-tree
    CARD_CHECK_PASS_RATE_MIN, CARD_CHECK_WRONG_RATE_MAX = 0.70, 0.02

STAGING_DECK = "LSAT::Staging"
LIVE_DECK = "LSAT::Drills"
STAGING_TAG = "lsat::staging"


@dataclass
class BatchResult:
    passing: list[Card]
    verdict_counts: dict[str, int]
    checked: int
    pass_rate: float
    wrong_rate: float
    gate_passed: bool
    degraded: bool = False
    parse_failures: int = 0
    dropped_unsupported: int = 0
    notes: list[str] = field(default_factory=list)


def run_batch(
    sources: list[tuple[str, str]],
    taxonomy_nodes: list[str],
    client: LLMClient,
    *,
    n_per_source: int = 10,
    pass_rate_min: float = CARD_CHECK_PASS_RATE_MIN,
    wrong_rate_max: float = CARD_CHECK_WRONG_RATE_MAX,
) -> BatchResult:
    """Generate + independently check a batch; compute the quality gate. Pure."""
    counts = {v: 0 for v in VERDICT_ORDER}
    passing: list[Card] = []
    checked = parse_failures = dropped = 0
    notes: list[str] = []

    for source_id, source_text in sources:
        gen = generate_cards(
            source_id, source_text, taxonomy_nodes, client, n=n_per_source
        )
        if gen.degraded:
            return BatchResult(
                [], counts, 0, 0.0, 0.0, False, degraded=True, notes=[gen.note]
            )
        if gen.parse_failed:
            parse_failures += 1
            notes.append(f"{source_id}: {gen.note}")
            continue
        dropped += gen.dropped_unsupported
        for idx, card in enumerate(gen.cards):
            try:
                verdict = check_card(
                    card, source_text, client, card_id=f"{source_id}-{idx}"
                )
            except LLMUnavailable as exc:
                return BatchResult(
                    [],
                    counts,
                    checked,
                    0.0,
                    0.0,
                    False,
                    degraded=True,
                    notes=[f"AI unavailable: {exc}"],
                )
            checked += 1
            counts[verdict.verdict] = counts.get(verdict.verdict, 0) + 1
            if verdict.passed:
                passing.append(card)

    pass_rate = counts.get(PASS_VERDICT, 0) / checked if checked else 0.0
    wrong_rate = counts.get("WRONG", 0) / checked if checked else 0.0
    gate = checked > 0 and pass_rate >= pass_rate_min and wrong_rate <= wrong_rate_max
    return BatchResult(
        passing=passing,
        verdict_counts=counts,
        checked=checked,
        pass_rate=pass_rate,
        wrong_rate=wrong_rate,
        gate_passed=gate,
        parse_failures=parse_failures,
        dropped_unsupported=dropped,
        notes=notes,
    )


def stage_and_promote(
    col: Collection, batch: BatchResult, *, promote: bool = True
) -> dict[str, object]:
    """Add passing cards to staging; promote to the live deck iff the gate passed."""
    from anki.decks import DeckId
    from lsat.notetypes import LSAT_CARD, ensure_notetypes
    from lsat.taxonomy import node_id_to_tag

    if not batch.passing:
        return {"staged": 0, "promoted": 0, "gate_passed": batch.gate_passed}

    ensure_notetypes(col)
    notetype = col.models.by_name(LSAT_CARD)
    assert notetype is not None
    staging_deck = DeckId(col.decks.add_normal_deck_with_name(STAGING_DECK).id)

    # Idempotency: skip cards whose citation already exists, so re-running the
    # pipeline on the same source does not duplicate cards in the deck.
    existing_quotes = {
        col.get_note(nid)["source_quote"]
        for nid in col.find_notes(f'note:"{LSAT_CARD}"')
    }

    staged_nids = []
    for card in batch.passing:
        if card.source_quote in existing_quotes:
            continue
        existing_quotes.add(card.source_quote)
        note = col.new_note(notetype)
        note["front"] = card.front
        note["back"] = card.back
        note["explanation"] = card.explanation
        note["skill_tags"] = " ".join(card.skill_tags)
        note["source_id"] = card.source_id
        note["source_quote"] = card.source_quote
        note.tags = [node_id_to_tag(t) for t in card.skill_tags] + [STAGING_TAG]
        col.add_note(note, staging_deck)
        col.sched.suspend_cards(list(note.card_ids()))
        staged_nids.append(note.id)

    promoted = 0
    if promote and batch.gate_passed:
        live_deck = DeckId(col.decks.add_normal_deck_with_name(LIVE_DECK).id)
        cids = [cid for nid in staged_nids for cid in col.get_note(nid).card_ids()]
        col.set_deck(cids, live_deck)
        col.sched.unsuspend_cards(cids)
        col.tags.bulk_remove(staged_nids, STAGING_TAG)
        promoted = len(staged_nids)

    return {
        "staged": len(staged_nids),
        "promoted": promoted,
        "gate_passed": batch.gate_passed,
    }


def run_generation_pipeline(
    col: Collection,
    sources: list[tuple[str, str]],
    taxonomy_nodes: list[str],
    client: LLMClient,
    *,
    n_per_source: int = 10,
    promote: bool = True,
) -> dict[str, object]:
    """End-to-end: generate + check a batch, then stage/promote. Degrades safely."""
    batch = run_batch(sources, taxonomy_nodes, client, n_per_source=n_per_source)
    result: dict[str, object] = {
        "degraded": batch.degraded,
        "checked": batch.checked,
        "verdict_counts": batch.verdict_counts,
        "pass_rate": batch.pass_rate,
        "wrong_rate": batch.wrong_rate,
        "gate_passed": batch.gate_passed,
        "dropped_unsupported": batch.dropped_unsupported,
        "parse_failures": batch.parse_failures,
    }
    if batch.degraded:
        result.update({"staged": 0, "promoted": 0})
        return result
    result.update(stage_and_promote(col, batch, promote=promote))
    return result
