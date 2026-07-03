# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Oracle-Verified Faded Worked Examples (research feature #1). [AI - optional]

The single AI feature whose correctness is a **proof**, not a model's opinion.
For a multi-arrow conditional-chain item an LLM may *draft* a step-by-step
derivation, but a decidable oracle -- the exact material-entailment grader
:func:`lsat.conditional_chain.entails` -- **re-derives every step and BLOCKS the
example unless all steps verify**. A hallucinated inference literally cannot pass:
it fails entailment (or cites a premise that does not license the step) and the
whole example is withheld. This is the "generate-with-a-proof" pattern: the LLM
proposes, the oracle disposes. Correctness never rests on the LLM.

Layers (strongest guarantee first):

- :func:`verify_worked_example` -- **the oracle gate.** Given a PROPOSED
  derivation, accept only if every step applies a real premise (direct or
  contrapositive) from the running frontier, the steps connect start->goal, and
  every cumulative claim is entailed. Anything else is BLOCKED (fail-closed).
- :func:`build_worked_example` -- the deterministic, oracle-DERIVED worked
  example (the AI-off floor + ground truth). Steps come from a shortest path over
  the implication+contrapositive graph; each partial conclusion is entails-checked.
  Abstains (fail-closed) on items with no clean chaining derivation.
- :func:`faded_variants` / :func:`grade_fill` -- **backward fading**: reveal the
  first steps, blank the last k, and oracle-grade the learner's filled step (any
  oracle-valid next move is accepted, not just the canonical one).
- :func:`draft_and_verify` -- **the AI feature**: an LLM drafts the ordered moves,
  the oracle verifies; on ``LLMUnavailable`` or a blocked/garbled draft it
  degrades to :func:`build_worked_example` (AI is additive, never load-bearing).
- :func:`narrate` -- optional fail-closed LLM rephrase of the (already-proven)
  step prose; never touches step correctness, mirrors
  :func:`lsat.ai.misconception.rephrase_with_ai`.
- :func:`theater_scenarios` -- the "Oracle Proof Theater" demo surface. A *recorded*
  LLM draft of a derivation (curated, replayable offline) is checked LIVE, step by
  step, by this exact oracle. On the planted hallucination the verdict flips to
  BLOCKED with the oracle's reason, then the oracle substitutes the continuation it
  can prove. The AI's words are a recording; every verdict is computed at call time
  by the same :func:`verify_worked_example` / :func:`entails` logic -- nothing baked.

Fully removable: with AI off the feature serves the deterministic oracle-derived
example and every grade stays oracle-decided.
"""

from __future__ import annotations

import json
import re
from collections import deque
from functools import lru_cache
from typing import Any

from lsat.ai.client import LLMClient, LLMUnavailable
from lsat.conditional_chain import (
    CHAIN_ITEMS,
    DOES_NOT_FOLLOW,
    MUST_FOLLOW,
    Implication,
    Lit,
    entails,
)

# A "move" the drafter/learner may choose: apply premise ``impl_index`` either
# directly or as its contrapositive. A derivation is an ordered list of moves;
# every move is checked against the oracle, so the choice set is closed and safe.
Edge = tuple[Lit, Lit, int, bool]  # (ante, cons, impl_index, is_contrapositive)


def _provenance_edges(chain: list[Implication]) -> list[Edge]:
    """Every legal single-step edge: each premise ``a->b`` licenses ``a->b`` AND
    its contrapositive ``not b -> not a``, tagged with the premise index."""
    out: list[Edge] = []
    for i, imp in enumerate(chain):
        out.append((imp.ante, imp.cons, i, False))
        cp = imp.contrapositive()
        out.append((cp.ante, cp.cons, i, True))
    return out


def _derive_path(
    chain: list[Implication], candidate: Implication
) -> list[dict[str, Any]] | None:
    """Shortest chaining derivation (a list of step dicts) from ``candidate.ante``
    to ``candidate.cons`` over premise + contrapositive edges, or ``None`` if the
    goal is not reachable by chaining (an entailment that does not ride a path --
    e.g. a vacuous/tautological case -- for which we deliberately abstain)."""
    start, goal = candidate.ante, candidate.cons
    if start == goal:
        return None  # trivial self-implication is not a teaching example
    edges = _provenance_edges(chain)
    prev: dict[Lit, Edge | None] = {start: None}
    q: deque[Lit] = deque([start])
    while q:
        node = q.popleft()
        if node == goal:
            break
        for edge in edges:
            a, b, _idx, _contra = edge
            if a == node and b not in prev:
                prev[b] = edge
                q.append(b)
    if goal not in prev:
        return None
    path: list[dict[str, Any]] = []
    node = goal
    while prev[node] is not None:
        a, b, idx, contra = prev[node]  # type: ignore[misc]
        path.append({"from": a, "to": b, "impl_index": idx, "contrapositive": contra})
        node = a
    path.reverse()
    return path


def build_worked_example(
    chain: list[Implication], candidate: Implication, *, note: str | None = None
) -> dict[str, Any]:
    """The deterministic, oracle-DERIVED worked example, or a fail-closed abstain.

    Builds only for a genuinely-entailed must-follow candidate that has a clean
    chaining derivation; every step's cumulative claim is verified by
    :func:`entails` (correct by construction). Returns
    ``{available: True, goal, premises, steps, note}`` or ``{available: False, reason}``.
    """
    if candidate.ante == candidate.cons:
        return {"available": False, "reason": "trivial self-implication"}
    if not entails(chain, candidate):
        return {
            "available": False,
            "reason": "candidate does not follow -- nothing to prove",
        }
    path = _derive_path(chain, candidate)
    if path is None:
        return {
            "available": False,
            "reason": "no chaining derivation (entailed non-constructively)",
        }
    steps: list[dict[str, Any]] = []
    for edge in path:
        partial = Implication(candidate.ante, edge["to"])
        # Correctness-by-construction guard: a real chaining path is always sound,
        # but we still assert each cumulative claim with the oracle and fail closed
        # rather than emit an unverified step.
        if not entails(chain, partial):
            return {"available": False, "reason": "internal: unverified partial step"}
        steps.append({**edge, "partial": partial})
    return {
        "available": True,
        "goal": candidate,
        "premises": list(chain),
        "steps": steps,
        "note": note,
    }


def verify_worked_example(
    chain: list[Implication], candidate: Implication, steps: Any
) -> dict[str, Any]:
    """THE ORACLE GATE. Accept a PROPOSED derivation iff (1) it is a non-empty list
    of well-formed steps, (2) each step applies a real premise edge (direct or
    contrapositive) *from the running frontier*, (3) each cumulative claim
    ``candidate.ante -> step.to`` is entailed, and (4) the last step reaches
    ``candidate.cons``. Any violation BLOCKS (fail-closed). A hallucinated step --
    a fabricated premise, an illegal jump, affirming-the-consequent -- cannot pass.
    Returns ``{verified: bool, reason: str|None, step_failed: int|None}``.
    """
    if not isinstance(steps, list) or not steps:
        return {
            "verified": False,
            "reason": "empty or non-list derivation",
            "step_failed": None,
        }
    edge_set = set(_provenance_edges(chain))
    frontier = candidate.ante
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return {"verified": False, "reason": "malformed step", "step_failed": i}
        try:
            a = step["from"]
            b = step["to"]
            idx = int(step["impl_index"])
            contra = bool(step["contrapositive"])
        except (KeyError, TypeError, ValueError):
            return {"verified": False, "reason": "malformed step", "step_failed": i}
        if not isinstance(a, Lit) or not isinstance(b, Lit):
            return {
                "verified": False,
                "reason": "malformed step literal",
                "step_failed": i,
            }
        if a != frontier:
            return {
                "verified": False,
                "reason": "step does not start at the current frontier",
                "step_failed": i,
            }
        if (a, b, idx, contra) not in edge_set:
            return {
                "verified": False,
                "reason": "cited premise does not license this step",
                "step_failed": i,
            }
        if not entails(chain, Implication(candidate.ante, b)):
            return {
                "verified": False,
                "reason": "cumulative claim is not entailed",
                "step_failed": i,
            }
        frontier = b
    if frontier != candidate.cons:
        return {
            "verified": False,
            "reason": "derivation does not reach the goal",
            "step_failed": len(steps) - 1,
        }
    return {"verified": True, "reason": None, "step_failed": None}


# -- backward fading + oracle-graded fill -------------------------------------


def faded_variants(example: dict[str, Any]) -> list[dict[str, Any]]:
    """Backward-fading variants of a built example: for each level ``k`` in
    ``1..N`` reveal the first ``N-k`` steps and blank the last ``k`` for the
    learner to supply. Each blank carries the oracle answer (for grading/reveal).
    Empty if the example is unavailable."""
    if not example.get("available"):
        return []
    steps = example["steps"]
    n = len(steps)
    out: list[dict[str, Any]] = []
    for k in range(1, n + 1):
        cut = n - k
        blanks = [
            {
                "index": cut + j,
                "frontier": steps[cut + j]["from"],
                "answer": {
                    "impl_index": steps[cut + j]["impl_index"],
                    "contrapositive": steps[cut + j]["contrapositive"],
                    "to": steps[cut + j]["to"],
                },
            }
            for j in range(k)
        ]
        out.append({"fade": k, "shown_steps": steps[:cut], "blanks": blanks})
    return out


def grade_fill(
    chain: list[Implication],
    candidate: Implication,
    frontier: Lit,
    impl_index: Any,
    contrapositive: Any,
) -> dict[str, Any]:
    """Oracle-grade a learner's filled step: is applying premise ``impl_index``
    (direct/contra) at ``frontier`` a legal, entailed step? ANY oracle-valid next
    move is correct (not just the canonical one). Fails closed on a bad premise."""
    try:
        idx = int(impl_index)
        contra = bool(contrapositive)
    except (TypeError, ValueError):
        return {"graded": False, "reason": "malformed move"}
    if not (0 <= idx < len(chain)):
        return {"graded": False, "reason": "unknown premise"}
    if not isinstance(frontier, Lit):
        return {"graded": False, "reason": "malformed frontier"}
    imp = chain[idx].contrapositive() if contra else chain[idx]
    if imp.ante != frontier:
        return {
            "graded": True,
            "correct": False,
            "reason": "that premise does not apply at this step",
        }
    to = imp.cons
    entailed = entails(chain, Implication(candidate.ante, to))
    return {
        "graded": True,
        "correct": bool(entailed),
        "to": to,
        "reason": None
        if entailed
        else "a valid step, but it does not advance toward the goal",
    }


# -- the AI feature: LLM drafts, the oracle verifies --------------------------

_MOVES_RE = re.compile(r"\[.*\]", re.DOTALL)

_DRAFT_SYSTEM = (
    "You are a logic tutor drafting a step-by-step derivation. You may ONLY cite "
    "the given premises by their integer index, each applied either directly or "
    "as its contrapositive. Return ONLY a JSON array of moves in order, each an "
    'object {"premise": <int>, "contrapositive": <true|false>}. Output nothing '
    "else -- no prose, no markdown. An external checker verifies every step and "
    "discards any derivation that does not fully and validly reach the goal."
)


def _render_lit(lit: Lit, props: list[str]) -> str:
    p = props[lit.term] if 0 <= lit.term < len(props) else f"p{lit.term}"
    return f"not {p}" if lit.neg else p


def _render_imp(imp: Implication, props: list[str]) -> str:
    return f"If {_render_lit(imp.ante, props)}, then {_render_lit(imp.cons, props)}."


def default_props(chain: list[Implication], candidate: Implication) -> list[str]:
    terms = {candidate.ante.term, candidate.cons.term}
    for imp in chain:
        terms.add(imp.ante.term)
        terms.add(imp.cons.term)
    n = max(terms) + 1
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [letters[i] if i < len(letters) else f"p{i}" for i in range(n)]


def _reconstruct_steps(
    chain: list[Implication], moves: Any
) -> list[dict[str, Any]] | None:
    """Turn a list of ``{premise, contrapositive}`` moves into structural steps
    (from/to derived from the cited premise). Returns ``None`` on any malformed
    move or out-of-range index. The frontier-connection + entailment checks are
    left to :func:`verify_worked_example` (a wrong move yields a step whose
    ``from`` will not match the frontier and is blocked there)."""
    if not isinstance(moves, list) or not moves:
        return None
    steps: list[dict[str, Any]] = []
    for m in moves:
        if not isinstance(m, dict):
            return None
        try:
            idx = int(m["premise"])
            contra = bool(m.get("contrapositive", False))
        except (KeyError, TypeError, ValueError):
            return None
        if not (0 <= idx < len(chain)):
            return None
        imp = chain[idx].contrapositive() if contra else chain[idx]
        steps.append(
            {
                "from": imp.ante,
                "to": imp.cons,
                "impl_index": idx,
                "contrapositive": contra,
            }
        )
    return steps


def draft_and_verify(
    chain: list[Implication],
    candidate: Implication,
    *,
    client: LLMClient | None = None,
    note: str | None = None,
    props: list[str] | None = None,
) -> dict[str, Any]:
    """The AI feature. With AI off (``client is None``) returns the deterministic
    oracle-derived example. With a client, asks the LLM to draft the ordered
    moves, then GATES the draft through :func:`verify_worked_example`; a verified
    draft is served (``source="ai_verified"``), otherwise -- unavailable, garbled,
    or blocked -- it degrades to the deterministic example. Either way the served
    example is oracle-correct; the LLM can never inject an unverified step."""
    det = build_worked_example(chain, candidate, note=note)
    if client is None or not det.get("available"):
        if det.get("available"):
            det["source"] = "deterministic"
        return det
    try:
        raw = client.complete(_DRAFT_SYSTEM, _draft_user(chain, candidate, props))
    except LLMUnavailable:
        return {
            **det,
            "source": "deterministic_fallback",
            "fallback_reason": "llm_unavailable",
        }
    moves = _parse_moves(raw)
    steps = _reconstruct_steps(chain, moves)
    if steps is None:
        return {
            **det,
            "source": "deterministic_fallback",
            "fallback_reason": "unparseable_moves",
        }
    verdict = verify_worked_example(chain, candidate, steps)
    if not verdict["verified"]:
        return {
            **det,
            "source": "deterministic_fallback",
            "fallback_reason": verdict["reason"],
        }
    for step in steps:
        step["partial"] = Implication(candidate.ante, step["to"])
    return {
        "available": True,
        "goal": candidate,
        "premises": list(chain),
        "steps": steps,
        "note": note,
        "source": "ai_verified",
    }


def _draft_user(
    chain: list[Implication], candidate: Implication, props: list[str] | None
) -> str:
    props = props or default_props(chain, candidate)
    prem_lines = "\n".join(
        f'{i}: "{_render_imp(imp, props)}"' for i, imp in enumerate(chain)
    )
    return (
        f"Premises:\n{prem_lines}\n\n"
        f'Goal to derive: "{_render_imp(candidate, props)}"\n\n'
        "Return the ordered moves as a JSON array."
    )


def _parse_moves(raw: str) -> Any:
    m = _MOVES_RE.search(raw or "")
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# -- optional narration (template default; AI rephrase is fail-closed) ---------


def _step_line(step: dict[str, Any], chain: list[Implication], props: list[str]) -> str:
    """One proven derivation sentence, built from the verified structure."""
    cited = chain[step["impl_index"]]
    cited = cited.contrapositive() if step["contrapositive"] else cited
    frm = _render_lit(step["from"], props)
    to = _render_lit(step["to"], props)
    tag = " (contrapositive)" if step["contrapositive"] else ""
    return f'Since "{frm}", and "{_render_imp(cited, props)}"{tag}, we get "{to}".'


def render_steps(example: dict[str, Any], props: list[str] | None = None) -> list[str]:
    """Template narration (the shipping default): one proven sentence per step,
    built from the verified structure -- no free prose. Empty if unavailable."""
    if not example.get("available"):
        return []
    chain = example["premises"]
    goal = example["goal"]
    props = props or default_props(chain, goal)
    lines = [_step_line(step, chain, props) for step in example["steps"]]
    lines.append(f'Therefore "{_render_imp(goal, props)}" QED.')
    return lines


_BANNED_NEW_CONTENT = re.compile(r"\d")


def narrate(line: str, client: LLMClient | None) -> str:
    """Optionally rephrase ONE proven step sentence. Fail-closed: the rephrase is
    used only if it stays short, adds no digits, and preserves the step's key
    terms; otherwise (or with AI off/unavailable) the template sentence stands.
    Never affects correctness -- only wording."""
    if client is None:
        return line
    try:
        raw = client.complete(
            "You rewrite one sentence of a logic derivation in plainer words. Keep "
            "the meaning and every term exactly, at most one sentence, add no facts "
            "or numbers.",
            f"Rewrite plainly, keeping every term:\n{line}",
        ).strip()
    except LLMUnavailable:
        return line
    terms = [t for t in re.findall(r"[a-z]+", line.lower()) if len(t) > 2]
    ok = (
        0 < len(raw) <= 2 * len(line)
        and raw.count(".") <= 1
        and not _BANNED_NEW_CONTENT.search(raw)
        and all(
            t in raw.lower()
            for t in terms
            if t not in ("since", "and", "get", "the", "then")
        )
    )
    return raw if ok else line


# -- convenience over the curated chain drills --------------------------------


def worked_example_for(
    item_id: str, *, client: LLMClient | None = None
) -> dict[str, Any]:
    """Build (and, with a client, LLM-draft-then-verify) the worked example for a
    curated ``chain-<n>`` drill item. Fails closed on an unknown id or a
    does-not-follow item."""
    try:
        head, sep, tail = str(item_id).partition("-")
        if head != "chain" or not sep:
            raise ValueError
        idx = int(tail)
        if not 0 <= idx < len(CHAIN_ITEMS):
            raise IndexError
    except (ValueError, IndexError):
        return {"available": False, "reason": "unknown chain item"}
    it = CHAIN_ITEMS[idx]
    if it["verdict"] != MUST_FOLLOW:
        return {
            "available": False,
            "reason": "does-not-follow item has no worked derivation",
        }
    return draft_and_verify(
        it["chain"], it["candidate"], client=client, note=it.get("note")
    )


def worked_items(*, client: LLMClient | None = None) -> list[dict[str, Any]]:
    """All curated must-follow items rendered as worked examples (oracle-derived,
    optionally LLM-drafted+verified). Deterministic and safe to serve."""
    out: list[dict[str, Any]] = []
    for i, it in enumerate(CHAIN_ITEMS):
        if it["verdict"] != MUST_FOLLOW:
            continue
        ex = draft_and_verify(
            it["chain"], it["candidate"], client=client, note=it.get("note")
        )
        if not ex.get("available"):
            continue
        props = it["props"]
        out.append(
            {
                "item_id": f"chain-{i}",
                "premises": [_render_imp(p, props) for p in it["chain"]],
                "goal": _render_imp(it["candidate"], props),
                "steps": render_steps(ex, props),
                "n_steps": len(ex["steps"]),
                "source": ex.get("source", "deterministic"),
                "note": it.get("note"),
            }
        )
    return out


def worked_example_ids() -> list[str]:
    """The ids of curated must-follow chain items that actually build a worked
    example (fail-closed: items entailed non-constructively are excluded)."""
    out: list[str] = []
    for i, it in enumerate(CHAIN_ITEMS):
        if it["verdict"] != MUST_FOLLOW:
            continue
        if build_worked_example(it["chain"], it["candidate"]).get("available"):
            out.append(f"chain-{i}")
    return out


def _parse_move_id(move_id: Any) -> tuple[int | None, bool]:
    """``"2:contra"`` -> ``(2, True)``; ``"0:direct"`` -> ``(0, False)``. Returns
    ``(None, False)`` on any malformed id (fail-closed)."""
    try:
        idx_s, _, orient = str(move_id).partition(":")
        return int(idx_s), (orient == "contra")
    except (ValueError, AttributeError):
        return None, False


def faded_drill(
    item_id: str, *, fade: int = 1, client: LLMClient | None = None
) -> dict[str, Any]:
    """A render-ready backward-faded worked-example drill for a curated chain item:
    the first ``N-fade`` proven steps shown as prose, the next step blanked for the
    learner to complete, and every premise (in both orientations) offered as a move
    option. The correct move + the item's teaching note are NOT in the payload
    (withheld until grading -- no leak). Fails closed on an unbuildable item."""
    ex = worked_example_for(item_id, client=client)
    if not ex.get("available"):
        return {"available": False, "reason": ex.get("reason", "unavailable")}
    chain, goal = ex["premises"], ex["goal"]
    steps = ex["steps"]
    n = len(steps)
    fade = max(1, min(int(fade), n))
    cut = n - fade
    frontier = steps[cut]["from"]
    props = default_props(chain, goal)
    options = []
    for i, imp in enumerate(chain):
        options.append({"move_id": f"{i}:direct", "text": _render_imp(imp, props)})
        options.append(
            {"move_id": f"{i}:contra", "text": _render_imp(imp.contrapositive(), props)}
        )
    frontier_text = _render_lit(frontier, props)
    return {
        "available": True,
        "item_id": item_id,
        "premises": [_render_imp(p, props) for p in chain],
        "goal": _render_imp(goal, props),
        "shown_steps": [_step_line(steps[j], chain, props) for j in range(cut)],
        "frontier": frontier_text,
        "prompt": (
            f"Complete the derivation: which premise (as-is or its contrapositive) "
            f'takes the next step from "{frontier_text}"?'
        ),
        "options": options,
        "fade": fade,
        "source": ex.get("source", "deterministic"),
        "verification": {
            "method": "material entailment (a decision procedure), not a language model",
            "steps_verified": cut,
            "claim": (
                "Every shown step was re-derived by a proof checker "
                "(lsat.conditional_chain.entails); an AI-proposed step that does not "
                "verify is discarded, so a hallucinated step cannot appear here."
            ),
        },
    }


def grade_move(item_id: str, move_id: str, *, fade: int = 1) -> dict[str, Any]:
    """Oracle-grade a learner's chosen move on a faded worked-example drill. Grades
    against the deterministic ground-truth derivation (no client needed); returns
    JSON-safe fields only (the reached literal is rendered to text). Fail-closed on
    an unknown item or malformed move."""
    ex = worked_example_for(item_id)  # deterministic ground truth
    if not ex.get("available"):
        return {"graded": False, "reason": ex.get("reason", "unavailable")}
    chain, goal = ex["premises"], ex["goal"]
    steps = ex["steps"]
    n = len(steps)
    fade = max(1, min(int(fade), n))
    frontier = steps[n - fade]["from"]
    idx, contra = _parse_move_id(move_id)
    if idx is None:
        return {"graded": False, "reason": "malformed move"}
    result = grade_fill(chain, goal, frontier, idx, contra)
    if result.get("graded") and isinstance(result.get("to"), Lit):
        props = default_props(chain, goal)
        result["to_text"] = _render_lit(result.pop("to"), props)
    if result.get("graded"):
        result["note"] = ex.get("note")
    return result


# -- Oracle Proof Theater: a recorded AI draft, vetoed LIVE by the oracle ------
#
# The marquee, offline-demoable AI feature. Each scenario ships a RECORDED draft
# (an ordered list of proposed moves) of a real conditional-chain derivation.
# MOST moves are valid; exactly one is a planted hallucination (an illegal jump /
# wrong direction / non-sequitur). Correctness is NEVER stored: at call time we
# walk the recorded moves from the candidate's antecedent frontier and, for each,
# compute `verified` with the SAME predicate :func:`verify_worked_example` applies
# (a real premise edge from the current frontier AND an entails-checked cumulative
# claim). The hallucinated step genuinely fails that predicate -> BLOCKED; the
# oracle then substitutes the continuation it can prove via
# :func:`build_worked_example`. "The AI proposes, the oracle disposes" -- live.


def _mk(a: int, b: int, *, na: bool = False, nb: bool = False) -> Implication:
    return Implication(Lit(a, na), Lit(b, nb))


# Curated scenarios. `moves` is the recorded draft: {premise_index, contrapositive}
# in order, with EXACTLY ONE planted hallucination (kept last so every earlier move
# verifies and there is exactly one bad step). Verdicts are computed, never stored.
_THEATER_DEFS: list[dict[str, Any]] = [
    {
        # A confident transitive chain where the model skips a link.
        "id": "theater-skip",
        "title": "The confident skip",
        "fallacy": "Illegal jump",
        "props": ["A", "B", "C", "D", "E"],
        "chain": [_mk(0, 1), _mk(1, 2), _mk(2, 3), _mk(3, 4)],  # A→B, B→C, C→D, D→E
        "candidate": _mk(0, 4),  # A ⊢ E
        "moves": [
            {"premise_index": 0, "contrapositive": False},  # A→B  ✓
            {"premise_index": 1, "contrapositive": False},  # B→C  ✓
            {"premise_index": 3, "contrapositive": False},  # D→E  ✗ (skips C→D)
        ],
    },
    {
        # A contrapositive chain where the model runs an arrow the wrong way.
        "id": "theater-backwards",
        "title": "Running the arrow backwards",
        "fallacy": "Affirms the consequent",
        "props": ["A", "B", "C", "D", "E"],
        "chain": [_mk(0, 1), _mk(1, 2), _mk(2, 3), _mk(3, 4)],  # A→B, B→C, C→D, D→E
        "candidate": _mk(4, 0, na=True, nb=True),  # not E ⊢ not A
        "moves": [
            {"premise_index": 3, "contrapositive": True},  # ¬E→¬D  ✓
            {"premise_index": 2, "contrapositive": True},  # ¬D→¬C  ✓
            {"premise_index": 1, "contrapositive": False},  # B→C   ✗ (needs ¬C→¬B)
        ],
    },
    {
        # A chain with an unrelated red-herring premise the model grabs.
        "id": "theater-redherring",
        "title": "The tempting red herring",
        "fallacy": "Non-sequitur",
        # term ids: A=0, B=1, C=2, E=3, D=4, F=5
        "props": ["A", "B", "C", "E", "D", "F"],
        "chain": [_mk(0, 1), _mk(1, 2), _mk(2, 3), _mk(4, 5)],  # A→B, B→C, C→E, D→F
        "candidate": _mk(0, 3),  # A ⊢ E
        "moves": [
            {"premise_index": 0, "contrapositive": False},  # A→B  ✓
            {"premise_index": 1, "contrapositive": False},  # B→C  ✓
            {"premise_index": 3, "contrapositive": False},  # D→F  ✗ (unrelated)
        ],
    },
]


def _cited_text(imp: Implication, contra: bool, props: list[str]) -> str:
    """Render the premise a move cites, noting when it is the contrapositive."""
    return _render_imp(imp, props) + (" (contrapositive)" if contra else "")


def _block_reason(
    defn: dict[str, Any],
    frontier: Lit,
    imp: Implication,
    props: list[str],
    starts_here: bool,
    cumulative_ok: bool,
    ante_s: str,
) -> str:
    """The oracle's human-readable veto, composed from the LIVE-computed failure:
    which check failed (frontier connection and/or entailment) is not stored -- it
    is read off the same booleans that set ``verified``."""
    frontier_s = _render_lit(frontier, props)
    cited_s = _render_imp(imp, props)
    a_s = _render_lit(imp.ante, props)
    b_s = _render_lit(imp.cons, props)
    parts: list[str] = []
    if not starts_here:
        parts.append(f"the draft has {frontier_s}, but “{cited_s}” starts from {a_s}")
    if not cumulative_ok:
        parts.append(f"the oracle cannot prove {ante_s} ⊢ {b_s}")
    detail = ", so ".join(parts) if parts else "the step does not verify"
    return f"{defn['fallacy']} — {detail}."


def _build_theater_scenario(defn: dict[str, Any]) -> dict[str, Any]:
    """Replay one recorded draft and CHECK IT LIVE against the oracle, returning a
    JSON-safe scenario dict. Verdicts (verified/blocked) and the corrected
    continuation are computed here at call time -- never read from ``defn``."""
    chain: list[Implication] = defn["chain"]
    candidate: Implication = defn["candidate"]
    props: list[str] = defn["props"]
    # Correct-by-construction guard: only stage a genuinely provable candidate.
    if not build_worked_example(chain, candidate).get("available"):
        raise AssertionError(f"theater scenario {defn['id']} candidate is not provable")

    edge_set = set(_provenance_edges(chain))
    ante = candidate.ante
    ante_s = _render_lit(ante, props)
    frontier = ante
    steps: list[dict[str, Any]] = []
    blocked_frontier: Lit | None = None

    for i, mv in enumerate(defn["moves"]):
        idx = int(mv["premise_index"])
        contra = bool(mv["contrapositive"])
        imp = chain[idx].contrapositive() if contra else chain[idx]
        a, b = imp.ante, imp.cons
        # The SAME three conditions verify_worked_example enforces per step, live:
        real_edge = (a, b, idx, contra) in edge_set
        starts_here = a == frontier
        cumulative_ok = entails(chain, Implication(ante, b))
        verified = real_edge and starts_here and cumulative_ok
        claim = f"{ante_s} ⊢ {_render_lit(b, props)}"
        cited = _cited_text(imp, contra, props)
        if verified:
            steps.append(
                {
                    "n": i + 1,
                    "claim": claim,
                    "cited": cited,
                    "verified": True,
                    "blocked": False,
                    "reason": None,
                }
            )
            frontier = b
        else:
            steps.append(
                {
                    "n": i + 1,
                    "claim": claim,
                    "cited": cited,
                    "verified": False,
                    "blocked": True,
                    "reason": _block_reason(
                        defn, frontier, imp, props, starts_here, cumulative_ok, ante_s
                    ),
                }
            )
            blocked_frontier = frontier
            break  # fail-closed: the oracle stops the draft at the first bad step

    # The oracle proves the continuation from the blocked frontier to the goal
    # (source flips to a deterministic_fallback, exactly like draft_and_verify).
    corrected: list[dict[str, Any]] = []
    if blocked_frontier is not None:
        cont = build_worked_example(chain, Implication(blocked_frontier, candidate.cons))
        if cont.get("available"):
            for st in cont["steps"]:
                imp2 = (
                    chain[st["impl_index"]].contrapositive()
                    if st["contrapositive"]
                    else chain[st["impl_index"]]
                )
                corrected.append(
                    {
                        "claim": f"{ante_s} ⊢ {_render_lit(st['to'], props)}",
                        "cited": _cited_text(imp2, st["contrapositive"], props),
                    }
                )

    verified_steps = sum(1 for s in steps if s["verified"])
    return {
        "id": defn["id"],
        "title": defn["title"],
        "premises": [_render_imp(p, props) for p in chain],
        "goal": _render_imp(candidate, props),
        "mode": "recorded",
        "steps": steps,
        "corrected": corrected,
        "receipt": {
            "verified_steps": verified_steps,
            "note": (
                f"{verified_steps} step"
                f"{'' if verified_steps == 1 else 's'} re-derived live by the "
                "material-entailment oracle; the AI's next step was blocked and the "
                "oracle proved the rest."
            ),
        },
    }


@lru_cache(maxsize=1)
def _theater_json() -> str:
    """Cache the heavy oracle work (entails enumerates truth tables) once; store the
    result as a JSON string so :func:`theater_scenarios` hands back a fresh,
    guaranteed-JSON-safe object on every call (never a shared mutable)."""
    return json.dumps([_build_theater_scenario(d) for d in _THEATER_DEFS])


def theater_scenarios() -> list[dict[str, Any]]:
    """The Oracle Proof Theater scenarios: recorded AI drafts, each checked LIVE by
    the entailment oracle so exactly one planted hallucination is BLOCKED (with the
    oracle's reason) and the oracle's provable continuation is appended. JSON-safe."""
    return json.loads(_theater_json())


# -- self-test ----------------------------------------------------------------


def _selftest() -> bool:  # noqa: C901 - a thorough gate is worth the length
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    must_follow = [it for it in CHAIN_ITEMS if it["verdict"] == MUST_FOLLOW]
    does_not = [it for it in CHAIN_ITEMS if it["verdict"] == DOES_NOT_FOLLOW]

    # 1. every must-follow item either builds a verified example or abstains
    #    cleanly (never a broken/unverified one), and a built example round-trips
    #    through the gate.
    built = 0
    for it in must_follow:
        ex = build_worked_example(it["chain"], it["candidate"], note=it.get("note"))
        if ex.get("available"):
            built += 1
            v = verify_worked_example(it["chain"], it["candidate"], ex["steps"])
            check(
                f"built example round-trips through the gate ({it['note'][:30]}...)",
                v["verified"],
            )
            check("built example has >=1 step", len(ex["steps"]) >= 1)
    check("at least one must-follow item builds a worked example", built >= 1)

    # 2. does-not-follow candidates NEVER build a worked example (fail-closed)
    for it in does_not:
        ex = build_worked_example(it["chain"], it["candidate"])
        check("does-not-follow item abstains", ex.get("available") is False)

    # 3. THE GATE blocks planted-wrong derivations (false-pass must be 0).
    it0 = must_follow[0]
    chain0, cand0 = it0["chain"], it0["candidate"]
    good = build_worked_example(chain0, cand0)["steps"]
    # 3a. empty derivation
    check(
        "gate blocks empty derivation",
        not verify_worked_example(chain0, cand0, [])["verified"],
    )
    # 3b. a fabricated first step (cite a premise that does not apply at the start)
    bad_edge = dict(good[-1])  # a real edge, but likely not from the start frontier
    if bad_edge["from"] != cand0.ante:
        check(
            "gate blocks a step not starting at the frontier",
            not verify_worked_example(chain0, cand0, [bad_edge])["verified"],
        )
    # 3c. a step citing a premise index that does not license from->to
    forged = dict(good[0])
    forged = {**forged, "impl_index": (forged["impl_index"] + 1) % len(chain0)}
    v3c = verify_worked_example(chain0, cand0, [forged, *good[1:]])
    check("gate blocks a forged premise citation", not v3c["verified"])
    # 3d. a truncated derivation that never reaches the goal
    if len(good) >= 2:
        check(
            "gate blocks a derivation that stops short",
            not verify_worked_example(chain0, cand0, good[:-1])["verified"],
        )
    # 3e. affirming the consequent: for A->..->D, the reversed candidate D->A does
    #     not follow, so build abstains AND any hand-built "derivation" is blocked.
    rev = Implication(cand0.cons, cand0.ante)
    check(
        "affirming-consequent candidate abstains",
        build_worked_example(chain0, rev).get("available") is False,
    )
    # 3f. a step with a non-Lit literal (garbage) is rejected
    check(
        "gate blocks garbage literal",
        not verify_worked_example(
            chain0,
            cand0,
            [{"from": "A", "to": "B", "impl_index": 0, "contrapositive": False}],
        )["verified"],
    )

    # 4. draft_and_verify: AI-off, AI-verified, malicious-blocked, down-degraded
    class GoodClient:
        def __init__(self, moves: list[dict[str, Any]]) -> None:
            self._moves = moves

        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            return json.dumps(self._moves)

    class MaliciousClient:
        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            # a plausible-but-wrong derivation: apply premises in reverse order
            return json.dumps([{"premise": len(chain0) - 1, "contrapositive": False}])

    class GarbageClient:
        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            return "Sure! Here's the proof: first A, then B, obviously D. Trust me."

    class DownClient:
        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            raise LLMUnavailable("offline")

    off = draft_and_verify(chain0, cand0, client=None)
    check(
        "AI-off returns deterministic example",
        off.get("available") and off.get("source") == "deterministic",
    )

    good_moves = [
        {"premise": s["impl_index"], "contrapositive": s["contrapositive"]}
        for s in good
    ]
    ai = draft_and_verify(chain0, cand0, client=GoodClient(good_moves))
    check(
        "valid AI draft is verified + served",
        ai.get("available") and ai.get("source") == "ai_verified",
    )
    v_ai = (
        verify_worked_example(chain0, cand0, ai["steps"])
        if ai.get("available")
        else {"verified": False}
    )
    check("served AI example re-verifies", v_ai["verified"])

    mal = draft_and_verify(chain0, cand0, client=MaliciousClient())
    check(
        "malicious AI draft is blocked -> deterministic fallback",
        mal.get("available") and mal.get("source") == "deterministic_fallback",
    )
    check(
        "fallback example is the CORRECT one (re-verifies)",
        verify_worked_example(chain0, cand0, mal["steps"])["verified"],
    )

    garb = draft_and_verify(chain0, cand0, client=GarbageClient())
    check(
        "garbled AI draft -> deterministic fallback",
        garb.get("source") == "deterministic_fallback",
    )

    down = draft_and_verify(chain0, cand0, client=DownClient())
    check(
        "LLM down -> deterministic fallback",
        down.get("source") == "deterministic_fallback",
    )

    # OfflineClient (rule-based, returns "[]" here) must degrade, never crash
    from lsat.ai.client import OfflineClient

    offc = draft_and_verify(chain0, cand0, client=OfflineClient())
    check(
        "OfflineClient degrades to deterministic",
        offc.get("available") and offc.get("source") == "deterministic_fallback",
    )

    # 5. backward fading + grade_fill
    ex0 = build_worked_example(chain0, cand0)
    variants = faded_variants(ex0)
    check(
        "fading produces N variants (levels 1..N)",
        len(variants) == len(good)
        and [x["fade"] for x in variants] == list(range(1, len(good) + 1)),
    )
    # the deepest fade blanks every step; grade the FIRST blank's correct answer
    deepest = variants[-1]
    first_blank = deepest["blanks"][0]
    g_ok = grade_fill(
        chain0,
        cand0,
        first_blank["frontier"],
        first_blank["answer"]["impl_index"],
        first_blank["answer"]["contrapositive"],
    )
    check(
        "grade_fill: correct move graded correct",
        g_ok.get("graded") and g_ok.get("correct"),
    )
    # a premise that does not apply at the start frontier is graded wrong (not crash)
    wrong_idx = next(
        (
            i
            for i in range(len(chain0))
            if chain0[i].ante != first_blank["frontier"]
            and chain0[i].contrapositive().ante != first_blank["frontier"]
        ),
        None,
    )
    if wrong_idx is not None:
        g_bad = grade_fill(chain0, cand0, first_blank["frontier"], wrong_idx, False)
        check(
            "grade_fill: inapplicable premise graded wrong",
            g_bad.get("graded") and not g_bad.get("correct"),
        )
    check(
        "grade_fill: fail-closed on bad premise index",
        grade_fill(chain0, cand0, first_blank["frontier"], 999, False).get("graded")
        is False,
    )

    # 6. render + convenience surface
    lines = render_steps(ex0)
    check(
        "template narration: one line per step + QED",
        len(lines) == len(good) + 1 and "QED" in lines[-1],
    )
    check(
        "narration is deterministic template (AI off leaves it unchanged)",
        narrate(lines[0], None) == lines[0],
    )
    items = worked_items()
    check(
        "worked_items non-empty + all oracle-derived",
        len(items) >= 1 and all(x["steps"] for x in items),
    )
    check(
        "worked_example_for: known must-follow id available",
        worked_example_for(f"chain-{CHAIN_ITEMS.index(must_follow[0])}").get(
            "available"
        ),
    )
    check(
        "worked_example_for: fail-closed on unknown id",
        worked_example_for("chain-999").get("available") is False,
    )
    dnf_idx = CHAIN_ITEMS.index(does_not[0]) if does_not else None
    if dnf_idx is not None:
        check(
            "worked_example_for: fail-closed on does-not-follow id",
            worked_example_for(f"chain-{dnf_idx}").get("available") is False,
        )

    # 7. the served drill surface (faded_drill + grade_move), JSON-safe end-to-end
    ids = worked_example_ids()
    check("worked_example_ids: only buildable must-follow items", len(ids) >= 1)
    import json as _json

    drill = faded_drill(ids[0], fade=1)
    check(
        "faded_drill: available + has options + no leaked answer",
        drill.get("available")
        and len(drill["options"])
        == 2 * len(chain0 if ids[0] == "chain-0" else drill["premises"])
        and "answer" not in drill
        and drill["shown_steps"] is not None,
    )
    check("faded_drill: JSON-serialisable", bool(_json.dumps(drill)))
    # grade the correct move for this drill's blank (derive it from ground truth)
    gt = worked_example_for(ids[0])
    last = gt["steps"][-1]
    correct_move = (
        f"{last['impl_index']}:{'contra' if last['contrapositive'] else 'direct'}"
    )
    gm = grade_move(ids[0], correct_move)
    check(
        "grade_move: correct move graded correct + JSON-safe",
        gm.get("graded")
        and gm.get("correct")
        and "to" not in gm
        and bool(_json.dumps(gm)),
    )
    # a wrong move id (a premise that does not apply) is graded, not crashed
    gm_wrong = grade_move(
        ids[0], "0:direct" if correct_move != "0:direct" else "0:contra"
    )
    check("grade_move: alternative move graded (bool)", gm_wrong.get("graded") is True)
    check(
        "grade_move: fail-closed on malformed move id",
        grade_move(ids[0], "not-a-move").get("graded") is False,
    )
    check(
        "grade_move: fail-closed on unknown item",
        grade_move("chain-999", correct_move).get("graded") is False,
    )
    check(
        "faded_drill: fail-closed on unknown item",
        faded_drill("chain-999").get("available") is False,
    )

    # 8. ORACLE PROOF THEATER: the veto is computed LIVE, not baked. For every
    #    scenario: exactly one step is blocked, the prefix all verifies, the REAL
    #    gate blocks the recorded draft at that same index, swapping the oracle's
    #    correct move back in re-verifies (proving False came from the logic), and
    #    the appended continuation genuinely re-derives to the goal.
    scenarios = theater_scenarios()
    check("theater: exactly 3 scenarios", len(scenarios) == 3)
    check("theater: JSON-serialisable end-to-end", bool(_json.dumps(scenarios)))
    entails_did_block = 0
    for defn, sc in zip(_THEATER_DEFS, scenarios):
        cid = defn["id"]
        chain, cand = defn["chain"], defn["candidate"]
        moves = defn["moves"]
        blocked = [s for s in sc["steps"] if s["blocked"]]
        check(f"theater[{cid}]: exactly one blocked step", len(blocked) == 1)
        if not blocked:
            continue
        bidx = next(i for i, s in enumerate(sc["steps"]) if s["blocked"])
        check(
            f"theater[{cid}]: the blocked step is genuinely unverified",
            blocked[0]["verified"] is False and bool(blocked[0]["reason"]),
        )
        check(
            f"theater[{cid}]: every step before the block verified",
            all(s["verified"] for s in sc["steps"][:bidx]),
        )
        # The FULL recorded draft, run through the real oracle gate, is blocked at
        # exactly the hallucinated step -- the same decision procedure the tests use.
        draft_steps = _reconstruct_steps(
            chain,
            [
                {"premise": m["premise_index"], "contrapositive": m["contrapositive"]}
                for m in moves
            ],
        )
        gate = verify_worked_example(chain, cand, draft_steps)
        check(f"theater[{cid}]: real gate vetoes the recorded draft", not gate["verified"])
        check(
            f"theater[{cid}]: gate vetoes at the hallucinated step",
            gate["step_failed"] == bidx,
        )
        # NOT BAKED: keep the verified prefix, drop the hallucination, and let the
        # oracle finish -- the SAME gate now returns verified=True. The False was
        # produced by the logic, not stored.
        prefix = draft_steps[:bidx]
        frontier = cand.ante if not prefix else prefix[-1]["to"]
        cont = build_worked_example(chain, Implication(frontier, cand.cons))
        check(f"theater[{cid}]: oracle can prove the continuation", cont.get("available"))
        fixed = [*prefix, *cont["steps"]]
        check(
            f"theater[{cid}]: corrected derivation re-verifies through the gate",
            verify_worked_example(chain, cand, fixed)["verified"],
        )
        check(
            f"theater[{cid}]: rendered continuation matches the oracle proof",
            len(sc["corrected"]) == len(cont["steps"]) >= 1,
        )
        # Recompute the blocked move's verdict LIVE and confirm it agrees it is
        # unprovable; tally the scenarios where entails() itself did the blocking.
        m = moves[bidx]
        bimp = (
            chain[m["premise_index"]].contrapositive()
            if m["contrapositive"]
            else chain[m["premise_index"]]
        )
        starts_here = bimp.ante == frontier
        cumulative_ok = entails(chain, Implication(cand.ante, bimp.cons))
        check(
            f"theater[{cid}]: live recompute agrees the step cannot verify",
            not (starts_here and cumulative_ok),
        )
        if not cumulative_ok:
            entails_did_block += 1
    check(
        "theater: entails() itself vetoes at least one hallucination (not just structure)",
        entails_did_block >= 1,
    )

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("WORKED_OK" if ok else "WORKED_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
