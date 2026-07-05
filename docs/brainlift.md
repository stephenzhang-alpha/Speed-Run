# Brainlift — Anki for LSAT

A record of the thinking behind the build: the point of view, the non-obvious
decisions, the sources, and what I'd still change. (Fill in the personal
narration where marked `>> you:`.)

## Spiky POVs (opinionated stances that shaped the build)

1. **A single "readiness score" is dishonest; a bridge of graded steps is not.**
   The LSAT is scored by equating with a published ~±3 band, so any tighter
   number is a lie by construction. We ship three scores, each with a range, each
   able to **abstain**, and we grade the _steps of the bridge_ (calibration,
   held-out accuracy, score-mapping) rather than a fabricated final number.

2. **The real change belongs in the engine, not the skin.** A Python/Qt reskin
   wouldn't reach AnkiDroid and would drift from the scheduler's own FSRS math.
   The points-at-stake queue is a **Rust** RPC, so it's fast over 50k cards,
   reuses the exact retrievability calculation, and ships to both platforms from
   one type-safe protobuf contract.

3. **The generator is never trusted; the checker is the gate.** LLM output is
   guilty until proven correct: every card must cite a verbatim source span
   (checked programmatically), an independent judge re-derives the verdict, and
   the checker itself is validated on a gold set for false-pass rate before we
   trust it. A wrong card is worse than no card.

4. **Correctness under conflict comes from data shape, not cleverness.** Graded
   responses are an append-only, id-keyed event log (set-union merge → no
   double-counting), and mutable snapshots use last-writer-wins by a Hybrid
   Logical Clock (not wall-clock), so a wrong device clock can't win.

5. **"It feels better" scores nothing; reproducible numbers do.** One command
   (`make eval` / `make bench` / `make ablation`) reproduces every gate, latency
   percentile, and the 3-arm ablation with ranges — and the report says what
   didn't work.

## Key decisions & trade-offs

| Decision                 | Chose                                                | Why / trade-off                                                                                                              |
| ------------------------ | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Points-at-stake location | Rust backend RPC (read-only)                         | speed on 50k + FSRS reuse + ships to AnkiDroid; deliberately did **not** touch the shared `QueueBuilder` (keeps rebase easy) |
| Performance model        | Rasch-style logistic (ability as coef-1 offset)      | can't invert on sparse data; interpretable + calibratable; vs. a full multi-feature logistic that was unstable               |
| Score → 120–180          | Monte-Carlo + documented equating table, range ≥ ±3  | honest about equating; no fake precision                                                                                     |
| device_id                | local sidecar, **not** synced                        | a synced id is copied to every device on download → HLC collisions; caught by the sync validation                            |
| LLM / embedder           | pluggable interface + deterministic offline stand-in | reproducible + offline eval + graceful degradation; real Claude/embedder plug in unchanged                                   |
| Eval data                | seeded synthetic, clearly labeled                    | no real students yet; proves the metric + gate mechanics, not field performance                                              |

## Bugs the process caught (evidence > assertion)

- Memory % could exceed 100% on corrupt FSRS stability → clamp recall to [0,1].
- Performance ability weight inverted on sparse data → make ability a fixed
  offset; k-fold (not per-event) calibration to avoid a leakage artifact.
- Readiness range fell below ±3 near 120/180 → shift the window inward.
- `device_id` in synced config collided across devices → local sidecar (found by
  `sync/validate.py`).
- AI eval non-determinism (verdict tally from a `set`) → fixed verdict order.

**Round-2 improvement pass (caught by the multi-agent audit + adversarial
self-review; see `docs/improvements-log.md`):**

- The B3 ablation was **not equal study time** — the `full` arm got ~1.6 extra
  ability-building events, so it reported an effect even with the feature
  neutralized → fixed to an identical fixed error-review budget (now ties at 0
  when inert).
- The leakage "embedding cosine" was a **token-exact tf-idf** that collapses on
  reworded near-copies (the exact LSAT risk) → added a character-n-gram shingle
  detector + a self-test that plants a reworded copy.
- The PWA "bearer token" was **never enforced** in LAN mode (the whole backend was
  open on the LAN) → per-endpoint token guard.
- Feature 4's phase-mode was **never set** (no caller), so the Blind-Review Gap
  Map / Choke Index were dark → wired a desktop menu + mobile toggle.
- The #22 HLC-baseline reconcile ran a **full log scan on every answer** (O(N²)
  per session) → memoized to O(1) amortized (append latency now flat).
- `ruff --fix` silently **re-broke** a deliberate import order (`sync/validate.py`
  circular import) → pinned with `# isort: off/on` (caught by re-running the
  validator).
- The paired Choke-Index flagged "confident" at n=5 where the bootstrap CI
  **under-covers** (~0.82) → only flag at n≥10, and the eval now validates at that
  operating floor.
- The exam-schedule eval simulated a **metric-optimizing greedy**, not the shipped
  `DR − projected_R` heuristic → rewired to the real ranking.

## Sources & prior art

- Anki (Ankitects) — FSRS scheduler, sync protocol, Rust/Python/Qt/TS layering.
- FSRS (Free Spaced Repetition Scheduler) — retrievability model we read, not
  reinvent.
- Cognitive science of **interleaving / desirable difficulties** (discrimination
  and transfer) — motivates the interleaving option + ablation.
- Hybrid Logical Clocks (Kulkarni et al.) — the conflict-resolution primitive.
- Calibration metrics — Brier score, log loss, ECE, reliability diagrams.
- Okapi **BM25** — the retrieval baseline the embedding method must beat.

## What I'd do next / still doesn't work

- Replace seeded synthetic eval data with **real graded responses** and re-run
  every gate; the current numbers demonstrate mechanics, not field results.
- Optimize the two scaling hot-spots from `make bench` (points-at-stake ~230 ms,
  dashboard build ~650 ms on 50k) — a Rust path for the dashboard fold + cached
  coverage.
- Wire the points-at-stake queue into the **default** reviewer order (needs the
  shared `QueueBuilder`) and build the **AnkiDroid** companion.
- Plug a real semantic embedder so the retrieval win over BM25 is decisive, and a
  real Claude client for generation/checking.

`>> you:` add a paragraph on what you personally learned building on a large,
multi-language codebase, and where your intuition was wrong.
