# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Append-only graded-performance event log + per-topic fold.

Each graded ``LSAT Item`` answer is appended as one ``LSAT PerformanceEvent``
note (PRD section 5.3). Because every event is its own note, the log rides
Anki's normal note sync and merges cleanly across devices -- and we never
mutate or delete an event, so the log is append-only. Each event carries a
hybrid logical clock (``answered_at_hlc``) and a stable ``device_id`` so a
later sync-conflict resolver can order/merge concurrent events deterministically.

:func:`fold_recent_performance` collapses the log into a per-topic
``perf_mastery`` in ``[0, 1]`` (recency-weighted accuracy). That value feeds the
points-at-stake queue (``rslib/src/scheduler/points_at_stake.rs``), where
``mastery = 0.5*recall + 0.5*perf_mastery`` and ``points = weight*(1-mastery)``:
a topic answered correctly & recently has high mastery (fewer points at stake);
an unseen or missed topic defaults to ``0.0`` (maximally weak -> studied first).
"""

from __future__ import annotations

import contextlib
import contextvars
import sys
import time
import uuid
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lsat.notetypes import (
    LSAT_PERFORMANCE_EVENT,
    ensure_notetypes,
    migrate_missing_fields,
)
from lsat.taxonomy import (
    TAG_SEP,
    Taxonomy,
    load_taxonomy,
    node_id_to_tag,
    tag_to_node_id,
)

if TYPE_CHECKING:
    from anki.collection import Collection
    from anki.notes import NoteId

EVENTS_DECK = "LSAT::Events"
# device_id is stored in a LOCAL sidecar (not synced config): a synced device_id
# would be copied to every device on first download, breaking HLC uniqueness.
DEVICE_ID_SIDECAR_SUFFIX = ".lsat-device"
HLC_CONFIG_KEY = "lsat:hlc_last"  # HLC baseline DOES sync (keeps devices monotonic)
DEFAULT_HALF_LIFE_DAYS = 30.0
_MS_PER_DAY = 86_400_000.0


# -- identity + clock ---------------------------------------------------------


def device_id(col: Collection) -> str:
    """A stable per-DEVICE id, stored in a local sidecar file beside the
    collection -- deliberately NOT in the synced config.

    A device_id kept in synced config would be copied to every device on the
    first full download, so two devices would share one id: HLC timestamps
    could then collide and the device_id tiebreak would be meaningless. Keying
    it to the local collection file makes it unique per device."""
    path = f"{col.path}{DEVICE_ID_SIDECAR_SUFFIX}"
    try:
        with open(path, encoding="utf-8") as fh:
            existing = fh.read().strip()
        if existing:
            return existing
    except OSError:
        pass
    new_id = uuid.uuid4().hex[:12]
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_id)
    except OSError:
        pass
    return new_id


def _reconcile_hlc_baseline(col: Collection) -> tuple[int, int]:
    """Raise the synced HLC baseline so it never sits below the event log.

    The baseline lives in synced config (``HLC_CONFIG_KEY``) and is merged by
    whole-map config last-writer-wins, so a sync can *lower* it -- which would let
    the next :func:`_next_hlc` mint a stamp BELOW an event that already exists,
    breaking the monotonicity the "a wrong clock cannot win" guarantee rests on.
    The append-only :func:`read_events` log, by contrast, merges by set union and
    is never lost, so it is the durable floor.

    Reconcile the baseline against that floor: raise it to the maximum
    ``(wall, counter)`` seen across (a) the current config baseline and (b) every
    logged event's HLC. Because the counter is included, the next stamp minted at
    the same wall is strictly greater than any existing event -- not merely equal
    by wall. Only ever raises the baseline (monotonic) and is a no-op once it
    already dominates the log, so it is safe to run before every mint. Returns the
    reconciled ``(wall, counter)`` so :func:`_next_hlc` need not re-read config.
    """
    last = col.get_config(HLC_CONFIG_KEY, None)
    cfg = (
        (int(last.get("wall", 0)), int(last.get("counter", 0)))
        if isinstance(last, dict)
        else (0, 0)
    )
    ev = (0, 0)
    for event in read_events(col):
        wall, counter, _ = _hlc_key(event.hlc)
        ev = max(ev, (wall, counter))
    baseline = max(cfg, ev)
    if baseline != cfg:
        col.set_config(HLC_CONFIG_KEY, {"wall": baseline[0], "counter": baseline[1]})
    return baseline


# Per open collection (keyed by object identity), the last (wall, counter) we
# minted. Reconciling the baseline against the event log is an O(events) scan, so
# doing it on EVERY append made answer-submission O(N) per event / O(N^2) per
# session on a large log. Instead we reconcile only when it can actually matter:
# on the first mint for a collection, OR when the config baseline is found BELOW
# what we last minted -- which only happens after a sync lowered it (config
# last-writer-wins). The normal path is O(1) (read config, compare, mint), and
# still can never regress below the append-only log floor.
_HLC_LAST_MINTED: dict[int, tuple[int, int]] = {}


def _next_hlc(col: Collection, dev: str, *, now_ms: int | None = None) -> str:
    """Next hybrid logical clock stamp ``"<wall_ms>:<counter>:<device>"``.

    Monotonic even if the wall clock stalls or goes backwards: the logical part
    (``wall``, ``counter``) strictly increases per call within a collection. The
    baseline is reconciled against the append-only event log
    (:func:`_reconcile_hlc_baseline`) on the first mint and whenever a sync is
    detected to have lowered the config baseline, so it can never mint a stamp
    below an event that already exists; the common path skips the log scan.
    """
    wall = now_ms if now_ms is not None else int(time.time() * 1000)
    key = id(col)
    last = col.get_config(HLC_CONFIG_KEY, None)
    cfg = (
        (int(last.get("wall", 0)), int(last.get("counter", 0)))
        if isinstance(last, dict)
        else (0, 0)
    )
    prev = _HLC_LAST_MINTED.get(key)
    if prev is None or cfg < prev:
        # First mint for this collection, or the config baseline dropped below
        # what we last minted (a sync lowered it) -> reconcile against the log.
        last_wall, last_counter = _reconcile_hlc_baseline(col)
    else:
        last_wall, last_counter = cfg
    logical = max(last_wall, wall)
    counter = last_counter + 1 if logical == last_wall else 0
    col.set_config(HLC_CONFIG_KEY, {"wall": logical, "counter": counter})
    _HLC_LAST_MINTED[key] = (logical, counter)
    return f"{logical:013d}:{counter:06d}:{dev}"


def _hlc_key(hlc: str) -> tuple[int, int, str]:
    parts = hlc.split(":")
    try:
        return (int(parts[0]), int(parts[1]), parts[2] if len(parts) > 2 else "")
    except (ValueError, IndexError):
        return (0, 0, "")


def resolve_lww(records: list[dict]) -> dict | None:
    """Last-writer-wins for a MUTABLE derived record, keyed by HLC then device_id.

    The reusable conflict primitive (see ``sync/README.md``): the record with the
    greater HLC timestamp wins; ties break on the lexicographically greater
    ``device_id`` (both are encoded in the HLC, so ``_hlc_key`` orders by
    ``(wall, counter, device)``). Because ordering uses the HLC and never the wall
    clock, a device with a wrong/skewed clock cannot spuriously win.

    No production record currently resolves with this rule: BOTH the graded-event
    log (:func:`append_event`) and the readiness-projection log
    (:mod:`lsat.models.projections`) are append-only, id-keyed, set-union merged
    note logs -- they are never overwritten and so need no winner. ``resolve_lww``
    is kept as the ready primitive for a *future* genuinely-mutable derived
    snapshot, and is exercised directly by the sync validation's wrong-clock
    scenario (``sync/validate.py``) to prove a skewed clock cannot win the LWW."""
    if not records:
        return None
    return max(records, key=lambda r: _hlc_key(str(r.get("hlc", ""))))


def _to_node_ids(skill_tags: list[str]) -> list[str]:
    """Normalise inputs (either ``lr.weaken`` node ids or ``lsat::`` tags)."""
    out: list[str] = []
    for s in skill_tags:
        s = s.strip()
        if not s:
            continue
        out.append(tag_to_node_id(s) if TAG_SEP in s else s)
    return out


# -- append (write) -----------------------------------------------------------

# The per-answer annotation fields added on top of the original event schema.
# Kept as one batch so the schema-changing migration (which forces exactly one
# full sync) is paid once.
ANNOTATION_FIELDS = ("chosen", "confidence", "phase", "identified")


def migrate_event_fields(col: Collection) -> bool:
    """Ensure the ``LSAT PerformanceEvent`` notetype carries the annotation
    fields (``chosen``/``confidence``/``phase``). Idempotent: a no-op once they
    exist, so it is safe to call on every append and on startup.

    ``ensure_notetypes`` deliberately does NOT add fields to an existing
    notetype (adding a field is a schema change that forces one full sync), so
    this does it explicitly and batches all annotation fields into a single
    change. A freshly created notetype already includes them (they are in
    ``EVENT_FIELDS``), so this only fires for collections seeded before the
    keystone landed. Returns True iff it changed the schema.
    """
    ensure_notetypes(col)
    return bool(
        migrate_missing_fields(col, LSAT_PERFORMANCE_EVENT, list(ANNOTATION_FIELDS))
    )


def append_event(
    col: Collection,
    *,
    item_id: str | int,
    skill_tags: list[str],
    correct: bool,
    response_ms: int,
    chosen: str = "",
    confidence: str | None = None,
    phase: str = "timed",
    identified: str = "",
    now_ms: int | None = None,
) -> NoteId:
    """Append one graded answer to the log; returns the new event note id.

    ``skill_tags`` may be node ids (``lr.weaken``) or full ``lsat::`` tags; both
    are stored as node ids in the field and as hierarchical tags on the note so
    the fold can query them and they roll up under ``lsat::`` like the deck.
    The event's card is suspended (events are logged, never studied).

    ``chosen`` (the selected letter), ``confidence`` ("sure"/"likely"/"guess",
    or ``None`` = unrated) and ``phase`` ("timed"/"blind"/"relaxed") are the
    per-answer annotation store -- they record *how* the answer was reached and
    feed the calibration, distractor-reasoning and blind-review models.
    ``identified`` is the identification-first stage grade ("1"/"0"; "" = no
    classify stage), so identification accuracy is analyzable separately from
    solution accuracy (SPOV 1 / A2).
    """
    from anki.decks import DeckId

    migrate_event_fields(col)
    notetype = col.models.by_name(LSAT_PERFORMANCE_EVENT)
    assert notetype is not None
    deck_id = DeckId(col.decks.add_normal_deck_with_name(EVENTS_DECK).id)

    dev = device_id(col)
    hlc = _next_hlc(col, dev, now_ms=now_ms)
    node_ids = _to_node_ids(skill_tags)

    note = col.new_note(notetype)
    note["item_id"] = str(item_id)
    note["skill_tags"] = " ".join(node_ids)
    note["correct"] = "1" if correct else "0"
    note["response_ms"] = str(max(0, int(response_ms)))
    note["answered_at_hlc"] = hlc
    note["device_id"] = dev
    note["chosen"] = (chosen or "").strip().upper()
    note["confidence"] = (confidence or "").strip().lower()
    note["phase"] = (phase or "timed").strip().lower()
    note["identified"] = identified if identified in ("0", "1") else ""
    note.tags = [node_id_to_tag(n) for n in node_ids]
    col.add_note(note, deck_id)
    col.sched.suspend_cards(list(note.card_ids()))
    return note.id


# -- idempotency (at-least-once replay guard) ---------------------------------
#
# The offline PWA queue (``ts/lib/lsat/client.ts``) drops a queued submission only
# AFTER the server acks it, so a lost ack -- the radio dropping during the response,
# after the event was already committed -- makes the client re-POST a submission the
# server already recorded. Without a guard that re-POST would append a SECOND event,
# breaking the "one PerformanceEvent per submission" invariant. Each queued
# submission therefore carries a stable client-generated ``_idempotency`` id; the
# server records ``id -> result`` for every processed submission in a bounded ring
# and, on an id it has already seen, returns the stored result WITHOUT appending
# again. The ring lives in config (which syncs, so the dedup even survives a restore)
# -- never in the append-only event log. It is FIFO-bounded to ``IDEMPOTENCY_CAP``
# distinct keys, so the guarantee is "no duplicate within the last N submissions":
# ample for a single phone whose retry lands on the very next reconnect, and past
# the window the worst case is one stale replay logging a single duplicate -- the log
# can never be corrupted, only marginally over-counted in an implausible tail.

IDEMPOTENCY_CONFIG_KEY = "lsat:idempotency"
IDEMPOTENCY_CAP = 256


def idempotent_lookup(col: Collection, key: str) -> dict | None:
    """Return the stored result for an already-processed submission ``key``, or
    ``None`` if unseen (or evicted past the bounded window). Empty key = no dedup."""
    if not key:
        return None
    store = col.get_config(IDEMPOTENCY_CONFIG_KEY, None)
    if not isinstance(store, dict):
        return None
    entry = store.get("map", {}).get(key)
    return entry if isinstance(entry, dict) else None


def idempotent_remember(col: Collection, key: str, result: dict) -> None:
    """Record ``key -> result`` so a later replay of the same submission returns the
    stored result instead of appending a duplicate. FIFO-bounded to
    ``IDEMPOTENCY_CAP`` keys; a key already present is left untouched (keep the first
    result + its queue position, so a re-remember can't refresh a key past eviction)."""
    if not key or not isinstance(result, dict):
        return
    store = col.get_config(IDEMPOTENCY_CONFIG_KEY, None)
    if not isinstance(store, dict) or not isinstance(store.get("order"), list) or not isinstance(
        store.get("map"), dict
    ):
        store = {"order": [], "map": {}}
    order: list = store["order"]
    mapping: dict = store["map"]
    if key in mapping:
        return
    order.append(key)
    mapping[key] = result
    while len(order) > IDEMPOTENCY_CAP:
        mapping.pop(order.pop(0), None)
    col.set_config(IDEMPOTENCY_CONFIG_KEY, {"order": order, "map": mapping})


# -- read + fold --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceEvent:
    note_id: int
    item_id: str
    node_ids: list[str]
    correct: bool
    response_ms: int
    hlc: str
    device_id: str
    # Per-answer annotation store (default to the pre-migration values so old
    # events -- which lack these fields -- read as unrated timed answers).
    chosen: str = ""
    confidence: str = ""
    phase: str = "timed"
    identified: str = ""  # "1"/"0" classify-stage grade; "" = no classify stage

    @property
    def wall_ms(self) -> int:
        return _hlc_key(self.hlc)[0]


def _safe_int(value: str) -> int:
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return 0


def _field(note: object, name: str, default: str = "") -> str:
    """Read a note field defensively: events logged before a field existed
    return the default rather than raising ``KeyError``."""
    try:
        val = note[name]  # type: ignore[index]
    except KeyError:
        return default
    return val if val is not None else default


# Request-scoped read cache. A single dashboard build (see
# ``lsat/dashboard_data.py::build``) reads the event log ~10 times -- once per
# model + insight panel -- each a full ``find_notes`` + per-note ``get_note``
# scan. Opening :func:`events_cache` around a read-only analysis window makes
# ``read_events`` return one shared parse instead, collapsing those scans into a
# single one. It is a ContextVar (isolated per async task/thread) keyed on the
# collection's identity, and it is deliberately used ONLY for read-only windows:
# no event *note* is written inside ``build`` (``append_projection`` writes
# config, not an event note), so the cached list cannot go stale mid-window.
_EVENTS_CACHE: contextvars.ContextVar[tuple[int, list[PerformanceEvent]] | None] = (
    contextvars.ContextVar("lsat_events_cache", default=None)
)


@contextlib.contextmanager
def events_cache(col: Collection) -> Iterator[list[PerformanceEvent]]:
    """Open a read-only window in which :func:`read_events` is parsed once.

    Every ``read_events(col)`` call inside the ``with`` block returns the same
    list (parsed on entry). Safe only where no new event note is appended inside
    the window -- it is meant for analysis/dashboard assembly, never around
    :func:`append_event`. Reentrant: a nested ``events_cache`` for the same
    collection reuses the outer parse.
    """
    existing = _EVENTS_CACHE.get()
    if existing is not None and existing[0] == id(col):
        yield existing[1]
        return
    events = _read_events_uncached(col)
    token = _EVENTS_CACHE.set((id(col), events))
    try:
        yield events
    finally:
        _EVENTS_CACHE.reset(token)


def read_events(col: Collection) -> list[PerformanceEvent]:
    """All logged events, sorted oldest -> newest by HLC.

    Inside an :func:`events_cache` window for the same collection this returns
    the cached parse (see the cache note above); otherwise it reads fresh.
    """
    cached = _EVENTS_CACHE.get()
    if cached is not None and cached[0] == id(col):
        return cached[1]
    return _read_events_uncached(col)


def _read_events_uncached(col: Collection) -> list[PerformanceEvent]:
    if col.models.by_name(LSAT_PERFORMANCE_EVENT) is None:
        return []
    events: list[PerformanceEvent] = []
    # Intern the highly-repetitive fields: across thousands of events the item ids,
    # skill tags, device id, phase, confidence and classify grade take only a
    # handful of distinct values, so interning collapses them to one shared string
    # object each (large retained-memory win on a heavy event log). `hlc` is
    # near-unique per event, so it is deliberately not interned.
    intern = sys.intern
    # De-duplicate the per-event tag-set container: across a log most events repeat
    # the same handful of skill-tag sets, so caching one shared list per distinct
    # set avoids thousands of redundant small list objects (on top of interning the
    # tag strings themselves). Safe because PerformanceEvent is frozen and every
    # consumer treats node_ids as read-only (verified: only iteration / len / list()).
    tagset_cache: dict[tuple[str, ...], list[str]] = {}
    for nid in col.find_notes(f'note:"{LSAT_PERFORMANCE_EVENT}"'):
        note = col.get_note(nid)
        tag_key = tuple(intern(t) for t in note["skill_tags"].split())
        node_ids = tagset_cache.get(tag_key)
        if node_ids is None:
            node_ids = list(tag_key)
            tagset_cache[tag_key] = node_ids
        events.append(
            PerformanceEvent(
                note_id=int(nid),
                item_id=intern(note["item_id"]),
                node_ids=node_ids,
                correct=note["correct"].strip() == "1",
                response_ms=_safe_int(note["response_ms"]),
                hlc=note["answered_at_hlc"],
                device_id=intern(note["device_id"]),
                chosen=intern(_field(note, "chosen").strip().upper()),
                confidence=intern(_field(note, "confidence").strip().lower()),
                phase=intern(_field(note, "phase", "timed").strip().lower() or "timed"),
                identified=intern(_field(note, "identified").strip()),
            )
        )
    events.sort(key=lambda e: _hlc_key(e.hlc))
    return events


def fold_recent_performance(
    col: Collection,
    taxonomy: Taxonomy | None = None,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
    phases: tuple[str, ...] | None = ("timed",),
    honest_mastery: bool = True,
) -> dict[str, float]:
    """Recency-weighted accuracy per taxonomy node id, in ``[0, 1]``.

    Recent answers count more: an answer's weight halves every
    ``half_life_days``. Only nodes that actually appear in the log are returned
    (callers default missing nodes to ``0.0``).

    ``phases`` filters which answer phases feed mastery (``None`` = all). It
    defaults to ``("timed",)`` -- honest mastery: only real, time-pressured
    answers count, so a relaxed/blind second-pass answer never inflates a
    topic's mastery (the blind pass is used elsewhere for the Gap Map / Choke
    Index). Pre-migration events read as ``phase="timed"`` so they still count.

    ``honest_mastery`` (Feature 4) additionally DROPS a *lucky timed win* -- a
    timed-correct answer whose most-recent untimed (blind/relaxed) re-answer was
    wrong -- so a guess the student could not reproduce untimed is never credited
    as mastery (``lsat.blind_review.lucky_timed_items``). It is a no-op until the
    student does an untimed second pass, so it degrades cleanly.
    """
    _ = taxonomy  # accepted for symmetry / future per-node config; not needed here
    events = read_events(col)
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    half_life_ms = max(1.0, half_life_days * _MS_PER_DAY)

    lucky: set[str] = set()
    if honest_mastery:
        # Lazy import (blind_review reads this same log) -> no import cycle.
        from lsat.blind_review import lucky_timed_items_from_events

        lucky = lucky_timed_items_from_events(events)

    # node id -> [weighted_correct, weighted_total]
    acc: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for event in events:
        if phases is not None and event.phase not in phases:
            continue
        # Honest-mastery filter: a timed win refuted by an untimed miss is a lucky
        # guess -> drop it (do not credit it as mastery).
        if honest_mastery and event.correct and event.item_id in lucky:
            continue
        age_ms = max(0, now_ms - event.wall_ms)
        weight = 0.5 ** (age_ms / half_life_ms)
        hit = weight if event.correct else 0.0
        for node_id in event.node_ids:
            acc[node_id][0] += hit
            acc[node_id][1] += weight

    return {
        node_id: (correct / total if total > 0 else 0.0)
        for node_id, (correct, total) in acc.items()
    }


# -- feed the points-at-stake queue ------------------------------------------


# B3 (SPOV 2): the misconception-priority queue toggle. ON by default; the
# ablation harness and the "interleaving-off"-style arms flip it. When OFF,
# confident-wrong history stops influencing the queue (errors weigh uniformly);
# the trap boost is a separate signal and is not governed by this flag.
MISCONCEPTION_QUEUE_CONFIG_KEY = "lsat:misconception_queue"


def misconception_queue_enabled(col: Collection) -> bool:
    return bool(col.get_config(MISCONCEPTION_QUEUE_CONFIG_KEY, True))


def misconception_penalty(
    col: Collection,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
) -> dict[str, float]:
    """Per-node-id priority penalty from confident-wrong history (B3).

    ``topic_weight x student_weakness x misconception_penalty``: the Rust queue
    already computes ``weight x (1 - mastery)``, so the penalty enters as an
    additive weight bump per node (recency-weighted confident-miss mass, from
    the hypercorrection boost). Empty when the toggle is off.
    """
    if not misconception_queue_enabled(col):
        return {}
    from lsat.models.calibration import hypercorrection_boost

    return hypercorrection_boost(col, half_life_days=half_life_days, now_ms=now_ms)


def _queue_boosts(
    col: Collection, *, half_life_days: float, now_ms: int | None
) -> dict[str, float]:
    """Per-tag priority boosts from the confidence + distractor signals.

    Combines the misconception penalty (high-confidence misses -- Metcalfe
    2017; toggleable, see ``MISCONCEPTION_QUEUE_CONFIG_KEY``) and the trap
    boost (the answer-choice families you keep falling for) so the queue leads
    with the most valuable errors. Lazily imported to avoid a cycle (both
    modules read this log). Best-effort: any failure yields no boost.
    """
    boosts: dict[str, float] = defaultdict(float)
    try:
        from lsat.error_patterns import trap_boost

        for nid, b in misconception_penalty(
            col, half_life_days=half_life_days, now_ms=now_ms
        ).items():
            boosts[node_id_to_tag(nid)] += b
        for nid, b in trap_boost(
            col, half_life_days=half_life_days, now_ms=now_ms
        ).items():
            boosts[node_id_to_tag(nid)] += b
    except Exception:
        return {}
    return dict(boosts)


def topic_weights_for_queue(
    col: Collection,
    taxonomy: Taxonomy | None = None,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
    apply_boosts: bool = True,
) -> list[tuple[str, float, float]]:
    """``(tag, weight, perf_mastery)`` triples for ``points_at_stake_queue``.

    Scored question types contribute their ``exam_weight``; cross-cutting skills
    contribute their ``study_weight`` (queue/mastery only). A topic with no
    graded events defaults to ``perf_mastery = 0.0`` (maximally weak).

    When ``apply_boosts`` is set, each tag's weight is additively nudged by the
    confidence/distractor signals (:func:`_queue_boosts`), so confident misses
    and habitual answer-choice traps surface sooner without touching the Rust
    queue (which still just computes ``weight*(1-mastery)``).
    """
    tax = taxonomy or load_taxonomy()
    mastery = fold_recent_performance(
        col, tax, half_life_days=half_life_days, now_ms=now_ms
    )
    boosts = (
        _queue_boosts(col, half_life_days=half_life_days, now_ms=now_ms)
        if apply_boosts
        else {}
    )
    triples: list[tuple[str, float, float]] = []
    for topic in tax.question_types:
        w = topic.exam_weight + boosts.get(topic.tag, 0.0)
        triples.append((topic.tag, w, mastery.get(topic.id, 0.0)))
    for skill in tax.cross_cutting:
        w = skill.study_weight + boosts.get(skill.tag, 0.0)
        triples.append((skill.tag, w, mastery.get(skill.id, 0.0)))
    return triples


def points_at_stake(
    col: Collection,
    *,
    deck_id: int = 0,
    limit: int = 0,
    taxonomy: Taxonomy | None = None,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
):
    """Convenience: build topic weights from the log and run the queue RPC."""
    tax = taxonomy or load_taxonomy()
    weights = topic_weights_for_queue(
        col, tax, half_life_days=half_life_days, now_ms=now_ms
    )
    return col.sched.points_at_stake_queue(weights, deck_id=deck_id, limit=limit)
