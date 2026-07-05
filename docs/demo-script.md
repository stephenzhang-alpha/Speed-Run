# Demo video — shot-by-shot script

Target length **~4–5 minutes**. (I can't record video from here; this is a
storyboard you record. Timings are approximate.) Record at 1080p+, terminal font
large enough to read. Everything below is runnable from this repo.

Pre-roll setup (off-camera): `export BUILD_ROOT=/Users/stephenzhang/.anki-lsat-build`.

---

### 0:00–0:20 — Hook / what it is

- **On screen:** the `README-lsat.md` title.
- **Say:** "Anki for LSAT — built directly on Anki's codebase. The LSAT is a
  skills test, so instead of one fake score, we ship three honestly-bounded
  scores, a real change to Anki's Rust engine, and an eval that runs before any
  student sees a generated card."

### 0:20–1:05 — The Rust engine change (the required real change)

- **Do:** open `rslib/src/scheduler/points_at_stake.rs`; scroll the scoring
  comment (`mastery = 0.5·recall + 0.5·perf_mastery`, `points = weight·(1−mastery)`).
- **Do:** run the Rust tests: `cargo test -p anki points_at_stake` (or show the
  green test names).
- **Say:** "A read-only backend RPC that orders due cards by exam-weight ×
  weakness. It's in Rust because it's a hot path over 50k cards and reuses the
  engine's FSRS math — and because the backend is shared, it ships to AnkiDroid
  too. It's a pure query: no writes, nothing to undo, can't corrupt scheduling."

### 1:05–1:55 — The desktop app: dashboard + honesty contract

- **Do:** `./run`; open **Tools → LSAT Dashboard** (Ctrl+Shift+L).
- **Point at:** Memory (per-topic % with a range), Performance and Readiness
  **abstaining** — "Not enough evidence yet," with exactly what's missing and the
  single best next thing to study.
- **Say:** "The readiness widget literally cannot render a number until 150
  graded items, 60% LR coverage, 40 timed items, and held-out calibration under
  0.05 — the give-up rule. No fabricated scores."

### 1:55–2:40 — Graded practice → the loop

- **Do:** review an **LSAT Item** card; click a multiple-choice answer; show the
  inline correct/incorrect highlight.
- **Say:** "Answering posts the choice to Python, which grades it against the
  authoritative answer, records the latency, and appends an immutable
  PerformanceEvent — an append-only, id-keyed event log that folds into per-topic
  mastery."

### 2:40–3:15 — "How you get questions wrong" (the differentiator + round-2 features)

- **Do:** on a **miss**, show the **Elaborated Contrast Card** — the two-column
  "why the credited answer wins" vs "why the (X) you picked is a trap + the
  minimal edit that would make it right" (deterministic, works with AI off).
- **Do:** flip **Tools → LSAT Study Mode** to _Blind Review_, re-answer an item
  untimed; open the dashboard's insight grid.
- **Point at:** the **Paired Choke Index** CI number-line (a _confident_ pacing
  gap only when the 95% CI clears zero), the **Gap Map** timed×untimed 2×2, the
  trap **fingerprint**, the calibration reliability diagram, and the **Fatigue
  Curve** (accuracy vs time-on-task). Set **Tools → Set LSAT Exam Date…** to show
  the **exam runway** + consolidation.
- **Say:** "We capture _how_ you got it wrong — the distractor you picked, your
  confidence, timed vs untimed — and turn it into a measured study plan. Every
  panel abstains until it has the evidence, and every claimed effect ships as an
  equal-study-time `eval/` arm with a bootstrap CI — honest single-digit gains,
  never two sigma."

### 3:15–3:20 — Round-3 winners (drills + honest progress)

- **Do:** on the phone, open the **Logic** tab → **Validity**: read a
  quantifier argument and tap _must / cannot / could_; then **Negation**: pick the
  exact negation (show that ¬"most" is "at most half," not "most … not").
- **Point at:** back on the dashboard, the **"Your progress"** section — a
  per-skill _self-referential_ up/down delta that only appears when its CI clears
  zero (never a rank or a fake readiness number) — and the **Rush-Error** and
  **Time-Leak** tiles.
- **Say:** "The quantifier drill's answer key is _proven_, not hand-typed — a Venn
  model-checker verifies every verdict in the test suite, so it can't teach a
  wrong rule. Progress is your own accuracy over time, CI-gated; rush and time-leak
  are diagnostics measured against your _own_ baseline. All four are round-3
  debate winners, each behind an `eval/` arm."

### 3:15–3:20 — Round-4 winners (test-day execution + precision drills)

- **Do:** from the Study tab tap **Start a timed section** → answer a few items
  under the LSAT-pace clock, _change_ one answer, submit; show the **First-Instinct
  Ledger** result.
- **Point at:** the ledger's _your own_ wrong→right vs right→wrong tally with a CI
  ("not enough evidence yet" if thin) — and, in the Logic tab, the **Stems**
  (EXCEPT/LEAST) and **Nec/Suf** drills.
- **Say:** "The section runner never reveals correctness mid-section — it sends
  your raw choices and the _server_ grades — so the ledger tells you whether
  changing answers helps _you_, refusing the folk 'never change' rule and the
  population base rate. The Nec/Suf drill's four-cell key is derived by that same
  proven model-checker. Rank-1 and two more round-4 winners, each behind an
  `eval/` arm — the section-runner's is a hard gate."

### 3:20–3:50 — Sync + conflict rule (7b)

- **Do:** run `out/pyenv/bin/python sync/validate.py`; show the six green rows.
- **Say:** "Two-way sync on a self-hosted server: 10 reviews on each of two
  devices → all 20 land once. Same card on both → both history rows preserved,
  one documented winner. And a device with a 10-day-stale clock can't win,
  because our mutable-record rule is last-writer-wins by a Hybrid Logical Clock,
  not wall time." (Show the verbatim rule in `sync/README.md`.)

### 3:20–4:00 — AI pipeline + the eval gate

- **Do:** `make eval`; show gates PASS + `out/eval/report.md` (reliability
  diagram, "what didn't work").
- **Say:** "The independent checker is the gate — it's validated on a 50-pair
  gold set for false-pass rate before we trust it. Any leaked test item fails the
  build. `make eval` exits non-zero on any gate fail, so generated cards and the
  readiness number are enabled only when it passes."

### 4:00–4:40 — Scale + robustness

- **Do:** `make bench`; show p50/p95/worst on the 50k deck, **20× crash test → 0
  corruption**, and the memory ceilings.
- **Do (optional):** `make ablation`; show the 3-arm result with ranges.
- **Say:** "50,000 cards: interactive paths stay fast; the crash test kills a
  writer mid-write twenty times and reopens with zero corruption; and the 3-arm
  ablation reports the interleaving effect with a bootstrap range at equal study
  time."

### 4:40–5:00 — Close

- **Say:** "Everything is reproducible with one command, licensed AGPL with full
  credit to Ankitects, and honest about what it doesn't yet know."

---

## Capture checklist

- [ ] Terminal font ≥ 16pt; light-on-dark for readability.
- [ ] `BUILD_ROOT` exported; `make eval` / `make bench` pre-warmed once so the
      recording isn't waiting on first-run downloads.
- [ ] The dashboard opened at least once before recording (webview warm).
- [ ] Mention the synthetic-data caveat for eval/ablation on screen.
