# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Card generation (docs/ai-card-pipeline.md section 1).

Builds the generator prompt, calls the LLM, and applies two defenses before a
card is even shown to the checker:

- **defensive parse**: strip stray code fences, ``json.loads`` in try/except; any
  failure fails the WHOLE batch (no partial/garbled output flows downstream);
- **programmatic source-span check**: ``source_quote`` must be a verbatim
  substring of the chunk we sent, else the citation was fabricated (or smuggled
  via injection) and the card is dropped.

If the LLM is unavailable the batch is skipped (empty result), never raised --
the review loop must not block on the AI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from lsat.ai.client import LLMClient, LLMUnavailable
from lsat.ai.prompts import GENERATOR_SYSTEM, generator_user

_REQUIRED_FIELDS = ("front", "back", "skill_tags", "source_id", "source_quote")


@dataclass
class Card:
    card_type: str
    front: str
    back: str
    explanation: str
    skill_tags: list[str]
    difficulty: str
    source_id: str
    source_quote: str

    def checker_json(self) -> str:
        """Card JSON for the checker -- WITHOUT ``explanation`` (independence:
        the judge must not treat the generator's rationale as authority)."""
        return json.dumps(
            {
                "card_type": self.card_type,
                "front": self.front,
                "back": self.back,
                "skill_tags": self.skill_tags,
                "difficulty": self.difficulty,
                "source_id": self.source_id,
                "source_quote": self.source_quote,
            },
            indent=2,
        )


@dataclass
class GenerationResult:
    cards: list[Card]
    dropped_unsupported: int = 0
    parse_failed: bool = False
    degraded: bool = False
    note: str = ""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def generate_cards(
    source_id: str,
    source_text: str,
    taxonomy_nodes: list[str],
    client: LLMClient,
    *,
    n: int = 10,
) -> GenerationResult:
    """Generate cited cards from one bounded source chunk (defensive)."""
    system = GENERATOR_SYSTEM
    user = generator_user(n, taxonomy_nodes, source_id, source_text)
    try:
        raw = client.complete(system, user, temperature=0.2)
    except LLMUnavailable as exc:
        return GenerationResult(cards=[], degraded=True, note=f"AI unavailable: {exc}")

    try:
        parsed = json.loads(_strip_fences(raw))
    except (json.JSONDecodeError, ValueError):
        return GenerationResult(cards=[], parse_failed=True, note="unparseable output")
    if not isinstance(parsed, list):
        return GenerationResult(cards=[], parse_failed=True, note="not a JSON array")

    cards: list[Card] = []
    dropped = 0
    # The exact taxonomy set we told the generator to tag against (see
    # generator_user's <taxonomy> block). Tags outside it are hallucinated.
    allowed_tags = set(taxonomy_nodes)
    for item in parsed:
        if not isinstance(item, dict) or not all(f in item for f in _REQUIRED_FIELDS):
            dropped += 1
            continue
        quote = str(item.get("source_quote", ""))
        # Programmatic source-span check: the citation must be verbatim from the
        # chunk we sent. Fabricated/injected citations are dropped here.
        if not quote or quote not in source_text:
            dropped += 1
            continue
        tags = item.get("skill_tags") or []
        if not isinstance(tags, list):
            dropped += 1
            continue
        tags = [str(t) for t in tags]
        # Taxonomy check (mirrors the source-span check above): a card with no
        # tags, or any tag outside the taxonomy we provided, is unroutable or
        # hallucinated -- drop it rather than admit an unlabeled/mis-labeled card.
        if not tags or any(t not in allowed_tags for t in tags):
            dropped += 1
            continue
        cards.append(
            Card(
                card_type=str(item.get("card_type", "")),
                front=str(item["front"]),
                back=str(item["back"]),
                explanation=str(item.get("explanation", "")),
                skill_tags=tags,
                difficulty=str(item.get("difficulty", "medium")),
                source_id=str(item["source_id"]),
                source_quote=quote,
            )
        )
    return GenerationResult(cards=cards, dropped_unsupported=dropped)
