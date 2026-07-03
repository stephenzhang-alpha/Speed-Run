# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Distractor-Reasoning trap fingerprint (DECISION.md section 3, Feature 2).

The event log now stores, per graded answer, the *letter* the student picked
(``chosen``) alongside ``correct`` (see ``lsat/events.py``). The ``LSAT Item``
notetype stores a ``distractor_traps`` map -- e.g.
``"B=extreme_language A=out_of_scope D=reversal"`` -- labelling each
wrong-answer letter with the engineered trap family it exploits (the
``skill.trap.*`` leaves in ``lsat/taxonomy.py``).

When a student *misses* an item, the trap family of the letter they actually
chose is the diagnosis, not noise (Sadler 1998). Folding those attributions
across items -- recency-weighted, exactly like ``fold_recent_performance`` --
yields a personal **trap fingerprint** ("extreme-language owns 38% of your
Strengthen misses") plus a per-``skill.trap.*`` **boost** the points-at-stake
queue can consume to drill the traps this student actually falls for.

This module is the read-only *analysis* layer only: the AI
``distractor_rejection`` card generation and the reviewer "which trap?" tap are
wired by the caller. Every output here is JSON-safe; every surfaced pattern
names the **fixable habit**, never the person, and **abstains** below an
evidence floor (DECISION.md section 5.v).
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lsat.events import DEFAULT_HALF_LIFE_DAYS, read_events
from lsat.taxonomy import (
    TRAP_FAMILIES,
    TRAP_FAMILY_LABELS,
    Taxonomy,
    load_taxonomy,
    trap_family_to_node_id,
)

if TYPE_CHECKING:
    from anki.collection import Collection

_MS_PER_DAY = 86_400_000.0

# Short, non-punitive "fixable habit" tips per trap family. The headline frames
# the habit to target, never a verdict on the person (DECISION.md section 5.v).
_FAMILY_TIPS = {
    "out_of_scope": "check each choice stays within the argument's scope",
    "extreme_language": "slow down on absolute words like all / never / only",
    "reversal": "confirm the conditional or causal direction before committing",
    "half_right": "reject choices that are only partly supported",
    "irrelevant_comparison": "make sure any compared groups are actually relevant",
}


# -- parse --------------------------------------------------------------------


def parse_distractor_traps(spec: str) -> dict[str, str]:
    """Parse a ``distractor_traps`` field into ``{letter: trap_family}``.

    Accepts space- or comma-separated ``LETTER=family`` pairs, e.g.
    ``"B=extreme_language A=out_of_scope, D=reversal"``. Letters are upper-cased;
    families are lower-cased and validated against :data:`TRAP_FAMILIES`.
    Malformed pairs (no ``=``, a multi-character or non-alphabetic letter, an
    unknown family) are ignored rather than raising, so a hand-edited or only
    partially-labelled field never breaks the fold. A later pair for the same
    letter wins.
    """
    out: dict[str, str] = {}
    for token in re.split(r"[\s,]+", (spec or "").strip()):
        letter, sep, family = token.partition("=")
        if not sep:
            continue
        letter = letter.strip().upper()
        family = family.strip().lower()
        if len(letter) != 1 or not letter.isalpha():
            continue
        if family not in TRAP_FAMILIES:
            continue
        out[letter] = family
    return out


# -- fold ---------------------------------------------------------------------


@dataclass
class _TrapFold:
    """Recency-weighted aggregates over attributed MISS events."""

    family_weight: dict[str, float] = field(default_factory=dict)
    family_count: dict[str, int] = field(default_factory=dict)
    # question-type node id -> trap family -> recency-weighted miss weight
    type_family_weight: dict[str, dict[str, float]] = field(default_factory=dict)
    type_count: dict[str, int] = field(default_factory=dict)
    n_attributed: int = 0
    total_weight: float = 0.0


def _fold_trap_misses(
    col: Collection,
    *,
    half_life_days: float,
    now_ms: int | None,
    taxonomy: Taxonomy | None = None,
) -> _TrapFold:
    """Fold MISS events by the trap family of the chosen letter.

    Only events with ``correct == False`` and a non-empty ``chosen`` letter that
    maps -- via the item's ``distractor_traps`` field -- to a known trap family
    are attributed; every other event is skipped (a correct answer, an unrated
    ``chosen``, a legacy/absent item, or a chosen letter with no trap label).
    An answer's weight halves every ``half_life_days`` (identical to
    ``fold_recent_performance``), so recent misses dominate the fingerprint.
    """
    from anki.errors import NotFoundError
    from anki.notes import NoteId

    tax = taxonomy or load_taxonomy()
    qt_ids = {t.id for t in tax.question_types}

    now = now_ms if now_ms is not None else int(time.time() * 1000)
    half_life_ms = max(1.0, half_life_days * _MS_PER_DAY)

    fold = _TrapFold()
    traps_cache: dict[str, dict[str, str]] = {}
    for event in read_events(col):
        # Timed answers only: the trap fingerprint is about the traps you fall for
        # under exam conditions, and this prevents an item's error being counted
        # twice when it is re-attempted in an untimed blind pass (matches the
        # honest-mastery convention in fold_recent_performance).
        if event.phase != "timed":
            continue
        if event.correct:
            continue
        chosen = (event.chosen or "").strip().upper()
        if not chosen:
            continue
        # Resolve (and cache) the item's distractor_traps map. Guard a missing
        # note, a non-numeric item_id, or a legacy item lacking the field.
        if event.item_id not in traps_cache:
            try:
                note = col.get_note(NoteId(int(event.item_id)))
                spec = note["distractor_traps"]
            except (KeyError, ValueError, NotFoundError):
                spec = ""
            traps_cache[event.item_id] = parse_distractor_traps(spec)
        family = traps_cache[event.item_id].get(chosen)
        if family is None:
            continue

        age_ms = max(0, now - event.wall_ms)
        weight = 0.5 ** (age_ms / half_life_ms)

        fold.n_attributed += 1
        fold.total_weight += weight
        fold.family_weight[family] = fold.family_weight.get(family, 0.0) + weight
        fold.family_count[family] = fold.family_count.get(family, 0) + 1
        for nid in event.node_ids:
            if nid not in qt_ids:
                continue
            per_family = fold.type_family_weight.setdefault(nid, {})
            per_family[family] = per_family.get(family, 0.0) + weight
            fold.type_count[nid] = fold.type_count.get(nid, 0) + 1
    return fold


def _dominant(weights: dict[str, float]) -> tuple[str, float]:
    """The family with the greatest weight; ties break on family name (stable)."""
    return max(weights.items(), key=lambda kv: (kv[1], kv[0]))


def _headline(
    fold: _TrapFold,
    by_family: dict[str, dict[str, float]],
    by_type_family: dict[str, dict[str, object]],
) -> str | None:
    """One non-punitive, fixable-habit sentence naming the top family + where it
    bites, or ``None`` when there is nothing attributed."""
    if not fold.family_weight:
        return None
    top_fam, _ = _dominant(fold.family_weight)
    label = TRAP_FAMILY_LABELS.get(top_fam, top_fam)
    tip = _FAMILY_TIPS.get(top_fam, "review why that choice is built to attract you")

    # "Where it bites" = the question type in which the top family owns the
    # largest within-type share of misses (tie-break by weight, then node id).
    best_type: str | None = None
    best_key = (-1.0, -1.0, "")
    for nid, per_family in fold.type_family_weight.items():
        w = per_family.get(top_fam, 0.0)
        if w <= 0.0:
            continue
        share = w / (sum(per_family.values()) or 1.0)
        key = (share, w, nid)
        if key > best_key:
            best_key, best_type = key, nid

    if best_type is not None and best_type in by_type_family:
        pct = best_key[0] * 100
        where = by_type_family[best_type]["name"]
        return (
            f"{label} owns {pct:.0f}% of your {where} misses -- a fixable habit: {tip}."
        )
    pct = by_family[top_fam]["share"] * 100
    return (
        f"{label} owns {pct:.0f}% of your attributed misses -- a fixable habit: {tip}."
    )


# -- public API ---------------------------------------------------------------


def trap_fingerprint(
    col: Collection,
    *,
    min_misses: int = 3,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
) -> dict:
    """A JSON-safe personal trap fingerprint folded from the graded-event log.

    Returns a dict with a consistent shape:

    - ``available`` (bool) -- ``False`` (with a ``reason``) below ``min_misses``
      attributed misses; the app abstains rather than name a pattern from too
      little evidence (DECISION.md section 5.v).
    - ``n_attributed_misses`` (int) -- MISS events whose chosen letter mapped to
      a trap family.
    - ``by_family`` -- ``{family: {misses, weight, share}}``, recency-weighted
      over attributed misses (``share`` sums to ~1 across families).
    - ``by_type_family`` -- keyed by question-type node id (each value carries
      the ``tag`` and display ``name``): the dominant trap family + its
      within-type ``share`` for that question type.
    - ``headline`` -- a single non-punitive, fixable-habit sentence naming the
      top family and where it bites (or ``None``).
    """
    tax = load_taxonomy()
    fold = _fold_trap_misses(
        col, half_life_days=half_life_days, now_ms=now_ms, taxonomy=tax
    )
    n = fold.n_attributed
    if n < min_misses:
        return {
            "available": False,
            "reason": (
                f"only {n} attributed miss(es); need >= {min_misses} "
                "before naming a trap pattern"
            ),
            "n_attributed_misses": n,
            "by_family": {},
            "by_type_family": {},
            "headline": None,
        }

    total = fold.total_weight or 1.0
    by_family: dict[str, dict[str, float]] = {
        fam: {
            "misses": fold.family_count[fam],
            "weight": round(w, 6),
            "share": round(w / total, 6),
        }
        for fam, w in fold.family_weight.items()
    }

    qt_by_id = {t.id: t for t in tax.question_types}
    by_type_family: dict[str, dict[str, object]] = {}
    for nid, per_family in fold.type_family_weight.items():
        topic = qt_by_id.get(nid)
        if topic is None:
            continue
        type_total = sum(per_family.values()) or 1.0
        top_fam, top_w = _dominant(per_family)
        by_type_family[nid] = {
            "name": topic.name,
            "tag": topic.tag,
            "family": top_fam,
            "family_label": TRAP_FAMILY_LABELS.get(top_fam, top_fam),
            "share": round(top_w / type_total, 6),
            "misses": fold.type_count.get(nid, 0),
        }

    return {
        "available": True,
        "reason": None,
        "n_attributed_misses": n,
        "by_family": by_family,
        "by_type_family": by_type_family,
        "headline": _headline(fold, by_family, by_type_family),
    }


def trap_boost(
    col: Collection,
    *,
    cap: float = 0.5,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
) -> dict[str, float]:
    """Per-``skill.trap.*`` node boost in ``[0, cap]``, for the queue weighting.

    Each trap family's boost is proportional to its recency-weighted share of
    attributed misses (``cap * share``), keyed by ``trap_family_to_node_id`` so
    the points-at-stake queue can lift the traps this student actually falls
    for. Returns ``{}`` when there is nothing attributed (or ``cap <= 0``).
    """
    cap = max(0.0, cap)
    fold = _fold_trap_misses(col, half_life_days=half_life_days, now_ms=now_ms)
    total = fold.total_weight
    if total <= 0.0 or cap == 0.0:
        return {}
    boosts: dict[str, float] = {}
    for family, w in fold.family_weight.items():
        boost = min(cap, max(0.0, cap * (w / total)))
        boosts[trap_family_to_node_id(family)] = round(boost, 6)
    return boosts


# -- self-test ----------------------------------------------------------------


def _ensure_anki_on_path() -> None:
    """Make the dev ``anki`` package importable (mirrors ``lsat/seed.py``)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("pylib", "out/pylib"):
        path = os.path.join(root, rel)
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def _selftest() -> bool:
    """Build a temp collection, exercise every path, print per-check PASS/FAIL."""
    import json
    import tempfile

    _ensure_anki_on_path()
    from anki.collection import Collection
    from anki.decks import DeckId
    from lsat.events import append_event
    from lsat.notetypes import LSAT_ITEM, ensure_notetypes, migrate_item_fields

    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # -- pure parser checks (no collection needed) ---------------------------
    check(
        "parse: valid pairs, letters upper-cased",
        parse_distractor_traps("B=extreme_language a=out_of_scope, D=reversal")
        == {"B": "extreme_language", "A": "out_of_scope", "D": "reversal"},
    )
    check(
        "parse: drops malformed pairs + unknown families",
        parse_distractor_traps("X junk B=not_a_family C= =reversal E=half_right")
        == {"E": "half_right"},
    )
    check("parse: empty spec -> {}", parse_distractor_traps("") == {})

    path = os.path.join(tempfile.mkdtemp(prefix="trap-"), "collection.anki2")
    col = Collection(path)
    try:
        ensure_notetypes(col)
        migrate_item_fields(col)
        deck_id = DeckId(col.decks.add_normal_deck_with_name("Trap::Items").id)
        base = 1_700_000_000_000  # fixed wall clock -> stable recency weights

        def add_item(correct: str, traps: str, skills: list[str]) -> int:
            notetype = col.models.by_name(LSAT_ITEM)
            assert notetype is not None
            note = col.new_note(notetype)
            note["stem"] = "stem"
            note["choices"] = "(A) a\n(B) b\n(C) c\n(D) d\n(E) e"
            note["correct"] = correct
            note["skill_tags"] = " ".join(skills)
            note["difficulty"] = "medium"
            note["distractor_traps"] = traps
            col.add_note(note, deck_id)
            return int(note.id)

        item_strength = add_item(
            "C",
            "A=extreme_language B=extreme_language D=out_of_scope E=reversal",
            ["lr.strengthen", "flaw.causal"],
        )
        item_weaken = add_item(
            "B",
            "A=extreme_language C=half_right D=out_of_scope E=reversal",
            ["lr.weaken", "flaw.causal"],
        )
        item_infer = add_item("A", "B=out_of_scope", ["lr.inference_must_be_true"])
        item_bare = add_item("A", "", ["lr.strengthen"])

        check(
            "abstains before any misses",
            trap_fingerprint(col, min_misses=3, now_ms=base)["available"] is False,
        )

        def miss(item_id: int, chosen: str, skills: list[str]) -> None:
            append_event(
                col,
                item_id=item_id,
                skill_tags=skills,
                correct=False,
                response_ms=30_000,
                chosen=chosen,
                now_ms=base,
            )

        def hit(item_id: int, chosen: str, skills: list[str]) -> None:
            append_event(
                col,
                item_id=item_id,
                skill_tags=skills,
                correct=True,
                response_ms=30_000,
                chosen=chosen,
                now_ms=base,
            )

        # extreme_language dominates: 5 attributed vs out_of_scope 2, half_right 1.
        strengthen = ["lr.strengthen", "flaw.causal"]
        weaken = ["lr.weaken", "flaw.causal"]
        infer = ["lr.inference_must_be_true"]
        for _ in range(3):
            miss(item_strength, "A", strengthen)  # extreme_language
        miss(item_strength, "D", strengthen)  # out_of_scope
        for _ in range(2):
            miss(item_weaken, "A", weaken)  # extreme_language
        miss(item_weaken, "C", weaken)  # half_right
        miss(item_infer, "B", infer)  # out_of_scope
        # Events that must NOT be attributed:
        hit(item_strength, "C", strengthen)  # a correct answer
        miss(item_infer, "C", infer)  # chosen letter has no trap label
        miss(item_bare, "D", ["lr.strengthen"])  # item has no distractor_traps map
        miss(item_strength, "", strengthen)  # unrated chosen letter

        fp = trap_fingerprint(col, min_misses=3, now_ms=base)
        check("becomes available past the floor", fp["available"] is True)
        check("counts only attributed misses (8)", fp["n_attributed_misses"] == 8)

        fam = fp["by_family"]
        check(
            "extreme_language recorded with 5 misses",
            fam.get("extreme_language", {}).get("misses") == 5,
        )
        dominant = max(fam.items(), key=lambda kv: kv[1]["weight"])[0]
        check("extreme_language is the dominant family", dominant == "extreme_language")
        check(
            "dominant family has the largest share",
            all(fam["extreme_language"]["share"] >= v["share"] for v in fam.values()),
        )

        headline = fp["headline"]
        check("headline names the top family", bool(headline) and "Extreme" in headline)
        check("headline names where it bites (Strengthen)", "Strengthen" in headline)
        check("headline is non-punitive", "bad at" not in headline.lower())

        btf = fp["by_type_family"]
        check(
            "by_type_family: Strengthen dominated by extreme_language",
            btf.get("lr.strengthen", {}).get("family") == "extreme_language",
        )
        check(
            "by_type_family: Inference dominated by out_of_scope",
            btf.get("lr.inference_must_be_true", {}).get("family") == "out_of_scope",
        )
        check(
            "by_type_family excludes non-question-type skills", "flaw.causal" not in btf
        )

        check(
            "abstains below a higher floor",
            trap_fingerprint(col, min_misses=9, now_ms=base)["available"] is False,
        )

        boost = trap_boost(col, cap=0.5, now_ms=base)
        ext_node = trap_family_to_node_id("extreme_language")
        check(
            "boost keys are skill.trap.* nodes",
            bool(boost) and all(k.startswith("skill.trap.") for k in boost),
        )
        check(
            "boost values within [0, cap]", all(0.0 <= v <= 0.5 for v in boost.values())
        )
        check(
            "extreme_language node boosted highest",
            bool(boost) and max(boost, key=lambda k: boost[k]) == ext_node,
        )

        try:
            json.dumps(trap_fingerprint(col, now_ms=base), allow_nan=False)
            json.dumps(trap_boost(col, now_ms=base), allow_nan=False)
            json_ok = True
        except (TypeError, ValueError):
            json_ok = False
        check("trap_fingerprint / trap_boost are JSON-safe", json_ok)
    finally:
        col.close()

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("TRAP_OK" if ok else "TRAP_FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
