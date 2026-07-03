# DECISION (Round 4) — Anki-for-LSAT: Fourth Design Ruling

**Chair:** neutral synthesis of a fourth four-lens design debate (cognitive
scientist · LSAT coach · engineer · student-advocate), run as a background
workflow over **24 proposals**, revisiting round-3 deferred items for shippability
and exploring fresh under-served ground (comparative reading, necessary/sufficient
discrimination, elimination discipline, spacing science, diction primitives,
section-level metacognition, notation/WM-load). Round-1..3 shipped features were
excluded from the proposal space.

Same honesty discipline: a learning *claim* ships only behind a measured `eval/`
arm at **equal study time** with a bootstrap CI excluding 0; diagnostics make no
learning claim; grading fails **closed**; nothing fabricates a readiness/percentile
/σ number.

## Winners (rank order)

### 1. Timed Section Runner + First-Instinct Ledger — #17 (Effort L) — SHIPPED
Top score (8.25, unanimous). A timed mini-section surface that captures the
per-question trajectory (dwell, each answer change from→to, flags,
reached/unreached) and reports the learner's OWN net wrong→right vs right→wrong
answer-change tally **with a CI**, refusing the always/never-change dogma. It's a
multiplier (the natural PT-practice surface; feeds pacing/choke/rush/time-leak real
section trajectories).
- **Shipped:** `lsat/answer_change.py` (the CI-gated ledger, 7/7) ·
  `eval/answer_change.py` (**HARD gate**: 50/50 false-direction 0.050 ≤ 0.06,
  planted-2:1 detection 0.863 ≥ 0.80 → ledger ON) · `lsat/section_runner.py` + a new
  append-only `LSAT SectionAttempt` notetype (cards suspended, HLC-synced, 7/7) ·
  a **no-leak** design (client sends raw choices, server grades) with a batch
  `section_items` fetch (`next_item` can't advance without a submit) · the
  `ts/routes/lsat-section-runner/` route (35-min-pace clock, palette, answer-change
  capture) + a "Start a timed section" mobile CTA + the First-Instinct Ledger
  dashboard tile. 17 endpoints; SERVER_OK; svelte-check 1300 files 0/0.

### 2. Stem-Polarity Parser & EXCEPT/LEAST Micro-Drill — #13 (Effort S) — SHIPPED
A deterministic lexicon+regex classifier of stem polarity (direct / EXCEPT / LEAST
/ negated) seeded from the taxonomy `stem_cues`, **fail-closed** on ambiguity —
zero external/AI data, smallest harm surface. Attacks the highest-frequency
*careless* error (reverting to the prepotent task on an inverted stem).
Automatization makes the correct attentional set resource-independent, so it is
*more* robust at the fatigue moment the lapse strikes.
- **Shipped:** `lsat/stem_polarity.py` (21/21, fail-closed) · `eval/stem_polarity.py`
  (drill−generic **+0.114**, CI +0.107..+0.122; speeded **+0.148**) · four
  token-guarded endpoints · mobile Logic-tab "Stems" segment.

### 3. Necessary/Sufficient Four-Cell Discrimination Drill — #5 (Effort M) — SHIPPED
Sort a candidate into necessary-only / sufficient-only / both / neither. The cell
is **derived, not authored** — it reuses the proven `lsat.quantifier` Venn
model-checker as an oracle (sufficient ⟺ P+[A] entails C; necessary ⟺ the LSAT
negation test: P+[¬A] makes C impossible), with a gap-guard requiring a genuine
argument gap. Cannot mis-teach: every cell is proven + cross-checked in the
self-test; grading fails closed on a degenerate/out-of-fragment item.
- **Shipped:** `lsat/assumption_discrimination.py` (22/22, cells model-checker-proven)
  · `eval/assumption_discrimination.py` (drill−generic **+0.102**, CI +0.095..+0.110,
  4-way sort) · endpoints · mobile Logic-tab segment.

### 4. Faded Flaw Ladder — #19 (Effort L, DEFERRED)
Backward-fade flaw decomposition + name-the-principle. Deferred: it needs ~15
**human-authored** flaw decompositions on a new notetype, AI-drafted steps routed
through the checker + gold-set + human spot-check — the same content-calibration
dependency that keeps RC-Judgment (round 3) off. Ships only when that content
exists and its held-out CI clears. (See the RC-Judgment staging report for the
identical rationale.)

## Also shipped (post-ruling)
- **#22 Conditional-Chain Trainer** — SHIPPED. Fully deterministic: structured
  implications rendered to prose, graded by **exact material entailment**
  (truth-table, complete) with reachability kept as a proven-*sound* explanation
  aid. `lsat/conditional_chain.py` (21/21) · `eval/conditional_chain.py`
  (drill−generic +0.112) · a "Chains" card in the redesigned Logic launcher. Fills
  the ≥3-arrow gap the single-conditional drill abstains on.

## Also this session — UI/UX
- **Logic-tab "Drill Launcher" redesign** (judge-panel workflow winner, 8.8): the
  cramped 5→6-segment control became a scannable grouped picker (CONDITIONALS /
  QUANTIFIERS / QUESTION TACTICS) with recency chips + full a11y. `DrillPicker.svelte`
  + `drillProgress.ts`; scales to more drills without cramping.

## Deferred (revive with conditions)
- **#10 Successive Relearning Track** — strongest mechanism, but reallocates study
  time via an unproven cross-session FSRS cap (more scheduler than Python+web+eval);
  revive opt-in + mechanism-only once its synthetic mechanics gate passes.
- **#7 Structured Elimination Pass**, **#20 Labor-in-Vain Stall Guard** — honest but
  slow/secondary; revive after the drill slate.

## Cut
- **#2 Passage-Relation Axes**, **#3 Shared-Assumption cross-passage** — data
  foundation too thin/subjective for a validity gate (rare item forms, low-reliability
  hand labels).
- **#6 Nec/Suf Confusion-Index**, **#12 Relapse Recovery Bout** — overlap shipped
  read-outs / duplicate #5 / #10.

## This session
Shipped **#13**, **#5** (deterministic, content-risk-free) and **#17** (the rank-1
Timed Section Runner + First-Instinct Ledger). Deferred **#19** (needs
human-authored flaw content — same rationale as RC-Judgment). Next candidate:
**#22** conditional-chain (fully deterministic; fills the ≥3-arrow gap the
single-conditional drill abstains on).
