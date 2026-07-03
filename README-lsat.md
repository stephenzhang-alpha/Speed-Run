# Anki for LSAT

**Content is free now — the proven truth about your own test is the scarce good.**
This is the LSAT tool whose AI *can't lie to you*: which points you leak under the
clock (a paired timed-vs-untimed **Blind-Review Delta** with a CI, on your own
answers), which "right" answers were luck (**oracle-verified evil twins**), and
which misses were confident misconceptions (confidence captured *before* the reveal,
feeding a real Rust scheduler queue). Where a decision procedure exists (formal-logic
LR) every AI answer is *proven*, not guessed — an AI-drafted step that doesn't verify
is deleted before you see it; everywhere else the AI is held to grounded-gold +
verbatim citation, and where we can't verify, we **abstain**. That verification
infrastructure — not the code — is the thing an afternoon with an LLM can't
reproduce (ask it to build the checker and it hands you one that returns `PASS`).

Built **directly on the Anki codebase**: spaced repetition for reusable LSAT
judgments, three honestly-bounded scores (Memory / Performance / Readiness), the
"points-at-stake" queue in Anki's Rust engine, oracle-verified worked examples +
evil twins, an AI card pipeline with an independent checker, two-way sync with a
written-down conflict rule, and a reproducible evaluation + benchmark harness (every
learning claim behind an equal-study-time bootstrap CI; the pinned model id recorded
and re-gated on any change).

This is a fork/extension of Anki. See **License & credit** below.

---

## Repository map

All LSAT work is **additive** and lives in clearly separated locations — upstream
Anki files are only lightly touched (LSAT hooks). Where to look:

- **`lsat/`** — the core LSAT engine (Python). `taxonomy.py` is the single source of
  truth (qtypes, flaws, exam weights, honesty gates); `events.py` is the per-answer
  annotation store; `dashboard_data.py` builds the dashboard payload; `selection.py`
  is the ZPD queue; `seed.py`/`deck_content.py` are the starter decks.
  - **Oracle-verified logic** (proofs, not opinions): `conditional.py`,
    `conditional_chain.py`, `quantifier.py`, `assumption_discrimination.py`,
    `worked_example.py`, `evil_twin.py`.
  - **Diagnostics**: `blind_review.py`, `answer_change.py`, `misconceptions.py`,
    `error_patterns.py`, plus `models/` (`memory`, `performance`, `readiness`,
    `calibration`, `fluency`).
  - **`lsat/ai/`** — the honesty-safe AI subsystem: independent `checker.py`,
    `generator.py`, `client.py` (offline + Claude), `gold_set.py`, fail-closed
    `misconception.py`.
  - **`lsat/server/`** — the standalone Flask backend that serves the mobile PWA.
  - **`lsat/api.py`** — framework-agnostic endpoint handlers shared by desktop + server.
- **`eval/`** — the reproducible evaluation harness (`make eval` → `eval/run.py`):
  held-out hard gates + equal-study-time bootstrap-CI report arms; `config.py` holds
  the pre-declared thresholds.
- **`ts/lib/lsat/`** — the Svelte/TS UI components + `theme.scss` design tokens;
  **`ts/routes/lsat-dashboard | lsat-mobile | lsat-section-runner`** — the three pages.
- **`qt/aqt/lsat_*.py`** — the desktop (PyQt) integration (`lsat_dashboard`,
  `lsat_performance`, `lsat_mobile`, `lsat_web`), plus LSAT hooks in `main.py`,
  `__init__.py`, `mediasrv.py`.
- **`mobile/`** — the **Android** app: a thin Capacitor WebView that loads the
  `lsat-mobile` PWA from `lsat/server` (no bundled assets — the served PWA *is* the app).
- **`rslib/src/scheduler/points_at_stake.rs`** (+ `mod.rs`, `service/mod.rs`,
  `proto/anki/scheduler.proto`) — the one Rust engine change: a read-only
  points-at-stake queue RPC, shared by desktop + AnkiDroid.
- **`docs/`** — product + engineering docs (`Anki-for-LSAT-PRD.md`,
  `Speedrun_AI_Features.md`, `Speedrun_Research_Support.md`, `ai-card-pipeline.md`,
  `models.md`, `demo-script.md`, `improvements-log.md` — the changelog — and
  `research/`). **`research/`** — the design-debate corpus + binding
  `debate/DECISION.md`. **`SKILL-*.md`** — Agent-Skill how-tos (build / eval /
  protobuf / sync). **`lsat-taxonomy.yaml`** — the taxonomy. **`Makefile`** —
  `eval` / `ablation` / `bench` / `taxonomy` targets.

---

## License & credit

- **Anki** is © Ankitects Pty Ltd and contributors, licensed **GNU AGPL v3 or
  later**. This project is a derivative work and is likewise licensed **AGPL
  v3+**; every source file we add carries the AGPL header.
- Full credit to **Ankitects** (Damien Elmes and contributors) for Anki, its
  FSRS scheduler, the sync protocol, and the multi-layer Rust/Python/Qt/TS
  architecture we build on. Upstream: <https://github.com/ankitects/anki>.
- The LSAT® is a registered trademark of LSAC. This project is **not** affiliated
  with or endorsed by LSAC, and ships **no** LSAC/PrepTest content — all cards,
  items, and the gold set are original or licensed (PRD §16).

## The exam

The LSAT is a **skills test**, not a facts test: Logical Reasoning (LR), Reading
Comprehension (RC), scored **120–180** via per-form equating (LSAC reports a
~±3-point band). Our taxonomy (`lsat-taxonomy.yaml`) models the scored question
types, a flaw catalog, cross-cutting skills, exam weights, the coverage basis,
and the give-up thresholds — it is the single source of truth for weights and
gates.

## Build & run

This checkout lives at a path containing a space, so build outputs are
redirected to a space-free directory via `BUILD_ROOT` (the `out` symlink points
there):

```bash
export BUILD_ROOT=/Users/stephenzhang/.anki-lsat-build   # space-free build dir
./run                # build pylib + qt and launch the desktop app (== `just run`)
```

`./run` sets `ANKI_API_PORT=40000`, builds via `./ninja pylib qt`, and launches
Anki. Convenience targets for the LSAT deliverables (`make help`):

```bash
make eval        # reproducible held-out eval + gates (python -m eval.run)
make ablation    # pre-registered B3 misconception-queue ablation (python -m eval.ablation)
make bench       # 50k-deck benchmark + crash test  (python -m lsat.bench)
make taxonomy    # print a taxonomy summary
```

`PYTHON` defaults to `out/pyenv/bin/python` (has `pyyaml`); override with any
interpreter that has `pyyaml`.

## The required Rust engine change

`GetPointsAtStakeQueue` is a **new read-only backend RPC** in Anki's Rust engine
that orders due cards by **topic exam weight × student weakness**
(`mastery = 0.5·recall + 0.5·perf_mastery`; `points = weight·(1−mastery)`).
Because the Rust backend is shared, it ships identically to desktop and
AnkiDroid. It is a pure query (no writes, no undo entry, cannot corrupt
scheduling state), with 3 Rust unit tests + 1 Python test.
**Full note:** [`lsat/docs/points-at-stake-rust-change.md`](lsat/docs/points-at-stake-rust-change.md)
(includes why-Rust, no-corruption argument, tests, and a files-touched /
merge-difficulty assessment — merge-difficulty **LOW**, additive only).

## Models

Three local, offline, calibratable score models (no LLM dependency), each shown
**with a range** and abstaining under the honesty contract:

- **Memory** — per-topic recall % from FSRS, with a Wilson interval + give-up.
- **Performance** — logistic / lightweight-IRT P(correct on a new item), per
  topic ± interval.
- **Readiness** — Monte-Carlo 120–180 projection with a ≥±3 range, gated by the
  give-up rule and the full honesty contract.

Plus the AI card pipeline (generator + independent checker), retrieval
(BM25 vs embedding), and the interleaving study option.
**Details:** [`docs/models.md`](docs/models.md).

## What makes it unique (novel, evidence-based features)

Plain Anki (and every LSAT competitor) records only **whether** you got a
question right. We capture **how** you got it wrong — and turn that into a
measured study plan. These features were chosen by a documented, cited,
multi-agent research debate: see **[`research/`](research/README.md)** and the
binding **[`research/debate/DECISION.md`](research/debate/DECISION.md)**.

**Keystone — the per-answer annotation store.** Every graded answer now records
the **distractor you picked** (`chosen`), a one-tap **confidence**
(`sure`/`likely`/`guess`), and the **phase** (`timed`/`blind`/`relaxed`). The
chosen letter was already computed in the reviewer and thrown away; now it feeds
everything. (`lsat/events.py`, `lsat/notetypes.py`, `qt/aqt/lsat_performance.py`.)

### The five headline features

Many mechanisms live under the hood, but in the app they surface as **five
prominent, demonstrable features** (full spec: [`docs/Speedrun_AI_Features.md`](docs/Speedrun_AI_Features.md)):

1. **Reasoning-Primitive Decks + Identification-First Study** — one-click original
   starter decks (diction / logic / question-type flashcards + graded practice
   items); classify-the-type-then-solve, with an **Elaborated Contrast Card** on a
   miss (why-credited vs why-this-trap + the minimal edit).
2. **The Logic Drill Suite** — a mobile Logic tab of instantly-graded micro-drills
   (conditional translation & chains, quantifier validity & negation, stem polarity,
   necessary-vs-sufficient) whose answer keys are *proven* by a model-checker, not
   hand-typed.
3. **Confidence & Misconception Engine** — capture confidence *before* the reveal,
   surface the confident-wrong "danger zone," and **schedule it first** via the
   points-at-stake **Rust** review queue.
4. **Timed Section Runner + Execution Diagnostics** — realistic timed practice → your
   own answer-change ledger, plus the Gap Map / Choke / Rush / Time-leak / Stamina
   read-outs that appear as you log timed + blind-review answers.
5. **Three Honest Scores + Readiness** — Memory / Performance / Readiness, each
   ranged and abstaining, with a give-up rule and no fabricated readiness number.

Load everything in one click via **Tools ▸ LSAT ▸ Load Starter Decks**. The tables
below are the detailed build record — grouped by the design-debate round that
produced each mechanism — and every mechanism folds under one of the five headliners
above.

| Feature | What it does | Evidence | Code |
|---|---|---|---|
| **ZPD Daily Engine (~85%)** | Serves each topic at the difficulty where people learn fastest, not the hardest card in the weakest topic | Metcalfe & Kornell 2005; Wilson 2019 | `lsat/selection.py` |
| **Distractor-Reasoning Engine** | Maps the trap you actually pick into a personal fingerprint ("extreme-language owns 38% of your Strengthen misses"), a one-tap "which trap got you?", and boosts trap-prone skills in the queue | competitive-MC retrieval g≈0.70 (Adesope 2017); self-explanation g=0.55 (Bisra 2018) | `lsat/error_patterns.py` |
| **Calibration + Hypercorrection** | A human reliability curve (are you as right as you feel?) + prioritizes confident-but-wrong misses on a spaced schedule | Metcalfe 2017; Butler/Fazio/Marsh 2011 | `lsat/models/calibration.py` |
| **Blind-Review "Gap Map"** | A timed→untimed second pass that splits "don't know it" (knowledge) from "ran out of time" (pacing), and stops crediting lucky timed guesses as mastery | Kruger & Dunning 1999; Beilock 2004 | `lsat/blind_review.py`, `lsat/pacing.py` |
| **Fluency Gates** | Retire a skill only when it's accurate *and* fast — the automaticity that cures choking | Beilock 2004; Mettler 2016 | `lsat/models/fluency.py` |
| **Transfer Meter** | Refuses to call a schema "learned" until you're right on *new surface topics* | Chi 1981; Barnett & Ceci 2002 | `eval/transfer.py` |

All of these surface on the dashboard under **"How you get questions wrong"** and
are honestly bounded — each abstains until it has enough evidence, and every
claimed effect ships as a measured `eval/` arm. **The honest headline:**
single-digit-point gains on held-out exam-style items at equal study time —
never "2 sigma."

**Round-2 features** (a second cited, multi-agent debate —
[`research/debate/DECISION-round2.md`](research/debate/DECISION-round2.md) — over
29 proposals; the winners below each ship with a measured `eval/` arm):

| Feature | What it does | Code / eval |
|---|---|---|
| **Paired Choke Index** | Replaces the unpaired timed−untimed gap (an item-difficulty confound) with a **within-item paired estimator + bootstrap 95% CI**; flags a choke only when the CI excludes 0, else abstains | `lsat/pacing.py` · `eval/choke_validity.py` |
| **Elaborated Contrast Card** | On a miss, a deterministic (AI-off, gold-set-gated) two-column **why-credited / why-this-trap + minimal-edit** contrast — upgrades the one-tap why-wrong | `lsat/contrast.py` · `eval/feedback.py` |
| **Exam-Day Retrievability Targeting** | Set a test date; a deadline-aware desired-retention ramp + FSRS exam-day projection surface a **consolidation queue** of cards that would decay below target by test day | `lsat/exam_schedule.py` · `eval/exam_schedule.py` |

New reviewer controls: **Tools ▸ LSAT Study Mode** (Timed / Blind / Relaxed —
feeds the phase-aware Gap Map, Choke Index, and honest-mastery filter) and **Tools
▸ Set LSAT Exam Date…** (feeds the exam runway). The eval harness gained
`choke_validity` (a hard gate) plus report arms `blind_review` (routing validity +
honest-mastery), `feedback`, and `exam_schedule`.

**Round-3 features** (a third cited, multi-agent debate —
[`research/debate/DECISION-round3.md`](research/debate/DECISION-round3.md) — over
21 proposals across 8 under-served areas; each winner ships with a measured
`eval/` arm):

| Feature | What it does | Code / eval |
|---|---|---|
| **Quantifier Reasoning Drill Suite** | Validity (must / cannot / could-be-true over quantifier premises — illicit conversion, undistributed middle, two-`most` overlap) + negation (¬all = *some-not*, ¬most = *at most half*). A bounded **Venn model-checker proves every curated verdict** from first principles in the self-test; grading fails closed | `lsat/quantifier.py` · `eval/quantifier.py` |
| **Mastery-Growth Panel** | The honest alternative to a fabricated readiness number: a **self-referential**, difficulty-matched, **CI-gated** per-skill early-vs-recent accuracy delta (never a rank) — emits improved/slipped only when the CI excludes 0, else abstains | `lsat/growth.py` · `eval/growth.py` (hard gate) |
| **Rush-Error Detector** | Flags a rush pattern only when your **fast** answers (under half your own careful pace) are **significantly more wrong** than your slower ones (CI-gated excess, per-learner baseline) — never a raw fast-and-wrong count | `lsat/pacing.py` · `eval/rush.py` (hard gate) |
| **Time-Leak Diagnostic** | Reclaimable seconds spent under the clock on items you also miss **untimed** (a gap, not a pace problem), reported **with a bootstrap CI**; strictly descriptive, leads with "need a blind pass first" | `lsat/triage.py` · `eval/triage_leak.py` |

The quantifier drills join the mobile **Logic** tab (Translate / Validity /
Negation); growth surfaces as a "Your progress" dashboard section; rush + time-leak
are dashboard insight tiles. The eval harness gained hard gates `growth` and `rush`
plus report arms `quantifier` and `triage_leak`. (Rank-4 **RC Judgment** is deferred
pending human-calibrated stimuli — see `research/debate/DECISION-round3.md`.)

**Round-4 features** (a fourth cited, multi-agent debate —
[`research/debate/DECISION-round4.md`](research/debate/DECISION-round4.md) — over
24 proposals; the three deterministic/diagnostic winners ship, each with a measured
`eval/` arm):

| Feature | What it does | Code / eval |
|---|---|---|
| **Timed Section Runner + First-Instinct Ledger** (rank 1) | A timed mini-section that captures each answer change; the ledger reports *your own* net wrong→right vs right→wrong **with a CI**, refusing the folk "never change" rule and the population base rate. No-leak (server grades); diagnostic-only | `lsat/answer_change.py`, `lsat/section_runner.py` · `eval/answer_change.py` (hard gate) |
| **Stem-Polarity Micro-Drill** | Trains the automatic detection of an inverted stem (direct / EXCEPT / LEAST / negated) — the highest-frequency careless LR error. Deterministic classifier seeded from the taxonomy `stem_cues`, **fails closed** on ambiguity | `lsat/stem_polarity.py` · `eval/stem_polarity.py` |
| **Necessary/Sufficient Discrimination** | Sort a candidate assumption into necessary-only / sufficient-only / both / neither. The cell is **derived by the proven quantifier Venn model-checker** (sufficient = adding it entails the conclusion; necessary = the LSAT negation test), never authored | `lsat/assumption_discrimination.py` · `eval/assumption_discrimination.py` |
| **Conditional-Chain Trainer** | Judge whether a candidate inference **must follow** from a 3+ arrow chain (transitive chaining + contrapositive vs affirming-the-consequent / denying-the-antecedent) — the gap the single-conditional drill abstains on. Graded by **exact material entailment**; reachability kept as a proven-sound explanation | `lsat/conditional_chain.py` · `eval/conditional_chain.py` |

The mobile **Logic** tab was also redesigned (a design judge-panel winner): the
cramped segmented control is now a scannable **Drill Launcher** — cards grouped
Conditionals / Quantifiers / Question-tactics, each with a recency chip and full
keyboard/focus a11y, scaling cleanly as drills are added.

The Section Runner is its own route (with a mobile "Start a timed section" CTA) +
a First-Instinct Ledger dashboard tile; the two drills join the mobile **Logic**
tab. The eval harness gained a hard gate `answer_change` plus report arms
`stem_polarity` (+0.114) and `assumption_discrimination` (+0.102). Rank-4 **Faded
Flaw Ladder** is deferred (needs human-authored content) — see the round-4 decision
+ `docs/research/rc-judgment-staging.md`.

## Two versions: desktop + mobile PWA

The UI ships in two forms that share the same Svelte components
([`ts/lib/lsat/`](ts/lib/lsat)) and the same Python models + grading
([`lsat/grading.py`](lsat/grading.py)):

- **Desktop (MacBook)** — the PyQt app. A redesigned, theme-aware dashboard
  ([`ts/routes/lsat-dashboard/`](ts/routes/lsat-dashboard)) and study card
  ([`lsat/notetypes.py`](lsat/notetypes.py) `_ITEM_QFMT`), built on Anki's design
  tokens so it matches light/dark automatically.
- **Mobile (installable PWA)** — a mobile-first route
  ([`ts/routes/lsat-mobile/`](ts/routes/lsat-mobile)) with a bottom tab bar
  (Study / Progress), served by the desktop app's own `mediasrv` over your LAN.
  It reuses the dashboard components and drives study through HTTP endpoints
  (`lsatNextItem` / `lsatSubmitAnswer` / `lsatSubmitTrap` in
  [`qt/aqt/lsat_web.py`](qt/aqt/lsat_web.py)) that call the *same* `lsat.grading`
  code as the desktop `pycmd` hook -- so a phone answer logs an identical
  `PerformanceEvent`. iOS/Android install via "Add to Home Screen".

**Pair a phone:** launch Anki with `ANKI_API_HOST=0.0.0.0` (bind to the LAN),
then **Tools -> Study on Your Phone (LSAT)** shows a link to open on your phone
(same Wi-Fi). Because a `mediasrv` bound to `0.0.0.0` exposes the API to the
local network, this is **off by default**, the link carries a per-session bearer
token, and the dialog warns to pair only trusted devices on trusted networks.
The offline service worker is a documented follow-up (installability + the app
shell work today via the web manifest).

## Sync conflict rule & give-up rules

**Conflict rule (two layers)** — full note + reproducible validation in
[`sync/README.md`](sync/README.md):

> For mutable derived records, the record with the greater HLC timestamp wins;
> ties are broken by the lexicographically greater `device_id`. Graded responses
> and readiness projections are append-only, id-keyed note logs and are never
> overwritten.

Layer 1 is Anki's native sync (append-only `revlog` → 10+10 reviews all survive;
full-sync fallback on unmergeable divergence). Layer 2 is our custom data: both
the graded-event log **and** the readiness-projection log are append-only
`LSAT PerformanceEvent` / `LSAT Projection` notes, merged by **set union on note
id**, so concurrent multi-device writes all survive (a single synced config list
would config-LWW one device's projections away — defect #20). Ordering uses a
Hybrid Logical Clock whose baseline is reconciled against the append-only log
before each mint, so a sync can't lower it and a wrong clock can't win (defect
#22). Because both logs are append-only, no record currently resolves by
last-writer-wins; the LWW rule lives as the reusable primitive
`lsat.events.resolve_lww` (exercised by the wrong-clock validation) for a future
mutable snapshot. `device_id` is stored per-device (local sidecar), never synced.

**Give-up rules** (no fabricated scores; `lsat-taxonomy.yaml`):

- **Readiness** shows no number until **all** hold: ≥ 150 graded performance
  items, ≥ 60% LR question-type coverage **and** ≥ 1 graded item in each RC type,
  ≥ 40 timed items, held-out calibration **ECE ≤ 0.05**, measured **student
  overconfidence ≤ +0.15** (once the one-tap confidence ratings make it
  measurable -- a student whose "sure" answers outrun their accuracy would make
  any point estimate an overstatement), and the deck covering ≥ 50% of the
  **primitive taxonomy** (diction + logic + qtype; a vocabulary-only deck must
  not read as "ready"). Otherwise it shows "Not enough evidence yet," exactly
  what's missing, and the best next thing to study. The readiness widget cannot
  render a number unless all eight honesty fields are populated.
- **Miscalibration widens the range (D2):** the reported band grows by
  `round(20 x max(0, overconfidence_index))` points per side (e.g. +0.10
  overconfidence -> +2 points each side; constant in `lsat-taxonomy.yaml`
  `readiness_uncertainty`). Underconfidence never narrows it. Calibration is a
  *diagnostic + discount*, never a coaching claim -- app feedback has a weak
  record at actually training calibration (see `docs/Speedrun_Research_Support.md`).
- **Memory** shows a topic only after ≥ 10 reviews for that topic.
- **Misconception re-tests (B3):** every confident-wrong item owes a spaced
  re-test **2 days** out (`lsat/relearning.py`; corrected confident errors
  return unless re-tested -- Butler/Fazio/Marsh 2011, Metcalfe & Miele 2014).

## Evaluation & benchmark

- `make eval` runs a **content-aware split** (+ `manifest.json`), memory
  **calibration** (Brier/log-loss/ECE + reliability diagram; gate ECE ≤ 0.05),
  held-out **performance** vs a memory-only baseline (AUC delta ≥ 0.05), **score
  mapping** (range ≥ ±3), the **paraphrase** gap, a **leakage** gate (any
  near-duplicate fails), the **card check** (three verdict counts + checker
  false-pass ≤ 0.02), and the **retrieval baseline**. It **exits non-zero on any
  gate fail** and writes `out/eval/report.md` (including a "what didn't work"
  section). All step inputs are seeded synthetic (stated in the report).
- `make bench` synthesizes a 50k-card deck and prints **p50 / p95 / worst-case**
  latency, a **20× crash test** (kill-mid-write → reopen → integrity-check → zero
  corruption), and **memory ceilings** (peak RSS + peak Python allocation).
- `make ablation` runs the **pre-registered** 3-arm ablation of the B3
  misconception-priority queue (on / feature-off / plain Anki) at equal study
  time — claim stated before running, result + bootstrap range reported even if
  null — plus the interleaving simulation as a secondary analysis.

## Files touched (the LSAT layer)

**New — `lsat/` (Python models + AI + helpers):** `taxonomy.py`, `notetypes.py`,
`seed.py`, `dashboard_data.py`, `events.py`, `interleaving.py`, `retrieval.py`,
`bench.py`, `models/{memory,performance,readiness,projections}.py`,
`ai/{prompts,client,generator,checker,pipeline,gold_set}.py`,
`docs/points-at-stake-rust-change.md`.

**New — `eval/`:** `config.py`, `metrics.py`, `split.py`, `calibration.py`,
`performance.py`, `score_map.py`, `paraphrase.py`, `leakage.py`, `card_check.py`,
`baselines.py`, `ablation.py`, `run.py`.

**New — `sync/`:** `validate.py`, `README.md`. **New — `qt/aqt/`:**
`lsat_dashboard.py`, `lsat_performance.py`. **New — `ts/routes/lsat-dashboard/`:**
`+page.svelte`, `+page.ts`. **New — `rslib/src/scheduler/`:** `points_at_stake.rs`.
**New — root:** `lsat-taxonomy.yaml`, `Makefile`, this README, `docs/`.

**Edited (additive / low-conflict):** `proto/anki/scheduler.proto`,
`pylib/anki/scheduler/base.py`, `pylib/tests/test_schedv3.py`,
`rslib/src/scheduler/{mod.rs,service/mod.rs}`, `rslib/src/stats/today.rs`,
`qt/aqt/{webview.py,mediasrv.py,__init__.py,main.py}`.

**Round-2 additions (the second debate's winners):** new **`lsat/`**
`contrast.py` (#13), `exam_schedule.py` (#7), `fatigue.py` (#10), `adherence.py`
(#4); new **`eval/`** `choke_validity.py` (#24), `feedback.py` (#13),
`exam_schedule.py` (#7), `fatigue.py` (#10), `adherence.py` (#4), `blind_review.py`
(the missing Feature-4 arm); new **`ts/lib/lsat/`** `ContrastCard.svelte`,
`FatigueCurve.svelte`; new **`research/debate/DECISION-round2.md`** and
**`docs/improvements-log.md`**. Edited (additive): `lsat/pacing.py` (paired Choke
Index), `lsat/selection.py` (exam-day queue boost), `lsat/events.py` (event cache +
honest-mastery fold + HLC reconcile), `lsat/models/memory.py` (single-scan),
`lsat/primitives.py`/`lsat/dashboard_data.py` (per-build caches + new panels),
`lsat/{grading,error_patterns}.py`, `lsat/notetypes.py` (contrast render + full LR
classify chips), the qt reviewer/menu hooks, and the Svelte insight panels
(round-2 UI/UX pass).

**Round-3 additions (the third debate's winners):** new **`lsat/`**
`quantifier.py` (r3 #1), `growth.py` (r3 #2), `triage.py` (r3 #5); new **`eval/`**
`quantifier.py`, `growth.py` (hard gate), `rush.py` (hard gate), `triage_leak.py`;
new **`ts/lib/lsat/`** `QuantifierDrill.svelte`, `MasteryGrowthPanel.svelte`,
`RushErrorsPanel.svelte`, `TimeLeakPanel.svelte`; new
**`research/debate/DECISION-round3.md`**. Edited (additive): `lsat/pacing.py`
(`rush_errors`), `lsat/dashboard_data.py` (growth + rush + time-leak panels),
`lsat/api.py` + `qt/aqt/{lsat_web,mediasrv}.py` + `lsat/server/app.py` (four
token-guarded quantifier endpoints, plus a standalone-server handler guard that
also closed a latent round-2 gap), and the mobile Logic tab + shared
`DashboardView.svelte`. Also hardened `lsat/conditional.py` to be genuinely
fail-closed (an adversarial-review fix).

**Round-4 additions (the fourth debate's winners):** new **`lsat/`**
`stem_polarity.py` (r4 #13), `assumption_discrimination.py` (r4 #5); new **`eval/`**
`stem_polarity.py`, `assumption_discrimination.py`; new **`ts/lib/lsat/`**
`StemPolarityDrill.svelte`, `AssumptionDrill.svelte`; new
**`research/debate/DECISION-round4.md`** and **`docs/research/rc-judgment-staging.md`**
(the deferral report). Edited (additive): four more token-guarded endpoints across
`lsat/api.py` + `qt/aqt/{lsat_web,mediasrv}.py` + `lsat/server/app.py`, and the
mobile Logic tab (segmented control generalized to N segments). A follow-up
adversarial review of the round-3 features fixed a HIGH honesty bug in
`lsat/growth.py` (difficulty-mix false-direction) — details in the improvements log.

**Round-4 rank-1 (#17 Timed Section Runner):** new **`lsat/`** `answer_change.py`,
`section_runner.py`; new **`eval/`** `answer_change.py` (hard gate); a new append-only
**`LSAT SectionAttempt`** notetype in `lsat/notetypes.py`; new **`ts/`**
`routes/lsat-section-runner/` + `lib/lsat/FirstInstinctLedger.svelte`. Edited
(additive): a batch `section_items` + `submit_section_attempt` endpoint across
`lsat/api.py` + the three server layers, the `answer_change` dashboard panel, a
mobile "Start a timed section" CTA, and `mediasrv.is_sveltekit_page` (route
registration). 17 PWA endpoints total; the server keeps its
`set(ENDPOINTS) ⊆ set(_HANDLERS)` import guard.

**Round-4 #22 (Conditional-Chain Trainer) + the Logic-tab redesign:** new
**`lsat/`** `conditional_chain.py`; new **`eval/`** `conditional_chain.py`; new
**`ts/lib/lsat/`** `ChainDrill.svelte`, `DrillPicker.svelte`, `drillProgress.ts`.
Edited (additive): `chain_drill`/`submit_chain` endpoints across the three server
layers (19 PWA endpoints now), and the mobile **Logic** tab rewired from a
segmented control to the grouped Drill Launcher (the six drills mount unchanged).

## Installer & demo

- **Installer build + clean-machine verification checklist:**
  [`docs/installer-verification.md`](docs/installer-verification.md). The final
  "install on a clean machine and launch" step is a manual/CI action.
- **Demo video script (shot-by-shot):** [`docs/demo-script.md`](docs/demo-script.md).
- **Brainlift (learning journey / POV / sources):** [`docs/brainlift.md`](docs/brainlift.md).
