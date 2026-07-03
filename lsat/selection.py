# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""ZPD Daily Engine: re-rank the points-at-stake queue toward the ~85% band.

Feature 1 of the design ruling (``research/debate/DECISION.md`` section 3). The
points-at-stake queue (``lsat/events.py::points_at_stake`` ->
``col.sched.points_at_stake_queue``) already picks the right *topics* -- the
weakest, highest-exam-weight ones -- but then surfaces the *hardest* due card in
that topic, which is the opposite of where humans actually learn fastest.

The region-of-proximal-learning result (Metcalfe & Kornell 2005: people learn
fastest on the *easiest-not-yet-mastered* item, and spend their most profitable
time at medium difficulty) and the "85% rule" (Wilson, Shenhav, Straccia &
Cohen 2019: training accuracy near ~85% is exponentially faster than fixed
difficulty) say: among the cards the queue surfaces, prefer the one whose
predicted P(correct) sits in a band around ``tau ~= 0.85`` -- not the hardest.

This module is a thin, pure-Python re-rank over the entries the RPC already
returns (zero Rust). It scores each entry::

    score(entry) = entry.points * zpd_weight(P_hat(entry.top_tag))

where :func:`zpd_weight` is a smooth bump peaking at ``tau`` and never falling
below a ``floor`` (a band around ``tau`` is favored while rare stretch/reach
items are damped but never fully starved). ``P_hat`` comes from the Rasch-style
``PerformanceModel`` (``lsat/models/performance.py``). When that model is thin
or unavailable the selector ABSTAINS: every entry gets a neutral weight, so the
result degrades cleanly to the queue's original points ordering (we never
impute a missing prediction -- see the keystone ruling, DECISION section 2).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, NamedTuple, Protocol, TypeVar

from lsat.events import points_at_stake
from lsat.models.performance import fit_performance_model
from lsat.taxonomy import Taxonomy, tag_to_node_id

if TYPE_CHECKING:
    from anki.collection import Collection
    from anki.scheduler.base import PointsAtStakeEntry

DEFAULT_TAU = 0.85  # the ~85% learning target (tunable, not a law)
DEFAULT_WIDTH = 0.18  # bump half-width in probability space
DEFAULT_FLOOR = 0.05  # min weight, so nothing due is fully starved
NEUTRAL_P = 0.5  # "unknown difficulty" -> a neutral mid weight on abstain
MIN_TOPIC_EVENTS = 1  # graded events a topic needs before we trust its P_hat
# Exam-day consolidation (DECISION-round2 #7): a card projected fully below its
# exam-day retention target (gap ~1) gets up to ~1.5x its queue score.
EXAM_CONSOLIDATION_BOOST = 0.5
_EPS = 1e-9


class _Entry(Protocol):
    """Structural type for a re-rankable entry (only ``points`` is read)."""

    @property
    def points(self) -> float: ...


E = TypeVar("E", bound=_Entry)


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def zpd_weight(
    p: float,
    tau: float = DEFAULT_TAU,
    width: float = DEFAULT_WIDTH,
    floor: float = DEFAULT_FLOOR,
) -> float:
    """A smooth "learn-fastest" bump: 1.0 at ``tau``, decaying either side, >= floor.

    ``p`` is a predicted P(correct); it is clamped to ``[0, 1]``. The bump is a
    Gaussian in probability space centered at ``tau`` with scale ``width``, so a
    band around ``tau`` is favored and the weight never drops below ``floor``
    (rare too-easy / too-hard items are damped, not eliminated). The result lies
    in ``[floor, 1.0]``. Callers must handle a ``None`` prediction themselves.
    """
    p = _clamp01(p)
    w = width if width > _EPS else _EPS
    bump = math.exp(-((p - tau) ** 2) / (2.0 * w * w))
    return floor + (1.0 - floor) * bump


def rerank(
    entries: Iterable[E],
    predict: Callable[[E], float | None],
    *,
    tau: float = DEFAULT_TAU,
    floor: float = DEFAULT_FLOOR,
    boost: Callable[[E], float] | None = None,
) -> list[E]:
    """Return ``entries`` sorted DESC by ``points * zpd_weight(predict(entry)) *
    boost(entry)``.

    Pure and stable: no I/O, the input is not mutated, and entries that compare
    equal keep their original order. ``predict`` maps an entry to a predicted
    P(correct) or ``None`` to abstain; an abstaining entry gets a neutral weight
    (``zpd_weight`` at a mid ``p``), so a queue whose predictions are all
    ``None`` degrades to plain points ordering. ``boost`` is an optional
    multiplicative factor (default 1.0 for every entry) used to fold in the
    exam-day consolidation priority; it never reorders when it returns 1.0.
    """
    neutral = zpd_weight(NEUTRAL_P, tau=tau, floor=floor)

    def _score(entry: E) -> float:
        p = predict(entry)
        weight = neutral if p is None else zpd_weight(p, tau=tau, floor=floor)
        b = boost(entry) if boost is not None else 1.0
        return float(entry.points) * weight * b

    # Python's sorted() is stable and keeps stability under reverse=True, so
    # equal-score entries retain their incoming (points-first) order.
    return sorted(entries, key=_score, reverse=True)


def select_zpd(
    col: Collection,
    *,
    deck_id: int = 0,
    limit: int = 0,
    tau: float = DEFAULT_TAU,
    taxonomy: Taxonomy | None = None,
) -> list[PointsAtStakeEntry]:
    """Points-at-stake queue re-ranked toward the ZPD (~``tau``) band.

    Runs the queue for *all* due entries, fits the performance model once, then
    re-ranks by ``points * zpd_weight(P_hat(top_tag))``. ``P_hat`` is the
    model's P(correct) for the entry's ``top_tag`` topic; it abstains
    (``None`` -> neutral weight) when the model is unavailable or the topic has
    too little graded evidence, so the result degrades gracefully to the queue's
    own points ordering. Truncates to ``limit`` when ``limit > 0``.
    """
    entries = list(points_at_stake(col, deck_id=deck_id, limit=0, taxonomy=taxonomy))
    model = fit_performance_model(col, taxonomy)

    # Exam-day consolidation boost (DECISION-round2 #7): when an exam date is set,
    # nudge cards that would decay below their exam-day retention target up the
    # queue, by the consolidation gap. Empty (a no-op) with no exam date or thin
    # FSRS state, so the daily engine is unchanged until a date is set.
    exam_gap = _exam_consolidation_gap(col, taxonomy)

    def boost(entry: PointsAtStakeEntry) -> float:
        return 1.0 + EXAM_CONSOLIDATION_BOOST * exam_gap.get(int(entry.card_id), 0.0)

    # Hard abstain on the ZPD term: with no fitted model there is nothing to
    # re-rank by -- but the exam-day boost still applies if a date is set.
    if not model.available:
        if not exam_gap:
            return entries[:limit] if limit > 0 else entries
        ranked = rerank(
            entries, lambda _e: None, tau=tau, floor=DEFAULT_FLOOR, boost=boost
        )
        return ranked[:limit] if limit > 0 else ranked

    def predict(entry: PointsAtStakeEntry) -> float | None:
        node_id = tag_to_node_id(entry.top_tag or "")
        if not node_id:
            return None
        counts = model.counts.get(node_id)
        # Soft abstain: never impute a prediction for a topic we have not seen.
        if not counts or counts[0] < MIN_TOPIC_EVENTS:
            return None
        try:
            return float(model.predict(node_id))
        except Exception:
            return None

    ranked = rerank(entries, predict, tau=tau, floor=DEFAULT_FLOOR, boost=boost)
    return ranked[:limit] if limit > 0 else ranked


def _exam_consolidation_gap(
    col: Collection, taxonomy: Taxonomy | None
) -> dict[int, float]:
    """``card_id -> exam-day consolidation gap`` when an exam date is set, else {}.

    Best-effort: any failure (or no date / thin FSRS state) yields an empty map,
    so the queue degrades cleanly to its ZPD ordering."""
    try:
        from lsat.exam_schedule import build_consolidation_queue, get_exam_date

        if get_exam_date(col) is None:
            return {}
        q = build_consolidation_queue(col, taxonomy=taxonomy)
        if not q.get("available"):
            return {}
        return {int(c["card_id"]): float(c["gap"]) for c in q["queue"]}
    except Exception:
        return {}


# -- self-test ----------------------------------------------------------------


class _ToyEntry(NamedTuple):
    """A minimal stand-in for ``PointsAtStakeEntry`` used by the self-test."""

    card_id: int
    points: float
    top_tag: str


def _report(name: str, checks: list[tuple[str, bool]]) -> bool:
    for label, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {label}")
    return all(passed for _, passed in checks)


def _check_zpd_weight() -> bool:
    tau, floor = DEFAULT_TAU, DEFAULT_FLOOR
    grid = [i / 20.0 for i in range(21)]  # 0.00, 0.05, ..., 1.00

    def w(p: float) -> float:
        return zpd_weight(p, tau=tau, floor=floor)

    checks = [
        ("peaks (=1.0) at tau", abs(w(tau) - 1.0) < 1e-9),
        ("<= 1.0 across [0, 1]", all(w(p) <= 1.0 + 1e-12 for p in grid)),
        (">= floor across [0, 1]", all(w(p) >= floor - 1e-12 for p in grid)),
        ("symmetric-ish about tau", abs(w(tau - 0.1) - w(tau + 0.1)) < 1e-9),
        ("decays below tau", w(0.85) > w(0.60) > w(0.30)),
        ("decays above tau", w(0.85) > w(0.92) > w(0.99)),
        ("tau-band beats 0.99 and 0.15", w(0.85) > w(0.99) > w(0.15)),
        ("clamps p < 0 to 0", abs(w(-0.7) - w(0.0)) < 1e-12),
        ("clamps p > 1 to 1", abs(w(1.7) - w(1.0)) < 1e-12),
    ]
    return _report("zpd_weight", checks)


def _check_rerank() -> bool:
    tau, floor = DEFAULT_TAU, DEFAULT_FLOOR
    sweet = _ToyEntry(1, 1.0, "lsat::lr::weaken")  # p ~= tau
    easy = _ToyEntry(2, 1.0, "lsat::lr::strengthen")  # p = 0.99 (too easy)
    hard = _ToyEntry(3, 1.0, "lsat::lr::flaw")  # p = 0.15 (too hard)
    pmap = {1: 0.85, 2: 0.99, 3: 0.15}

    def predict(e: _ToyEntry) -> float | None:
        return pmap.get(e.card_id)

    scrambled = [hard, easy, sweet]
    ranked_order = [e.card_id for e in rerank(scrambled, predict, tau=tau, floor=floor)]

    varied = [_ToyEntry(10, 0.2, "t"), _ToyEntry(11, 0.9, "t"), _ToyEntry(12, 0.5, "t")]
    none_order = [
        e.card_id for e in rerank(varied, lambda e: None, tau=tau, floor=floor)
    ]

    tied = [_ToyEntry(20, 0.5, "t"), _ToyEntry(21, 0.5, "t")]
    tied_order = [e.card_id for e in rerank(tied, lambda e: None, tau=tau, floor=floor)]

    checks = [
        ("~tau outranks 0.15 and 0.99 at equal points", ranked_order == [1, 2, 3]),
        ("None predict -> plain points DESC order", none_order == [11, 12, 10]),
        ("stable on equal score (input order kept)", tied_order == [20, 21]),
        ("pure: input list not mutated", [e.card_id for e in scrambled] == [3, 2, 1]),
    ]
    return _report("rerank", checks)


def _check_select_zpd() -> bool:
    try:
        from anki.collection import Collection
    except Exception as exc:  # anki not built in this env -> skip, don't fail
        print(f"  [SKIP] select_zpd: anki unavailable ({exc})")
        return True

    import os
    import tempfile

    from lsat.events import append_event
    from lsat.notetypes import LSAT_ITEM
    from lsat.seed import seed_deck

    path = os.path.join(tempfile.mkdtemp(prefix="lsat-selection-"), "c.anki2")
    col = Collection(path)
    try:
        seed_deck(col)
        # Seeded LSAT Item cards are New; flip them to due Review so the queue
        # actually surfaces them (mirrors the Rust test harness / lsat.bench).
        card_ids = [
            cid
            for nid in col.find_notes(f'note:"{LSAT_ITEM}"')
            for cid in col.get_note(nid).card_ids()
        ]
        if card_ids:
            ids = ",".join(str(c) for c in card_ids)
            col.db.execute(
                f"update cards set type = 2, queue = 2, due = 0 where id in ({ids})"
            )

        base = [e.card_id for e in points_at_stake(col)]

        # (1) no events yet -> model unavailable -> abstain to plain points order.
        pre = select_zpd(col)
        abstain_ok = isinstance(pre, list) and [e.card_id for e in pre] == base

        # A small, deterministic accuracy spread so the model becomes available.
        pattern = [
            ("lr.weaken", True),
            ("lr.weaken", True),
            ("lr.weaken", True),
            ("lr.strengthen", False),
            ("lr.strengthen", False),
            ("lr.flaw", True),
            ("lr.flaw", False),
        ]
        for i, (node, correct) in enumerate(pattern):
            append_event(
                col,
                item_id=f"sel-{i}",
                skill_tags=[node],
                correct=correct,
                response_ms=45_000,
            )

        # (2) model available -> re-ranked, without raising, same due-card set.
        post = select_zpd(col, tau=DEFAULT_TAU)
        limited = select_zpd(col, limit=2)
        checks = [
            ("abstains to points order with no events", abstain_ok),
            ("runs and returns a list", isinstance(post, list)),
            (
                "preserves the due-card set",
                sorted(e.card_id for e in post) == sorted(base),
            ),
            ("respects limit", isinstance(limited, list) and len(limited) <= 2),
            (
                "entries expose card_id/points/top_tag",
                all(
                    hasattr(e, "card_id")
                    and hasattr(e, "points")
                    and hasattr(e, "top_tag")
                    for e in post
                ),
            ),
        ]
        print(f"  [INFO] select_zpd ranked {len(post)} due card(s)")
        return _report("select_zpd", checks)
    except Exception as exc:
        print(f"  [FAIL] select_zpd: raised {exc!r}")
        return False
    finally:
        col.close()


def _selftest() -> bool:
    ok = all([_check_zpd_weight(), _check_rerank(), _check_select_zpd()])
    print("SELECTION_OK" if ok else "SELECTION_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
