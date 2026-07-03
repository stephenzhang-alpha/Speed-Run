# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The independent card checker -- the gate (docs/ai-card-pipeline.md section 2).

Runs as a separate LLM call with its own rubric. It re-derives the verdict from
the card + cited source span; it never sees the generator's ``explanation`` and
never trusts that a card is correct because a model produced it. A card enters
the deck only if ``verdict == CORRECT_USEFUL``.

Before it can be trusted as a gate it must be validated against the gold set:
:func:`validate_checker` measures the **false-pass rate** (how often it marks a
known-wrong card CORRECT_USEFUL).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from lsat.ai.client import LLMClient
from lsat.ai.generator import Card, _strip_fences
from lsat.ai.prompts import CHECKER_SYSTEM, checker_user

PASS_VERDICT = "CORRECT_USEFUL"
# Fixed order so verdict tallies serialise deterministically (reproducible eval;
# a set's iteration order varies with PYTHONHASHSEED across processes).
VERDICT_ORDER = ("CORRECT_USEFUL", "WRONG", "CORRECT_BUT_BAD_TEACHING")
VERDICTS = frozenset(VERDICT_ORDER)


@dataclass
class Verdict:
    card_id: str
    verdict: str
    supported_by_source: bool
    failed_criteria: list[str]
    rationale: str

    @property
    def passed(self) -> bool:
        return self.verdict == PASS_VERDICT


def check_card(
    card: Card,
    source_span: str,
    client: LLMClient,
    *,
    gold_answer: str | None = None,
    card_id: str = "card",
) -> Verdict:
    """Independently judge one card. May raise ``LLMUnavailable`` (caller degrades).

    Any unparseable/invalid checker output is treated as WRONG -- a card we
    cannot verify is never admitted (fail closed)."""
    user = checker_user(card.checker_json(), source_span, gold_answer, card_id)
    raw = client.complete(CHECKER_SYSTEM, user, temperature=0.0)
    try:
        obj = json.loads(_strip_fences(raw))
        verdict = obj.get("verdict", "")
    except (json.JSONDecodeError, ValueError, AttributeError):
        return Verdict(card_id, "WRONG", False, ["unparseable_checker_output"], "")
    # Fail closed on any malformed shape: a non-string verdict (list/dict is
    # unhashable) or a non-list failed_criteria must yield WRONG, never a
    # TypeError that would crash the batch (the review loop must not block).
    if not isinstance(verdict, str) or verdict not in VERDICTS:
        return Verdict(card_id, "WRONG", False, ["invalid_verdict"], "")
    raw_failed = obj.get("failed_criteria", [])
    failed = [str(c) for c in raw_failed] if isinstance(raw_failed, list) else []
    return Verdict(
        card_id=card_id,
        verdict=verdict,
        supported_by_source=bool(obj.get("supported_by_source", False)),
        failed_criteria=failed,
        rationale=str(obj.get("rationale", "")),
    )


def validate_checker(
    cases: list[tuple[Card, str, str, bool]], client: LLMClient
) -> dict[str, float]:
    """Validate the checker against labelled cases before trusting it as a gate.

    ``cases`` = ``(card, source_span, gold_answer, is_actually_correct)``. Returns
    the false-pass rate (known-wrong cards admitted as CORRECT_USEFUL), the
    false-block rate, agreement, and counts."""
    n = len(cases)
    if n == 0:
        return {
            "false_pass_rate": 0.0,
            "false_block_rate": 0.0,
            "agreement": 1.0,
            "n": 0,
        }
    false_pass = false_block = agree = wrong_total = correct_total = 0
    for idx, (card, span, gold, is_correct) in enumerate(cases):
        v = check_card(card, span, client, gold_answer=gold, card_id=f"gold-{idx}")
        admitted = v.passed
        if is_correct:
            correct_total += 1
            if admitted:
                agree += 1
            else:
                false_block += 1
        else:
            wrong_total += 1
            if admitted:
                false_pass += 1
            else:
                agree += 1
    return {
        "false_pass_rate": (false_pass / wrong_total) if wrong_total else 0.0,
        "false_block_rate": (false_block / correct_total) if correct_total else 0.0,
        "agreement": agree / n,
        "n": float(n),
    }
