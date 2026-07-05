# Review-side verification

Everything a reviewer needs to confirm the two things that are hard to take on faith —
**(1) the learning-science eval actually runs and passes**, and **(2) the phone works
offline and syncs on reconnect** — is committed here, with the exact command to
reproduce each. All commands assume `BUILD_ROOT` is set (this checkout's path has a
space; see below).

```bash
export BUILD_ROOT=/Users/<you>/.anki-lsat-build   # space-free build dir (the `out` symlink)
```

## 1. The eval, baseline, and leakage outputs

The **actual committed outputs** live in [`docs/eval/`](eval/) so you can read them
without running anything:

- [`docs/eval/report.md`](eval/report.md) — every gate/arm + 95% CI + the calibration
  reliability diagram + an honest "what didn't work" section. Headline: **`GATE OK` —
  0 hard gates failed.**
- [`docs/eval/metrics.json`](eval/metrics.json) — machine-readable per-arm metrics.
- [`docs/eval/manifest.json`](eval/manifest.json) — the auditable 40/10 content-aware split.
- [`docs/eval/README.md`](eval/README.md) — provenance + the **baseline** and **leakage**
  outputs called out explicitly.

**Baseline (retrieval, honest negative):** the offline TF-IDF stand-in does _not_ beat
BM25 — `reciprocal_rank 0.9238 vs 0.9162`, paired bootstrap 95% CI `[0.0, 0.0222]`
**includes 0**, so `embedding_wins: false`. Reported, not hidden.

**Leakage (gate, PASS):** `0` near-duplicate leaks across the `40×10` train/held-out
pairs; the detector self-test proves it catches verbatim **and** reworded duplicates
and leaves unrelated items alone.

**Regenerate:**

```bash
make eval        # writes out/eval/{report.md,metrics.json,manifest.json}; exits non-zero on any gate fail
cp out/eval/{report.md,metrics.json,manifest.json} docs/eval/   # refresh the committed snapshot
```

## 2. Offline review + reconnect sync (the phone requirement)

The Android app is **no longer a purely network-dependent WebView**. The client
(`ts/lib/lsat/client.ts`) prefetches items, queues graded answers durably in
`localStorage` when offline (or on a connectivity failure), and replays them to the
server on reconnect, where each is graded and appended to the same append-only
`PerformanceEvent` log (the no-answer-leak invariant means grading is always
server-side, so a queued answer is graded when it syncs). The Study tab shows an
offline banner + a live "N queued" count that clears on sync.

**The recording (video):** [`docs/offline-sync-recording.webm`](offline-sync-recording.webm)
— a real Chromium screen recording (phone form factor) of the **actual `lsat-mobile`
PWA** driven against the **real `lsat/server` backend**: it loads online, goes offline
(the "Offline — answers save on this device…" banner appears), answers an item (the
"Saved offline" card shows — the answer is queued, not sent), then reconnects and the
banner clears as the queue flushes. An interactive Playwright trace is at
[`docs/offline-sync-trace.zip`](offline-sync-trace.zip) (open with
`out/node_modules/.bin/playwright show-trace docs/offline-sync-trace.zip`).

The server log during the recording is the proof: `POST /_anki/lsatSectionItems` (online
prefetch) → **no `/_anki/lsatSubmitAnswer` while offline** → a single
`POST /_anki/lsatSubmitAnswer` only _after_ reconnect (the queue replaying).

**Reproduce the video / transcript / unit proof:**

```bash
BUILD_ROOT=… just rebuild-web    # bake the offline client into the served PWA
out/node_modules/.bin/playwright test --config playwright.offline.config.ts
                                 # -> re-records out/e2e-offline/.../video.webm (asserts the invariant + passes/fails)
make sync-demo                   # end-to-end transcript against lsat/server (docs/offline-sync-recording.txt)
just test-ts                     # ts/lib/lsat/client.offline.test.ts: 9 unit cases (queue offline, replay on
                                 # reconnect, connectivity-failure queues, HTTP-error surfaces, offline prefetch,
                                 # persistence, partial-sync FIFO/resume, lost-ack keeps a stable idempotency id)
```

A companion text transcript is [`docs/offline-sync-recording.txt`](offline-sync-recording.txt):

```
ONLINE    -> prefetched 5 items (payload carries NO correct answer -> no leak)
OFFLINE   -> answered 3 items, all QUEUED locally; server PerformanceEvents: 0 (unchanged)
RECONNECT -> synced 3/3; server PerformanceEvents: 3  (graded + append-only logged)
DEMO OK: offline review queued 3 with the server untouched; reconnect synced 3 -> 3 new events.
```

## 3. What changed to tighten the Android path

- **Offline data** — durable answer queue + item prefetch + reconnect flush in
  `client.ts` (`postDurable`, `flushQueue`, `initOfflineSync`, `prefetchItems`,
  `pendingCount`); the Study tab banner in `ts/routes/lsat-mobile/+page.svelte`.
- **Configurable API base** — `client.ts` `apiBase()` (default same-origin) lets a
  locally-bundled shell reach a remote server; set via a one-time `#api=<origin>`
  pairing fragment.
- **Local-bundle deployment mode** — `mobile/capacitor.config.ts` now supports
  `LSAT_LOCAL_BUNDLE=1` (the PWA is bundled _into_ the app, so the shell loads with no
  network) in addition to the remote WebView mode; both are offline-review capable.
  See [`mobile/README.md`](../mobile/README.md) → "Offline review & reconnect sync".

**Hardening applied since the first pass** (from a 227-agent improvement sweep + a
95-agent adversarial verification sweep, each change re-tested):

- **Duplicate-event bug fixed (client)** — `flushQueue` is now serialized with an
  in-flight lock and dequeues a row only AFTER the server acks it, so a reconnect
  radio-flap can't re-POST the queue and double-log append-only events.
- **At-least-once replay closed (server + client)** — a lost ack (the radio dropping
  during the response, after the event committed) would make the client re-POST a
  submission the server already recorded → a duplicate event. The client now stamps a
  stable `_idempotency` id **before the online attempt** (not just when queuing), so a
  committed-but-lost-ack retry carries the SAME id it originally sent; `submit_answer` /
  `submit_section_attempt` record `id → result` in a bounded config ring
  (`lsat.events.idempotent_lookup`) and return the stored result on a replayed id
  **without appending again** — so the "one `PerformanceEvent` per submission"
  invariant holds even under an unreliable phone radio. (The stamp-before-online-post
  gap was itself caught by the adversarial verification pass and fixed + regression
  tested.) Proven by `qt/tests/test_lsat_idempotency.py` (7 server cases: ring
  FIFO/eviction, first-result-wins, empty-key inert, both replay paths short-circuiting
  before any re-processing) and the `client.offline.test.ts` "lost-ack keeps a stable
  idempotency id" case.
- **Transient-vs-permanent replay** — a 5xx/408/429/auth failure on reconnect now
  RETAINS the queued graded work (retry) and only drops a permanent 4xx, so a server
  hiccup can't silently discard answers.
- **No more mid-section data loss** — `submitSectionAttempt` (minutes of work) now goes
  through the durable queue with a "saved offline" runner state, and the error card's
  "Try again" re-POSTs the SAME trajectory rather than fetching a fresh section.
- **No false "saved offline"** — a storage-quota / private-mode failure surfaces instead
  of reporting a queued answer that was never persisted.
- **`load()` guard** — a double-tap can no longer drop a prefetched offline item.
- **Parity guard un-blinded** — the desktop⇄Android endpoint-parity test
  (`test_lsat_parity.py`) previously matched only `post(...)` calls and was blind to the
  `postDurable(...)` wrapper, so it falsely saw `lsatSubmitAnswer` /
  `lsatSubmitSectionAttempt` as uncalled; the scanner now recognizes any `post*(...)`
  helper, restoring the drift guarantee for the two offline-queued endpoints.
- **Service worker added** — `lsat/server` serves a root-scoped `/service-worker.js`
  (registered by `pwa.ts`); the e2e asserts it's served + registers + controls the page.
- **Eval gate-teeth** — committed negative controls now prove the calibration,
  score_map, and performance gates can fail (self-asserting, in `docs/eval/`).

**Second hardening pass** (mined from a 556-agent find→verify sweep that the org spend
limit cut short mid-run — 105 finders completed, their 154 findings triaged + verified
by hand; each fix below re-tested):

- **Server-error body no longer counts as "synced"** — both transports return a
  server-side grading exception as HTTP 200 + `{"error":…}` (pycmd parity). `post()`
  now throws (synthetic 500) on such a body, so the offline replay can't drop an
  un-logged submission from the durable queue as a false success (`client.ts`).
- **Transient online failures are queued, not lost** — `postDurable` now queues on any
  transient failure (5xx/408/429/auth/connectivity), not just a `TypeError`; a 503 on a
  graded submit is saved durably instead of thrown away. Safe against append-only: the
  id is stamped before the online attempt, so the queued replay dedups.
  `postDurable` and `doFlush` now share one `isTransientError` classifier so they can't
  drift into a keep-vs-drop asymmetry.
- **Offline unit suite now 13 cases** — added: lost-ack keeps a stable idempotency id;
  permanent-4xx surfaced-not-queued; transient-5xx queued; 200+error-body queued;
  `doFlush` drops a poison 4xx but keeps transient (FIFO); server-error-body kept on
  replay; and a **concurrent-flush lock** test (two overlapping flushes POST the row
  exactly once — the append-only guard, previously untested).
- **The e2e now has teeth** — the reconnect step asserts the **durable queue actually
  drained to 0** (a real sync), not merely that the `navigator.onLine`-bound banner
  cleared; a broken flush (drop or double-POST) now fails the test.
- **The demo now proves exactly-once** — `sync/offline_demo.py` asserts the no-leak
  invariant on the prefetch payload and adds a **lost-ack replay pass** (re-POST the
  same `_idempotency`-stamped submissions) asserting the event count does **not** grow.

**Confirmed-but-deferred (eval gate-teeth, needs the adversarial-validation loop the
spend limit cut short — documented so a change can't silently weaken a gate):**

- `eval/choke_validity.py` — the gate (CI coverage + low false-positive + beats-naive)
  has **no true-positive/power arm**, so a degenerate never-flagging estimator would
  pass vacuously. Fix: add a power arm (ground-truth penalty ≈1.5–2.0, n above
  `MIN_CONFIDENT_FLAG_ITEMS`, require the paired estimator to flag in a high fraction)
  and AND it into the gate — a strengthening, but it must be calibrated against
  `make eval` across seeds to avoid a flaky false-fail.
- `eval/growth.py` (mix-drift control falls below `MIN_PER_BAND` → abstains, never
  exercises the pooled-delta path) and `eval/worked_example.py` (entailment cross-check
  branch is effectively unsatisfiable) show the same "control doesn't exercise the
  guarded path" shape. `eval/performance.py`'s null control was reviewed and is **sound**
  (delta is exactly 0 when the difficulty signal is removed — the cleanest teeth).

**Honest scope:** the offline queue/prefetch/sync logic is proven three ways — a real
browser **video** (`playwright.offline.config.ts`), an end-to-end **server transcript**
(`make sync-demo`), and **unit tests** (`just test-ts`). The **guaranteed** cold-offline
shell is the **local-bundle** deployment (the PWA ships inside the APK); the service
worker additionally caches the shell for the remote deployment as it is used. Producing
the signed `.apk`/`.aab` + a device screen-capture is the one manual Android-Studio step.

## Verify each claim

| Claim                               | Command                                                        | Expected                                                       |
| ----------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------- |
| Eval runs + all hard gates pass     | `make eval`                                                    | `GATE OK -- 0 hard gate(s) failed`                             |
| Baseline is an honest negative      | read `docs/eval/README.md`                                     | CI `[0.0, 0.0222]` includes 0                                  |
| No train/held-out leakage           | `make eval` (leakage gate)                                     | `0 leak(s) in 40x10 pairs; PASS`                               |
| Offline review + reconnect (video)  | open `docs/offline-sync-recording.webm`                        | offline banner → "Saved offline" → banner clears on reconnect  |
| Offline review + reconnect (e2e)    | `playwright test --config playwright.offline.config.ts`        | `2 passed`; reconnect drains the durable queue to 0 (asserted) |
| Offline review + reconnect (server) | `make sync-demo`                                               | `DEMO OK: … synced 3 -> 3; duplicate replay added 0 (deduped)` |
| Offline queue logic (unit)          | `just test-ts`                                                 | `client.offline.test.ts` green (13 cases)                      |
| Replay can't double-log an event    | `just test-py` (or `pytest qt/tests/test_lsat_idempotency.py`) | `test_lsat_idempotency.py` green (7 cases)                     |
| Desktop⇄Android endpoint parity     | `just test-py` (or `just check`)                               | `test_lsat_parity.py` green                                    |
| Types/lint clean                    | `just lint`                                                    | `Build succeeded`                                              |
