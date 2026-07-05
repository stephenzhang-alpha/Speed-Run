---
name: anki-sync-conflict
description: "Use this skill whenever working on sync between the desktop app and the AnkiDroid companion, or on conflict resolution: setting up the self-hosted sync server, the two-way / offline sync requirements, the same-card-on-two-devices conflict rule (challenge 7b), the 'no lost or double-counted reviews' test, syncing the app's own graded-performance data, or the wrong-clock / offline-mid-sync / interrupted-sync adversarial cases. Read this BEFORE implementing or testing sync. Pairs with the project README and the PRD (§9, §3.3)."
---

# Two-way sync + conflict resolution (desktop ⇄ AnkiDroid)

The brief (challenge 7b) wants: 10 cards reviewed offline on the phone + 10 different cards offline on desktop → reconnect → **all 20 land once, none lost or double-counted**; then the **same card** reviewed on both offline → sync → a **clear, correct, documented winner**. Plus offline review and a wrong-clock-safe rule.

The winning MVP strategy is **two layers**: use Anki's existing sync for the standard collection (it already meets most of 7b), and define your **own explicit rule** for the custom data you add. Don't reimplement the scheduler's sync in Swift/JS — that fails the brief.

## Layer 1 — standard collection: use Anki's existing sync

The standard collection (cards, notes, **revlog**, decks, config) syncs via a sync server. What it already guarantees, and why it covers most of 7b:

- **Two sync modes.** A _normal_ (incremental) sync sends only changes since the last sync, tracked by **USN** (Update Sequence Number): locally changed objects carry `usn = -1`, and the server assigns the next USN on sync. A _full_ sync is the fallback when sides can't be merged.
- **Both-sides merge.** After the initial one-way upload/download, Anki **merges changes from multiple locations**, and under normal circumstances **reviews and edits made on two devices before syncing are both preserved**. The `revlog` is effectively **append-only** (each review row has a unique millisecond id), so two reviews on two devices both survive — **this is exactly the 10+10 test, and Anki passes it natively**.
- **Deletions** are tracked in the `graves` table (card/note/deck) so they propagate.
- **Conflict fallback.** When an automatic merge isn't possible (e.g. a schema change like adding a card template, or an incompatible divergence), Anki requires a **full sync** and the user chooses **Upload** (this device wins) or **Download** (server wins), overwriting the other side.

**The same-card case (what to document).** When the same card is reviewed on both devices offline, both `revlog` rows are preserved on merge (no double-count of history), and the card's _current_ scheduling state resolves to one device's update. Don't assert Anki's internal tiebreak from memory — **run the 7b test and document the observed winner** for the standard collection. For history integrity you can rely on the append-only revlog; for the _current state_ you state the rule you observe (and, if you want determinism independent of wall-clock, prefer Layer-2 handling for any state you compute yourself).

### Self-hosted sync server (do this so desktop ⇄ AnkiDroid sync at all)

The server is built into desktop Anki (2.1.57+). Two ways to run a standalone:

```bash
# Python standalone (PyPI 'anki' package; Python 3.9+)
python3 -m venv ~/syncserver
~/syncserver/bin/pip install anki
SYNC_USER1=user:pass ~/syncserver/bin/python -m anki.syncserver

# Rust standalone (Anki 2.1.66+)
cargo install --locked --git https://github.com/ankitects/anki.git --tag <latest-version> anki-sync-server
SYNC_USER1=user:pass anki-sync-server
```

- `SYNC_USER1=user:pass` is required (add `SYNC_USER2…` for more). `SYNC_HOST` / `SYNC_PORT` set the bind address. `PASSWORDS_HASHED=1` to use PHC-format hashes.
- The server stores its **own copy** of the collection in a folder that **must not** be your client's Anki data folder. You must _sync_ data in, not copy files.
- It listens over **plain HTTP** — keep it on your LAN or put a VPN / HTTPS reverse proxy in front. `protoc` must be installed to build.
- **Point both clients at it:** set the sync URL in desktop preferences and in AnkiDroid's advanced/sync settings (e.g. `http://192.168.1.x:8080/`). AnkiDroid explicitly supports a self-hosted server.
- **Scheduler parity:** confirm the desktop and your AnkiDroid build use the same scheduler version (v3); a mismatch can force full syncs. Verify against your AnkiDroid version rather than assuming.

## Layer 2 — the app's custom data: your explicit conflict rule

Anki's sync knows nothing about the data your three-score models add (graded **performance-item** responses, topic mastery, readiness projections, timing). You must sync these and define the rule the brief asks you to "write down." Two design choices make this clean and adversary-proof:

### 2a. Store graded responses as an append-only event log (kills double-counting)

Model each graded performance response as an immutable event with a **globally unique id** (e.g. `device_id + monotonic_counter`, or a UUID):

```
PerformanceEvent { event_id, item_id, skill_tags, correct, response_ms, answered_at_hlc, device_id }
```

- Merging two devices' logs is a **set union keyed by `event_id`** — idempotent and commutative. A re-sent batch (e.g. after an interrupted sync) is deduplicated; reordering doesn't matter. **No event is lost or double-counted, and no "winner" is needed for history.**
- "Current mastery" is a **fold over the merged log**, so it's derived, not stored-and-conflicting. This is the same principle that makes Anki's revlog safe, applied to your data.

### 2b. For mutable derived records, last-writer-wins by a Hybrid Logical Clock (kills the wrong-clock case)

For records that are genuinely mutable (e.g. a per-topic mastery snapshot, a saved readiness projection), use **last-writer-wins keyed by a Hybrid Logical Clock (HLC)**, not wall-clock time:

- An HLC timestamp = `(physical_time, logical_counter)`; on each event a device takes `max(its physical clock, last seen physical time)` and bumps the counter on ties. This stays monotonic **even if a phone's wall clock is wrong or skewed**, so a device with a bad clock can't spuriously win.
- **Tiebreak deterministically by `device_id`** when HLC timestamps are equal, so the winner is always well-defined and reproducible.
- **Write the rule down (verbatim, in the README):** _"For mutable derived records, the record with the greater HLC timestamp wins; ties are broken by the lexicographically greater device_id. Graded responses are an append-only, id-keyed event log and are never overwritten."_

### Where to put the custom data

Simplest for the MVP: store it inside the Anki collection (e.g. in collection config / a custom key, or your own tables that ride the collection) so it syncs through Anki's existing mechanism and inherits USN tracking. If you outgrow that, run a parallel sync channel for the event log — but the append-only + HLC rules above are what make either option correct.

## Offline, interrupted, and clock-skew handling

- **Offline review:** both apps work fully offline; changes queue locally (`usn = -1` for standard objects; appended events for custom data) and sync the delta on reconnect. (PRD §13 target: a normal session syncs in < 5 s.)
- **Phone goes offline mid-sync:** sync is transactional — an interrupted sync must leave the local collection intact and retry; worst case escalates to a full sync. For the custom event log, the id-keyed union means a partially-sent batch is safely re-sent (dedup on `event_id`). Test this explicitly (kill the network mid-sync; reconnect; assert no corruption and counts correct).
- **Wrong clock:** handled by the HLC for custom data; for the standard collection, the append-only revlog keeps history safe regardless, and you can additionally warn on large client/server clock skew before syncing.

## The 7b test procedure (exactly what to run and prove)

1. **No loss / no double-count.** Offline, review **10 cards on the phone** and **10 different cards on desktop**. Reconnect; sync both. Verify all 20 reviews are present **once**: query the `revlog` and assert 20 distinct review ids (and that your `PerformanceEvent` log has the expected count with no duplicate `event_id`s). `TRACESQL=1` helps you watch the SQL.
2. **Same-card conflict.** Offline, review the **same card** on both devices. Sync. Show the documented winner: both revlog rows preserved; the card's current state resolves per the rule you documented; for any custom mutable record, the HLC winner is the expected one. Demonstrate that **setting the phone's clock wrong does not change the winner** (HLC).
3. **Record the recording** (phone review appearing on desktop after sync) for the Friday/Sunday proof.

## Definition of done (maps to the brief)

- Friday: two-way sync works (phone↔desktop, nothing lost/doubled); offline review then sync-on-reconnect.
- Sunday: sync handles conflicts with a **correct, documented** winner; the conflict rule is written down; both apps still run with AI off. Challenge 7b: the 10+10 result and the same-card winner are demonstrated, with the rule stated.
