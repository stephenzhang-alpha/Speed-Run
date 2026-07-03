# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Framework-agnostic LSAT API handlers (the mobile/back-end contract).

These functions take an open ``Collection`` plus plain arguments and return
plain JSON-safe dicts -- no Flask, no ``aqt``, no request/response objects. Both
front-ends call them so there is exactly one implementation:

- the desktop mediasrv endpoints (``qt/aqt/lsat_web.py``, using ``aqt.mw.col``),
- the standalone hosted server (``lsat/server/app.py``, opening a collection via
  pylib directly).

A mobile answer therefore produces the identical append-only ``PerformanceEvent``
a desktop answer would (all grading flows through :mod:`lsat.grading`).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anki.collection import Collection

# The endpoints the mobile PWA calls (client.ts). Kept here so the desktop
# (mediasrv) and the standalone server register exactly the same set -- the server
# enforces set(ENDPOINTS) <= set(_HANDLERS) at import.
ENDPOINTS = (
    "lsatDashboardData",
    "lsatNextItem",
    "lsatSubmitAnswer",
    "lsatSubmitTrap",
    "lsatSubmitClassify",
    "lsatConditionalDrill",
    "lsatSubmitConditional",
    "lsatQuantifierValidityDrill",
    "lsatSubmitQuantifierValidity",
    "lsatQuantifierNegationDrill",
    "lsatSubmitQuantifierNegation",
    "lsatStemPolarityDrill",
    "lsatSubmitStemPolarity",
    "lsatAssumptionDrill",
    "lsatSubmitAssumption",
    "lsatSectionItems",
    "lsatSubmitSectionAttempt",
    "lsatChainDrill",
    "lsatSubmitChain",
    "lsatWorkedExampleDrill",
    "lsatSubmitWorkedStep",
    "lsatOracleTheater",
    "lsatEvilTwinDrill",
    "lsatSubmitEvilTwin",
)

CONDITIONAL_DRILL_INDEX_KEY = "lsat:cond_drill_idx"
CHAIN_DRILL_INDEX_KEY = "lsat:chain_drill_idx"
QUANTIFIER_VAL_INDEX_KEY = "lsat:qval_drill_idx"
QUANTIFIER_NEG_INDEX_KEY = "lsat:qneg_drill_idx"
STEM_POLARITY_INDEX_KEY = "lsat:stem_polarity_idx"
ASSUMPTION_INDEX_KEY = "lsat:assumption_drill_idx"
WORKED_DRILL_INDEX_KEY = "lsat:worked_example_idx"
EVIL_TWIN_INDEX_KEY = "lsat:evil_twin_idx"


def pick_item_card(col: Collection) -> Any:
    """The next LSAT Item card to study: ZPD-ordered due items first, else any
    Item (so the client always has something to practice)."""
    from anki.cards import CardId
    from lsat.notetypes import LSAT_ITEM

    try:
        from lsat.selection import select_zpd

        for entry in select_zpd(col, limit=50):
            card = col.get_card(CardId(int(entry.card_id)))
            nt = card.note().note_type()
            if nt and nt["name"] == LSAT_ITEM:
                return card
    except Exception:
        pass
    ids = col.find_cards(f'note:"{LSAT_ITEM}"')
    return col.get_card(ids[0]) if ids else None


def section_items(col: Collection, *, n: int = 10) -> dict[str, Any]:
    """Up to ``n`` DISTINCT LSAT items for a timed section (stem + choices; NEVER
    the correct letter). ``next_item`` returns only the single top ZPD card and
    does not advance until an answer is logged, so a section (which must not submit
    answers mid-run -- no leak) needs this batch fetch. ZPD-ordered, then topped up
    with any remaining items; deduped by item id."""
    from anki.cards import CardId
    from lsat.grading import parse_choices
    from lsat.notetypes import LSAT_ITEM

    n = max(1, min(int(n or 10), 50))
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    def _add(card: Any) -> None:
        note = card.note()
        nt = note.note_type()
        if not nt or nt["name"] != LSAT_ITEM:
            return
        iid = str(note.id)
        if iid in seen:
            return
        seen.add(iid)
        items.append(
            {
                "item_id": iid,
                "stem": note["stem"],
                "choices": parse_choices(note["choices"] or ""),
                "skill_tags": (note["skill_tags"] or "").split(),
            }
        )

    try:
        from lsat.selection import select_zpd

        for entry in select_zpd(col, limit=max(50, n * 3)):
            if len(items) >= n:
                break
            try:
                _add(col.get_card(CardId(int(entry.card_id))))
            except Exception:
                continue
    except Exception:
        pass

    if len(items) < n:
        for cid in col.find_cards(f'note:"{LSAT_ITEM}"'):
            if len(items) >= n:
                break
            try:
                _add(col.get_card(cid))
            except Exception:
                continue

    return {"items": items, "n": len(items)}


def _item_note(col: Collection, item_id: Any) -> Any:
    from anki.notes import NoteId
    from lsat.notetypes import LSAT_ITEM

    note = col.get_note(NoteId(int(item_id)))
    nt = note.note_type()
    if nt is None or nt["name"] != LSAT_ITEM:
        raise ValueError("not an LSAT item")
    return note


# -- endpoint handlers -------------------------------------------------------


def dashboard(col: Collection) -> dict[str, Any]:
    """The full dashboard payload (scores + insights + coverage)."""
    from lsat.dashboard_data import build

    return build(col)


def next_item(col: Collection) -> dict[str, Any]:
    """The next item to study (stem + choices; never the correct letter)."""
    from lsat.grading import parse_choices

    card = pick_item_card(col)
    if card is None:
        return {"done": True, "item_id": "", "stem": "", "choices": []}
    note = card.note()
    return {
        "item_id": str(note.id),
        "stem": note["stem"],
        "choices": parse_choices(note["choices"] or ""),
        "skill_tags": (note["skill_tags"] or "").split(),
        "done": False,
    }


def submit_answer(
    col: Collection,
    *,
    item_id: Any,
    chosen: str = "",
    confidence: str | None = None,
    response_ms: int = 0,
    phase: str = "timed",
    identified: str = "",
) -> dict[str, Any]:
    """Grade a chosen answer, append the graded event, report the result."""
    from lsat.grading import grade_answer

    note = _item_note(col, item_id)
    ident = identified if identified in ("0", "1") else ""
    return grade_answer(
        col,
        note,
        chosen=str(chosen or ""),
        confidence=(confidence or None),
        response_ms=int(response_ms or 0),
        phase=str(phase or "timed"),
        identified=ident,
    )


def submit_trap(
    col: Collection, *, item_id: Any, chosen: str = "", family: str = ""
) -> dict[str, Any]:
    """Grade a "which trap is (X)?" tap against the item's authoritative labels."""
    from lsat.grading import grade_trap

    note = _item_note(col, item_id)
    return grade_trap(note, chosen=str(chosen or ""), family=str(family or ""))


def submit_classify(
    col: Collection, *, item_id: Any, named: str = ""
) -> dict[str, Any]:
    """Grade the identification-first stage (name the question type)."""
    from lsat.grading import grade_classify

    note = _item_note(col, item_id)
    return grade_classify(note, named=str(named or ""))


def _tap_drills() -> list[tuple[str, str, str, str]]:
    """Curated drills whose sufficient AND necessary terms are BOTH non-negated,
    so "which clause is the sufficient condition?" is a clean, exactly-gradeable
    tap (negated forms like 'unless'/'no' are still TAUGHT via the post-answer
    reveal, just not served as taps). Returns (item_id, sentence, suff, nec)."""
    from lsat.conditional import DRILL_SENTENCES, parse_conditional

    out: list[tuple[str, str, str, str]] = []
    for i, s in enumerate(DRILL_SENTENCES):
        p = parse_conditional(s)
        if (
            p.get("available")
            and "not (" not in p["sufficient"]
            and "not (" not in p["necessary"]
        ):
            out.append((f"cond-{i}", s, p["sufficient"], p["necessary"]))
    return out


def conditional_drill(col: Collection) -> dict[str, Any]:
    """The next Conditional Translation Drill (DECISION-round2 #19): a conditional
    sentence + its two clauses (shuffled) for the learner to tap which is the
    sufficient condition. Cycles deterministically through the tap-friendly set;
    never reveals which clause is sufficient (graded by :func:`submit_conditional`)."""
    tap = _tap_drills()
    if not tap:
        return {"done": True, "item_id": "", "sentence": "", "options": []}
    n = len(tap)
    # Store a raw counter with period 2n: `k = c % n` selects the item and
    # `cycle = c // n` (0/1) flips the option order each time an item reappears,
    # so a repeat learner can't memorize the answer's slot (it isn't fixed per
    # sentence). Grading is order-independent, so this only affects presentation.
    c = int(col.get_config(CONDITIONAL_DRILL_INDEX_KEY, 0) or 0) % (2 * n)
    k = c % n
    cycle = c // n
    col.set_config(CONDITIONAL_DRILL_INDEX_KEY, (c + 1) % (2 * n))
    item_id, sentence, suff, nec = tap[k]
    first_suff = (cycle + k) % 2 == 0
    options = [suff, nec] if first_suff else [nec, suff]
    return {"item_id": item_id, "sentence": sentence, "options": options, "done": False}


def submit_conditional(
    col: Collection,
    *,
    item_id: Any,
    sufficient: str = "",
    necessary: str = "",
    response_ms: int = 0,
) -> dict[str, Any]:
    """Grade a conditional-translation attempt and log a graded event tagged
    ``skill.conditional_logic`` (so the drill feeds mastery/fluency/the queue).
    Returns the deterministic grade + the worked arrow/contrapositive; on an
    unparseable sentence it abstains (``graded: False``) and logs nothing."""
    from lsat.conditional import DRILL_SENTENCES, grade_conditional
    from lsat.events import append_event

    try:
        idx = int(str(item_id).split("-", 1)[1])
        sentence = DRILL_SENTENCES[idx]
    except (ValueError, IndexError):
        return {"graded": False, "reason": "unknown drill item"}

    result = grade_conditional(
        sentence, sufficient=str(sufficient or ""), necessary=str(necessary or "")
    )
    if result.get("graded"):
        append_event(
            col,
            item_id=str(item_id),
            skill_tags=["skill.conditional_logic"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


# -- conditional-chain drill (DECISION-round4 #22) ---------------------------


def chain_drill(col: Collection) -> dict[str, Any]:
    """The next Conditional-Chain Drill: a 3+ arrow chain + a candidate inference
    for the learner to judge must-follow / does-not-follow. Cycles deterministically;
    withholds the verdict + note until submit (no leak). The two options are fixed
    labels."""
    from lsat.conditional_chain import VERDICTS, drill_items

    items = drill_items()
    if not items:
        return {
            "done": True,
            "item_id": "",
            "premises": [],
            "candidate": "",
            "options": [],
        }
    n = len(items)
    k = int(col.get_config(CHAIN_DRILL_INDEX_KEY, 0) or 0) % n
    col.set_config(CHAIN_DRILL_INDEX_KEY, (k + 1) % n)
    it = items[k]
    return {
        "item_id": it["item_id"],
        "premises": it["premises"],
        "candidate": it["candidate"],
        "options": list(VERDICTS),
        "done": False,
    }


def submit_chain(
    col: Collection, *, item_id: Any, chosen: str = "", response_ms: int = 0
) -> dict[str, Any]:
    """Grade a chain must-follow/does-not-follow judgment (deterministic + fail-closed)
    and log a ``skill.conditional_logic`` event so the drill feeds mastery/fluency."""
    from lsat.conditional_chain import grade_chain
    from lsat.events import append_event

    result = grade_chain(str(item_id), str(chosen or ""))
    if result.get("graded"):
        append_event(
            col,
            item_id=str(item_id),
            skill_tags=["skill.conditional_logic"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


# -- oracle-verified faded worked examples (research feature #1) --------------


def worked_example_drill(col: Collection) -> dict[str, Any]:
    """The next Oracle-Verified Faded Worked Example: the first proven steps of a
    conditional-chain derivation are shown and the final step is blanked for the
    learner to complete (backward fading). Every step is derived + checked by the
    exact material-entailment oracle, so a hallucinated step can never be served.
    Cycles deterministically; withholds the correct move + note until submit (no
    leak). AI-off by construction (the deterministic derivation is the default)."""
    from lsat.worked_example import faded_drill, worked_example_ids

    ids = worked_example_ids()
    if not ids:
        return {"done": True, "item_id": "", "premises": [], "goal": "", "options": []}
    n = len(ids)
    k = int(col.get_config(WORKED_DRILL_INDEX_KEY, 0) or 0) % n
    col.set_config(WORKED_DRILL_INDEX_KEY, (k + 1) % n)
    drill = faded_drill(ids[k], fade=1)
    if not drill.get("available"):
        return {"done": True, "item_id": "", "premises": [], "goal": "", "options": []}
    drill["done"] = False
    return drill


def submit_worked_step(
    col: Collection, *, item_id: Any, move_id: str = "", response_ms: int = 0
) -> dict[str, Any]:
    """Oracle-grade the learner's chosen move to complete a faded worked example
    (deterministic + fail-closed) and log a ``skill.conditional_logic`` event so
    the drill feeds mastery/fluency like the other logic drills."""
    from lsat.events import append_event
    from lsat.worked_example import grade_move

    result = grade_move(str(item_id), str(move_id or ""))
    if result.get("graded"):
        append_event(
            col,
            item_id=str(item_id),
            skill_tags=["skill.conditional_logic"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


# -- Oracle Proof Theater (marquee AI demo; read-only, no col mutation) --------


def oracle_theater(col: Collection) -> dict[str, Any]:
    """The Oracle Proof Theater payload: curated scenarios whose recorded AI draft
    is checked LIVE, step by step, by the material-entailment oracle (the same one
    the tests exercise) -- one planted hallucination is blocked and the oracle's
    provable continuation is substituted. Read-only. ``mode`` reflects whether a
    real model key is present (``live``) or the draft is a replayed recording
    (``recorded``); the VERDICTS are computed live either way."""
    from lsat.worked_example import theater_scenarios

    return {
        "scenarios": theater_scenarios(),
        "mode": "live" if os.environ.get("ANTHROPIC_API_KEY") else "recorded",
    }


# -- oracle-proven "skill or luck?" discrimination twins (research follow-on) --


def evil_twin_drill(col: Collection) -> dict[str, Any]:
    """The next "Skill or Luck?" evil twin: a minimally-edited variant of a
    formal-logic item whose correct answer FLIPS. Every candidate twin is proven by
    a decision procedure (``quantifier.classify`` / ``conditional_chain.entails``);
    an LLM, when present, only selects which proven twin + picks logically-inert
    surface nouns. Cycles deterministically; the correct verdict + edit note are
    withheld until submit (no leak). AI-off by construction here."""
    from lsat.evil_twin import evil_twin_drill as build_twin
    from lsat.evil_twin import twin_source_ids

    ids = twin_source_ids()
    if not ids:
        return {
            "done": True,
            "item_id": "",
            "premises": [],
            "conclusion": "",
            "options": [],
        }
    n = len(ids)
    k = int(col.get_config(EVIL_TWIN_INDEX_KEY, 0) or 0) % n
    col.set_config(EVIL_TWIN_INDEX_KEY, (k + 1) % n)
    drill = build_twin(ids[k])
    if not drill.get("available"):
        return {
            "done": True,
            "item_id": "",
            "premises": [],
            "conclusion": "",
            "options": [],
        }
    drill["done"] = False
    return drill


def submit_evil_twin(
    col: Collection, *, twin_key: Any, chosen: str = "", response_ms: int = 0
) -> dict[str, Any]:
    """Oracle-grade a verdict on an evil twin (the answer is re-derived by the
    decision procedure every time -- stateless + fail-closed) and log a
    ``skill.conditional_logic`` event so the drill feeds mastery/fluency."""
    from lsat.events import append_event
    from lsat.evil_twin import grade_twin

    result = grade_twin(str(twin_key), str(chosen or ""))
    if result.get("graded"):
        append_event(
            col,
            item_id=str(twin_key),
            skill_tags=["skill.conditional_logic"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


# -- quantifier reasoning drills (DECISION-round3 #1) ------------------------


def quantifier_validity_drill(col: Collection) -> dict[str, Any]:
    """The next Quantifier Validity Drill: premises + a candidate conclusion for
    the learner to judge must-be-true / cannot-be-true / could-be-either. Cycles
    deterministically; never reveals the verdict (graded by
    :func:`submit_quantifier_validity`)."""
    from lsat.quantifier import validity_drill_items

    items = validity_drill_items()
    if not items:
        return {"done": True, "item_id": "", "premises": [], "conclusion": ""}
    n = len(items)
    k = int(col.get_config(QUANTIFIER_VAL_INDEX_KEY, 0) or 0) % n
    col.set_config(QUANTIFIER_VAL_INDEX_KEY, (k + 1) % n)
    it = items[k]
    # Verdict + teaching note are withheld until submit (no leak).
    return {
        "item_id": it["item_id"],
        "premises": it["premises"],
        "conclusion": it["conclusion"],
        "done": False,
    }


def submit_quantifier_validity(
    col: Collection, *, item_id: Any, chosen: str = "", response_ms: int = 0
) -> dict[str, Any]:
    """Grade a validity judgment (deterministic + fail-closed) and log a
    ``skill.quantifier_logic`` event so the drill feeds mastery/fluency/the queue."""
    from lsat.events import append_event
    from lsat.quantifier import grade_validity

    result = grade_validity(str(item_id), str(chosen or ""))
    if result.get("graded"):
        append_event(
            col,
            item_id=str(item_id),
            skill_tags=["skill.quantifier_logic"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


def quantifier_negation_drill(col: Collection) -> dict[str, Any]:
    """The next Quantifier Negation Drill: a statement + shuffled candidate
    negations (the classic traps: 'no' for ¬all, 'most-not' for ¬most). Cycles
    deterministically and rotates option order so the answer's slot isn't fixed;
    never reveals the answer (graded by :func:`submit_quantifier_negation`)."""
    from lsat.quantifier import negation_drill_items

    items = negation_drill_items()
    if not items:
        return {"done": True, "item_id": "", "sentence": "", "options": []}
    n = len(items)
    # period 4*n: k=c%n selects the item, rot=c//n rotates the 4 options, so a
    # repeat learner can't memorize the answer's position. Grading is by quant key.
    c = int(col.get_config(QUANTIFIER_NEG_INDEX_KEY, 0) or 0) % (4 * n)
    k = c % n
    rot = c // n
    col.set_config(QUANTIFIER_NEG_INDEX_KEY, (c + 1) % (4 * n))
    it = items[k]
    opts = it["options"]
    r = rot % len(opts)
    rotated = opts[r:] + opts[:r]
    # send only {quant, text} -- the `answer` key is never included.
    options = [{"quant": o["quant"], "text": o["text"]} for o in rotated]
    return {
        "item_id": it["item_id"],
        "sentence": it["sentence"],
        "options": options,
        "done": False,
    }


def submit_quantifier_negation(
    col: Collection, *, item_id: Any, chosen: str = "", response_ms: int = 0
) -> dict[str, Any]:
    """Grade a negation choice (the chosen quantifier form) deterministically and
    fail-closed; log a ``skill.quantifier_logic`` event on a graded attempt."""
    from lsat.events import append_event
    from lsat.quantifier import grade_negation

    result = grade_negation(str(item_id), str(chosen or ""))
    if result.get("graded"):
        append_event(
            col,
            item_id=str(item_id),
            skill_tags=["skill.quantifier_logic"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


# -- stem-polarity micro-drill (DECISION-round4 #13) -------------------------


def stem_polarity_drill(col: Collection) -> dict[str, Any]:
    """The next Stem-Polarity Micro-Drill: a question stem for the learner to tap
    as direct / EXCEPT / LEAST / negated. Cycles deterministically through the
    curated stems; withholds the polarity + instruction until submit (no leak).
    The four polarity options are fixed semantic labels (the learner maps
    stem->task-set, not a position), so no shuffling is needed."""
    from lsat.stem_polarity import DRILL_STEMS, POLARITIES

    if not DRILL_STEMS:
        return {"done": True, "item_id": "", "stem": "", "options": []}
    n = len(DRILL_STEMS)
    k = int(col.get_config(STEM_POLARITY_INDEX_KEY, 0) or 0) % n
    col.set_config(STEM_POLARITY_INDEX_KEY, (k + 1) % n)
    stem, _polarity = DRILL_STEMS[k]
    return {
        "item_id": f"stem-{k}",
        "stem": stem,
        "options": list(POLARITIES),
        "done": False,
    }


def submit_stem_polarity(
    col: Collection, *, item_id: Any, chosen: str = "", response_ms: int = 0
) -> dict[str, Any]:
    """Grade a stem-polarity call (deterministic + fail-closed) and log a
    ``diction.except`` event so the drill feeds mastery/fluency/the queue."""
    from lsat.events import append_event
    from lsat.stem_polarity import DRILL_STEMS, grade_stem_polarity

    try:
        idx = int(str(item_id).split("-", 1)[1])
        if not 0 <= idx < len(DRILL_STEMS):
            raise IndexError
        stem = DRILL_STEMS[idx][0]
    except (ValueError, IndexError):
        return {"graded": False, "reason": "unknown stem-polarity item"}

    result = grade_stem_polarity(stem, str(chosen or ""))
    if result.get("graded"):
        append_event(
            col,
            item_id=str(item_id),
            skill_tags=["diction.except"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


# -- necessary/sufficient discrimination drill (DECISION-round4 #5) ----------


def assumption_drill(col: Collection) -> dict[str, Any]:
    """The next Necessary/Sufficient Discrimination Drill: an argument (premises +
    conclusion) + a candidate assumption for the learner to sort into
    necessary-only / sufficient-only / both / neither. Cycles deterministically;
    withholds the derived cell + note until submit (no leak). The four cell options
    are fixed semantic labels (the learner maps argument->cell, not a position)."""
    from lsat.assumption_discrimination import CELLS, drill_items

    items = drill_items()
    if not items:
        return {
            "done": True,
            "item_id": "",
            "premises": [],
            "conclusion": "",
            "candidate": "",
            "options": [],
        }
    n = len(items)
    k = int(col.get_config(ASSUMPTION_INDEX_KEY, 0) or 0) % n
    col.set_config(ASSUMPTION_INDEX_KEY, (k + 1) % n)
    it = items[k]
    return {
        "item_id": it["item_id"],
        "premises": it["premises"],
        "conclusion": it["conclusion"],
        "candidate": it["candidate"],
        "options": list(CELLS),
        "done": False,
    }


def submit_assumption(
    col: Collection, *, item_id: Any, chosen: str = "", response_ms: int = 0
) -> dict[str, Any]:
    """Grade a four-cell assumption sort (deterministic + fail-closed, cells derived
    by the proven quantifier model-checker) and log a graded event tagged with both
    assumption node ids so it feeds mastery/fluency/the queue."""
    from lsat.assumption_discrimination import DRILL_ITEMS, grade_assumption
    from lsat.events import append_event

    try:
        idx = int(str(item_id).split("-", 1)[1])
        if not 0 <= idx < len(DRILL_ITEMS):
            raise IndexError
        it = DRILL_ITEMS[idx]
    except (ValueError, IndexError):
        return {"graded": False, "reason": "unknown assumption item"}

    result = grade_assumption(
        it["premises"], it["conclusion"], it["candidate"], str(chosen or "")
    )
    if result.get("graded"):
        result["note"] = it["note"]  # the teaching explanation, revealed post-answer
        append_event(
            col,
            item_id=str(item_id),
            skill_tags=["lr.assumption_necessary", "lr.assumption_sufficient"],
            correct=bool(result.get("correct")),
            response_ms=int(response_ms or 0),
            phase="timed",
        )
    return result


# -- timed section runner (DECISION-round4 #17) ------------------------------


def _safe_int(x: Any, default: int = 0) -> int:
    """Coerce to int, never raising -- keeps submit_section_attempt fail-closed on a
    crafted non-numeric field (e.g. dwell_ms: 'abc' / [1] / '3.5')."""
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def _item_correct_letter(col: Collection, item_id: Any) -> str | None:
    """The correct answer letter for an LSAT Item, or None if not gradeable. Used
    to grade a section attempt SERVER-side so first/final correctness is never sent
    to the client mid-section (a timed section must stay blind until submit)."""
    from anki.notes import NoteId
    from lsat.notetypes import LSAT_ITEM

    try:
        note = col.get_note(NoteId(int(item_id)))
        nt = note.note_type()
        if nt is None or nt["name"] != LSAT_ITEM:
            return None
        return (note["correct"] or "").strip().upper() or None
    except Exception:
        return None  # missing note / absent field / bad id -> not gradeable


def submit_section_attempt(
    col: Collection, *, trajectory: Any = None
) -> dict[str, Any]:
    """Persist a completed timed-section attempt and return the refreshed
    First-Instinct Ledger. The client sends raw first/final CHOICES per question
    (never correctness -- a timed section stays blind until submit); this grades
    them server-side against each item's answer, enriches the trajectory with
    first/final correctness, persists it append-only, and recomputes the ledger.
    Fail-closed on a non-list / empty payload."""
    from lsat.answer_change import compute_answer_change
    from lsat.section_runner import record_section_attempt

    if not isinstance(trajectory, list) or not trajectory:
        return {"ok": False, "reason": "trajectory must be a non-empty list"}

    enriched: list[dict[str, Any]] = []
    for q in trajectory:
        if not isinstance(q, dict):
            continue
        first = str(q.get("first_choice", "") or "").strip().upper()
        final = str(q.get("final_choice", "") or "").strip().upper()
        rec: dict[str, Any] = {
            "item_id": str(q.get("item_id", "")),
            "reached": bool(q.get("reached", True)) and bool(final),
            "changed": bool(first) and bool(final) and first != final,
            "flagged": bool(q.get("flagged")),
            "dwell_ms": _safe_int(q.get("dwell_ms")),
        }
        correct = _item_correct_letter(col, q.get("item_id"))
        if correct is not None:  # gradeable -> attach correctness (server-side)
            rec["first_correct"] = bool(first) and first == correct
            rec["final_correct"] = bool(final) and final == correct
        enriched.append(rec)

    if not enriched:
        return {"ok": False, "reason": "trajectory has no valid question records"}
    record_section_attempt(col, trajectory=enriched)
    ledger = compute_answer_change(col)
    return {"ok": True, "n_questions": len(enriched), "ledger": ledger}
