# DECISION (Round 3) — Anki-for-LSAT: Third Design Ruling

**Chair:** neutral synthesis of a third four-lens design debate (cognitive
scientist · LSAT coach · engineer · student-advocate), run as a background
workflow over **21 new proposals** across 8 deliberately under-served areas:
RC drillable judgments, test-day execution, metacognition/planning, schedule
science, diction primitives, error-analysis depth, honest motivation/engagement,
and anxiety/pressure inoculation. All Round-1 and Round-2 shipped features were
explicitly excluded from the proposal space.

Every winner obeys the project honesty discipline: a feature ships a _claim_ only
behind a measured `eval/` arm at **equal study time** with a bootstrap CI that
excludes 0; diagnostics make **no** learning-effect claim; nothing invents a
readiness/percentile/σ number; grading fails **closed**.

## Winners (rank order)

### 1. Quantifier Reasoning Drill Suite (validity + negation) — merged #12 + #13

Field-topping score (8.0 / 7.3, top single-min 8), fatal-flaw-free. Pure
Python + web + eval; **zero** Rust/proto/schema. Drills a reusable _judgment_
(categorical/quantifier inference over abstract terms) so it is not data-blocked.

- **Mechanism:** automaticity of a component operation frees working memory for
  the argument (Sweller & Cooper 1985); higher-order validity/negation judgment
  is the transfer-friendly form (Pan & Rickard 2018).
- **Correctness gate:** one canonical rule table is the single source of truth;
  a bounded Venn-region **model-checker** (≤3 terms → ≤8 regions) runs in
  `_selftest` and _proves_ every table entry (not asserts it). Grading FAILS
  CLOSED outside the verified table; negation self-checks double-negation.
- **Honest claim:** near-transfer only — a time-matched lift in P(correct) on
  **held-out** quantifier judgments with **novel** surface terms, plus speeded
  accuracy at matched median RT. Single-digit accuracy points. Far-transfer arms
  (full quantifier-tagged LR; Necessary-Assumption items) ship OFF until their
  own CI excludes 0. No WM-causal claim, no scaled/percentile/σ claim.

### 2. Mastery-Growth Panel (CI-gated self-referential progress) — #16

Second-highest (7.7 / 7.0); the only motivation/engagement idea that survives the
honesty discipline. Fills the exact gap the discipline forbids (a fabricated
readiness/σ number) with a _truthful, self-referential_ progress signal.

- **Mechanism:** Kluger & DeNisi — ego/rank/comparison feedback is the third of
  feedback interventions that _hurt_; task/process feedback helps. So progress is
  strictly self-referential per-skill mastery (early vs recent window, matched on
  difficulty band + timed phase), never a rank/percentile.
- **Correctness gate:** a bootstrap CI gates every readout — assert
  improved/slipped only when the CI excludes 0, else ABSTAIN. Sub-threshold
  negatives are never rendered. HARD eval gate = a false-positive mechanics arm
  (on true-no-change learners it must assert "improved" <5% of the time, and it
  must detect true improvement).
- **Honest claim:** in-UI, only a self-referential mastery delta with calibrated
  abstention — no scaled-score claim; downstream score movement is just the
  mechanical value of extra practice (not double-counted; mirrors `adherence`).

### 3. Rush-Error Detector — #21 (Effort S)

Per-learner-baseline read-out of timed answers that come in far under the
learner's own untimed median RT _and_ are wrong. Extends `lsat/pacing.py`.

- **Honest claim:** purely diagnostic, makes no learning claim. The strong rating
  is for estimator _validity_ (recover a planted rush pattern; beat a naive
  baseline-free fast-and-wrong count). Abstains below the event floor.

### 4. RC Judgment Module (Main-Point Discrimination + Viewpoint Attribution) — #3/#1 (Effort M–L)

Authored RC stimuli with hidden main-point trap labels + optional
viewpoint-attribution map; grade against labels, fail closed. **Requires human
calibration** of the candidate labels and a cue-ABSENT viewpoint subset before
any item is admitted — so it ships study-only until its held-out CI excludes 0.
Sequenced after the cheap drills; treated with extra care (authoring risk).

### 5. Time-Leak Diagnostic — #4 (Effort S)

Reclaimable-seconds triage read-out (mirrors `pacing.py`): needs multiple
confirming untimed misses before flagging an item "unwinnable"; reports leak
seconds with their own CI; leads with the abstain path when no blind pass exists.
Strictly descriptive — never translated into a promised point gain.

## Deferred (revive with conditions)

- **#14 Faded Flaw Ladders** — valuable but partial data-blocked (needs ~15
  hand-authored flaw decompositions) + new notetype + independent checker.
- **#5 Commit-or-Bail Triage** — a mid-question pressure gate can induce panic;
  revive only rare/opt-in, correct-per-fixed-budget metric, null pre-committed.
- **#7 Expected-Points-per-Minute Allocator** + **#8 Labor-in-Vain Stall Guard**
  — depend on readiness calibration; second wave, slope-CI-gated.
- **#19 Arousal-Reappraisal Prime** — within-subject RCT powers slowly; low
  priority, default-OFF, never claim anxiety reduction.

## Cut

- **#6 Two-Pass Fixed-Budget Mode** — likely null for score, data-blocked, adds
  nothing the eval harness doesn't already measure.
- **#18 Value-Relevance micro-prompt** — contested evidence, no shippable claim.

## Implementation order

1 → 2 → 3 → 5, then 4 last (authoring risk). Each: feature module + measured
eval arm (equal study time, bootstrap CI) + UI + full verification, logged in
`docs/improvements-log.md`.
