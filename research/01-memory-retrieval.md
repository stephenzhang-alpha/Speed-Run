# Memory & Retrieval Science — Research & Feature Proposals

**Researcher 01 lens:** memory & retrieval science _beyond_ basic spacing/interleaving (we already ship
FSRS spacing + type interleaving). Scope: the testing effect / retrieval practice, feedback timing,
successive relearning, desirable difficulties, the generation effect, self-explanation / elaborative
interrogation, retrieval-induced forgetting, competitive-distractor retrieval, errorful generation /
productive failure, and pretesting (the "prequestion" effect) — each mapped to LSAT mechanics and to
our real stack (`lsat/events.py`, `lsat/notetypes.py`, `lsat/ai/`, `lsat/models/`, points-at-stake,
the dashboard).

**Research-integrity note.** Every empirical source below was located via web search and read from a
captured full-text page or the article's abstract/results (not cited from memory); numbers/effect
sizes are quoted from those retrieved texts. Foundational papers named only for provenance (e.g.
Slamecka & Graf 1978; Kapur 2008) are carried by retrieved meta-analyses and are labelled
`[provenance-only]`. LSAT-format facts are from the official LSAC site and flagged as such.

**Coordination with sibling proposals (avoid duplication for the debate stage).** Proposal **B**
(`research/proposals/B-metacognition-blind-review.md`) already owns _metacognition/calibration_, the
_hypercorrection error queue_, _blind review_, and a one-time _self-explanation autopsy_. Proposal
**C** owns _transfer/argument schemas_. So although hypercorrection and self-explanation appear in my
findings (they are memory science), **my five features are deliberately the retrieval/feedback/
relearning _scheduling_ mechanics that B and C do not cover**, and I flag every point of contact.

---

## Current-LSAT grounding (verified 2026, official LSAC)

Since the **August 2024** change, the multiple-choice LSAT is **two scored Logical Reasoning (LR)
sections + one scored Reading Comprehension (RC) section + one unscored variable section** (LR or RC),
four 35-minute sections with a 10-minute intermission; **Analytical Reasoning ("Logic Games") was
permanently removed**. Scale remains **120–180**; a separate unscored **Argumentative Writing** task is
taken remotely. Sources: LSAC FAQ [32] and LSAC "Changes coming August 2024" [33]. **Implications for
this lens:** (1) the scored test is now **~2/3 Logical Reasoning** — reasoning-error retrieval is worth
double; (2) **RC is ~1/3 and rising** — pre-reading priming (pretesting) matters more than in the
Logic-Games era; (3) the test is **speeded** (35 min/section), so any "desirable difficulty" we add
must not simply make timed performance worse without a durable-learning payoff.

---

## Key findings

Each bullet: **claim** · citation(s) · specific number/effect size · **evidence rating**
(`strong` = meta-analytic/replicated · `moderate` · `weak` · `contested`).

- **Retrieval practice (the testing effect) beats restudy for durable retention.** Rowland (2014),
  _Psychological Bulletin_ [2]: meta-analysis of **159 effect sizes / 61 studies**, overall
  **g = 0.50**, and **81% of comparisons favored testing**; benefits grow when initial retrieval
  success is high (>~75%), and **recall tests beat recognition tests**. Adesope, Trevisan &
  Sundararajan (2017), _Review of Educational Research_ [3]: **118 articles / 272 effect sizes /
  15,427 participants**, **g = 0.61 (fixed) / 0.70 (random)** vs non-testing and **g = 0.51 vs
  restudy**. Seminal demonstration on prose passages: Roediger & Karpicke (2006) [1] — at 5 min
  restudy wins, but at **2 days / 1 week testing wins substantially**, even though restudy made
  students _feel_ more confident (an illusion-of-competence warning). **STRONG.**

- **For an all-multiple-choice exam, well-built MC retrieval practice is as strong as it gets — but
  only if the distractors are competitive.** Adesope et al. (2017) [3] found **multiple-choice
  practice tests produced a _large_ effect (g = 0.70), larger than short-answer (g = 0.48)** and
  mixed formats (g = 0.80) — reconciling with Rowland's "recall > recognition" via test _quality_:
  Little, Bjork, Bjork & Angello (2012), _Psychological Science_ [21] show MC tests trigger
  **productive retrieval only when incorrect options are _plausible/competitive_** — learners then
  retrieve _why the right answer is right AND why each wrong answer is wrong_, which also improves
  later recall of the _distractor-related_ material (cued-recall tests did **not** do this). Benefits
  persisted over a 48-h delay and beat a time-on-task control (Little & Bjork 2015 [22]); a classroom
  replication found gains for **both tested and non-tested related** content with **no** net
  retrieval-induced forgetting (Bjork, Little & Storm 2014 [23]). **STRONG** — and unusually
  on-target, because the LSAT _is_ best-of-five with engineered competitive traps.

- **The _timing_ of feedback is a manipulable lever — and it is genuinely contested.** In
  multiple-choice learning, **delayed** feedback often beats **immediate** on a delayed final test
  because it spaces the correct-answer presentation: Butler, Karpicke & Roediger (2007),
  _JEP: Applied_ [4] found **delayed feedback → superior delayed cued-recall**, and answer type
  (standard vs answer-until-correct) _didn't matter_. But the applied literature disagrees: Kulik &
  Kulik (1988) [5] — classroom studies usually favor _immediate_ feedback; Smith & Kimball (2010) [6]
  reviewed 39 studies (**16 favored delayed, 12 immediate, 11 null**). **CONTESTED/MODERATE** →
  ship feedback timing as a _measured, configurable knob_, not a dogma.

- **Successive relearning — retrieval to a mastery criterion across multiple _spaced_ sessions —
  produces exceptionally durable memory.** Rawson, Dunlosky & Sciartelli (2013), _Educational
  Psychology Review_ [8]; Rawson & Dunlosky (2011) [9]. Rawson, Vaughn, Walsh & Dunlosky (2018) [10]:
  one session → **~20% recall at 1 week**; **3 spaced relearning sessions to mastery → ~80% at 1 week
  (Cohen's d ≈ 4.19)** and 77% at 3 weeks. Classroom: Janes et al. (2020) [11] boosted exam learning
  **by ≥10% (ds 0.54–1.10)**. **STRONG**, with an honest caveat: when time-on-task is _matched_, the
  effect shrinks (Higham et al. 2022, **d ≈ 0.28**, per [8]) — the cost is time.

- **"Learning" ≠ "performance": conditions that slow you down now can raise durable learning
  (desirable difficulties).** Soderstrom & Bjork (2015), _Perspectives on Psychological Science_ [12];
  Bjork & Bjork (2011) [13]. Current (timed, in-session) performance is an _unreliable_ index of
  learning; manipulations that add errors during acquisition often _increase_ long-term retention.
  **STRONG** as a framework — with the crucial boundary condition that a difficulty is only
  "desirable" if the learner can actually overcome it.

- **The generation effect: producing an answer beats reading it.** Bertsch, Pesta, Wiscott &
  McDaniel (2007), _Memory & Cognition_ [14]: meta-analysis of **445 effect sizes / 86 studies /
  17,711 subjects**, overall **d = 0.40** (~half an SD, called an underestimate), robust but
  moderated. Seminal: Slamecka & Graf (1978) [15] `[provenance-only]`. **STRONG.**

- **Self-explanation ("why is the right answer right / each wrong answer wrong?") is a robust
  booster — and can be computer-prompted.** Bisra, Liu, Nesbit, Salimi & Winne (2018), _Educational
  Psychology Review_ [16]: random-effects **g = 0.55, 95% CI [0.45, 0.65]** over **69 effect sizes /
  64 reports / 5,917 participants**; the authors explicitly recommend **computer-generated
  self-explanation prompts** — i.e., our AI pipeline. Elaborative interrogation is a close cousin of
  similar magnitude. In Dunlosky et al. (2013) [17], self-explanation and elaborative interrogation
  rate **MODERATE** utility (vs **HIGH** for practice testing & distributed practice). **MODERATE→STRONG.**

- **Errorful generation & productive failure: attempting (and often failing) _before_ instruction
  can help — for the right content.** Kornell, Hays & Bjork (2009), _JEP: LMC_ [24]: an unsuccessful
  retrieval attempt before seeing the answer beat read-only, _even on items guessed wrong_. Sinha &
  Kapur (2021), _Review of Educational Research_ [25]: meta-analysis of **53 studies / 166
  comparisons**, problem-solving-then-instruction over instruction-then-problem-solving
  **g = 0.36 (95% CI 0.20–0.51)**; **g = 0.37–0.58** with high productive-failure fidelity;
  **g ≈ 0.87** after correcting for publication bias. Kapur (2008) [26] `[provenance-only]`.
  **MODERATE-STRONG**, with sharp boundary conditions: it needs **corrective feedback** and
  **semantically related** material, and it **did not help procedural knowledge (g = −0.03)** or
  younger learners. (Favorable for adult, conceptual, transfer-heavy LR.)

- **Pretesting / the prequestion effect: being quizzed _before_ studying improves later memory of the
  quizzed material.** Richland, Kornell & Kao (2009), _JEP: Applied_ [27]: pretesting beat
  extended study even for **non-retrieved** items, controlling for attention direction (bolding).
  Pan & Carpenter (2023), _Educational Psychology Review_ [28]: 60+ studies; benefits persist
  **≥24 h (text passages ≥7 days)**, with reported **d ≈ 0.44 to >2.0 for the tested information**.
  **STRONG for tested content**, with a key caveat: pretesting **does NOT reliably generalize to
  untested/related** material (unlike post-testing) — so prequestions must target exactly what you
  want learned.

- **High-confidence errors are corrected _more_ readily than low-confidence errors
  (hypercorrection).** Butterfield & Metcalfe (2001), _JEP: LMC_ [29]; Metcalfe (2017), _Annual
  Review of Psychology_ [30]. Counterintuitively, being **sure-and-wrong** is the highest-yield
  correction target; the effect holds at immediate and delayed retest (caveat: confident errors can
  _return_ if the correction is later forgotten). **STRONG.** _(Feature ownership: this powers
  Proposal B's hypercorrection queue; I cite it only to justify **which** errors my
  distractor/relearning features should prioritize.)_

- **Retrieval-induced forgetting (RIF): practicing a subset can suppress related non-retrieved
  items — a caution for over-drilling "the right answer."** Murayama, Miyatsu, Buchli & Storm (2014),
  _Psychological Bulletin_ [18]: **512 samples**, overall **g = 0.35 (95% CI 0.32–0.38)**, fail-safe
  **N = 56,111** (very robust existence; mechanism debated). Anderson, Bjork & Bjork (1994) [19].
  **Design implication:** _integrated/elaborated_ encoding **reduces** RIF (Anderson & McCulloch
  1999 [20]), and competitive-MC practice showed **no** net RIF in the classroom [23] — so a feature
  that makes the learner _relate_ distractors to the correct answer is the RIF-safe design. **STRONG.**

### Myth / "that-doesn't-work" warnings (required)

- **Learning styles are a myth — do NOT build modality "matching."** Pashler, McDaniel, Rohrer &
  Bjork (2008), _Psychological Science in the Public Interest_ [31]: after reviewing the literature,
  **"virtually no evidence"** supports the meshing hypothesis (teach to a learner's preferred
  modality → better learning); several well-designed studies **contradict** it. **DEBUNKED.** Any
  "we adapt to your learning style" framing would be pseudoscience and is off-limits.
- **Passive re-reading, highlighting, and cramming create fluency illusions, not durable learning.**
  Dunlosky et al. (2013) [17] rate **rereading, highlighting/underlining, and summarization LOW
  utility**; Roediger & Karpicke (2006) [1] show restudy _feels_ better but loses to testing at a
  delay; Soderstrom & Bjork (2015) [12] show massed practice inflates immediate performance without
  durable learning. **Implication:** never reward re-exposure to explanations as if it were study —
  make the substrate _graded retrieval_.

---

## Proposed features

All five extend (not re-propose) what exists: the append-only `LSAT PerformanceEvent` log
(`lsat/events.py`: `append_event(...)`, `read_events`, `fold_recent_performance`,
`topic_weights_for_queue`), the `LSAT Item`/`LSAT Card` notetypes and the `pycmd("lsatAnswer:…")`
capture hook (`lsat/notetypes.py`, `qt/aqt/lsat_performance.py`), the generate→check→gate AI pipeline
with a **verbatim source-span** requirement (`lsat/ai/{generator,checker,pipeline,prompts}.py`), the
logistic/IRT performance model with a `timing_z` covariate (`lsat/models/performance.py`), FSRS memory
(`lsat/models/memory.py`), the points-at-stake queue (`rslib/src/scheduler/points_at_stake.rs`, fed by
`topic_weights_for_queue`), the taxonomy tags incl. `skill.trap.*` (`lsat-taxonomy.yaml`), and the
Svelte/Qt dashboard + `eval/` harness.

> **Shared enabling change (small, one-time): capture the chosen distractor.** Today the reviewer hook
> _knows_ the chosen letter (`chosen` in `qt/aqt/lsat_performance.py::_on_js_message`) but
> `append_event(...)` **discards it** — `EVENT_FIELDS` stores only `correct`/`response_ms`. Add a
> **`chosen`** field to the `LSAT PerformanceEvent` notetype (a one-time notetype _schema_ change in
> `ensure_notetypes`) and a `chosen=` arg on `append_event`. Every event stays append-only + HLC-ordered
> (sync-clean). Features 1 and 3 read it. _(This composes cleanly with Proposal B's proposed
> `phase`/`confidence` fields on the same notetype.)_

---

### Feature 1 — Trap Retrieval: spaced "why is (X) wrong?" distractor cards, aimed at the traps you actually fall for

- **One-line pitch.** Turn each missed LSAT item into a set of durable, spaced **distractor-rejection
  retrieval** cards — one per plausible wrong option — prioritized toward the specific trap _letters_
  the learner empirically chooses.
- **Mechanism (what the learner does).** After a graded `LSAT Item`, the app records the chosen letter.
  For missed (or confidently-wrong) items, the AI pipeline emits, per competitive distractor, a
  micro-card: _"In this argument, why is (C) wrong?"_ The learner must **retrieve and state the
  rejection rationale** (short free text or a "pick-the-flaw-in-the-trap" MC), then sees the
  source-grounded answer. These become `LSAT Card`s tagged with the question type **and** `skill.trap.*`,
  entering FSRS + points-at-stake so the trap patterns you keep choosing get surfaced first.
- **Theory + citations.** Competitive-distractor MC drives retrieval of _why-wrong_ and aids related
  material (Little, Bjork, Bjork & Angello 2012 [21]; Little & Bjork 2015 [22]; classroom, no net RIF:
  Bjork, Little & Storm 2014 [23]) — **STRONG**; MC practice large effect (Adesope g = 0.70 [3]);
  articulating the rationale is self-explanation (Bisra g = 0.55 [16], which _recommends_
  computer-generated prompts) — **MODERATE→STRONG**. Integrating distractors with the correct answer is
  the RIF-safe design (Anderson & McCulloch 1999 [20]).
- **LSAT fit.** The LSAT is best-of-five with _engineered_ traps; "explain why each wrong answer is
  wrong" is the canonical high-scorer habit, and we already have a `skill.trap.*` taxonomy. Targeting the
  learner's _actual_ wrong-letter distribution turns a generic drill into a personal weakness hunter.
- **Implementability (files/data, effort M).** Needs the shared **`chosen`** field (above). New AI
  `card_type: "distractor_rejection"` in `lsat/ai/{prompts,generator}.py`, gated by the existing verbatim
  span checker (`lsat/ai/checker.py`) so a rationale must cite the stimulus; optionally precompute a
  `choice_explanations` field on `LSAT Item`. Trap-granular priority via `topic_weights_for_queue`
  (Python-only; no Rust change). Dashboard: per-trap mastery bars (`lsat/dashboard_data.py`,
  `ts/routes/lsat-dashboard/`).
- **Novelty.** Anki has no distractor modelling; our AI pipeline currently generates from _source text_,
  not from the learner's _own error pattern per option_. **Vs Proposal B Feature 3** (a one-time,
  student-_written_ autopsy): this is **AI-generated, checker-gated, per-distractor _retrieval_ cards that
  live in FSRS/points-at-stake and are steered by the empirically chosen letter** — complementary, not
  duplicative. Competitor LSAT apps show static per-choice explanations; none schedule spaced
  distractor-rejection retrieval keyed to your trap profile.
- **Risks / failure modes.** (a) _RIF / over-drilling the correct answer_ — mitigate by the
  integrate-the-distractor framing [20] and the no-net-RIF competitive-MC result [23]. (b) _Cards teach
  item-specific trivia, not transferable traps_ — mitigate with pattern-level phrasing + trap tags + the
  checker's non-triviality gate. (c) _Generation cost / quality_ — the existing quality gate
  (`eval/config.py` pass/wrong-rate) already guards this; degrade gracefully (pipeline already skips a bad
  batch). Measure with an `eval/` ablation: future error rate on the _same trap_ with vs without trap cards.

---

### Feature 2 — Delayed Elaborated Feedback: schedule the explanation as its own spaced event (a configurable feedback-timing knob)

- **One-line pitch.** Decouple _grading_ from _explanation_: instead of instantly flashing the full
  rationale, re-present the stem + the learner's own answer + the elaborated explanation as a **spaced
  feedback event** — with the immediate-vs-delayed timing a measured setting.
- **Mechanism.** On answering, show minimal correctness (or, for a "blind" set, withhold it). The
  elaborated explanation is enqueued as a separate feedback review later that session / next day. When it
  surfaces, the learner re-sees their (possibly wrong) choice and must re-engage with the correct
  reasoning before it's revealed.
- **Theory + citations.** Delayed feedback can beat immediate on delayed MC tests by spacing the
  correct-answer presentation (Butler, Karpicke & Roediger 2007 [4]); feedback timing is otherwise
  **CONTESTED** (Kulik & Kulik 1988 [5]: classrooms favor immediate; Smith & Kimball 2010 [6]:
  16 delayed / 12 immediate / 11 null). Withholding the key until re-engagement also blocks the
  re-reading fluency illusion (Roediger & Karpicke 2006 [1]; Dunlosky 2013 [17]). Rating **MODERATE/
  CONTESTED** — hence a _knob_, not a fixed policy.
- **LSAT fit.** The current Item template reveals the correct letter **instantly** (`_ITEM_AFMT` in
  `lsat/notetypes.py`); a spaced feedback pass spaces the correct-reasoning presentation and prevents
  "I read the explanation, so I know it" fluency — exactly the trap that inflates practice-test optimism.
- **Implementability (files/data, effort M).** The answer hook already fires
  (`qt/aqt/lsat_performance.py`); add a lightweight feedback-event scheduler (a due `LSAT Card` clone or a
  small per-collection queue) with a `feedback_delay` config; reuse the item's `explanation` or generate
  one via `lsat/ai/`. **Because the evidence is contested, wire immediate vs delayed as an `eval/`
  ablation arm** (mirroring `eval/ablation.py`) and let the data pick the default.
- **Novelty.** Anki reveals the back on flip; there is no delayed-feedback scheduling anywhere in the
  stack, and no LSAT competitor treats feedback _timing_ as a manipulable variable. Distinct from B and C.
- **Risks / failure modes.** (a) _The evidence is mixed_ — be honest; make it configurable + measured.
  (b) _Learners ignore delayed corrections_ — make the feedback event mandatory and re-present their own
  wrong pick (raises attention). (c) _Session complexity_ — default to a single same-session delay; keep
  a pure-immediate mode.

---

### Feature 3 — Pattern Mastery Loops: successive relearning of missed reasoning patterns with _fresh_ items

- **One-line pitch.** A missed reasoning pattern (e.g. `lr.flaw.causal`, or a specific trap) opens a
  **relearning loop**: you must correctly answer **fresh** items of that pattern on **N separated days**
  before it counts as "relearned" — a criterion loop _above_ FSRS.
- **Mechanism.** On a miss, the pattern enters "relearning." Each subsequent day, the queue serves a
  _new_ item of that pattern (not the same card); a correct, reasonably-paced answer advances the streak;
  a miss resets it. Reaching the criterion (say 3 correct on 3 separated sessions) marks the pattern
  relearned and releases queue pressure.
- **Theory + citations.** Successive relearning = spaced retrieval to a mastery criterion across sessions;
  it is one of the most durable known techniques (Rawson, Dunlosky & Sciartelli 2013 [8]; Rawson &
  Dunlosky 2011 [9]; Rawson et al. 2018 [10] — **~80% at 1 week, d ≈ 4.19** vs ~20% single-session;
  Janes et al. 2020 [11]: **≥10% course-exam gains**). **STRONG**, with the honest time-cost caveat
  (time-matched **d ≈ 0.28** [8]). Using _fresh_ items each cycle recruits the transfer/generation
  benefit ([14]) rather than memorizing one item.
- **LSAT fit.** LR/RC skills are _patterns_ that recur across arbitrary surface topics — the exam is a
  transfer test — so "relearn the pattern to criterion across days with new items" fits the LSAT far
  better than per-card FSRS alone, and complements Proposal C's schema work.
- **Implementability (files/data, effort M–L).** New `lsat/relearning.py`: read per-node history from
  `read_events`/`fold_recent_performance`, track a per-pattern correct-retrieval streak keyed on **distinct
  HLC wall-days**, pull fresh items from the item bank / `lsat/ai/` generator, and set a `relearned` flag
  that feeds `topic_weights_for_queue` (raise weight until relearned; Python-only). Dashboard: a
  relearning-progress panel.
- **Novelty.** FSRS schedules a _single card's_ next review; it does **not** enforce a cross-session
  mastery criterion over a _pattern_ with _fresh_ items. No Anki construct and no LSAT competitor does
  criterion-based successive relearning. Distinct from B (calibration) and C (schema), though it can carry
  C's schemas as the "pattern."
- **Risks / failure modes.** (a) _Time cost_ (state it plainly; the time-matched effect is smaller). (b)
  _Fresh-item supply/quality_ — depends on the AI pipeline; the existing quality gate + graceful
  degradation apply. (c) _Criterion tuning_ (N, spacing) — expose as config; start from Rawson's ~3×.
  (d) _Interference from over-focusing one pattern_ — cap concurrent loops. Measure via `eval/` on
  delayed P(correct) for relearned vs FSRS-only patterns at matched budget.

---

### Feature 4 — Prime-then-Read: pretests/prequestions before an RC passage or a new LR pattern

- **One-line pitch.** Before a dense RC passage (or a new LR concept), serve 1–3 **prequestions** the
  learner will probably miss; they commit a guess, then read/learn, then see the answers — priming
  encoding of exactly what we want learned.
- **Mechanism.** Prequestion → learner commits (guessing is expected and low-stakes) → passage/instruction
  → **answers revealed and studied**. Both the guess and the post-read attempt are logged.
- **Theory + citations.** Pretesting improves later memory of quizzed content even when the pretest is
  failed (Richland, Kornell & Kao 2009 [27], controlling for attention direction; Kornell, Hays & Bjork
  2009 [24]); benefits persist **≥24 h / text ≥7 days**, **d ≈ 0.44 to >2.0** for tested info (Pan &
  Carpenter 2023 [28]). **STRONG for tested content**, with the explicit caveat that it **does not
  reliably generalize to untested material** — so prequestions must target the exact skill/inference.
- **LSAT fit.** RC is now ~1/3 of the scored test and rising; priming attention before a hard passage is
  high-value, and LR benefits from prequestioning the specific flaw/inference before the stimulus analysis.
- **Implementability (files/data, effort M).** New AI `card_type: "prequestion"` bound to a passage
  `source_id` (checker-gated verbatim span). Reviewer flow: prequestion → reveal → passage → graded items;
  **enforce the answer-reveal step** (Richland: the correction must be studied). Log both attempts via
  `append_event`.
- **Novelty.** SRS is inherently _retrospective_ (test after study); pre-study testing is an architectural
  addition. Not present in Anki or (as a scheduled feature) in LSAT competitors. Distinct from B and C.
- **Risks / failure modes.** (a) _No generalization to untested material_ — target precisely; measure
  transfer separately. (b) _Frustration at guaranteed-fail items_ — frame as priming, keep stakes zero.
  (c) _Must actually study the answer afterward_ — enforce in the flow. Measure with an `eval/` arm:
  passage-item accuracy with vs without a preceding prequestion.

---

### Feature 5 — Commit-First Drills: errorful generation / productive failure before the worked method

- **One-line pitch.** When introducing a **new** reasoning skill, make the learner **generate and commit**
  an answer + one-line rationale to a hard item **before** the expert method/schema is shown.
- **Mechanism.** Present a hard target item → learner commits an answer and a one-line reason (captured via
  `pycmd`) → _then_ reveal the source-grounded worked method. Problem-solving precedes instruction.
- **Theory + citations.** Unsuccessful pre-instruction retrieval beats read-only, even when wrong
  (Kornell, Hays & Bjork 2009 [24]); the generation effect **d = 0.40** (Bertsch et al. 2007 [14]);
  productive failure meta-analysis **g = 0.36 (CI 0.20–0.51)**, up to **0.87** corrected (Sinha & Kapur
  2021 [25]; Kapur 2008 [26] `[provenance-only]`). **MODERATE-STRONG**, with hard boundary conditions:
  it needs **corrective feedback** and **semantically related** content, and **did not help procedural
  knowledge (g = −0.03)** or young learners — favorable for adult, conceptual, transfer-heavy LR.
- **LSAT fit.** LR is conceptual/transfer (the regime where productive failure works best); a committed
  generation attempt activates prior knowledge and primes encoding of the schema — pairs naturally with
  Proposal C's argument schemas and with Feature 4.
- **Implementability (files/data, effort M).** Reuse `LSAT Item` with a two-phase reveal: capture the
  pre-instruction commit via a new `pycmd("lsatCommit:…")` branch in `qt/aqt/lsat_performance.py`, then
  show an AI-generated, checker-gated worked method (store in the card `explanation`). Log the commit as an
  event.
- **Novelty.** Standard SRS shows Q→A (a single generation); this is a _designed_ problem-solving-before-
  instruction sequence with the pre-instruction attempt captured. Distinct from B (calibration) and C
  (schema/contrasting cases), though it can wrap C's schemas.
- **Risks / failure modes.** (a) _Ineffective/negative for procedural or feedback-poor designs_ — restrict
  to conceptual LR/RC and always follow with strong instruction (enforce reveal). (b) _Frustration/time_ —
  keep it to skill-introduction, not every item. (c) _Difficulty must be surmountable_ to stay a
  _desirable_ difficulty (Soderstrom & Bjork [12]) — calibrate item difficulty (we have per-item
  `difficulty`). Measure with an `eval/` arm: schema retention/transfer for commit-first vs method-first.

---

## Ranked shortlist (best first)

1. **Trap Retrieval (Feature 1).** Highest LSAT specificity and strongest evidence (competitive-MC
   distractor retrieval [21][22][23] + self-explanation [16]); reuses the AI pipeline + trap taxonomy;
   only needs the small `chosen`-letter capture. Biggest differentiated payoff.
2. **Pattern Mastery Loops (Feature 3).** Durable-learning heavyweight (successive relearning [8][10])
   and a genuinely new construct above FSRS; effort M–L, honest time-cost caveat.
3. **Prime-then-Read (Feature 4).** Strong, well-replicated, and aimed at the _growing_ RC share of the
   test; architecturally novel (pre-study testing). Watch the no-generalization caveat.
4. **Commit-First Drills (Feature 5).** Solid conceptual-LR fit (generation + productive failure), but
   heterogeneous evidence and boundary conditions → ship as a skill-introduction augment.
5. **Delayed Elaborated Feedback (Feature 2).** Cheapest and a nice honesty story, but the evidence is
   contested → best framed as a measured knob rather than a headline feature.

---

## Sources (all located via web search and read from captured text / abstracts unless marked)

1. Roediger, H. L., & Karpicke, J. D. (2006). _Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention._ Psychological Science, 17(3), 249–255. <https://doi.org/10.1111/j.1467-9280.2006.01693.x>
2. Rowland, C. A. (2014). _The Effect of Testing Versus Restudy on Retention: A Meta-Analytic Review of the Testing Effect._ Psychological Bulletin, 140(6), 1432–1463. <https://doi.org/10.1037/a0037559>
3. Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). _Rethinking the Use of Tests: A Meta-Analysis of Practice Testing._ Review of Educational Research, 87(3), 659–701. <https://doi.org/10.3102/0034654316689306>
4. Butler, A. C., Karpicke, J. D., & Roediger, H. L. (2007). _The Effect of Type and Timing of Feedback on Learning From Multiple-Choice Tests._ Journal of Experimental Psychology: Applied, 13(4), 273–281. <https://doi.org/10.1037/1076-898X.13.4.273>
5. Kulik, J. A., & Kulik, C.-L. C. (1988). _Timing of Feedback and Verbal Learning._ Review of Educational Research, 58(1), 79–97. <https://doi.org/10.3102/00346543058001079>
6. Smith, T. A., & Kimball, D. R. (2010). _Learning From Feedback: Spacing and the Delay–Retention Effect._ Journal of Experimental Psychology: Learning, Memory, and Cognition, 36(1), 80–95. <https://www.ou.edu/memorylab/pdfs/SmithKimball_2010_LearningFromFeedback_ms.pdf>
7. Butler, A. C., & Roediger, H. L. (2008). _Feedback enhances the positive effects and reduces the negative effects of multiple-choice testing._ Memory & Cognition, 36(3), 604–616. <https://doi.org/10.3758/MC.36.3.604> _(found in the Adesope [3] & Bjork-lab reference lists; supports Feature 2 qualitatively)_
8. Rawson, K. A., Dunlosky, J., & Sciartelli, S. M. (2013). _The Power of Successive Relearning: Improving Performance on Course Exams and Long-Term Retention._ Educational Psychology Review, 25(4), 523–548. <https://doi.org/10.1007/s10648-013-9240-4>
9. Rawson, K. A., & Dunlosky, J. (2011). _Optimizing schedules of retrieval practice for durable and efficient learning: How much is enough?_ Journal of Experimental Psychology: General, 140(3), 283–302. <https://doi.org/10.1037/a0023956>
10. Rawson, K. A., Vaughn, K. E., Walsh, M., & Dunlosky, J. (2018). _Investigating and Explaining the Effects of Successive Relearning on Long-Term Retention._ Journal of Experimental Psychology: Applied, 24(1), 57–71. <https://doi.org/10.1037/xap0000146>
11. Janes, J. L., Dunlosky, J., Rawson, K. A., & Jasnow, A. M. (2020). _Successive relearning improves performance on a high-stakes exam in a difficult biopsychology course._ Applied Cognitive Psychology, 34(5), 1118–1132. <https://doi.org/10.1002/acp.3699>
12. Soderstrom, N. C., & Bjork, R. A. (2015). _Learning Versus Performance: An Integrative Review._ Perspectives on Psychological Science, 10(2), 176–199. <https://doi.org/10.1177/1745691615569000>
13. Bjork, E. L., & Bjork, R. A. (2011). _Making Things Hard on Yourself, But in a Good Way: Creating Desirable Difficulties to Enhance Learning._ In _Psychology and the Real World_ (pp. 56–64). <https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/04/EBjork_RBjork_2011.pdf>
14. Bertsch, S., Pesta, B. J., Wiscott, R., & McDaniel, M. A. (2007). _The generation effect: A meta-analytic review._ Memory & Cognition, 35(2), 201–210. <https://doi.org/10.3758/BF03193441>
15. Slamecka, N. J., & Graf, P. (1978). _The generation effect: Delineation of a phenomenon._ Journal of Experimental Psychology: Human Learning and Memory, 4(6), 592–604. `[provenance-only, via 14]`
16. Bisra, K., Liu, Q., Nesbit, J. C., Salimi, F., & Winne, P. H. (2018). _Inducing Self-Explanation: A Meta-Analysis._ Educational Psychology Review, 30(3), 703–725. <https://doi.org/10.1007/s10648-018-9434-x>
17. Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). _Improving Students' Learning With Effective Learning Techniques._ Psychological Science in the Public Interest, 14(1), 4–58. <https://doi.org/10.1177/1529100612453266>
18. Murayama, K., Miyatsu, T., Buchli, D., & Storm, B. C. (2014). _Forgetting as a Consequence of Retrieval: A Meta-Analytic Review of Retrieval-Induced Forgetting._ Psychological Bulletin, 140(5), 1383–1409. <https://doi.org/10.1037/a0037505>
19. Anderson, M. C., Bjork, R. A., & Bjork, E. L. (1994). _Remembering Can Cause Forgetting: Retrieval Dynamics in Long-Term Memory._ Journal of Experimental Psychology: Learning, Memory, and Cognition, 20(5), 1063–1087. <https://doi.org/10.1037/0278-7393.20.5.1063>
20. Anderson, M. C., & McCulloch, K. C. (1999). _Integration as a general boundary condition on retrieval-induced forgetting._ Journal of Experimental Psychology: Learning, Memory, and Cognition, 25(3), 608–629. <https://doi.org/10.1037/0278-7393.25.3.608>
21. Little, J. L., Bjork, E. L., Bjork, R. A., & Angello, G. (2012). _Multiple-Choice Tests Exonerated, at Least of Some Charges: Fostering Test-Induced Learning and Avoiding Test-Induced Forgetting._ Psychological Science, 23(11), 1337–1344. <https://doi.org/10.1177/0956797612443370>
22. Little, J. L., & Bjork, E. L. (2015). _Optimizing multiple-choice tests as tools for learning._ Memory & Cognition, 43(1), 14–26. <https://doi.org/10.3758/s13421-014-0452-8>
23. Bjork, E. L., Little, J. L., & Storm, B. C. (2014). _Multiple-choice testing as a desirable difficulty in the classroom._ Journal of Applied Research in Memory and Cognition, 3(2), 90–99. <https://doi.org/10.1016/j.jarmac.2014.03.002>
24. Kornell, N., Hays, M. J., & Bjork, R. A. (2009). _Unsuccessful Retrieval Attempts Enhance Subsequent Learning._ Journal of Experimental Psychology: Learning, Memory, and Cognition, 35(4), 989–998. <https://doi.org/10.1037/a0015729>
25. Sinha, T., & Kapur, M. (2021). _When Problem Solving Followed by Instruction Works: Evidence for Productive Failure._ Review of Educational Research, 91(5), 761–798. <https://doi.org/10.3102/00346543211019105>
26. Kapur, M. (2008). _Productive Failure._ Cognition and Instruction, 26(3), 379–424. <https://doi.org/10.1080/07370000802212669> `[provenance-only, via 25]`
27. Richland, L. E., Kornell, N., & Kao, L. S. (2009). _The Pretesting Effect: Do Unsuccessful Retrieval Attempts Enhance Learning?_ Journal of Experimental Psychology: Applied, 15(3), 243–257. <https://doi.org/10.1037/a0016496>
28. Pan, S. C., & Carpenter, S. K. (2023). _Prequestioning and Pretesting Effects: A Review of Empirical Research, Theoretical Perspectives, and Implications for Educational Practice._ Educational Psychology Review, 35, 97. <https://doi.org/10.1007/s10648-023-09814-5>
29. Butterfield, B., & Metcalfe, J. (2001). _Errors Committed With High Confidence Are Hypercorrected._ Journal of Experimental Psychology: Learning, Memory, and Cognition, 27(6), 1491–1494. <https://doi.org/10.1037/0278-7393.27.6.1491>
30. Metcalfe, J. (2017). _Learning from Errors._ Annual Review of Psychology, 68, 465–489. <https://doi.org/10.1146/annurev-psych-010416-044022>
31. Pashler, H., McDaniel, M., Rohrer, D., & Bjork, R. (2008). _Learning Styles: Concepts and Evidence._ Psychological Science in the Public Interest, 9(3), 105–119. <https://doi.org/10.1111/j.1539-6053.2009.01038.x>
32. LSAC — _Frequently Asked Questions about the LSAT_ (official; retrieved 2026). <https://www.lsac.org/lsat/frequently-asked-questions-about-lsat>
33. LSAC — _Changes are coming to the LSAT in August 2024_ (official; retrieved 2026). <https://www.lsac.org/lsat/lsat-changes-coming-august-2024>
