# Adaptive Learning, Psychometrics & LSAT-Specific Pedagogy — Research & Feature Proposals

**Researcher D · lens:** _how to sequence and diagnose optimally, and what is actually known about
LSAT prep._ I cover mastery learning (Bloom's "2 sigma" and its failed scale-up), knowledge tracing
(Bayesian and deep), item response theory + computerized adaptive testing (CAT), cognitive diagnostic
models (attribute mastery), and optimal-difficulty / zone-of-proximal-development sequencing (the "85%
rule," the region of proximal learning). Spacing/retrieval are covered by sibling memos, so I focus on
**item SELECTION, DIFFICULTY TARGETING, and DIAGNOSIS**. My proposals **extend** — never duplicate —
the three models already built: the points-at-stake queue (`rslib/src/scheduler/points_at_stake.rs`),
the Rasch/logistic performance model (`lsat/models/performance.py`), and the Monte-Carlo readiness
model (`lsat/models/readiness.py`).

**Research-integrity note.** Every empirical source below was retrieved this pass (2026-07-01) via web
search/fetch; effect sizes are quoted from the retrieved text. The LSAC August-2024 format page and the
LSAC Khan-Academy report were fetched and read in full. Two items are named for provenance but were
**not** independently retrieved (Beck & Chang 2007 on BKT identifiability; Bjork & Bjork 2011 on
desirable difficulties) and are labelled `[provenance-only]`; their claims are carried by retrieved
sources (van de Sande 2013; Metcalfe & Kornell 2003/2005). LR question-type frequencies and pacing
norms come from prep-community sources and are flagged `[market-grounding]`, not peer-reviewed.

---

## Key findings

Each bullet: **claim · citation · number/effect size · evidence rating.**

### Mastery learning and the "2 sigma" myth (read this first — it disciplines every claim below)

- **Bloom's "2 sigma" was real in the lab but has never replicated at scale, and it was never
  tutoring _alone_.** Bloom (1984) reported that one-to-one tutoring plus mastery learning moved the
  average student to **+2 SD** (98th percentile) and mastery learning alone to **+1 SD** (84th
  percentile) over conventional instruction. Bloom, B.S. (1984), _The 2 Sigma Problem_, _Educational
  Researcher_ 13(6):4–16 <https://www.jstor.org/stable/1175554>. But the underlying Anania/Burke
  dissertations used **small samples on narrow, experimenter-made tests**, and the effect bundled
  tutoring **with** frequent testing, feedback and corrective re-teaching (Education Next analysis,
  <https://www.educationnext.org/two-sigma-tutoring-separating-science-fiction-from-science-fact/>).
  **Evidence for a scalable 2σ: CONTESTED / effectively debunked.**
- **The honest, replicated tutoring number is ≈0.37 SD, not 2.0.** Nickow, Oreopoulos & Quan (2020),
  _The Impressive Effects of Tutoring on PreK-12 Learning_, NBER WP 27476,
  <https://www.nber.org/papers/w27476>: pooled **d = 0.37 SD across 96 randomized trials** (≈50th→66th
  percentile), matching Dietrichson 2017 (0.36) and Ritter 2009 (0.30). **STRONG (meta-analysis of
  RCTs).**
- **MYTH WARNING — "software gets you 2 sigma."** Intelligent tutoring systems do **not** reach 2σ.
  VanLehn (2011), _Educational Psychologist_ 46(4):197–221
  <https://doi.org/10.1080/00461520.2011.611369>: **human tutoring d = 0.79, ITS d = 0.76,
  answer-based CAI d = 0.31** — the widely-believed 0.3/1.0/2.0 ladder was **not** confirmed. Kulik &
  Fletcher (2016), _Review of Educational Research_ 86(1):42–78
  <https://doi.org/10.3102/0034654315581420>: ITS **median d = 0.66** over 50 evaluations, **but 0.73
  on local tests vs only 0.13 on standardized tests** — effects shrink when the outcome is not aligned
  to the tutored content. **STRONG.** _Implication for us: promise honest, single-digit-percentile
  gains and validate on held-out, exam-style items — never claim "2 sigma from an app."_
- **Mastery learning itself is a moderate, well-replicated effect (~0.5), and helps weaker students
  most.** Kulik, Kulik & Bangert-Drowns (1990), _Effectiveness of Mastery Learning Programs_, _Review
  of Educational Research_ 60(2):265–299 <https://doi.org/10.3102/00346543060002265>: **mean d ≈ 0.52
  across 108 evaluations**, larger for weaker students, but it **increases time-on-task** and
  self-paced variants can **reduce completion**. **STRONG (meta-analysis).** _This is the realistic
  ceiling for mastery-gating (Feature 6), and a caution against over-gating._

### Knowledge tracing (how to estimate per-skill mastery from a graded log)

- **Bayesian Knowledge Tracing (BKT) is the interpretable standard: a 2-state HMM with four
  parameters.** Corbett & Anderson (1995), _Knowledge Tracing: Modeling the Acquisition of Procedural
  Knowledge_, _User Modeling and User-Adapted Interaction_ 4(4):253–278
  <https://doi.org/10.1007/BF01099821>. Per skill it fits **P(L0)** (prior known), **P(T)** (learn per
  opportunity), **P(G)** (guess), **P(S)** (slip), updates P(mastery) after each attempt, and declares
  mastery at **P(mastery) ≥ 0.95**. **STRONG / foundational** (2,000+ citations). Caveat: BKT can be
  **non-identifiable** (different parameter sets → identical predictions; Beck & Chang 2007
  `[provenance-only]`, analysed by van de Sande 2013, _JEDM_,
  <https://jedm.educationaldatamining.org/index.php/JEDM/article/download/35/pdf_27>) — mitigated by
  bounding parameters.
- **MYTH WARNING — deep knowledge tracing (DKT) is not magic, and it over-fits sparse single-user
  data.** Piech et al. (2015), _Deep Knowledge Tracing_, NeurIPS 28
  <https://proceedings.neurips.cc/paper/2015/file/bac9162b47c56fc8a4d2a519803d51b3-Paper.pdf>, reported
  a **25% AUC gain** (Assistments AUC **0.86 vs BKT 0.69**). But Khajah, Lindsey & Mozer (2016), _How
  Deep is Knowledge Tracing?_, EDM/arXiv:1604.02416 <https://arxiv.org/abs/1604.02416>, showed the gap
  was largely an **evaluation artifact** (properly-run BKT scores **0.73, not 0.67**) and that a BKT
  **extended** with forgetting, per-student ability, and skill-discovery becomes **statistically
  indistinguishable from DKT** — "knowledge tracing may be a domain that does not require depth."
  **STRONG (direct replication).** _Implication: a single-user desktop app has tiny per-skill sequences;
  an RNN would over-fit. We should use BKT (few, interpretable parameters), which is exactly the
  "over-fitting adaptive models on sparse data" trap to avoid._

### Item response theory + computerized adaptive testing (efficient measurement)

- **CAT reaches equal (or better) measurement precision with ~50% fewer items by selecting the
  maximally-informative item at the current ability estimate.** Weiss (1982), _Improving Measurement
  Quality and Efficiency with Adaptive Testing_, _Applied Psychological Measurement_ 6(4):473–492
  <https://doi.org/10.1177/014662168200600408>: a 201-item battery needed **~100 items on average**
  adaptively (subtests as low as **13–30%** of fixed length), with equal/greater accuracy. Practitioner
  reviews report **50–90% length reductions** (assess.com,
  <https://assess.com/computerized-adaptive-testing/>). **STRONG (decades of simulation + live
  studies).** _Key nuance for us: for a 1PL/Rasch model, item information is maximized where
  **P(correct) ≈ 0.5** — that is the objective for MEASURING ability, and it is DIFFERENT from the
  objective for LEARNING (≈85%, below). Confusing the two is a common design error._

### Cognitive diagnostic models (per-attribute mastery from response patterns)

- **Cognitive diagnostic / diagnostic-classification models turn right/wrong patterns into a binary
  mastered/not-mastered profile over fine-grained attributes, via a Q-matrix (item × attribute).** de
  la Torre (2009), _DINA Model and Parameter Estimation: A Didactic_, _JEBS_ 34(1):115–130
  <https://doi.org/10.3102/1076998607309474>; de la Torre (2011), _The Generalized DINA Model
  Framework_, _Psychometrika_ 76(2):179–199 <https://doi.org/10.1007/s11336-011-9207-7>. The **DINA**
  model is conjunctive ("need ALL required attributes to answer right"); **G-DINA** generalizes it and
  subsumes DINA/DINO. Tooling: Ma & de la Torre (2020), _GDINA: An R Package…_, _J. Stat. Software_
  93(14). **STRONG / mature psychometrics.**
- **CDMs are only as good as the Q-matrix; misspecification degrades classification accuracy.** Rupp &
  Templin (2008), _The Effects of Q-Matrix Misspecification…in the DINA Model_, _Educational and
  Psychological Measurement_ 68(1):78–96 <https://doi.org/10.1177/0013164407301545>. **STRONG.**
  _Implication: start from an expert Q-matrix (our taxonomy already is one) and validate empirically;
  don't trust a hand-wavy attribute map._

### Optimal difficulty / zone of proximal development (the SEQUENCING core)

- **The "Eighty-Five Percent Rule": for gradient-descent learners on binary classification, learning
  rate is maximized at ~85% training accuracy (15.87% error).** Wilson, Shenhav, Straccia & Cohen
  (2019), _The Eighty Five Percent Rule for optimal learning_, _Nature Communications_ 10:4646
  <https://doi.org/10.1038/s41467-019-12552-4>: training at the optimal difficulty is **exponentially
  faster** than fixed difficulty. **MODERATE for humans** — it is a theoretical result demonstrated on
  artificial and biologically-plausible neural nets, **not** a classroom RCT; treat **85% as a tunable
  target, not a law.**
- **Humans, given free choice, learn fastest by studying the _easiest not-yet-mastered_ items and
  spending the most time on _medium-difficulty_ items — not the hardest.** Metcalfe & Kornell (2005),
  _A Region of Proximal Learning model of study time allocation_, _Journal of Memory and Language_
  52(4):463–477 <https://doi.org/10.1016/j.jml.2004.12.001>; Metcalfe & Kornell (2003), _JEP: General_
  132(4):530–542 <https://doi.org/10.1037/0096-3445.132.4.530>: against the "study the hardest first"
  (discrepancy-reduction) view, learners **study easiest-unlearned first (high→low JOL)** and best
  performance results when **most time goes to medium-difficulty items**; a "judgment of rate of
  learning" (jROL→0) is the natural stop rule. Complements Bjork's **desirable difficulties** (make it
  effortful but manageable; Bjork & Bjork 2011 `[provenance-only]`). **STRONG (8 experiments +
  replications).** _This is the single most important finding for us: our current queue serves the
  HARDEST items in the WEAKEST topics — the opposite of the region of proximal learning._

### LSAT-specific facts (verified)

- **Current scored format (verified against LSAC, fetched in full): two scored Logical Reasoning
  sections + one scored Reading Comprehension section + one unscored (LR or RC).** Analytical Reasoning
  ("Logic Games") **sunset after June 2024**; replaced by a second LR section from **August 2024**.
  LSAC, _What to Expect Starting With the August 2024 LSAT_
  <https://www.lsac.org/blog/what-to-expect-starting-with-august-2024-lsat>. Verbatim: "the LSAT will
  consist of two scored Logical Reasoning (LR) sections, one scored Reading Comprehension (RC) section,
  plus one unscored section." Swapping AR→LR2 changed the **mean score by 1/100 of a point** (N =
  218,243; 150.82→150.83) and predictive validity by **< 1/100 point**. **STRONG (primary/official).**
  _Consequence: LR is now ~2/3 of the scored test — our taxonomy's `lr.exam_weight: 0.66`,
  `format_as_of: "2024-08"` is correct._
- **The test is heavily speeded.** Each LR section is **~24–26 questions in 35 minutes ≈ 1 min 24 s per
  question** `[market-grounding]` (test-ninjas <https://test-ninjas.com/lsat-logical-reasoning>;
  lawschooli <https://lawschooli.com/lsat-logical-reasoning-timing/>). Difficulty tends to rise within a
  section, so the standard advice is to bank time early and skip-and-return. **MODERATE (consistent
  across prep sources; the 35-min/section fact is LSAC-official).**
- **LR question mix is dominated by a few types.** Assumptions, Flaw, and Strengthen/Weaken together
  ≈ **46%** of an LR section; adding Inference, Principle, and Paradox exceeds ~75%; Parallel
  Reasoning/Parallel Flaw are rare (~1–2/section) and the most time-consuming `[market-grounding]`
  (ScoreGap <https://scoregap.com/guides/lsat-question-type-frequency>; Magoosh
  <https://magoosh.com/lsat/lsat-logical-reasoning-question-types/>). Mirrors our
  `lsat-taxonomy.yaml` weights.
- **Does prep raise scores? Yes, modestly, and more for lower starters — but the evidence is
  quasi-experimental, not causal.** LSAC's own study — Dustman, Camilli & Gallagher (2021), _LSAT
  Takers and Khan Academy Preparation_ (RR 21-01),
  <https://www.lsac.org/sites/default/files/research/LSAT-Test-Taker-Khan-Preparation_RR-21-01_full-report.pdf>
  (read in full) — found that students at the **90th percentile of practice time (47 h) scored 4.3
  points higher** than the 10th percentile (26 min), **effect size 0.40** (each increase ÷ the LSAT SD
  of 10.7); taking **9–10 practice exams was associated with +7.26 points** vs zero (standardized slope
  β = .21), rising monotonically from +1.59 (1–2 exams) → +3.58 → +4.39 → +5.59 → +7.26; and
  **lower-baseline students had a higher return per practice minute**. The authors explicitly caution it is **quasi-experimental — causation
  cannot be established** (self-selection). LSAC's self-reported-methods summaries are **purely
  descriptive** (Sweeney, Fox & Reese 2019, TR 18-03,
  <https://www.lsac.org/data-research/research/summary-self-reported-methods-test-preparation-lsat-takers-testing-years-1>).
  **MODERATE (large-N quasi-experiment with controls) / weak causally.** _Two design lessons: (1) ~4–7
  points is a realistic honest target; (2) the biggest wins are for weaker students — our
  weakest-first, ZPD-difficulty queue targets exactly them._

### Myths & over-claims to avoid (required warnings, all disciplining the proposals)

- **MYTH 1 — "2 sigma from an app."** No software reaches Bloom's tutoring +2σ; the honest, replicated
  numbers are tutoring **d≈0.37** [2], ITS **d≈0.66** (and only **0.13** on _standardized_ vs 0.73 on
  _local_ tests) [4], human/ITS tutoring **0.79/0.76** [3], mastery learning **0.52** [5]. **We will
  promise honest, single-digit-percentile gains and validate on held-out, exam-style items — never "2
  sigma."** **STRONG.**
- **MYTH 2 — "deep models beat interpretable ones on our data."** DKT's famous 25% AUC edge over BKT was
  largely an evaluation artifact; a properly-run, extended BKT is _indistinguishable_ from a deep net
  [7][8]. A single-user desktop app has **tiny, sparse per-skill sequences**; an RNN (or an over-
  parameterized CDM) would **overfit**. **Every model below is deliberately low-parameter, bounded, and
  abstains under sparsity** — the anti-overfitting discipline is a design requirement, not an
  afterthought. **STRONG.**
- **MYTH 3 — "measure the student at the same difficulty you teach them."** The information-optimal
  difficulty for _measuring_ ability (1PL/Rasch Fisher information peaks at **P(correct)=0.5**) is _not_
  the difficulty that maximizes _learning_ (**≈0.85**) [10][14]. Conflating them is a real, common design
  error; F1 (learn) and F4 (measure) are deliberately built as **opposite-difficulty** engines and
  cross-checked.
- **MYTH 4 — "adapt to the learner's style / more PrepTests = more points."** Learning-styles matching is
  debunked (see memo 01); and prep-score associations are **quasi-experimental**, not causal [18]. We
  frame every claim as association + measured effect in our own harness, never as a guaranteed lift.

## Proposed features

All six **extend** an existing model rather than duplicate it, and each names the exact seam. Two
shared, one-time enabling changes recur (both additive, both sync-clean):

> **(a) A continuous per-item difficulty (`b`).** `LSAT Item` today carries only a 3-level ordinal
> `difficulty` (easy/medium/hard → +1/0/−1 in `lsat/models/performance.py::_difficulty_ord`). A real
> IRT difficulty is a scalar. Add an optional `b_difficulty` field (float) to `LSAT Item` in
> `lsat/notetypes.py`; when absent, fall back to the ordinal (fully backward-compatible). F1/F4/F5 use
> it; the performance model already treats difficulty as a covariate, so this is a drop-in refinement.
> **(b) Reuse the existing capture hook.** Every feature logs through the proven
> `pycmd("lsatAnswer:<LETTER>")` → `append_event(...)` path (`lsat/notetypes.py`, `lsat/events.py`) —
> append-only, HLC-ordered, one note per attempt — so nothing touches the sync/conflict contract.

---

### F1 — ZPD Item Selector: re-rank the queue to the ~85% "desirable-difficulty" sweet spot

- **Pitch.** Keep the points-at-stake queue's _topic_ priorities, but among the cards it surfaces, serve
  the one whose **predicted P(correct) is closest to ~85%** — the empirically fastest place to learn —
  instead of blindly serving whatever is due (often the hardest card in the weakest topic, the _opposite_
  of the region of proximal learning).
- **Mechanism.** After `points_at_stake_queue` returns its ranked `PointsAtStakeEntry` list
  (`rslib/src/scheduler/points_at_stake.rs`), a thin Python re-rank (`lsat/selection.py`) scores each
  candidate `value(card) = points(card) · zpd(P̂)`, where `P̂ = PerformanceModel.predict(top_tag,
  item.difficulty, timing_z≈0)` and `zpd(P̂) = exp(−(P̂ − τ)² / 2σ²)` peaks at a tunable target `τ≈0.85`
  (band ~0.75–0.90). The learner still studies the highest-value _topics_, but at the difficulty where
  learning is fastest; too-easy and too-hard cards are down-weighted, not hidden. `τ`, `σ` are config.
- **Theory + citations.** The 85% Rule: for gradient-descent learners on binary classification, learning
  rate is maximized at ~85% accuracy (15.87% error) and is _exponentially_ faster than fixed difficulty
  (Wilson et al. 2019 [14]) — **MODERATE for humans** (a theoretical/neural-net result, not a classroom
  RCT; treat 85% as a tunable target). Humans given free choice learn fastest on the _easiest
  not-yet-mastered_ items and spend most time on _medium_ difficulty, with a jROL stop rule (Metcalfe &
  Kornell 2005/2003 [15]) — **STRONG (8 experiments + replications)**; complements Bjork's desirable
  difficulties. **Evidence: STRONG (human study-choice) / MODERATE (the exact 85% figure).**
- **LSAT fit.** The exam is a graded speed–accuracy task; a student stuck on only-hardest items in their
  weakest type stalls, while trivially-easy items waste the tight prep window. Targeting each type's
  personal sweet spot maximizes learning per item — and the Khan data says weaker starters (who sit
  furthest below their ZPD) gain the most [18].
- **Implementability.** `lsat/selection.py` (new, pure Python) wrapping the existing
  `col.sched.points_at_stake_queue(...)` call in `lsat/events.py::points_at_stake`; reads
  `PerformanceModel.predict` (`lsat/models/performance.py`) and the item `difficulty`/`b_difficulty`
  field. **No Rust change for v1** (re-rank the returned entries); an optional v2 pushes `τ` into
  `best_points` in `points_at_stake.rs` for a single-pass Rust sort. Ablation: a `+zpd` arm in
  `eval/ablation.py` at equal study budget, primary metric = held-out P(correct), `bootstrap_ci`.
  **Effort: S–M.**
- **Novelty.** The current queue (`points = weight·(1−mastery)`) **ignores item difficulty entirely** —
  it ranks by topic weakness and serves due cards in FSRS order. This adds the difficulty axis the queue
  lacks, turning "study your weakest type" into "study your weakest type _at the difficulty where you
  learn fastest_." Anki has no difficulty-targeted selection; no LSAT product (7Sage/LSAT Demon/
  PowerScore/LawHub) tunes item difficulty to a per-skill ~85% target. Deliberately the **inverse** of
  F4 (measure at 0.5).
- **Risks / failure modes.** _The 85% figure is model-derived, not a human RCT_ — expose `τ` as an
  ablatable config and let `eval/` pick it. _`P̂` is only as good as the performance model_ — abstain to
  plain points-at-stake ordering when a topic lacks evidence (reuse the give-up gate). _Coarse ordinal
  difficulty_ blurs the target until per-item `b` exists (enabling change a). _Over-narrowing_ (never
  seeing hard items) — keep a band + occasional stretch items; F4/F5 still expose full-range items for
  measurement.

---

### F2 — Bayesian Knowledge Tracing: a real per-skill mastery posterior feeding the queue

- **Pitch.** Replace the queue's recency-weighted accuracy with a **Bayesian Knowledge Tracing** posterior
  `P(mastered)` per skill — a 4-parameter model that separates _guessing_ and _slipping_ from true
  mastery, giving a better weakness estimate on sparse data and a principled "mastered at ≥0.95" signal.
- **Mechanism.** For each taxonomy node, fit BKT's four parameters — prior `P(L0)`, learn `P(T)`, guess
  `P(G)`, slip `P(S)` — from that skill's _ordered_ attempt sequence (`read_events` is already HLC-sorted),
  and update `P(L_t)` after every graded answer. `topic_weights_for_queue` then passes
  `perf_mastery = P(mastered)` instead of the recency fold — identical output contract, so the Rust queue
  and readiness model are unchanged. A skill crossing `P(L_t) ≥ 0.95` is flagged "mastered" (feeds F6).
- **Theory + citations.** BKT is the interpretable standard: a 2-state HMM, four parameters, mastery
  threshold ~0.95 (Corbett & Anderson 1994/1995 [6]) — **STRONG/foundational (2,000+ citations)**. Its
  guess/slip terms are exactly what raw accuracy conflates. **Anti-overfitting is the whole point:** deep
  knowledge tracing's edge is largely an evaluation artifact and an extended BKT matches it [7][8], and a
  single user's per-skill sequences are far too short for an RNN — so we use **few, bounded parameters**.
  BKT's Markov-chain form is only 3-identifiable (the identifiability problem; van de Sande 2013, after
  Beck & Chang 2007 [9]), so we **bound** `P(G)<0.3`, `P(S)<0.1` and share priors across skills.
  **Evidence: STRONG.**
- **LSAT fit.** LSAT skills are drilled repeatedly across items — the exact repeated-practice setting BKT
  was built for. Guessing matters concretely: best-of-five means a not-mastered student is right ~20% by
  chance, which the current recency-accuracy fold credits as partial mastery; BKT's `P(G)` discounts it,
  so the queue stops prematurely "graduating" a skill the student is really just guessing.
- **Implementability.** New `lsat/models/knowledge_tracing.py` (pure Python; EM or a bounded grid search
  at 0.01 grain, the EDM-standard fitting approach) reading `read_events`; swap it into
  `lsat/events.py::topic_weights_for_queue` behind a config flag, blending with `fold_recent_performance`
  when `n` is small (graceful cold-start). Surface `P(mastered)` per skill in `lsat/dashboard_data.py`.
  **No Rust change** (same `(tag, weight, perf_mastery)` triples). Validate held-out next-answer AUC vs
  the recency fold in `eval/` (reuse `eval/metrics.py::auc`, `bootstrap_ci`; must beat the fold by
  `PERF_MIN_DELTA_AUC` before it's trusted). **Effort: M.**
- **Novelty.** The queue's mastery today is `fold_recent_performance` — a recency-weighted _accuracy_ with
  no guess/slip model and no learning-transition dynamics. BKT adds a principled latent-mastery posterior
  and a defensible mastery criterion. Anki has FSRS (memory of a _card_) but no per-_skill_ knowledge
  tracing; competitors show raw per-type accuracy, not a guess-corrected mastery probability.
- **Risks / failure modes.** _Identifiability / degeneracy on sparse single-user data_ — bound
  guess/slip, use hierarchical priors, abstain below a per-skill event floor (mirror the give-up rule).
  _BKT ignores forgetting_ — that is FSRS's job; keep the blend `mastery = f(FSRS recall, BKT P(mastered))`
  exactly as the Rust queue already blends recall+perf. _A wrong mastery flag mis-gates F6_ — require a
  minimum event count + keep F6 a soft gate.

---

### F3 — Cognitive-Diagnosis Attribute Profile: infer hidden prerequisite mastery from response patterns

- **Pitch.** Fit a **cognitive diagnostic model** (DINA/G-DINA) over the taxonomy's cross-cutting skills
  and flaw catalog to infer a **binary mastered/not-mastered profile of latent _attributes_** — e.g.
  "conditional logic: not mastered" — from the _pattern_ of right/wrong answers across item types, even
  for attributes the learner never sees a dedicated item for.
- **Mechanism.** The taxonomy's `cross_cutting[].appears_in` map (`lsat-taxonomy.yaml`) **is already a
  Q-matrix** (attribute × question-type): `skill.conditional_logic` → {sufficient/necessary assumption,
  parallel, inference, principle, flaw, cannot-be-true}, etc. DINA models each item as conjunctive ("need
  _all_ its required attributes to answer right, modulo guess/slip"); EM estimates per-item guess/slip and
  a **posterior over each attribute's mastery**. Output: a per-attribute mastered/not badge + probability,
  which pinpoints the _root-cause_ subskill dragging down many surface types, and feeds F6's gate and the
  dashboard.
- **Theory + citations.** DINA is the tractable, interpretable CDM (de la Torre 2009 [11]); G-DINA
  generalizes it and subsumes DINA/DINO (de la Torre 2011 [12]) — **STRONG/mature psychometrics.** CDMs
  are only as good as the Q-matrix: misspecification biases guess/slip and lowers classification accuracy
  (Rupp & Templin 2008 [13]) — so we start from the **expert** taxonomy Q-matrix and validate. **Evidence:
  STRONG (method) / the fit is MODERATE on sparse single-user data — so abstain when thin.**
- **LSAT fit.** LR/RC performance is driven by a small set of reusable competencies (conditional logic,
  quantifiers, conclusion-vs-evidence, structural reading) that cut across many question types. A student
  who is "weak at Sufficient Assumption _and_ Parallel _and_ Must-Be-True" usually has one latent hole —
  conditional logic — that a per-type accuracy table never names. CDM surfaces the shared cause.
- **Implementability.** New `lsat/models/diagnosis.py` (pure Python DINA EM) whose Q-matrix is built
  directly from `Taxonomy.cross_cutting[].appears_in` + `flaw_catalog` (`lsat/taxonomy.py`), reading item
  `skill_tags` and `read_events`. Surface the attribute profile in `lsat/dashboard_data.py` →
  `qt/aqt/lsat_dashboard.py` + `ts/routes/lsat-dashboard/`; feed F6. **No Rust change.** **Effort: M–L**
  (EM + Q-matrix validation is the cost).
- **Novelty.** This is a **latent-attribute** model inferred from _correctness patterns via a Q-matrix_ —
  categorically different from sibling **memo 03's F3** (which _counts observed chosen-distractor trap
  labels_: "you pick extreme-language 38% of the time") and **memo 01's F1** (distractor-rejection cards).
  Those describe _observed_ error frequencies on items you saw; CDM infers _unobserved prerequisite-skill
  mastery_ that explains errors across types. Complementary — trap-frequency (03) says _what_ you pick,
  CDM says _which underlying skill is missing_. Neither Anki nor mainstream LSAT products fit a diagnostic
  classification model.
- **Risks / failure modes.** _Q-matrix misspecification_ [13] — validate the expert map empirically, let
  the checker flag items whose observed difficulty contradicts their attributes. _DINA's conjunctive
  assumption may be wrong_ — offer G-DINA as the general fallback. _Sparse single-user data → wide
  posteriors_ — abstain per attribute until enough items load it (give-up pattern), and never hard-gate on
  a low-confidence attribute. _Attribute overlap with BKT (F2)_ — F2 tracks a skill's mastery _over time_;
  F3 infers a _joint attribute profile_ from a cross-section — run both, reconcile on the dashboard.

---

### F4 — Adaptive Measurement Probe: a mini-CAT that measures ability at P≈0.5, not 0.85

- **Pitch.** A "measure my level" mode that selects the **most informative** next item at the current
  ability estimate (for a Rasch model, the item where **P(correct)≈0.5**) to pin down each topic's ability
  with the **fewest items** — tightening the readiness interval and clearing the give-up gates roughly
  _twice as fast_ as random practice.
- **Mechanism.** Given the performance model's current ability for a topic, the probe picks the due item
  whose difficulty maximizes Fisher information — under the 1PL/Rasch form the model already uses,
  `I(θ) ∝ P·(1−P)`, maximized at `P=0.5` — administers it, updates the ability, and repeats until the
  standard error hits a target (or coverage is met). It is a deliberately **harder** stream than F1's
  learning queue. The resulting sharp ability estimates flow straight into `readiness.monte_carlo`,
  shrinking the projected-score band and satisfying `min_timed_items` / coverage / ECE gates with far
  fewer questions.
- **Theory + citations.** IRT-based adaptive testing reaches equal precision with far fewer items by
  administering only informative items — Weiss (1982): adaptive tests needed **~half the items for equal
  reliability and ~one-third for equal validity**, with real-data batteries as low as **18%** of fixed
  length (Brown & Weiss 1977) [10] — **STRONG (decades of simulation + live studies).** The key nuance,
  and the reason this is a _separate_ engine from F1: **maximum information is at P≈0.5, which is not the
  learning optimum (~0.85)** [10][14]. **Evidence: STRONG (measurement efficiency).**
- **LSAT fit.** Prep time is scarce and the readiness give-up rule demands **≥150 graded + ≥40 timed
  items with good coverage** before it will show a number (`lsat-taxonomy.yaml`; `readiness.give_up`).
  A CAT-style probe reaches a trustworthy, tight projected 120–180 with the _fewest_ questions — the exact
  efficiency the honesty contract needs — and mirrors how a real diagnostic/PrepTest localizes a scorer.
- **Implementability.** New `lsat/models/adaptive_probe.py` (pure Python): an information-maximizing
  item selector over due `LSAT Item`s using `PerformanceModel` (`lsat/models/performance.py`) and per-item
  `b_difficulty` (enabling change a; the current 3-level ordinal makes targeting coarse — an honest
  motivation for continuous `b`). A "Measure my level" reviewer session logs timed events via
  `append_event`, then re-runs `build_readiness`. **No Rust change** (it only chooses which due card to
  show next). **Effort: M.**
- **Novelty.** `readiness.monte_carlo` today _passively simulates_ a random scored mix from whatever
  evidence exists; it never _chooses_ which item to ask next. F4 makes measurement **active and adaptive**,
  the standard CAT move, and is explicitly the **difficulty-inverse of F1** — a distinction most study apps
  blur. Anki has nothing adaptive-testing-shaped; competitors give fixed-form PrepTests, not a
  Fisher-information probe.
- **Risks / failure modes.** _Coarse difficulty_ caps information targeting until per-item `b` is
  calibrated — start with the ordinal, refine. _Measuring ≠ learning_ — this mode is for assessment, not
  study; keep it separate from F1 and cap its share of a session. _Content exposure / boredom at P≈0.5_ —
  it feels hard by design; frame it as a short "level check," not daily practice. _Single-user ability
  drift_ — re-probe periodically; the estimate is a snapshot, and readiness already logs a track record
  (`lsat/models/projections.py`).

---

### F5 — Realistic Section Simulator + Adaptive Pacing Policy (current 2-LR + 1-RC format)

- **Pitch.** A full, timed **mock section** faithful to the _current_ format (two scored LR + one RC, 35
  min each, within-section difficulty ramp), plus a data-driven **pacing policy** — when to skip-and-
  return, when to guess-and-move — that trains the speed–accuracy tradeoff the LSAT actually scores.
- **Mechanism.** The sim assembles a section from the item bank matching the taxonomy's
  `scored_sections: ["LR","LR","RC"]` mix and typical counts (~25 LR / ~27 RC), imposes the 35-minute
  clock and a rising difficulty ramp, and tracks a **pacing policy**: given time-left and questions-left,
  it recommends/enforces skip-and-return and a guess threshold, and measures **speededness** (how many
  items go unattempted vs missed). Raw score → 120–180 via the existing `raw_to_scaled` equating table.
  Every answer is a timed `append_event`, feeding the performance model's `timing_z` covariate, the
  `skill.pacing` competency, and the readiness `min_timed_items` gate.
- **Theory + citations.** Current format verified against LSAC — two scored LR + one RC + one unscored;
  Analytical Reasoning removed Aug 2024 [16][17] — **STRONG (official).** LR is ~2/3 of the score and
  each 35-min LR section is ~24–26 Q (≈**1:24 per question**), difficulty tending to rise within a
  section [16][19][20] — **STRONG (LSAC time) / MODERATE (prep-community pacing norms, flagged
  `[market-grounding]`).** Timed performance is the scored construct; efficient measurement of it is an
  IRT/CAT problem [10]. **Evidence: STRONG (format/timing) / MODERATE (optimal pacing policy).**
- **LSAT fit.** The exam is _heavily speeded_; two of the three scored sections are now LR, so pacing on
  LR is doubly decisive. "Bank time early, skip-and-return, never leave blanks" is the canonical high-
  scorer strategy — but no tool _optimizes and measures_ the skip/guess policy against the learner's own
  accuracy-vs-time curve. A faithful current-format simulator also stops students practicing the retired
  Logic Games or the wrong section counts.
- **Implementability.** New `lsat/section_sim.py` assembling sections from the taxonomy mix and reusing
  `lsat/interleaving.py` for order and `readiness.raw_to_scaled` for scoring; a timed reviewer session
  mode (`qt/aqt/lsat_performance.py` already captures per-item latency) and a pacing/speededness panel in
  the dashboard. Pure Python; **no Rust change.** Ablate pacing-policy variants in `eval/` (equal-time,
  `bootstrap_ci`). **Effort: M–L** (the timed session UI is the main cost).
- **Novelty.** `readiness.monte_carlo` simulates a score _distribution_ but never a _timed section a human
  sits_; there is no pacing engine anywhere in the stack. This is **distinct from sibling memo 03's F5**
  (per-item time-budget ratcheting + a Choke Index + an opt-in anxiety-writing tool): F5 here is the
  _whole-section simulation reproducing the exam structure_ plus a _strategic skip/guess policy_ and a
  _speededness metric_; memo 03's is per-item pressure + choke diagnosis. They **compose** — 03's Choke
  Index can read F5's timed section data. Competitors sell timed PrepTests but not an optimized,
  measured pacing _policy_.
- **Risks / failure modes.** _Item-bank size_ — a faithful section needs enough calibrated items; degrade
  to shorter sets and flag it. _Pacing policy is a heuristic_ — expose thresholds as config and let `eval/`
  tune them; don't over-promise an "optimal" policy. _Equating is a documented approximation_ (LSAC
  equates per form; `raw_to_scaled` is a labelled table, `readiness.py`) — never present the section score
  as an official scaled score; keep the ±3 band. _Simulation caveat_ — like `eval/ablation.py`, any
  policy benefit is synthetic until a real A/B.

---

### F6 — Mastery-Gated Advanced Item Types (soft prerequisite gating)

- **Pitch.** Hold back the rarest, hardest item types (Parallel Reasoning, Parallel Flaw, Method-of-
  Reasoning) until the learner has **mastered their prerequisite attributes** — so effort goes to the
  foundations that unlock them, rather than grinding advanced items whose sub-skills aren't in place.
- **Mechanism.** The taxonomy's `appears_in` map inverts into a prerequisite graph (e.g. Parallel/Parallel
  Flaw depend on `skill.conditional_logic` + `skill.argument_parts` + relevant `flaw_catalog` attributes).
  Until those prerequisites read "mastered" (BKT `P(L_t)≥0.95` from F2 and/or CDM "mastered" from F3), the
  advanced type's queue weight is **softly down-weighted** (a multiplier, not a hard block); as
  prerequisites are mastered, the gate opens and the advanced type rises in the queue. Fully configurable;
  the gate is advisory and always overridable.
- **Theory + citations.** Mastery learning is a moderate, well-replicated effect (~**0.52**), larger for
  weaker students (Kulik, Kulik & Bangert-Drowns 1990 [5]) — **STRONG (108-study meta-analysis)** — and
  its ITS incarnation is knowledge-tracing-to-a-0.95-criterion (Corbett & Anderson [6]). Bloom's mastery
  component was ~1σ [1]. **Honest ceiling + caution:** the same meta-analysis warns mastery learning
  **increases time-on-task** and **self-paced mastery can reduce completion** [5] — so we **soft-gate**,
  never hard-lock, and never gate the F4 measurement mode. **Evidence: STRONG (mastery effect) / the
  gating _policy_ is MODERATE.**
- **LSAT fit.** Parallel Reasoning, Parallel Flaw and Method are the **rarest** LR types (~1–4% each) and
  the most time-expensive [19][20]; they are multi-step structural mappings that _presuppose_ conditional
  logic and clean conclusion/premise identification. Drilling them before the prerequisites are solid is
  low-ROI; sequencing foundations first is exactly where mastery learning + the region of proximal
  learning agree.
- **Implementability.** A prerequisite table derived from `Taxonomy.cross_cutting[].appears_in`
  (`lsat/taxonomy.py`) + a small `prereqs` block in `lsat-taxonomy.yaml`; the gate is a multiplier applied
  in `lsat/events.py::topic_weights_for_queue` (or in F1's re-rank), reading F2/F3 mastery. **No Rust
  change** (it only reshapes the weights already passed to the RPC). Dashboard shows the locked/unlocked
  ladder. **Effort: S–M.**
- **Novelty.** The current queue has **no notion of prerequisites** — every type competes purely on
  `weight·(1−mastery)`. F6 adds a curriculum structure (the `appears_in` map already encodes it) so the
  sequence respects skill dependencies. Anki has no prerequisite graph; LSAT courses _suggest_ an order
  but don't _gate on measured prerequisite mastery_. Distinct from all sibling proposals.
- **Risks / failure modes.** _Over-gating starves coverage the readiness model needs_ — keep it soft,
  cap the down-weight, and **exempt F4's measurement probe** (which must sample all types). _Reduced
  completion / motivation_ [5] — surface the "why this is locked + the 2 skills to unlock it" so it
  motivates rather than frustrates; make it opt-out. _Wrong prerequisite map_ — start from the expert
  taxonomy, validate that mastering prereqs actually predicts advanced-type accuracy (an `eval/` check)
  before trusting the gate. _Mastery-flag error from F2/F3_ — require minimum evidence + keep overridable.

## Ranked shortlist (best first)

1. **F1 — ZPD Item Selector.** Highest leverage-to-effort: a small Python re-rank that fixes a real
   defect (the queue ignores difficulty and tends to serve the hardest card in the weakest topic), backed
   by the strongest human evidence here (region of proximal learning [15]) plus the 85% Rule [14].
   **Evidence: STRONG/MODERATE.**
2. **F2 — Bayesian Knowledge Tracing.** Upgrades the queue's mastery signal from recency-accuracy to a
   guess/slip-aware posterior with a principled 0.95 criterion; interpretable, low-parameter, and the
   textbook anti-overfitting choice over DKT [6][7][8]. Enables F6. **Evidence: STRONG.**
3. **F4 — Adaptive Measurement Probe.** Cheap, high-value: reaches a trustworthy readiness projection with
   ~half the items [10], and its measure-at-0.5 vs learn-at-0.85 contrast is a clean, defensible design
   story. **Evidence: STRONG (efficiency).**
4. **F5 — Section Simulator + Pacing Policy.** Directly targets the exam's defining speededness on the
   _current_ format; strong on format/timing, moderate on the optimal policy; larger UI build.
   **Evidence: STRONG (format) / MODERATE (policy).**
5. **F3 — CDM Attribute Profile.** The most differentiated diagnostic (latent prerequisite mastery via the
   taxonomy Q-matrix), but the fit is data-hungry for a single user and Q-matrix-sensitive [11][12][13];
   ship report-only first. **Evidence: STRONG (method) / MODERATE (single-user fit).**
6. **F6 — Mastery-Gated Advanced Types.** Useful sequencing structure on top of F2/F3, but gated last
   because over-gating can hurt completion/coverage [5]; soft, configurable, and dependent on F2/F3 being
   trustworthy. **Evidence: STRONG (mastery effect) / MODERATE (policy).**

## Threats to validity (what the debate should attack — and my answers)

- **"You're promising ITS/2-sigma magic."** No — I explicitly cap the honest ceiling at tutoring d≈0.37 /
  ITS 0.66 / mastery 0.52 [2][4][5], and validate on held-out exam-style items (`eval/`), never on local
  practice items where effects inflate [4].
- **"These models overfit one user's sparse log."** That's why every model is low-parameter and bounded:
  BKT (4 params, bounded guess/slip) not DKT [7][8][9]; DINA/G-DINA seeded from the expert Q-matrix with
  per-attribute abstention [11][13]; all reuse the existing give-up/abstain discipline.
- **"85% is not a human law."** Conceded — it's a neural-net/theoretical result [14]; I ship `τ` as an
  ablatable config and lean on the _human_ region-of-proximal-learning evidence [15] for the direction.
- **"F1 and F4 contradict each other."** By design — F1 _teaches_ at ~0.85, F4 _measures_ at ~0.5; keeping
  them separate is the correct psychometrics [10][14], and most apps get this wrong.
- **"F3 duplicates memo 03's error diagnosis / F5 duplicates its pacing."** No — F3 infers _latent
  prerequisite mastery_ from correctness patterns (vs 03's _observed chosen-distractor counts_), and F5 is
  a _whole-section simulator + pacing policy_ (vs 03's _per-item budget + choke/anxiety_). Both compose
  with 03; I flag the seams so the debate can merge deliberately.
- **"The eval is synthetic."** True today (documented in `eval/ablation.py`); I ship pre-registered,
  equal-time, `bootstrap_ci` designs with ablatable parameters — the same honesty stance as the existing
  `INTERLEAVE_BONUS`, pending a real A/B.

## Sources

_Every source below was retrieved and read via web search this pass (2026-07-01); effect sizes are quoted
from the retrieved text. `[provenance-only]` = named for provenance, its claim carried by a retrieved
source. `[market-grounding]` = prep-community/secondary source for an LSAT-format fact, not peer-reviewed._

**Mastery learning, tutoring & the "2 sigma" critique.**

1. Bloom, B. S. (1984). The 2 Sigma Problem: The Search for Methods of Group Instruction as Effective as
   One-to-One Tutoring. _Educational Researcher, 13_(6), 4–16.
   https://doi.org/10.3102/0013189X013006004 · PDF: https://gwern.net/doc/psychology/1984-bloom.pdf
2. Nickow, A., Oreopoulos, P., & Quan, V. (2020). The Impressive Effects of Tutoring on PreK-12 Learning:
   A Systematic Review and Meta-Analysis of the Experimental Evidence. _NBER Working Paper 27476_
   (pooled d = 0.37 SD, 96 RCTs). https://www.nber.org/papers/w27476 · https://doi.org/10.3386/w27476
3. VanLehn, K. (2011). The Relative Effectiveness of Human Tutoring, Intelligent Tutoring Systems, and
   Other Tutoring Systems. _Educational Psychologist, 46_(4), 197–221 (human d = 0.79, ITS d = 0.76;
   refutes the believed 0.3/1.0/2.0 ladder). https://doi.org/10.1080/00461520.2011.611369
4. Kulik, J. A., & Fletcher, J. D. (2016). Effectiveness of Intelligent Tutoring Systems: A Meta-Analytic
   Review. _Review of Educational Research, 86_(1), 42–78 (median d = 0.66; 0.73 local vs 0.13
   standardized tests). https://doi.org/10.3102/0034654315581420
5. Kulik, C.-L. C., Kulik, J. A., & Bangert-Drowns, R. L. (1990). Effectiveness of Mastery Learning
   Programs: A Meta-Analysis. _Review of Educational Research, 60_(2), 265–299 (mean d = 0.52, 108
   evaluations; stronger for weaker students; self-paced can cut completion).
   https://doi.org/10.3102/00346543060002265 · PDF:
   https://www.uky.edu/~gmswan3/575/kulik_kulik_Bangert-Drowns_1990.pdf

**Knowledge tracing.**
6. Corbett, A. T., & Anderson, J. R. (1994/1995). Knowledge Tracing: Modeling the Acquisition of
Procedural Knowledge. _User Modeling and User-Adapted Interaction, 4_(4), 253–278 (2-state HMM; four
params L0/T/G/S; mastery ~0.95). https://doi.org/10.1007/BF01099821
7. Piech, C., Bassen, J., Huang, J., Ganguli, S., Sahami, M., Guibas, L., & Sohl-Dickstein, J. (2015).
Deep Knowledge Tracing. _NeurIPS 28_, 505–513 (Assistments AUC 0.86 vs BKT 0.69; "25% gain").
https://proceedings.neurips.cc/paper/2015/file/bac9162b47c56fc8a4d2a519803d51b3-Paper.pdf ·
arXiv:1506.05908
8. Khajah, M., Lindsey, R. V., & Mozer, M. C. (2016). How Deep is Knowledge Tracing? _EDM 2016_
(properly-run BKT = 0.73 not 0.67; extended BKT indistinguishable from DKT; "may be a domain that does
not require depth"). https://arxiv.org/abs/1604.02416 · PDF:
https://educationaldatamining.org/EDM2016/proceedings/paper_144.pdf
9. van de Sande, B. (2013). Properties of the Bayesian Knowledge Tracing Model. _Journal of Educational
Data Mining, 5_(2), 1–10 (BKT Markov-chain form is a 3-parameter exponential → the identifiability
problem of Beck & Chang 2007 `[provenance-only]`).
https://jedm.educationaldatamining.org/index.php/JEDM/article/download/35/pdf_27 ·
https://doi.org/10.5281/zenodo.3554630

**IRT / computerized adaptive testing.**
10. Weiss, D. J. (1982). Improving Measurement Quality and Efficiency with Adaptive Testing. _Applied
Psychological Measurement, 6_(4), 473–492 (adaptive tests need ~½ the items for equal reliability,
~⅓ for equal validity; real-data battery as low as 18% — Brown & Weiss 1977).
https://doi.org/10.1177/014662168200600408

**Cognitive diagnostic models.**
11. de la Torre, J. (2009). DINA Model and Parameter Estimation: A Didactic. _Journal of Educational and
Behavioral Statistics, 34_(1), 115–130. https://doi.org/10.3102/1076998607309474
12. de la Torre, J. (2011). The Generalized DINA Model Framework. _Psychometrika, 76_(2), 179–199.
https://doi.org/10.1007/s11336-011-9207-7
13. Rupp, A. A., & Templin, J. (2008). The Effects of Q-Matrix Misspecification on Parameter Estimates and
Classification Accuracy in the DINA Model. _Educational and Psychological Measurement, 68_(1), 78–96.
https://doi.org/10.1177/0013164407301545

**Optimal difficulty / region of proximal learning.**
14. Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for
optimal learning. _Nature Communications, 10_, 4646 (optimal training error 15.87% ≈ 85% accuracy;
exponentially faster than fixed difficulty; neural-net/theoretical, not a classroom RCT).
https://doi.org/10.1038/s41467-019-12552-4
15. Metcalfe, J., & Kornell, N. (2005). A Region of Proximal Learning model of study time allocation.
_Journal of Memory and Language, 52_(4), 463–477 (study high→low JOL, easiest-unlearned first; jROL
stop rule). https://doi.org/10.1016/j.jml.2004.12.001 · companion: Metcalfe & Kornell (2003), _JEP:
General, 132_(4), 530–542 (most study time to medium-difficulty). https://doi.org/10.1037/0096-3445.132.4.530

**LSAT format & prep (official + market).**
16. LSAC. What to Expect Starting With the August 2024 LSAT (verbatim: "two scored Logical Reasoning (LR)
sections, one scored Reading Comprehension (RC) section, plus one unscored section").
https://www.lsac.org/blog/what-to-expect-starting-with-august-2024-lsat · Changes coming Aug 2024:
https://www.lsac.org/lsat/lsat-changes-coming-august-2024
17. LSAC. FAQ / Specifications of the LSAT and LSAT Argumentative Writing (current four-section format;
35-min sections; 120–180). https://www.lsac.org/lsat/frequently-asked-questions-about-lsat ·
https://www.lsac.org/lsat/register-lsat/accommodations/specifications-lsat-and-lsat-argumentative-writing
· corroboration (AR→LR2 changed the mean score ~1/100 pt over 218,243 exams): Reuters (2023-10-18)
https://www.reuters.com/legal/legalindustry/law-school-admission-test-drop-logic-games-questions-exam-2023-10-18/
18. Dustman, K., Camilli, G., & Gallagher, A. (2021). LSAT Takers and Khan Academy Preparation (RR 21-01)
(90th-vs-10th-pct practice time = +4.3 pts, ES 0.40; 9–10 practice exams = +7.26 pts, β = .21;
quasi-experimental; lower-baseline students gain most).
https://www.lsac.org/sites/default/files/research/LSAT-Test-Taker-Khan-Preparation_RR-21-01_full-report.pdf
· SSRN: https://ssrn.com/abstract=3845015
19. `[market-grounding]` LR question-type frequency (Assumptions/Flaws/Strengthen-or-Weaken ≈15.4% each,
~46% combined; Parallel/Matching ~4% each). ScoreGap: https://scoregap.com/guides/lsat-question-type-frequency
· test-ninjas: https://test-ninjas.com/lsat-logical-reasoning-question-types
20. `[market-grounding]` LR pacing & counts (~24–26 Q per 35-min LR section ≈ 1:24/question; ~75–80 scored
questions; LR ≈ ⅔ of the score). Magoosh: https://magoosh.com/lsat/how-does-lsat-scoring-work/ ·
Kaplan: https://www.kaptest.com/study/lsat/whats-tested-on-the-lsat/
