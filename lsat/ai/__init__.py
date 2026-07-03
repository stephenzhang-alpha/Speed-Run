# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Anki for LSAT: the AI card pipeline (generation + independent checker).

See ``docs/ai-card-pipeline.md`` for the spec. The graded invariants live here:

1. every card cites a verbatim ``source_quote`` span (traceability),
2. an independent checker is the gate (never trusts the generator),
3. the source is untrusted data, never instructions (prompt-injection defense),
4. the app works with AI off (graceful degradation).

The LLM is abstracted behind :class:`lsat.ai.client.LLMClient`; an
:class:`~lsat.ai.client.OfflineClient` makes the whole pipeline runnable and
reproducible with no network (and is the degradation path), while a real
Claude adapter plugs in unchanged.
"""
