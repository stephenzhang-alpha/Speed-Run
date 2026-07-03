# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Memory model: per-topic memory % from FSRS recall, with a range + give-up rule.

Memory (PRD section 5.1) is the probability the student can reproduce a taught
judgment *right now*. We do NOT reinvent memory estimation: we read Anki's FSRS
retrievability per card (via the engine's ``extract_fsrs_retrievability`` SQL
function) and aggregate it per taxonomy topic.

- memory %  = mean FSRS recall over the topic's reviewed cards.
- range     = a Wilson score interval, which widens honestly when few cards
              inform the estimate (a documented approximation).
- give-up   = a topic with fewer than ``min_reviews_per_topic_for_display``
              reviews shows no score ("not enough evidence yet").

The aggregation (:func:`summarize_topic`, :func:`wilson_interval`) is pure and
unit-testable without a collection; :func:`compute_memory` wires it to Anki.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import TYPE_CHECKING

from lsat.taxonomy import TAG_SEP, Taxonomy, load_taxonomy

if TYPE_CHECKING:
    from anki.collection import Collection

# z for a 95% interval.
Z_95 = 1.96

KIND_QUESTION_TYPE = "question_type"
KIND_CROSS_CUTTING = "cross_cutting"


def wilson_interval(p: float, n: int, z: float = Z_95) -> tuple[float, float]:
    """95% Wilson score interval for a proportion ``p`` estimated from ``n`` samples.

    Bounded to [0, 1] and never collapses to zero width for small ``n``, so it
    communicates honest uncertainty when a topic has little data. ``n == 0``
    returns the whole [0, 1] range. The returned interval always contains ``p``.
    """
    # Recall is a proportion in [0, 1]; clamp so an out-of-range p cannot make
    # sqrt(p * (1 - p)) a math-domain error.
    p = min(1.0, max(0.0, p))
    if n <= 0:
        return (0.0, 1.0)
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (z * sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    # Bound to [0, 1] and guarantee the interval contains the point estimate:
    # float rounding can otherwise push center +/- margin just past p at the
    # boundaries (e.g. high < p when p == 1.0).
    low = max(0.0, min(p, center - margin))
    high = min(1.0, max(p, center + margin))
    return (low, high)


@dataclass(frozen=True)
class TopicMemory:
    node_id: str
    name: str
    tag: str
    kind: str
    n_cards: int  # cards with an FSRS recall available
    n_reviews: int  # revlog rows across the topic's cards
    memory: float | None  # mean recall (0..1); None when abstaining
    low: float | None
    high: float | None
    enough_evidence: bool
    note: str


@dataclass(frozen=True)
class MemoryReport:
    min_reviews_for_display: int
    topics: list[TopicMemory]

    @property
    def displayed(self) -> list[TopicMemory]:
        return [t for t in self.topics if t.enough_evidence]

    @property
    def abstained(self) -> list[TopicMemory]:
        return [t for t in self.topics if not t.enough_evidence]


def summarize_topic(
    node_id: str,
    name: str,
    tag: str,
    kind: str,
    recalls: list[float],
    n_reviews: int,
    min_reviews: int,
) -> TopicMemory:
    """Aggregate per-card recalls into a topic memory score (pure; no DB)."""
    n_cards = len(recalls)
    if n_reviews < min_reviews:
        return TopicMemory(
            node_id,
            name,
            tag,
            kind,
            n_cards,
            n_reviews,
            None,
            None,
            None,
            False,
            f"not enough evidence yet ({n_reviews}/{min_reviews} reviews)",
        )
    if n_cards == 0:
        # passed the review gate but no card carries FSRS state (e.g. SM2 cards)
        return TopicMemory(
            node_id,
            name,
            tag,
            kind,
            0,
            n_reviews,
            None,
            None,
            None,
            False,
            "no FSRS memory state on the topic's cards yet",
        )
    mean = sum(recalls) / n_cards
    low, high = wilson_interval(mean, n_cards)
    return TopicMemory(
        node_id,
        name,
        tag,
        kind,
        n_cards,
        n_reviews,
        mean,
        low,
        high,
        True,
        f"memory {mean * 100:.0f}% ({low * 100:.0f}-{high * 100:.0f}%) from {n_cards} cards",
    )


def _tag_ancestors(tag: str) -> list[str]:
    """Every tag that Anki's ``tag:X`` search would match for a card tagged
    ``tag`` -- i.e. ``tag`` itself and each hierarchical ancestor. A card tagged
    ``lsat::flaw::causal::sampling`` matches nodes ``lsat::flaw::causal``,
    ``lsat::flaw`` and ``lsat`` (Anki matches ``tag:X`` to ``X`` and ``X::*``)."""
    parts = tag.split(TAG_SEP)
    out: list[str] = []
    acc = ""
    for i, part in enumerate(parts):
        acc = part if i == 0 else f"{acc}{TAG_SEP}{part}"
        out.append(acc)
    return out


def compute_memory(
    col: Collection,
    taxonomy: Taxonomy | None = None,
    include_cross_cutting: bool = True,
) -> MemoryReport:
    """Compute the per-topic memory report for a collection.

    One joined scan over the LSAT-tagged cards (returning each card's tags *and*
    its FSRS retrievability together) buckets recall per taxonomy node in Python,
    instead of running one ``find_cards(tag:X)`` search per node. On the 50k-card
    benchmark that is the difference between ~490 ms (36 per-node tag scans) and a
    single scan -- the dominant cost in the PRD section 13 dashboard budget.
    """
    from anki.utils import ids2str, int_time

    tax = taxonomy or load_taxonomy()
    min_reviews = tax.give_up.memory_min_reviews_per_topic_for_display
    timing = col._backend.sched_timing_today()
    days_elapsed = timing.days_elapsed
    next_day_at = timing.next_day_at
    now = int_time()

    nodes: list[tuple[str, str, str, str]] = [
        (t.id, t.name, t.tag, KIND_QUESTION_TYPE) for t in tax.question_types
    ]
    if include_cross_cutting:
        nodes += [(c.id, c.name, c.tag, KIND_CROSS_CUTTING) for c in tax.cross_cutting]

    node_tags = {tag for _, _, tag, _ in nodes}
    root = nodes[0][2].split(TAG_SEP)[0] if nodes else "lsat"

    # Single joined scan: (card id, note tags, FSRS retrievability) for every card
    # whose note carries an LSAT tag. The ``like`` is only a pre-filter; exact
    # membership is decided per-tag below, replicating Anki's hierarchical match.
    recall_by_cid: dict[int, float] = {}
    node_cards: dict[str, list[int]] = {tag: [] for tag in node_tags}
    for cid, tags, recall in col.db.all(
        "select c.id, n.tags, extract_fsrs_retrievability("
        "c.data, case when c.odue != 0 then c.odue else c.due end, c.ivl, ?, ?, ?) "
        "from cards c, notes n where c.nid = n.id and n.tags like ?",
        days_elapsed,
        next_day_at,
        now,
        f"%{root}{TAG_SEP}%",
    ):
        matched: set[str] = set()
        for token in tags.split():
            for anc in _tag_ancestors(token.lower()):
                if anc in node_tags:
                    matched.add(anc)
        if not matched:
            continue
        # FSRS retrievability is a probability: clamp to [0, 1] (corrupted or
        # imported cards can carry out-of-spec stability that yields recall > 1
        # or non-finite values) so the memory % never exceeds its own range.
        if recall is not None and isfinite(recall):
            recall_by_cid[cid] = min(1.0, max(0.0, recall))
        for tag in matched:
            node_cards[tag].append(cid)

    # Revlog rows per card, in one grouped query over the LSAT-tagged cards.
    all_cids = sorted({cid for cids in node_cards.values() for cid in cids})
    reviews_by_cid: dict[int, int] = {}
    if all_cids:
        id_list = ids2str(all_cids)
        for cid, cnt in col.db.all(
            f"select cid, count() from revlog where cid in {id_list} group by cid"
        ):
            reviews_by_cid[cid] = cnt

    topics: list[TopicMemory] = []
    for node_id, name, tag, kind in nodes:
        cids = node_cards.get(tag, [])
        recalls = [recall_by_cid[c] for c in cids if c in recall_by_cid]
        n_reviews = sum(reviews_by_cid.get(c, 0) for c in cids)
        topics.append(
            summarize_topic(node_id, name, tag, kind, recalls, n_reviews, min_reviews)
        )
    return MemoryReport(min_reviews_for_display=min_reviews, topics=topics)


def _ensure_anki_on_path() -> None:
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for rel in ("pylib", "out/pylib"):
        path = os.path.join(root, rel)
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Print the per-topic memory model.")
    parser.add_argument(
        "--collection", required=True, help="path to a .anki2 collection"
    )
    args = parser.parse_args(argv)

    _ensure_anki_on_path()
    from anki.collection import Collection

    col = Collection(args.collection)
    try:
        report = compute_memory(col)
    finally:
        col.close()

    print(f"Memory model (give-up: >= {report.min_reviews_for_display} reviews/topic)")
    print(f"  displayed: {len(report.displayed)}   abstained: {len(report.abstained)}")
    for t in report.displayed:
        assert t.memory is not None and t.low is not None and t.high is not None
        print(
            f"  [{t.kind[:2]}] {t.node_id:28} {t.memory * 100:5.1f}%  "
            f"({t.low * 100:.0f}-{t.high * 100:.0f}%)  cards={t.n_cards} reviews={t.n_reviews}"
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
