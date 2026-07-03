# The Rust engine change: points-at-stake review queue

Implements PRD §7 (challenge 7a). This is the project's required, real change to
Anki's **Rust** engine — not a Python/Qt re-skin — and because the backend is
shared it ships to both the desktop app and the AnkiDroid build.

## What it does

A new **read-only** backend RPC, `GetPointsAtStakeQueue`, orders the due cards in
a deck by **topic exam weight × student weakness**, so the single most valuable
card to study surfaces first:

```text
mastery(card, tag) = RECALL_WEIGHT * recall + PERF_WEIGHT * perf_mastery(tag)   # 0.5 / 0.5
points(card)       = max over card.tags of  weight(tag) * (1 - mastery(card, tag))
```

- `recall` = the card's current FSRS retrievability (0.0 when the card has no
  FSRS memory state, i.e. treat an unknown card as maximally weak), computed on
  demand from the card's stored memory state with the same `fsrs` crate the
  scheduler uses.
- `weight` and `perf_mastery` come from the LSAT taxonomy and are passed **per
  request** (`repeated TopicWeight`), so the weights stay editable in one place
  (`lsat-taxonomy.yaml`) rather than hard-coded in Rust. Tags are the
  hierarchical `lsat::…` note tags.

Call it from Python:

```python
entries = col.sched.points_at_stake_queue(
    [("lsat::lr::weaken", 0.066, 0.30), ("lsat::flaw::causal", 0.086, 0.55)],
    deck_id=0,   # 0 = whole collection
    limit=50,    # 0 = no limit
)
# entries: highest-priority first; each has .card_id, .points, .top_tag
```

## Why this belongs in Rust, not Python

1. **Hot path over large collections.** The queue scores up to ~50k due cards.
   Gathering them reuses Anki's in-process search/SQL layer and reads card +
   note rows directly; doing this in Python would marshal every candidate card
   across the rsbridge FFI, which is far slower and would risk blocking the UI.
2. **Reuse the exact FSRS recall math.** Recall is computed with the same
   `fsrs` crate (`FSRS::current_retrievability_seconds`) and the same
   `Card::seconds_since_last_review` logic the scheduler/browser already use.
   Re-deriving retrievability in Python would drift from what the engine
   believes and could disagree with the scheduler.
3. **Shared engine → ships to both platforms once.** The Rust backend is wrapped
   by the desktop app *and* AnkiDroid. Implementing the queue once in Rust gives
   identical behaviour on desktop and Android, with a single type-safe protobuf
   contract across Rust, Python, and TypeScript/Kotlin. A Python reimplementation
   would not exist on Android, would diverge, and would be slow.

## Read-only / undo / no-corruption

The RPC is a **pure query**. `Collection::points_at_stake_queue`
(`rslib/src/scheduler/points_at_stake.rs`) only **reads** — `search_cards`,
`storage.get_card`, `storage.get_note`, and an FSRS retrievability calculation —
and returns a response struct.

- It does **not** call `self.transact(...)`, records **no** undo entry, returns
  **no** `OpChanges`, and performs **no** writes.
- Therefore it cannot leave the collection half-modified and **cannot corrupt
  scheduling state**, and it does not perturb the undo history of other
  operations. (Contrast mutating ops such as `answer_card` /
  `bury_or_suspend_cards`, which wrap work in `transact(Op, …)` and return
  `OpChanges` to participate in undo. Our query deliberately does none of that —
  there is nothing to undo.)
- **Verified by tests:** the Python test asserts `select count() from revlog == 0`
  after calling the RPC (no reviews/changes recorded), and the Rust unit tests
  exercise ordering without any mutation. `cargo clippy` and `rustfmt` are clean.

## Tests

- **3 Rust unit tests** in `rslib/src/scheduler/points_at_stake.rs`:
  - `orders_by_topic_weight_when_weakness_equal` — at equal weakness, the
    higher-exam-weight topic ranks first.
  - `orders_by_weakness_when_weight_equal` — at equal weight, the weaker topic
    (lower `perf_mastery`) ranks first.
  - `respects_limit_and_ignores_unweighted_tags` — `limit` truncates; a card
    whose tag has no configured weight scores 0 and sorts last.
- **1 Python test** (`pylib/tests/test_schedv3.py::test_points_at_stake_queue`)
  calls `col.sched.points_at_stake_queue(...)` end-to-end and asserts the
  ordering, the points value, and that the collection was not mutated.

## Files touched & merge-difficulty assessment

New files (purely additive — rebase clean):

- `rslib/src/scheduler/points_at_stake.rs` — the whole feature (logic + unit
  tests).
- `lsat/docs/points-at-stake-rust-change.md` — this note.

Existing files, **appended-to only** (no existing definition modified):

- `proto/anki/scheduler.proto` — one `rpc` added at the end of
  `SchedulerService`; four new messages appended at the end of the file.
- `pylib/anki/scheduler/base.py` — two type aliases and one method appended.
- `pylib/tests/test_schedv3.py` — one test appended.

Existing files, **one-line additions** (low conflict risk):

- `rslib/src/scheduler/mod.rs` — `pub(crate) mod points_at_stake;` added to the
  module list.
- `rslib/src/scheduler/service/mod.rs` — one method added inside the existing
  `impl crate::services::SchedulerService for Collection` block; no existing
  method body changed.

Generated (not hand-edited; regenerated by the build from the proto): the Rust
service trait + dispatch, `out/pylib/anki/_backend_generated.py` +
`scheduler_pb2.py`, and `out/ts/lib/generated/backend.ts`.

**Merge-difficulty: LOW.** The change is overwhelmingly additive. We deliberately
avoided the high-conflict shared scheduler internals — the `ReviewCardOrder`
enum (`proto/anki/deck_config.proto`), `review_order_sql` / `ReviewOrderSubclause`
(`rslib/src/storage/card/mod.rs`), `QueueBuilder`, and `CardQueues` — so future
rebases onto upstream Anki stay easy. The only edits to existing files are a new
module-declaration line and a new method appended to an existing `impl` block,
both of which rebase cleanly unless upstream reorders those exact lines.

## Notes & follow-ups

- The candidate set is "due" cards (`is:due`) in the deck (and children), gathered
  via Anki's existing search. This standalone RPC powers the dashboard's "single
  best next thing to study" and an ordered study session; making it drive the
  *default* reviewer order would require editing the shared `QueueBuilder` and is
  intentionally deferred.
- The 0.5 / 0.5 recall↔performance blend is a documented default; it will be
  tuned and stated in the model notes.
