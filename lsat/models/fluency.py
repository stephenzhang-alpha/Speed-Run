# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Feature 5 -- Fluency Gates (+ Structure Sprints): RT-aware mastery.

Retire a skill only when the learner is **accurate AND fast**, shown as a
passive ``Not-yet -> Effortful -> Automatic`` badge (DECISION.md section 3,
Feature 5). Automaticity is the proven **anti-choke** lever: problems practised
to automaticity show *no* choking under pressure (Beilock, Kulp, Holt & Carr
2004), and "accurate but slow" is the exact mid-160s LR plateau. This module
reads the latency the event log **already captures** (``response_ms`` on timed
``LSAT PerformanceEvent`` notes, via :func:`lsat.events.read_events`) -- no new
schema, no Rust.

Evidence discipline (from the ruling): this feature is **MODERATE evidence and
LSAT-transfer unproven**, so it ships as a *passive, measured badge*, never a
gate that hides cards and never speed-shaming. Two guards enforce that:

- **RT-gaming guard.** "Fast" alone never earns ``automatic``; a skill must
  *also* clear the accuracy gate. Clicking through quickly to look fluent stays
  ``not_yet`` because accuracy is the co-criterion.
- **Non-punitive framing.** The states read "Not yet" / "Becoming automatic" /
  "Automatic!" -- an accurate-but-slow skill is "becoming automatic" (speed is
  still building), never "too slow".

The "fast" threshold (documented choice). A raw LSAT item has no fixed length --
a wordy parallel-reasoning stem legitimately takes longer than a one-line flaw
stem -- so there is no honest absolute "N seconds = fast" constant. We therefore
derive the threshold *adaptively from the learner's own data*: it is the
**median of the per-skill median solve times**, taken over skills that clear the
evidence floor (``min_items``). A skill is "fast" when its own median solve time
is at or below that typical-skill median. This is a self-referential, relative
anchor ("automatic *for you*, relative to your other skills"), which is the
non-punitive, sparse-data-honest choice: with one single-user log we cannot fit
a trustworthy per-skill speed baseline (the same "abstain rather than overfit
one sparse user" philosophy the rest of the app follows), so v1 uses one global
adaptive threshold and reports it per node as ``fast_ms``. Below the floor a
node abstains (``available=False``, no state) rather than guessing from a
handful of answers.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from lsat.events import _MS_PER_DAY, read_events
from lsat.notetypes import LSAT_ITEM
from lsat.taxonomy import TAG_SEP, tag_to_node_id

if TYPE_CHECKING:
    from anki.collection import Collection

# Fluency states (ordered weakest -> strongest).
NOT_YET = "not_yet"
EFFORTFUL = "effortful"
AUTOMATIC = "automatic"

# Non-punitive, passive-badge framing (never "too slow" / never speed-shaming).
STATE_LABELS = {
    NOT_YET: "Not yet",
    EFFORTFUL: "Becoming automatic",
    AUTOMATIC: "Automatic!",
}

# Characters of the stem shown in a Structure-Sprint card ("name the type/flaw"
# in seconds -- the learner only needs enough to classify, not to solve).
STEM_EXCERPT_CHARS = 120

# Documented, reported alongside the number so the choice is never a black box.
FAST_MS_BASIS = (
    "fast = per-skill median response_ms at or below the median of all per-skill "
    "medians (skills with n >= min_items); a self-referential anchor because raw "
    "LSAT items have no fixed length"
)


def _recency_weight(age_ms: float, half_life_ms: float) -> float:
    """Weight of an answer that is ``age_ms`` old: halves every half-life.

    Identical curve to :func:`lsat.events.fold_recent_performance` so the
    accuracy criterion here matches the mastery the queue already uses.
    """
    return 0.5 ** (age_ms / half_life_ms)


def _aggregate_timed(
    col: Collection, now_ms: int | None, half_life_days: float
) -> dict[str, tuple[int, float, int]]:
    """Per node id, over TIMED answers that carry a real latency, return
    ``(n, recency_weighted_accuracy, median_response_ms)``.

    We read only ``phase == "timed"`` answers with ``response_ms > 0`` so the
    speed and accuracy criteria describe the *same* attempts (honest mastery:
    blind/relaxed second passes never feed the fluency badge). Accuracy is
    recency-weighted (recent answers count more); the median is over *raw*
    response times (robust to the odd very-slow outlier).
    """
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    half_life_ms = max(1.0, half_life_days * _MS_PER_DAY)

    n: dict[str, int] = defaultdict(int)
    w_correct: dict[str, float] = defaultdict(float)
    w_total: dict[str, float] = defaultdict(float)
    times: dict[str, list[int]] = defaultdict(list)

    for event in read_events(col):
        if event.phase != "timed" or event.response_ms <= 0:
            continue
        weight = _recency_weight(max(0, now - event.wall_ms), half_life_ms)
        for node_id in event.node_ids:
            n[node_id] += 1
            w_total[node_id] += weight
            if event.correct:
                w_correct[node_id] += weight
            times[node_id].append(event.response_ms)

    out: dict[str, tuple[int, float, int]] = {}
    for node_id, count in n.items():
        accuracy = (
            w_correct[node_id] / w_total[node_id] if w_total[node_id] > 0 else 0.0
        )
        median_ms = int(round(statistics.median(times[node_id])))
        out[node_id] = (count, accuracy, median_ms)
    return out


def _node_note(state: str, accuracy: float, median_ms: int, n: int) -> str:
    secs = median_ms / 1000.0
    pct = f"{accuracy * 100:.0f}%"
    if state == AUTOMATIC:
        return (
            f"Automatic! {pct} accurate at a {secs:.1f}s median over {n} timed answers."
        )
    if state == EFFORTFUL:
        return (
            f"Becoming automatic -- {pct} accurate; speed is still building "
            f"({secs:.1f}s median over {n} timed answers)."
        )
    return f"Building accuracy first -- {pct} over {n} timed answers."


def fluency_status(
    col: Collection,
    *,
    min_items: int = 8,
    accuracy_gate: float = 0.85,
    half_life_days: float = 30.0,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """RT-aware mastery per skill node, as a JSON-safe dict.

    For each node seen in the TIMED log (with a real latency) we report a
    ``state``:

    - ``automatic`` -- recency-weighted accuracy ``>= accuracy_gate`` **and**
      median ``response_ms <= fast_ms`` (accurate *and* fast: retire it),
    - ``effortful`` -- accuracy ``>= accuracy_gate`` but median ``> fast_ms``
      (accurate but slow: "becoming automatic"),
    - ``not_yet``   -- accuracy ``< accuracy_gate`` (build accuracy first; the
      accuracy co-criterion is what guards against RT-gaming).

    ``fast_ms`` is the single global adaptive threshold derived from the
    observed per-skill median distribution (see the module docstring and
    ``fast_ms_basis``). Each measured node also carries ``accuracy``,
    ``median_ms``, ``n`` and the ``fast_ms`` it was judged against. A node below
    ``min_items`` abstains: ``available=False`` and no ``state`` (we never label
    a skill from a handful of answers).
    """
    agg = _aggregate_timed(col, now_ms, half_life_days)

    # Adaptive "fast" threshold: median of the per-skill medians, over skills
    # that clear the evidence floor (thin skills never skew the anchor).
    qualifying = sorted(
        median_ms for (count, _acc, median_ms) in agg.values() if count >= min_items
    )
    fast_ms = float(statistics.median(qualifying)) if qualifying else None

    nodes: dict[str, Any] = {}
    for node_id in sorted(agg):
        count, accuracy, median_ms = agg[node_id]
        if fast_ms is None or count < min_items:
            nodes[node_id] = {
                "available": False,
                "n": count,
                "note": f"not yet measurable ({count}/{min_items} timed answers)",
            }
            continue
        if accuracy < accuracy_gate:
            state = NOT_YET
        elif median_ms <= fast_ms:
            state = AUTOMATIC
        else:
            state = EFFORTFUL
        nodes[node_id] = {
            "available": True,
            "state": state,
            "label": STATE_LABELS[state],
            "accuracy": round(accuracy, 4),
            "median_ms": median_ms,
            "n": count,
            "fast_ms": fast_ms,
            "note": _node_note(state, accuracy, median_ms, count),
        }

    measured = [nd for nd in nodes.values() if nd.get("available")]
    counts = {
        "measured": len(measured),
        "automatic": sum(1 for nd in measured if nd["state"] == AUTOMATIC),
        "effortful": sum(1 for nd in measured if nd["state"] == EFFORTFUL),
        "not_yet": sum(1 for nd in measured if nd["state"] == NOT_YET),
        "abstained": sum(1 for nd in nodes.values() if not nd.get("available")),
    }
    return {
        "available": fast_ms is not None,
        "params": {
            "min_items": min_items,
            "accuracy_gate": accuracy_gate,
            "half_life_days": half_life_days,
        },
        "fast_ms": fast_ms,
        "fast_ms_basis": FAST_MS_BASIS,
        "counts": counts,
        "nodes": nodes,
    }


def _norm_node_id(value: str) -> str:
    """Accept either a node id (``lr.weaken``) or a tag (``lsat::lr::weaken``)."""
    v = value.strip()
    return tag_to_node_id(v) if TAG_SEP in v else v


def _focus_node_ids(col: Collection, node_ids: list[str] | None) -> set[str]:
    """Skills a sprint should drill: the caller's ``node_ids`` if given, else
    the learner's **non-automatic** skills (``not_yet``/``effortful`` and any
    still-abstaining skill -- everything that has not yet been retired)."""
    if node_ids is not None:
        return {_norm_node_id(s) for s in node_ids if s and s.strip()}
    status = fluency_status(col)
    return {
        node_id
        for node_id, nd in status["nodes"].items()
        if nd.get("state") != AUTOMATIC
    }


def _stem_excerpt(stem: str, limit: int = STEM_EXCERPT_CHARS) -> str:
    text = " ".join((stem or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + "\u2026"


def sprint_items(
    col: Collection,
    *,
    n: int = 10,
    node_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Up to ``n`` ``LSAT Item`` notes for a seconds-long "name the type/flaw"
    classification sprint (Structure Sprints), as JSON-safe dicts.

    Each dict is ``{item_id, stem_excerpt, target}`` where ``target`` is the
    item's *primary* skill node id (the first entry in its ``skill_tags``) -- the
    answer the learner races to classify. Items whose skills fall in the focus
    set (see :func:`_focus_node_ids`) come first; when ``node_ids`` is omitted the
    focus is the learner's non-automatic skills, so a sprint naturally drills what
    still needs speeding up. Ordering is deterministic (focus first, then by
    item id) so the same collection always yields the same sprint.
    """
    if col.models.by_name(LSAT_ITEM) is None:
        return []
    focus = _focus_node_ids(col, node_ids)

    ranked: list[tuple[bool, int, dict[str, Any]]] = []
    for nid in col.find_notes(f'note:"{LSAT_ITEM}"'):
        note = col.get_note(nid)
        skills = note["skill_tags"].split()
        if not skills:
            continue  # no classifiable target -> not a sprint candidate
        item_id = int(nid)
        in_focus = any(skill in focus for skill in skills)
        ranked.append(
            (
                in_focus,
                item_id,
                {
                    "item_id": str(item_id),
                    "stem_excerpt": _stem_excerpt(note["stem"]),
                    "target": skills[0],
                },
            )
        )

    # Focus items first (in_focus True), then ascending item id -> deterministic.
    ranked.sort(key=lambda row: (not row[0], row[1]))
    limit = max(0, int(n))
    return [payload for _in_focus, _item_id, payload in ranked[:limit]]


# -- self-test ----------------------------------------------------------------


def _ensure_anki_on_path() -> None:
    """Make the dev ``anki`` package importable (mirrors the other models)."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for rel in ("pylib", "out/pylib", "."):
        path = os.path.join(root, rel)
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def _selftest() -> bool:
    """Build a temp collection, exercise both entry points, print PASS/FAIL."""
    _ensure_anki_on_path()

    import json
    import tempfile

    from anki.collection import Collection
    from anki.decks import DeckId
    from lsat.events import append_event
    from lsat.notetypes import ensure_notetypes

    ok = True

    def check(name: str, cond: object, extra: str = "") -> None:
        nonlocal ok
        passed = bool(cond)
        ok = ok and passed
        print(
            f"  [{'PASS' if passed else 'FAIL'}] {name}{(' -- ' + extra) if extra else ''}"
        )

    # A fixed, near-real clock so recency weights are ~1 (and constant across
    # answers, so the weighted accuracy is exactly the hit rate).
    now = int(time.time() * 1000)

    auto_skill = "lr.weaken"  # fast + accurate  -> automatic
    effort_skill = "lr.strengthen"  # accurate but slow -> effortful
    notyet_skill = "lr.assumption_necessary"  # inaccurate       -> not_yet
    thin_skill = "lr.flaw"  # below the floor  -> abstain

    col = Collection(os.path.join(tempfile.mkdtemp(), "fluency.anki2"))
    try:
        ensure_notetypes(col)

        # -- abstain path: no events yet ------------------------------------
        empty = fluency_status(col, now_ms=now)
        check(
            "empty log abstains cleanly",
            empty["available"] is False
            and empty["fast_ms"] is None
            and empty["nodes"] == {},
            str({k: empty[k] for k in ("available", "fast_ms")}),
        )
        json.dumps(empty, allow_nan=False)  # must not raise

        # -- seed timed answers ---------------------------------------------
        # 12 answers each (>= min_items). Same timestamp => recency cancels, so
        # weighted accuracy == hit rate; median == the (constant) response time.
        for i in range(12):
            append_event(
                col,
                item_id=f"a{i}",
                skill_tags=[auto_skill],
                correct=(i > 0),
                response_ms=1500,
                phase="timed",
                now_ms=now,
            )
            append_event(
                col,
                item_id=f"e{i}",
                skill_tags=[effort_skill],
                correct=(i > 0),
                response_ms=15000,
                phase="timed",
                now_ms=now,
            )
            append_event(
                col,
                item_id=f"n{i}",
                skill_tags=[notyet_skill],
                correct=(i < 4),
                response_ms=3000,
                phase="timed",
                now_ms=now,
            )
        # 3 timed answers -> below min_items=8 -> abstain
        for i in range(3):
            append_event(
                col,
                item_id=f"t{i}",
                skill_tags=[thin_skill],
                correct=True,
                response_ms=1200,
                phase="timed",
                now_ms=now,
            )

        status = fluency_status(col, now_ms=now)
        nodes = status["nodes"]
        fast_ms = status["fast_ms"]

        check("overall available", status["available"] is True)
        check(
            "fast_ms derived from the median distribution",
            isinstance(fast_ms, float) and fast_ms > 0,
            f"fast_ms={fast_ms}",
        )
        check(
            "fast + accurate -> automatic",
            nodes[auto_skill]["state"] == AUTOMATIC,
            str(nodes.get(auto_skill)),
        )
        check(
            "accurate + slow -> effortful",
            nodes[effort_skill]["state"] == EFFORTFUL,
            str(nodes.get(effort_skill)),
        )
        check(
            "inaccurate -> not_yet",
            nodes[notyet_skill]["state"] == NOT_YET,
            str(nodes.get(notyet_skill)),
        )
        check(
            "below-floor skill abstains (state omitted)",
            nodes[thin_skill]["available"] is False
            and "state" not in nodes[thin_skill],
            str(nodes.get(thin_skill)),
        )

        check(
            "automatic node reports accuracy/median/n/fast_ms",
            {"accuracy", "median_ms", "n", "fast_ms"} <= set(nodes[auto_skill])
            and nodes[auto_skill]["n"] == 12,
        )
        check(
            "automatic really is accurate AND fast",
            nodes[auto_skill]["accuracy"] >= 0.85
            and nodes[auto_skill]["median_ms"] <= fast_ms,
        )
        check(
            "effortful is accurate but slow",
            nodes[effort_skill]["accuracy"] >= 0.85
            and nodes[effort_skill]["median_ms"] > fast_ms,
        )

        # RT-gaming guard: the not_yet skill is actually *fast* (median <= fast_ms)
        # yet stays not_yet because accuracy is the co-criterion.
        check(
            "RT-gaming guarded: fast-but-inaccurate is NOT automatic",
            nodes[notyet_skill]["median_ms"] <= fast_ms
            and nodes[notyet_skill]["state"] == NOT_YET,
            f"median={nodes[notyet_skill]['median_ms']} <= fast_ms={fast_ms}",
        )

        # Non-punitive framing (never "too slow" / speed-shaming).
        check(
            "non-punitive labels",
            nodes[auto_skill]["label"] == "Automatic!"
            and nodes[effort_skill]["label"] == "Becoming automatic"
            and "slow" not in nodes[effort_skill]["note"].lower(),
        )

        # counts summary is consistent
        check(
            "counts summary consistent",
            status["counts"]["automatic"] == 1
            and status["counts"]["effortful"] == 1
            and status["counts"]["not_yet"] == 1
            and status["counts"]["abstained"] == 1,
            str(status["counts"]),
        )

        # -- blind/relaxed answers must NOT affect the badge ----------------
        before = dict(nodes[auto_skill])
        for i in range(10):  # slow, wrong -- would wreck the badge IF counted
            append_event(
                col,
                item_id=f"a{i}",
                skill_tags=[auto_skill],
                correct=False,
                response_ms=60000,
                phase="blind",
                now_ms=now,
            )
            append_event(
                col,
                item_id=f"a{i}",
                skill_tags=[auto_skill],
                correct=False,
                response_ms=60000,
                phase="relaxed",
                now_ms=now,
            )
        after = fluency_status(col, now_ms=now)["nodes"][auto_skill]
        check(
            "blind/relaxed answers excluded (timed-only)",
            after == before,
            f"{before} != {after}",
        )

        # -- JSON-safe -------------------------------------------------------
        try:
            json.dumps(fluency_status(col, now_ms=now), allow_nan=False)
            check("fluency_status is JSON-safe (allow_nan=False)", True)
        except (TypeError, ValueError) as exc:
            check("fluency_status is JSON-safe (allow_nan=False)", False, str(exc))

        # -- sprint_items ----------------------------------------------------
        item_notetype = col.models.by_name(LSAT_ITEM)
        assert item_notetype is not None
        practice = DeckId(col.decks.add_normal_deck_with_name("LSAT::Practice").id)

        def add_item(stem: str, skills: list[str]) -> int:
            note = col.new_note(item_notetype)
            note["stem"] = stem
            note["choices"] = "(A) alpha\n(B) beta\n(C) gamma"
            note["correct"] = "A"
            note["skill_tags"] = " ".join(skills)
            col.add_note(note, practice)
            return int(note.id)

        long_stem = (
            "Which one of the following, if true, most weakens the argument? " * 6
        )
        id_effort = add_item(long_stem, [effort_skill, "flaw.causal"])
        id_notyet = add_item("Classify the flaw in this short stem.", [notyet_skill])
        id_auto = add_item("A quick, already-automatic skill item stem.", [auto_skill])

        sprints = sprint_items(col, n=10)
        check(
            "sprint_items returns a list of dicts",
            isinstance(sprints, list)
            and all(isinstance(d, dict) for d in sprints)
            and len(sprints) == 3,
            f"n={len(sprints)}",
        )
        check(
            "sprint dicts are well-formed",
            all({"item_id", "stem_excerpt", "target"} <= set(d) for d in sprints),
        )
        check(
            "every sprint has a non-empty target",
            all(bool(d["target"]) for d in sprints),
        )
        check(
            "stem excerpt is non-empty and bounded",
            all(0 < len(d["stem_excerpt"]) <= STEM_EXCERPT_CHARS + 1 for d in sprints),
        )

        pos = {d["item_id"]: i for i, d in enumerate(sprints)}
        check(
            "non-automatic skills preferred over automatic",
            pos[str(id_effort)] < pos[str(id_auto)]
            and pos[str(id_notyet)] < pos[str(id_auto)],
            str(pos),
        )
        check(
            "ordering is deterministic",
            [d["item_id"] for d in sprint_items(col, n=10)]
            == [d["item_id"] for d in sprints],
        )

        forced = sprint_items(col, n=1, node_ids=["lsat::lr::weaken"])
        check(
            "explicit node_ids (tags accepted) selects that skill first",
            len(forced) == 1 and forced[0]["item_id"] == str(id_auto),
            str(forced),
        )

        json.dumps(sprints, allow_nan=False)  # must not raise
    finally:
        col.close()

    print("FLUENCY_OK" if ok else "FLUENCY_FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
