# Sync & conflict resolution (Anki for LSAT)

Two-way sync between devices (challenge 7b) uses **two layers**: Anki's existing
sync for the standard collection, and one explicit, written-down rule for the
custom data the LSAT layer adds. We do **not** reimplement the scheduler's sync.

## Running the self-hosted sync server

The server is built into this fork. Run a standalone instance:

```bash
SYNC_USER1=user:pass \
SYNC_HOST=127.0.0.1 SYNC_PORT=8080 \
SYNC_BASE=/path/to/server-data \
PYTHONPATH=pylib:out/pylib out/pyenv/bin/python -m anki.syncserver
```

- `SYNC_USER1=user:pass` is required (`SYNC_USER2…` for more users; `PASSWORDS_HASHED=1` for PHC hashes).
- `SYNC_BASE` is the server's **own** collection store — it must **not** be a client's Anki folder. You sync data in; you never copy files.
- It serves plain HTTP — keep it on your LAN / behind a VPN or HTTPS proxy.
- Point each desktop client at `http://<host>:8080/` in Preferences → Syncing.

## Validating it (reproducible)

`sync/validate.py` stands up the server on localhost, points two client
collections at it, and asserts the 7b scenarios end to end:

```bash
out/pyenv/bin/python sync/validate.py
```

Observed result (all pass):

| Scenario | What it proves |
| --- | --- |
| device-id per-device | the two collections keep **distinct** `device_id`s after a full download |
| 10+10 no-loss/no-double | 20 distinct `revlog` ids on both sides, zero duplicates |
| same-card conflict | **both** revlog rows preserved; the card's current state **converges** to one documented winner |
| event-log set-union | both graded events present once on both sides (keyed by id) |
| wrong-clock (HLC LWW) | a device with a 10-day-stale clock still gets the greater HLC and wins correctly |
| interrupted/retry | re-syncing changes nothing (idempotent) |

## Layer 1 — standard collection (Anki's native sync)

Cards, notes, **revlog**, decks, and config sync via the server, tracked by
**USN** (locally changed rows carry `usn = -1`; the server assigns the next USN).

- The **`revlog` is append-only** — each review row has a unique millisecond id,
  so two reviews made on two devices before syncing **both survive**. This is
  exactly the 10+10 test, and Anki passes it natively (verified: 20 distinct ids,
  none lost or doubled).
- **Deletions** propagate via the `graves` table.
- **Same card on two devices:** both revlog rows are preserved (history is never
  double-counted); the card's *current* scheduling state resolves to one side and
  both devices **converge** to it on the next sync (verified). We do not assert an
  internal tiebreak from memory — the validation records the observed converged
  state.
- **Unmergeable divergence** (e.g. a schema change) falls back to a **full sync**,
  where the user picks **Upload** (this device wins) or **Download** (server wins).

## Layer 2 — the LSAT custom data (our explicit rule)

Anki's sync knows nothing about the graded-performance data the score models add.
We make it correct and adversary-proof with two design choices:

1. **Every custom record we persist is an append-only, id-keyed note log.** A
   graded response is an immutable `LSAT PerformanceEvent` note with a globally
   unique id (`answered_at_hlc` = HLC that embeds the `device_id`); a saved
   readiness projection is an immutable `LSAT Projection` note carrying its own
   `(device_id, hlc)` id (`lsat/models/projections.py`). Because each is a note,
   both ride Anki's note sync; merging two devices' logs is a **set union keyed by
   note id** — idempotent and commutative, so a re-sent batch after an interrupted
   sync is **deduplicated** and **nothing is lost or double-counted**. "Current
   mastery" and the readiness **track record** are a **fold/read over the merged
   log** (derived, never stored-and-conflicting), so they need no winner. This is
   exactly why the projection log is a set of notes and **not** a single synced
   config list: whole-map config last-writer-wins would replace the list on a
   concurrent multi-device edit and silently drop one device's projections
   (defect #20). Both logs are verified by the projection-survival + HLC
   self-test: `out/pyenv/bin/python -m lsat.models.projections`.

2. **A Hybrid Logical Clock orders records without trusting the wall clock.** An
   HLC stamp is `(physical_time, logical_counter, device_id)`; each mint takes
   `max(local clock, last-seen physical time)` and bumps the counter on ties, so
   it stays monotonic **even if a device's wall clock is wrong**. The HLC baseline
   syncs via collection config so devices stay monotonic relative to each other —
   but whole-map config last-writer-wins could *lower* that baseline on a sync. To
   stop a lowered baseline from minting a stamp **below an event that already
   exists**, each mint first **reconciles the baseline against the append-only
   event log** (which set-unions and is never lost): the baseline is raised to at
   least the newest logged HLC before use
   (`lsat.events._reconcile_hlc_baseline`), so it is non-regressing and the "a
   wrong clock cannot win" guarantee holds across syncs (defect #22). The
   **`device_id` is stored in a local sidecar file, never synced** — a synced
   `device_id` would be copied to every device on first download and break HLC
   uniqueness and the tiebreak.

### The rule (verbatim)

> For mutable derived records, the record with the greater HLC timestamp wins;
> ties are broken by the lexicographically greater `device_id`. Graded responses
> and readiness projections are append-only, id-keyed note logs and are never
> overwritten.

Both records we persist today are append-only, so **no production record
currently resolves by last-writer-wins.** The LWW half of the rule is implemented
as the reusable primitive `lsat.events.resolve_lww` (order by HLC, tie-break on
`device_id`) — kept ready for a *future* genuinely-mutable derived snapshot, and
exercised directly by the wrong-clock validation (`sync/validate.py`) to prove a
skewed clock cannot win it. The append-only logs are `lsat.events`
(`append_event` / `read_events` / `fold_recent_performance`) and
`lsat.models.projections` (`append_projection` / `read_projections` /
`track_record`).

## Offline, interrupted, and clock-skew

- **Offline:** changes queue locally (`usn = -1` for standard objects; appended
  events for custom data) and sync the delta on reconnect.
- **Interrupted mid-sync:** sync is transactional — an interrupted sync leaves the
  local collection intact and retries; the id-keyed event union makes a
  partially-sent batch safe to re-send (verified: re-sync is idempotent).
- **Wrong clock:** handled by the HLC for custom data; the append-only revlog
  keeps standard history safe regardless (verified: a 10-day-stale clock does not
  change the winner).
