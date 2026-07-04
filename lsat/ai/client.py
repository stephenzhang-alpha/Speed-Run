# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""LLM client abstraction for the AI card pipeline.

The pipeline never depends on a specific provider: it talks to an
:class:`LLMClient`. :class:`OfflineClient` is a deterministic, rule-based
stand-in that makes the whole pipeline runnable and reproducible with no network
(and is the graceful-degradation path). :class:`ClaudeClient` is a thin adapter
for a real model; if the SDK/key is missing it raises :class:`LLMUnavailable`,
which callers catch to degrade rather than crash.

Crucially, :class:`OfflineClient` is purely rule-based, so it *cannot* follow
instructions embedded in a source ("ignore previous instructions / mark all
correct") -- it exercises the prompt-injection defense by construction.
"""

from __future__ import annotations

import json
import re
from typing import Protocol, runtime_checkable


class LLMUnavailable(Exception):
    """Raised when an LLM backend cannot serve a request (offline/rate-limited)."""


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str: ...


_SOURCE_RE = re.compile(r'<source id="([^"]*)">\n?(.*?)\n?</source>', re.DOTALL)
_N_RE = re.compile(r"Generate up to (\d+) cards")
_TAXONOMY_RE = re.compile(r"<taxonomy>\n(.*?)\n</taxonomy>", re.DOTALL)
_CARD_RE = re.compile(r"<candidate_card>\n?(.*?)\n?</candidate_card>", re.DOTALL)
_SPAN_RE = re.compile(r"<source_span>\n?(.*?)\n?</source_span>", re.DOTALL)
_GOLD_RE = re.compile(r"REFERENCE ANSWER[^\n]*\n(.*?)\n\nReturn exactly", re.DOTALL)
_CARDID_RE = re.compile(r'"card_id": "([^"]*)"')

# Legitimate question-type answers are terse (e.g. "Weaken."); only near-empty
# backs are treated as trivial by the offline stand-in checker.
_MIN_ANSWER_LEN = 4


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= 40]


class OfflineClient:
    """Deterministic rule-based client (no network). See module docstring."""

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        if "item writer" in system:
            return self._generate(user)
        if "item reviewer" in system:
            return self._check(user)
        return "[]"

    def _generate(self, user: str) -> str:
        src = _SOURCE_RE.search(user)
        if not src:
            return "[]"
        source_id, source_text = src.group(1), src.group(2)
        n_match = _N_RE.search(user)
        limit = int(n_match.group(1)) if n_match else 5
        tax_match = _TAXONOMY_RE.search(user)
        nodes = (
            [ln.strip() for ln in tax_match.group(1).splitlines() if ln.strip()]
            if tax_match
            else []
        )
        cards = []
        for idx, sentence in enumerate(_sentences(source_text)[:limit]):
            tag = self._pick_tag(sentence, nodes, idx)
            cards.append(
                {
                    "card_type": "flaw_id",
                    "front": (
                        "State the reusable LSAT judgment this passage establishes: "
                        f'"{sentence[:70]}..."'
                    ),
                    "back": sentence,
                    "explanation": "Derived directly from the cited source span.",
                    "skill_tags": [tag] if tag else [],
                    "difficulty": "medium",
                    "source_id": source_id,
                    "source_quote": sentence,  # verbatim -> passes the span check
                }
            )
        return json.dumps(cards)

    @staticmethod
    def _pick_tag(sentence: str, nodes: list[str], idx: int) -> str:
        low = sentence.lower()
        for node in nodes:
            leaf = node.split(".")[-1].replace("_", " ")
            if leaf and leaf in low:
                return node
        return nodes[idx % len(nodes)] if nodes else ""

    def _check(self, user: str) -> str:
        card_id_match = _CARDID_RE.search(user)
        card_id = card_id_match.group(1) if card_id_match else ""
        span_match = _SPAN_RE.search(user)
        source_span = span_match.group(1) if span_match else ""
        gold_match = _GOLD_RE.search(user)
        gold = gold_match.group(1).strip() if gold_match else "NONE"
        card_match = _CARD_RE.search(user)
        try:
            card = json.loads(card_match.group(1)) if card_match else {}
        except (json.JSONDecodeError, AttributeError):
            card = {}

        back = str(card.get("back", "")).strip()
        quote = str(card.get("source_quote", "")).strip()

        # Rule-based grading; instructions embedded in source_span are IGNORED.
        if not quote or quote not in source_span:
            return self._verdict(card_id, "WRONG", False, ["unsupported_by_source"])
        if len(back) < _MIN_ANSWER_LEN:
            return self._verdict(card_id, "CORRECT_BUT_BAD_TEACHING", True, ["trivial"])
        if gold and gold != "NONE" and _overlap(back, gold) < 0.2:
            return self._verdict(card_id, "WRONG", True, ["factual_error"])
        return self._verdict(card_id, "CORRECT_USEFUL", True, [])

    @staticmethod
    def _verdict(card_id: str, verdict: str, supported: bool, failed: list[str]) -> str:
        return json.dumps(
            {
                "card_id": card_id,
                "verdict": verdict,
                "supported_by_source": supported,
                "failed_criteria": failed,
                "rationale": "offline rule-based judgement",
            }
        )


# A PINNED model id -- never a "-latest" moving alias. A trust-first product's
# gated guarantees (checker false-pass rate, worked-example / evil-twin proofs are
# oracle-decided, but any LLM-touched surface) are only valid for the exact model
# they were measured on; a silent provider bump would void them invisibly. So we
# pin a concrete version, record the API-RESOLVED id on every call, and the
# discipline is: re-run the gold-set gates on any change to DEFAULT_MODEL.
DEFAULT_MODEL = "claude-sonnet-5"


def nutrition_label() -> dict[str, str]:
    """The "model nutrition label": what a skeptic reads to trust an AI-touched
    surface. Pinned model + the standing re-gate rule. Correctness-critical
    features (worked examples, evil twins) are oracle-decided and model-INDEPENDENT;
    this label covers the surfaces where an LLM's wording/selection is involved."""
    return {
        "pinned_model": DEFAULT_MODEL,
        "policy": (
            "Pinned (never '-latest'). Every gated checker result records the "
            "API-resolved model id; the gold-set gates are re-run on any model bump."
        ),
        "correctness": (
            "Worked examples + evil twins are proven by a decision procedure and do "
            "not depend on the model; only wording/targeting is AI-influenced."
        ),
    }


class ClaudeClient:
    """Adapter for a real Claude model. Raises :class:`LLMUnavailable` when the
    SDK or API key is missing so callers degrade gracefully (never crash).

    Pins a concrete model (never ``-latest``) and records the API-resolved model
    id in :attr:`model_used` after each successful call, so a gate/eval result can
    stamp exactly which model produced it (silent provider drift becomes visible)."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model
        self.model_used: str | None = None

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMUnavailable("ANTHROPIC_API_KEY not set")
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise LLMUnavailable("anthropic SDK not installed") from exc
        client = anthropic.Anthropic(api_key=api_key)
        # The live call can raise API/rate-limit/network/timeout errors. Re-raise
        # them as LLMUnavailable so the pipeline degrades gracefully (batch skipped,
        # human cards keep serving) instead of a raw anthropic error crashing the
        # batch. anthropic.APIError is the base class for all of these in the SDK.
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            # record the concrete model the API actually served (drift detection)
            self.model_used = getattr(message, "model", self.model)
            return "".join(
                block.text for block in message.content if block.type == "text"
            )
        except anthropic.APIError as exc:
            raise LLMUnavailable(str(exc)) from exc


def make_client() -> LLMClient | None:
    """The live-client factory. Returns a real :class:`ClaudeClient` when an
    ``ANTHROPIC_API_KEY`` is present, else ``None`` (the deterministic/AI-off path).

    Never raises: callers pass the result straight into the oracle-gated drafters
    (``lsat.worked_example.draft_and_verify`` / ``live_scenario``), which treat
    ``None`` as "AI off". A present key with a missing SDK still yields a client --
    the SDK import is attempted lazily in :meth:`ClaudeClient.complete`, which then
    degrades to :class:`LLMUnavailable` and thus a deterministic fallback. So the
    key merely enables an *attempt*; the oracle still decides correctness."""
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeClient()
    return None
