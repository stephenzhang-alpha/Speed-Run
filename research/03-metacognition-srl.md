# 03 — Metacognition, Confidence Calibration, Error Analysis, Deliberate Practice & Self-Regulated Learning

## Lens & scope

On a tightly-timed, 120–180 reasoning test, the highest-leverage skill after "can you
do the item" is **knowing *when* you are actually right** and **diagnosing the specific
reasoning bug that keeps snaring you.** This lens covers the science of *monitoring* one's
own knowledge (confidence–accuracy calibration, judgments of learning, the Nelson–Narens
monitoring/control loop), *learning from errors* (the hypercorrection effect), *targeting*
practice where it pays (deliberate practice and its honest limits), *closing the loop*
(Zimmerman's self-regulated-learning cycle), and *performing under the clock* (test anxiety,
choking under pressure, speed–accuracy). I treat popular claims skeptically: I report
effect sizes, replication status, and — where the pop-science version is overstated
(Dunning–Kruger, "10,000 hours," "just write your worries away") — I say so.

**Research-integrity note.** Every empirical source below was retrieved and read this
session (web search + full-text capture); numbers are quoted from the retrieved text, not
from memory. One foundational paper (Ericsson et al. 1993) is named for provenance but was
**not** independently retrieved — its claim is carried by the meta-analysis that tested it
(Macnamara 2014) and is labelled `[provenance-only]`. Feature-implementability claims were
checked against the actual code (`lsat/events.py`, `lsat/notetypes.py`,
`lsat/models/performance.py`, `eval/metrics.py`, `qt/aqt/lsat_performance.py`,
`lsat-taxonomy.yaml`).

---

## Key findings

Each bullet: **claim** · citation · a number/effect size · **evidence rating**.

- **People are systematically over-confident, and (descriptively) the weakest are the most
  miscalibrated — on logical reasoning specifically.** Kruger & Dunning (1999), *Unskilled and
  Unaware of It*, *J. Personality & Social Psych.* 77(6):1121–1134. In their **Study 2 (a
  logical-reasoning test)**, bottom-quartile performers scored at the **12th percentile but
  rated their ability at the ~68th and their score at the ~62nd**; training the underlying
  skill improved the self-assessment. **Evidence: STRONG as a robust, replicated *description*.**
  Relevance: an LSAT app must *measure* confidence against outcomes rather than trust learners'
  self-reports.

- **⚠️ MYTH-CHECK (rigor): the Dunning–Kruger *mechanism* is largely overstated — much of the
  famous chart is a statistical artefact.** Gignac & Zajenkowski (2020), *The Dunning–Kruger
  effect is (mostly) a statistical artefact*, *Intelligence* 80:101449. In **N=929**, the
  classic quartile plot reproduced the "DK pattern" (mean over-estimate: low=32.6, low-avg=22.1,
  high-avg=20.2, high=12.7 IQ points; ANOVA η²=0.20), **but the valid tests failed**: the Glejser
  heteroscedasticity correlation was **near zero (r≈−0.05)** and the self-vs-objective relation
  was **essentially linear** (no quadratic). Most of the effect is the **better-than-average
  effect (d≈1.71) + regression to the mean**. **Evidence: CONTESTED (with active back-and-forth
  replies).** Implication for us: use the *descriptive* fact that confidence ≠ accuracy, but do
  **not** build features that assume "the incompetent are uniquely blind"; measure each learner's
  own calibration curve instead.

- **High-confidence errors are corrected *more* readily than low-confidence errors — the
  hypercorrection effect.** Butterfield & Metcalfe (2001), *Errors committed with high confidence
  are hypercorrected*, *J. Exp. Psych.: LMC* 27(6):1491–1494; reviewed in Metcalfe (2017),
  *Learning from Errors*, *Annu. Rev. Psych.* 68:465–489. Confident errors are the *most* likely
  to be corrected on retest (immediate **and** delayed), driven by **surprise** — a feedback-locked
  **P3a** ERP that "rallies attention." **Evidence: STRONG (highly replicable across labs).**
  Relevance: the "I was *sure* and wrong" moment is the single highest-ROI review target.

- **…but confident errors *return* if you don't re-practice them.** Butler, Fazio & Marsh (2011),
  *The hypercorrection effect persists over a week, but high-confidence errors return*, *Psychon.
  Bull. Rev.* 18(6):1238–1244. The correction survives a 1-week delay, **yet the higher the
  original confidence, the more likely the error is to reappear** unless the learner gets
  **additional retrieval practice with feedback** (cf. Fazio 2011). **Evidence: MODERATE.**
  Implication: don't just show the fix once — **schedule a spaced re-test** of the corrected item
  (which is exactly what our FSRS layer is for).

- **Monitoring and control are separable, and control is only as good as monitoring is accurate.**
  Nelson & Narens (1990), *Metamemory: A theoretical framework and new findings*, *Psych. of
  Learning & Motivation* 26:125–173. The canonical model: a **meta-level** holds a model of the
  **object-level**; **monitoring** flows up (object→meta), **control** flows down (meta→object,
  e.g., allocate study time, re-read, stop). **Evidence: STRONG (foundational framework, not an
  effect size).** Relevance: our whole loop is "measure monitoring (confidence) → drive control
  (what to study next, how long, when to stop)."

- **⚠️ MYTH-CHECK: judgments of learning are driven by *fluency*, not learning — feeling ready
  ≠ being ready.** Rhodes & Castel (2008), *Memory predictions are influenced by perceptual
  information*, *J. Exp. Psych.: General* 137(4):615–625: words shown in **48-pt vs 18-pt** font
  got **higher JOLs but recall was unchanged**, and the illusion **survived explicit warnings**.
  Counter-lever: Nelson & Dunlosky (1991), *the "delayed-JOL effect"*, *Psych. Science*
  2(4):267–271 — **delayed** judgments are far more accurate than immediate ones. **Evidence:
  STRONG/robust.** Relevance: never trust an in-the-moment "felt easy"; capture confidence at the
  point of a *graded* answer, and prefer *delayed* self-assessment.

- **⚠️ MYTH-CHECK (the big one): deliberate practice does *not* explain "almost everything."**
  Macnamara, Hambrick & Oswald (2014), *Deliberate Practice and Performance…: A Meta-Analysis*,
  *Psych. Science* 25(8):1608–1618 (**88 studies, 111 samples, 157 effect sizes, N=11,135**).
  Accumulated practice explained **26% (games), 21% (music), 18% (sports), 4% (education), <1%
  (professions, p=.62)** of performance variance; with **log-based (higher-fidelity) practice
  measures, only ~5%**. The original strong claim — Ericsson, Krampe & Tesch-Römer (1993)
  `[provenance-only]` that individual differences "can largely be accounted for by…amounts of
  practice" — is **not** supported at that strength. **Evidence: STRONG (meta-analysis).** BUT
  the same paper gives us the design lever: DP paid **most in *high-predictability* domains
  (24% variance) vs low-predictability (4%)** — and LSAT question types are highly structured/
  predictable, so *targeted, structured* practice is exactly where DP earns its keep. Takeaway:
  "just do more PrepTests" is weak; **structured, feedback-rich, error-focused, edge-of-ability**
  practice is the win.

- **Self-regulated learning is a cycle, and skipping the reflection phase is what novices do.**
  Zimmerman (2002), *Becoming a Self-Regulated Learner: An Overview*, *Theory Into Practice*
  41(2):64–70. Three cyclical phases — **forethought** (task analysis, goal-setting, self-efficacy)
  → **performance** (self-control + self-observation/monitoring) → **self-reflection**
  (self-judgment + attribution) — where reflection feeds the next forethought. Experts set
  hierarchical process→outcome goals and self-monitor; poor learners rely on social comparison and
  attribute failure to fixed ability. **Evidence: MODERATE (dominant, well-validated framework;
  much correlational).** Relevance: turn the dashboard from a *readout* into a *closed loop*.

- **Pressure harms the *ablest* most, because it eats the working memory they rely on.** Beilock &
  Carr (2005), *When High-Powered People Fail*, *Psych. Science* 16(2):101–105: under pressure,
  **only high-working-memory individuals' math accuracy dropped**, and only on the highest-WM-demand
  problems. Mechanism = worries consume WM (distraction theory). **Evidence: STRONG/MODERATE
  (replicated lab effect).** Relevance: an LSAT taker who is fine untimed but craters under the
  35-minute clock is *choking*, not *ignorant* — a different intervention entirely.

- **Choking is *trainable away* by practicing to automaticity.** Beilock, Kulp, Holt & Carr (2004),
  *More on the Fragility of Performance*, *J. Exp. Psych.: General* 133(4):584–600: pressure hurt
  **unpracticed, high-demand** problems, but problems **practiced 50× (answers retrieved directly
  from memory) showed no choking.** **Evidence: MODERATE.** Relevance: over-learning core LR moves
  (conditional transforms, flaw IDs) so they're *retrieved* not *computed* is a direct anti-choke
  intervention.

- **⚠️ MYTH-CHECK: "write your worries away" is promising but NOT a guaranteed fix.** Ramirez &
  Beilock (2011), *Writing About Testing Worries Boosts Exam Performance*, *Science* 331:211–213:
  a 10-min pre-exam expressive-writing task helped, especially for high-anxiety students —
  **field d=0.57** (writers beat controls by ~6% and the test-anxiety↔score correlation fell from
  **r=−0.51 in controls to −0.14 with writing**); lab **d=2.48**. **BUT** Myers, Davis & Chan (2021),
  *Cognitive Research: Principles & Implications* 6(1):44, ran it across four authentic class exams
  and found **neither expressive writing nor an instructional intervention worked**; other
  replications are mixed. **Evidence: CONTESTED/MIXED.** Ship it as an *opt-in* micro-tool and
  **measure it in our own harness** rather than promising a benefit. (And per the brief: we do
  **not** touch debunked ideas like "learning styles.")

---

## Current-LSAT grounding (verified 2026)

Independently verified via LSAC's own pages this session:

- The multiple-choice LSAT is **two scored Logical Reasoning sections + one scored Reading
  Comprehension section + one unscored variable section** (LR or RC); **four 35-minute sections**
  with a **10-minute intermission** after section 2 (LSAC FAQ; "What to Expect…August 2024";
  "Changes are coming…August 2024").
- **Analytical Reasoning ("Logic Games") was permanently removed** (from the Aug 2024 test) and
  replaced by the second LR section.
- **From the August 2026 LSAT, testing moves to in-center at test centers for almost all
  candidates** (limited accommodation exceptions), and **LSAT Argumentative Writing** is a
  separate, required, online task (LSAC "Specifications…").

**Why this lens matters more now.** (1) **LR is ~2/3 of the scored test** — reasoning-error
calibration and error-type diagnosis are worth double. (2) **RC is ~1/3** — metacognitive
monitoring of comprehension matters. (3) It is a **speeded** exam moving to **high-stakes,
in-center** conditions — so *pacing and choking* become first-class problems, and the diagnostic
"slow/cracked-under-pressure vs doesn't-actually-know" split is central. Our taxonomy already
reflects this: `format_as_of: "2024-08"`, `scored_sections: ["LR","LR","RC"]`, and a cross-cutting
`skill.pacing` competency fed by response timing (`lsat-taxonomy.yaml`).

---

## What the app already has (so these features go *beyond* it)

- Append-only graded-event log with **latency** per answer (`lsat/events.py`), captured today via
  `qt/aqt/lsat_performance.py` → `pycmd("lsatAnswer:<LETTER>")` → `card.time_taken()` →
  `append_event(...)`. **It stores `correct` + `response_ms` but NOT the chosen option or any
  confidence.**
- A **model-calibration** notion already exists: `lsat/models/performance.py` fits a logistic/IRT
  P(correct) with a **`timing_z`** covariate and reports **held-out ECE/Brier/log-loss** (k-fold),
  consumed by the readiness give-up rule (`max_heldout_calibration_ece`). This measures whether
  **the app's** probabilities are calibrated — *not* whether **the student's** confidence is.
- Reusable metrics: `eval/metrics.py` ships `brier`, `log_loss`, `reliability_bins`, `ece`, `auc`,
  `bootstrap_ci`.
- A **points-at-stake** queue: `points = weight·(1 − mastery)`, with weights computed in Python
  (`lsat/events.topic_weights_for_queue`) and passed to a Rust RPC — so re-weighting needs **no
  Rust change**.
- Taxonomy hooks: `skill.pacing`, a set of `skill.trap.*` (out-of-scope, extreme_language,
  reversal, half_right, irrelevant_comparison), and a `flaw_catalog`; an AI generate-then-check
  pipeline (`lsat/ai/`); and the Svelte/Qt dashboard.

> **Shared enabling change (small, one-time).** Add three fields to the `LSAT PerformanceEvent`
> notetype in `lsat/notetypes.py` (`EVENT_FIELDS`, created in `ensure_notetypes`): **`confidence`**
> (0–100, or a 3-way sure/likely/guess mapped to a probability), **`chosen`** (the selected letter,
> needed for error-pattern mining), and optionally **`phase`** (`timed`/`relaxed`). Capture them by
> extending the Item template's one-tap flow to post `pycmd("lsatAnswer:<LETTER>:conf=<0–100>")` and
> threading the values through `append_event` in `qt/aqt/lsat_performance.py`. Every event stays
> append-only, one-note-per-attempt, HLC-ordered — sync and conflict rules untouched. **Effort: S.**
> All features below read these fields.

---

## Proposed features

### Feature 1 — Confidence Tagging + Human-Calibration Dashboard ("Are you as right as you feel?")

- **Pitch.** One tap of confidence on every graded item, turned into a personal calibration
  report that spotlights **confident-but-wrong traps**.
- **Mechanism.** After choosing an answer, the learner taps **sure / likely / guess** (or a 0–100%
  slider). A dashboard panel shows: a **reliability curve** (stated confidence vs actual accuracy),
  a per-skill **Over-confidence Index** = mean(confidence) − mean(accuracy), a **Resolution** score
  = `auc(confidence, correct)` (does your confidence actually *separate* your right from wrong
  answers?), and a ranked **"sure-and-wrong" list**. A coaching line reads, e.g., *"On Necessary
  Assumption you're 28 pts hotter than your accuracy; your guesses are better-calibrated than your
  'sures.'"*
- **Theory + citations.** Monitoring/control (Nelson & Narens 1990, **STRONG framework**);
  confidence≠accuracy (Kruger & Dunning 1999, **STRONG description**, with the Gignac & Zajenkowski
  2020 caveat that we measure the *individual's* curve, not assume a universal mechanism —
  **CONTESTED mechanism**); fluency illusions mean we must score feelings against outcomes and
  prefer delayed judgments (Rhodes & Castel 2008; Nelson & Dunlosky 1991, **STRONG**).
- **LSAT fit.** The 5-choice "best answer" format is *engineered* to manufacture confident errors
  via seductive traps (already in our `skill.trap.*`); on a tight 120–180 curve a handful of
  confident misses move the score. A calibration coach is a uniquely LSAT-shaped intervention.
- **Implementability.** New `lsat/models/calibration.py` reusing `eval/metrics.py` verbatim
  (`reliability_bins`, `ece`, `auc`, `brier`, `bootstrap_ci`), fed by the `confidence` field;
  surface via `lsat/dashboard_data.py` + a panel in `ts/routes/lsat-dashboard/` (Qt host
  `qt/aqt/lsat_dashboard.py`). Reuses the existing reliability-diagram machinery. **Effort: M.**
- **Novelty.** Anki's Again/Hard/Good/Easy is a *prospective* self-rating **never scored against
  outcomes**; our built ECE measures the *model's* calibration. This measures the *human's* —
  an orthogonal, new axis. No mainstream LSAT product reports a personal Brier/resolution curve.
- **Risks / failure modes.** Prompt fatigue (mitigate: one tap, sample every Nth item, skippable);
  **degenerate flat ratings** (caught by the Resolution/AUC metric and a variance check);
  small-sample noise (require ≥k events, show `bootstrap_ci`, abstain below threshold — mirror the
  readiness give-up philosophy).

### Feature 2 — Hypercorrection-Prioritized, Spaced Error Queue ("fix what you were sure about, then re-test it")

- **Pitch.** Your review queue leads with **high-confidence misses**, then *re-tests* each one on
  a short, spaced schedule so the correction sticks.
- **Mechanism.** A confident-wrong answer is flagged, its feedback framed as a **"surprise"**
  correction ("You were 90% sure — here's why (E) beats (B)"), and the item is **scheduled for a
  near-term, then spaced, re-test** rather than shown once. A "Confident Errors" queue and a
  weekly "corrected vs relapsed" counter track it.
- **Theory + citations.** Hypercorrection: confident errors are corrected best (Butterfield &
  Metcalfe 2001; Metcalfe 2017 — surprise/P3a, **STRONG**). Crucially, Butler, Fazio & Marsh (2011,
  **MODERATE**) show confident errors **return without re-practice** — so the *spacing* is not
  optional; retrieval-practice-with-feedback is what makes the fix durable (a natural fit for FSRS).
- **LSAT fit.** LR/RC misses are reasoning slips, not vocabulary; the confident ones are where a
  mistaken *rule* ("a necessary assumption must be stated strongly") is entrenched — the highest-
  yield thing to overwrite before test day.
- **Implementability.** Pure Python: in `lsat/events.topic_weights_for_queue`, add a **bounded
  boost** for skills/items with recent high-confidence misses (reads `confidence`); create the
  concrete re-test either by biasing the points-at-stake weights or by rescheduling that item's
  `LSAT Card`/`Item` via the existing FSRS layer. **No Rust change** (weights are computed in Python
  and passed to the RPC). **Effort: S–M.**
- **Novelty.** The current queue is **recency-weighted accuracy only** — it has no notion of
  *confidence-at-time-of-error*, so a confident miss and a shrugged guess look identical. This adds
  a theory-backed new priority signal *and* enforces the re-test that keeps it corrected.
- **Risks / failure modes.** Over-boosting a fluky confident miss (cap the boost, require repetition
  before it dominates); confidence-gaming (cross-checked by Feature 1's resolution metric); make
  sure the spaced re-test doesn't crowd out coverage (blend, don't replace, the exam-weighted queue).

### Feature 3 — Reasoning-Bug ("Cognitive Leech") Diagnosis ("you keep picking the too-strong answer")

- **Pitch.** Detect the *recurring error type* across items — not a hard card, but a hard *habit* —
  e.g., "you fall for **extreme-language** traps on 38% of your Strengthen misses."
- **Mechanism.** Because we now log the **chosen** option, we map each *distractor* to a trap/flaw
  label (`skill.trap.*` / `flaw_catalog`) and fold errors by that label. When a pattern crosses a
  threshold, the app names the bug in plain language, shows 2–3 exemplar misses, and offers a
  targeted mini-lesson + drill for that specific trap.
- **Theory + citations.** Learning-from-errors requires **analysis of the reasoning that led to the
  mistake**, not just the right answer (Metcalfe 2017, **STRONG**); this is the *monitoring→control*
  loop applied at error-*type* granularity (Nelson & Narens 1990). Confident, patterned errors are
  precisely the hypercorrection targets (Feature 2 feeds this).
- **LSAT fit.** LR/RC wrong answers are systematic and *named* by the prep community (out-of-scope,
  reversal of sufficient/necessary, half-right, extreme language) — a finite bug taxonomy we already
  encode. Diagnosing "which trap owns you" is the difference between grinding items and fixing the
  root cause.
- **Implementability.** New `lsat/error_patterns.py` folds events by chosen-distractor label; the
  labels come from the **AI pipeline** (`lsat/ai/`) tagging each distractor at generation time,
  verified by the existing independent checker (source-span requirement). Surface in the dashboard;
  feed the queue at **trap granularity** via `topic_weights_for_queue`. **Effort: M** (needs
  distractor→trap labels; leverages taxonomy + AI pipeline).
- **Novelty.** Anki's "leech" is a *card-level* repeated-failure flag; this is an **error-*type*-level**
  diagnosis *across* items — impossible without the chosen-option capture we add. No SRS does this;
  LSAT courses teach the trap taxonomy but don't *mine each learner's* trap fingerprint.
- **Risks / failure modes.** Mislabeled distractors (gate on checker pass-rate, start with the
  clearest trap types); multi-cause misses (allow multiple labels, report probabilistically);
  small-n over-interpretation (threshold + CIs before naming a "bug").

### Feature 4 — Deliberate-Practice Micro-Loops on the Single Weakest Sub-Skill ("edge-of-ability, not more volume")

- **Pitch.** Instead of another full PrepTest, a short, focused, feedback-rich loop on your
  *current weakest* node, at the *edge of your ability*, with an explicit per-loop goal.
- **Mechanism.** The app picks the weakest node (lowest `predict_interval` lower-bound with enough
  evidence), states a **process goal** ("get 8/10 Sufficient-Assumption at medium difficulty under
  90s"), serves a tight AI-generated set **targeted to that skill + difficulty**, gives **immediate
  per-item feedback**, and **stops when the mastery threshold is hit** (Nelson–Narens "control:
  terminate"), then hands off to spacing.
- **Theory + citations.** Deliberate practice works when it is *structured, targeted, and
  feedback-rich* — and matters **more in high-predictability domains (24% variance) than in
  unstructured ones (4%)** (Macnamara et al. 2014, **STRONG**; construct origin Ericsson et al.
  1993 `[provenance-only]`). Goal-setting + monitoring + stop-rules are the SRL performance phase
  (Zimmerman 2002, **MODERATE**). Honest caveat: DP explains a *minority* of variance, so this is a
  **targeting** tool, not a silver bullet.
- **LSAT fit.** LSAT question types are highly structured and repeatable — the exact profile where
  targeted DP pays — so concentrating reps on the weakest *transferable* move (e.g., conditional
  contrapositive) beats spreading effort across full sections.
- **Implementability.** Orchestration in `lsat/` reading `lsat/models/performance.py` to pick the
  weakest node; generation targeting via `lsat/ai/` (skill + difficulty); reuse the reviewer flow
  and event log; a "focus loop" surface in the dashboard/reviewer. **Effort: M–L.**
- **Novelty.** Goes beyond our interleaving toggle and points-at-stake queue (which *order* a mixed
  queue) by running a **bounded, goal-gated, edge-of-ability drill with a stop-rule** — an explicit
  DP loop, not just prioritization.
- **Risks / failure modes.** Over-drilling one node (cap loop length, rotate, keep interleaving for
  retention); AI item quality/leakage (reuse `eval/leakage.py` + checker gates); demotivation from
  narrow grinding (frame as short, celebrate the goal hit — SRL self-reaction).

### Feature 5 — Pacing & Choke Trainer with Opt-In Anxiety Reset ("separate 'too slow' from 'don't know'")

- **Pitch.** Build time-pressure tolerance with **calibrated, gradually-tightening** per-item
  budgets, quantify a personal **Choke Index**, and offer a 2-minute pre-session worry-dump.
- **Mechanism.** From each learner's `response_ms` distribution the app sets a per-item budget and
  **ratchets it down** as accuracy holds (over-learning toward automaticity). A **Choke Index** =
  (relaxed-mode accuracy − timed-mode accuracy) per skill flags where pressure — not knowledge — is
  the problem, routing those skills to *automaticity* drills rather than new content. An **opt-in**
  90-second expressive-writing "brain dump" is offered before high-pressure sessions.
- **Theory + citations.** Pressure consumes the working memory the ablest rely on (Beilock & Carr
  2005, **STRONG/MODERATE**); practicing to *retrieval/automaticity* removes choking (Beilock et al.
  2004, **MODERATE**); pre-exam expressive writing can help anxious students (Ramirez & Beilock 2011,
  **d=0.57**) **but doesn't always replicate** (Myers, Davis & Chan 2021 — **CONTESTED**), so it's
  opt-in and measured, never promised.
- **LSAT fit.** 35-minute sections, moving to high-stakes in-center testing (Aug 2026): the
  timed↔relaxed accuracy gap is the LSAT's central diagnostic, and our `skill.pacing` competency +
  `timing_z` covariate already exist to power it.
- **Implementability.** Reuses `response_ms` (already captured) and the `phase` field (timed vs
  relaxed) from the shared change; budget logic + Choke Index in `lsat/` (extending
  `skill.pacing`); a reviewer timer + a dashboard pacing panel; the writing tool is a simple
  pre-session modal logged as a session flag. **Effort: M.**
- **Novelty.** Our stack *observes* timing (`timing_z`) but never *trains* pacing or distinguishes
  choking from ignorance; no SRS applies calibrated time-pressure or an anxiety-reset. LSAT courses
  give generic "pacing tips," not a per-skill, data-driven choke diagnosis.
- **Risks / failure modes.** Time pressure can *induce* anxiety (ramp gently, keep a relaxed mode);
  the writing intervention may do nothing (that's why it's opt-in + A/B-measured in `eval/`); Choke
  Index needs both timed and relaxed samples (abstain until both exist).

### Feature 6 — Self-Regulated-Learning Loop: Forethought → Performance → Reflection ("predict, do, reconcile")

- **Pitch.** Wrap each study session in Zimmerman's cycle: a 20-second **goal + score prediction**
  up front, monitoring during, and a **predicted-vs-actual + attribution** reflection after.
- **Mechanism.** *Forethought:* pick a focus and **predict** session accuracy / a score band (a
  session-level, *scored* judgment of learning). *Performance:* the confidence taps (F1) supply
  live monitoring. *Self-reflection:* show predicted vs actual, your calibration delta, and a
  one-tap **attribution** ("ran out of time" / "misread the stem" / "didn't know the rule") that
  routes to the right fix (F5 pacing / F3 bug / F4 drill) and seeds the next session's forethought.
- **Theory + citations.** Zimmerman (2002, **MODERATE**) — the reflection phase is what novices skip
  and experts run; Nelson & Narens (1990) control depends on accurate monitoring; **delayed,
  outcome-anchored** self-judgment beats in-the-moment fluency (Nelson & Dunlosky 1991; Rhodes &
  Castel 2008, **STRONG**). Attribution to *controllable* causes (strategy/effort) rather than fixed
  ability is the motivational core of SRL.
- **LSAT fit.** LSAT prep is a months-long solo grind where learners over-rely on raw section scores
  and "felt fluency." A structured predict→reconcile loop converts each session into calibrated,
  attributable evidence and directly trains the metacognition the exam rewards.
- **Implementability.** A thin session wrapper in `lsat/` + reviewer start/end screens; stores a
  small session record (a mutable snapshot handled by the existing `resolve_lww` LWW rule) linking
  the prediction to realized accuracy; reads Feature 1's calibration and the readiness model.
  **Effort: S–M.**
- **Novelty.** Anki has no notion of session goals, predictions, or reflection; our dashboard is a
  *readout*, not a *loop*. This closes it — and makes the session-level prediction another
  calibration signal.
- **Risks / failure modes.** Friction/skipping (keep it ~20s, make prediction one tap); reflection
  theater (tie attributions to concrete routes so it changes behavior); prediction anchoring (use
  delayed/next-session framing; don't show the target mid-session).

---

## Ranked shortlist (best first)

1. **Confidence Tagging + Human-Calibration Dashboard (F1)** — cheap (reuses `eval/metrics.py`),
   orthogonal to everything built, and the *enabler* for F2/F5/F6. Strong, LSAT-shaped.
2. **Hypercorrection-Prioritized Spaced Error Queue (F2)** — highest score-relevant ROI (confident
   errors first), strong evidence, Python-only, and it makes the queue theory-aware.
3. **Reasoning-Bug ("Leech") Diagnosis (F3)** — differentiating and LSAT-native (trap taxonomy);
   depends on chosen-option capture + distractor labels.
4. **Pacing & Choke Trainer (F5)** — addresses the exam's defining constraint; separates "slow"
   from "doesn't know"; the anxiety tool is opt-in/measured given mixed evidence.
5. **Deliberate-Practice Micro-Loops (F4)** — the honest, targeted answer to "just do more tests";
   larger build, best after F1/F3 identify the weak node.
6. **SRL Loop (F6)** — the connective tissue that turns the above into a Zimmerman cycle; small, but
   most valuable once F1 exists.

---

## Sources (all retrieved & read this session unless marked `[provenance-only]`)

1. Kruger, J., & Dunning, D. (1999). *Unskilled and Unaware of It: How Difficulties in Recognizing
   One's Own Incompetence Lead to Inflated Self-Assessments.* Journal of Personality and Social
   Psychology, 77(6), 1121–1134. https://doi.org/10.1037/0022-3514.77.6.1121
   (full text: https://www.rhps.org/stuff/psp7761121.pdf)
2. Gignac, G. E., & Zajenkowski, M. (2020). *The Dunning–Kruger effect is (mostly) a statistical
   artefact: Valid approaches to testing the hypothesis with individual differences data.*
   Intelligence, 80, 101449. https://doi.org/10.1016/j.intell.2020.101449
   (full text: https://gwern.net/doc/iq/2020-gignac.pdf)
3. Butterfield, B., & Metcalfe, J. (2001). *Errors committed with high confidence are hypercorrected.*
   Journal of Experimental Psychology: Learning, Memory, and Cognition, 27(6), 1491–1494.
   https://doi.org/10.1037/0278-7393.27.6.1491
4. Metcalfe, J. (2017). *Learning from Errors.* Annual Review of Psychology, 68, 465–489.
   https://doi.org/10.1146/annurev-psych-010416-044022
   (full text: https://www.columbia.edu/cu/psychology/metcalfe/PDFs/Learning%20from%20errorsAnnual%20ReviewMetcalfe2016.pdf)
5. Butler, A. C., Fazio, L. K., & Marsh, E. J. (2011). *The hypercorrection effect persists over a
   week, but high-confidence errors return.* Psychonomic Bulletin & Review, 18(6), 1238–1244.
   https://doi.org/10.3758/s13423-011-0173-y
6. Nelson, T. O., & Narens, L. (1990). *Metamemory: A theoretical framework and new findings.* In
   G. H. Bower (Ed.), The Psychology of Learning and Motivation (Vol. 26, pp. 125–173). Academic
   Press. https://doi.org/10.1016/S0079-7421(08)60053-5
   (full text: https://sites.socsci.uci.edu/~lnarens/1990/Nelson%26Narens_Book_Chapter_1990.pdf)
7. Macnamara, B. N., Hambrick, D. Z., & Oswald, F. L. (2014). *Deliberate Practice and Performance
   in Music, Games, Sports, Education, and Professions: A Meta-Analysis.* Psychological Science,
   25(8), 1608–1618. https://doi.org/10.1177/0956797614535810
   (full text: https://www.psychologie.uzh.ch/dam/jcr:658d39fe-2f4b-467f-9ae2-ffeb25caf2b6/McNamara.PsychSci.25.2014.pdf)
8. Ericsson, K. A., Krampe, R. T., & Tesch-Römer, C. (1993). *The Role of Deliberate Practice in
   the Acquisition of Expert Performance.* Psychological Review, 100(3), 363–406.
   https://doi.org/10.1037/0033-295X.100.3.363  `[provenance-only — claim carried by Macnamara 2014]`
9. Zimmerman, B. J. (2002). *Becoming a Self-Regulated Learner: An Overview.* Theory Into Practice,
   41(2), 64–70. https://doi.org/10.1207/s15430421tip4102_2
   (full text: https://www.leiderschapsdomeinen.nl/wp-content/uploads/2016/12/Zimmerman-B.-2002-Becoming-Self-Regulated-Learner.pdf)
10. Beilock, S. L., & Carr, T. H. (2005). *When High-Powered People Fail: Working Memory and
    "Choking Under Pressure" in Math.* Psychological Science, 16(2), 101–105.
    https://doi.org/10.1111/j.0956-7976.2005.00789.x
11. Beilock, S. L., Kulp, C. A., Holt, L. E., & Carr, T. H. (2004). *More on the Fragility of
    Performance: Choking Under Pressure in Mathematical Problem Solving.* Journal of Experimental
    Psychology: General, 133(4), 584–600. https://doi.org/10.1037/0096-3445.133.4.584
12. Ramirez, G., & Beilock, S. L. (2011). *Writing About Testing Worries Boosts Exam Performance in
    the Classroom.* Science, 331(6014), 211–213. https://doi.org/10.1126/science.1199427
13. Myers, S. J., Davis, S. D., & Chan, J. C. K. (2021). *Does expressive writing or an instructional
    intervention reduce the impacts of test anxiety in a college classroom?* Cognitive Research:
    Principles and Implications, 6(1), 44. https://doi.org/10.1186/s41235-021-00309-x
14. Rhodes, M. G., & Castel, A. D. (2008). *Memory predictions are influenced by perceptual
    information: Evidence for metacognitive illusions.* Journal of Experimental Psychology: General,
    137(4), 615–625. https://doi.org/10.1037/a0013684
15. Nelson, T. O., & Dunlosky, J. (1991). *When people's judgments of learning (JOLs) are extremely
    accurate at predicting subsequent recall: The "delayed-JOL effect."* Psychological Science,
    2(4), 267–271. https://doi.org/10.1111/j.1467-9280.1991.tb00147.x
16. LSAC. *Frequently Asked Questions about the LSAT.* https://www.lsac.org/lsat/frequently-asked-questions-about-lsat
17. LSAC. *What to Expect Starting With the August 2024 LSAT.* https://www.lsac.org/blog/what-to-expect-starting-with-august-2024-lsat
18. LSAC. *Changes are coming to the LSAT in August 2024.* https://www.lsac.org/lsat/lsat-changes-coming-august-2024
19. LSAC. *Specifications of the LSAT and LSAT Argumentative Writing.* https://www.lsac.org/lsat/register-lsat/accommodations/specifications-lsat-and-lsat-argumentative-writing
