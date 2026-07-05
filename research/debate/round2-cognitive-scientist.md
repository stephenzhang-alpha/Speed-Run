# Round 2 — Rebuttal & Refinement

**Speaker:** Dr. Vera Sorensen — cognitive scientist, evidence purist.
**Mode:** convergence. Concede what's right, hold what's measured, and re-engineer
the surviving features so they are _evidence-valid AND low-friction_ — because a
mechanism a burned-out test-taker won't perform at 10pm has an effect size of zero,
and a mechanism we can't measure on held-out items is a vibe.

**One breath.** The four openings converge more than they diverge. All of us
independently landed on the same tiny keystone (capture `chosen`/`confidence`/`phase`),
the same calibration+hypercorrection stack, the same distractor-reasoning flagship, the
same ZPD fix, and the same honesty instruments. Round 1 I optimized _effect size_; the
coach, engineer and advocate have correctly beaten me on _time-matched_ effect size,
_friction_, and _build cost per study-minute_. I move toward them on design and hold the
line only where the line is a _measurement_ line.

---

## 1. Concessions — where the coach, engineer, and advocate changed my mind

1. **The engineer's shared primitive is the right architecture, and I was under-costing it.**
   Priya is right that `chosen` + `confidence` + `phase` should land as **one additive,
   append-only schema bump** on `LSAT PerformanceEvent`, not three, and that `ensure_notetypes`
   won't migrate an existing collection's fields (so retrofitting forces exactly _one_ full
   sync — pay it once). I called the capture "non-negotiable" in Round 1 but treated the three
   fields as separable; they are not — batch them. I also concede her sequencing correction:
   **build order should be evidence-per-build-hour**, so the cheap Python-only wins that ride
   the primitive (calibration, hypercorrection, ZPD re-rank) ship _before_ the heavier
   AI-pipeline and relearning features, even though the latter have bigger headline effects.

2. **The advocate's "select-not-type" is right, and it changes my flagship.** Sam's core
   critique lands: my Round-1 "Trap Autopsy" leaned on _free-text_ self-explanation, and a
   stressed solo learner will not type a paragraph per item for three months — and when
   forced, the typing eats the very working memory Beilock & Carr (2005) show pressure already
   drains. My own literature contains the rebuttal: Barbieri et al. (2023) found
   self-explanation prompts _negatively_ moderated the worked-example effect. So I concede that
   free-text-every-item was adherence-naive and evidence-optional. I keep the _mechanism_
   (§3) but move it to a structured tap.

3. **The advocate's P≈0.5 warning is correct and I adopt it as a hard rule.** A mini-CAT that
   makes you wrong half the time, every day, is the _opposite_ of the region of proximal
   learning (Metcalfe & Kornell 2005) and the 85% rule (Wilson 2019). Sam is right that
   _measuring_ the student and _practicing_ the student are opposite-difficulty jobs. I fully
   endorse: **the daily engine runs at ~85% (ZPD); any P≈0.5 probe is a rare, opt-in,
   clearly-labeled level-check, capped as a small share of a session** — never the driver.

4. **The coach's timed-vs-untimed _mode declaration_ is a real design principle, not just
   pedagogy.** Marcus is right that "learning a skill" and "executing it under a stopwatch"
   are different jobs and each feature must declare its mode — and that **heavy articulation
   during _timed_ practice corrupts the pacing signal**. This is consistent with
   Soderstrom & Bjork (2015): performance ≠ learning. I concede: articulation/self-explanation
   is an **untimed-mode** interaction; under the clock it is one tap or nothing.

5. **Partial concession to the coach on Blind Review — as a _measurement instrument_.** I will
   not grant that Blind Review is evidence-based _intervention_ (it is 7Sage community practice,
   not an RCT — Proposal B says so). But I concede its best half fits _my_ philosophy: the
   `phase` field enables a **timed↔untimed honest-mastery filter** that drops lucky timed
   guesses from the mastery estimate. That is a _measurement_ correction, and I fold it into my
   calibration stack (§4, R2). The routing claims must be measured, not asserted.

---

## 2. Held positions — what I still insist on, and the evidence for it

1. **No transfer or mastery claim ships without a held-out, equal-time measurement whose
   bootstrap CI excludes 0.** This is the whole point of the Transfer Meter (Chi, Feltovich &
   Glaser 1981 established structure-vs-surface sorting as the expertise read-out; Barnett &
   Ceci 2002: report transfer as a _distance-graded curve, never a single number_). The meter is
   a **precondition** for Structure Twins, not an optional add-on. Effects inflate ~6× on local
   vs standardized outcomes (Kulik & Fletcher 2016: ITS d=0.73 local vs **0.13 standardized**),
   so the primary metric is always _unseen exam-style items_, never the drilled ones.

2. **Successive relearning is reported at the honest, time-matched number.** The headline is
   ~80% vs ~20% recall at one week, d≈4.19 (Rawson et al. 2018) — but time-matched it collapses
   to **d≈0.28** (Higham et al. 2022 via Rawson et al. 2013), and our users have _fixed_ prep
   hours. I plan around 0.28 and demand the eval hold study time equal. The engineer and coach
   are right that this feature _consumes the scarce resource_; that lowers its build priority
   (§4), but the durability evidence keeps it in the set.

3. **Calibration is monitoring-only. No Dunning–Kruger _mechanism_ claim.** Confidence≠accuracy
   is a robust _description_ on logic tasks (Kruger & Dunning 1999), and the monitoring/control
   framework is foundational (Nelson & Narens 1990) — but the DK _mechanism_ is mostly a
   statistical artefact (Gignac & Zajenkowski 2020: near-zero Glejser correlation, r≈−0.05). We
   measure _the individual's_ reliability curve and guard degenerate flat ratings with the
   Resolution/AUC check. We never assert "the weak are uniquely blind."

4. **CUT the single-user CDM (DINA/G-DINA) — reaffirmed as my strongest cut, and now
   _unanimous_.** All four of us independently cut it. Strong psychometrics (de la Torre
   2009/2011) that overfits one sparse log: you cannot validate a Q-matrix on one person
   (Rupp & Templin 2008), posteriors go wide, and a wrong "attribute not mastered" flag then
   mis-gates other features. DKT dies on the same grounds (Khajah et al. 2016: the AUC edge was
   an evaluation artifact; extended BKT is indistinguishable). If we want per-skill mastery,
   bounded BKT is the honest version — and even that must beat the recency fold on held-out AUC
   before it is trusted.

5. **Self-explanation is A/B'd, not assumed, and re-exposure is never rewarded as study.**
   Bisra et al. (2018) g=0.55 is an _average_ that Barbieri et al. (2023) shows can flip
   negative, so the why-wrong step ships against a no-prompt arm. And re-reading/highlighting
   are LOW utility (Dunlosky et al. 2013) — the substrate stays _graded retrieval_, never more
   prose. Learning-styles/modality matching remains vetoed on sight (Pashler et al. 2008).

---

## 3. Refined designs — evidence-valid _and_ low-friction

### 3a. The reconciliation the moderator asked for: a structured "why-wrong tap"

The generative benefit in self-explanation and the generation effect comes from **retrieval
and discrimination among competitors — not from the motor act of typing.** Bertsch et al.
(2007) generation effect (d=0.40) and Little/Bjork's competitive-MC results both show the
active ingredient is _producing/choosing among plausible alternatives_. So I re-cast the
autopsy as a **one-tap discriminative retrieval**:

- On a **miss or confident-wrong item only** (advocate constraint: never add friction to a
  correct answer), the app surfaces the distractor the learner actually picked and asks a
  single **competitive multiple-choice micro-question: "which trap is (C)?"** — the options are
  _plausible_ trap families drawn from `skill.trap.*` (out-of-scope, extreme-language, reversal,
  half-right, irrelevant-comparison). Because the trap-label options are themselves competitive,
  **this is not recognition of one fact — it is the same competitive-MC retrieval that earns
  Adesope's g=0.70** (Little, Bjork, Bjork & Angello 2012: the gain appears _only_ when the
  alternatives are competitive). The learner must retrieve _why (C) is wrong_ to pick its family.
- This preserves the mechanism, cuts friction to one tap (untimed _or_ timed mode), and — a bonus
  the engineer will like — it is **deterministically gradeable**, removing the noisy/gameable
  free-text AI grading and shrinking the checker's false-pass surface.
- The _one thing_ the tap sacrifices vs free-text is the depth of a produced explanation. So I
  keep an **optional one-line free-text as a sampled bonus** (untimed mode only) and
  **pre-register the A/B** — `no-tap` vs `tap-only` vs `tap+free-text` — to _measure_ whether
  produced depth adds anything over structured selection. That is the honest way to settle my
  disagreement with the advocate rather than assert it.

Note the elegant convergence: the immediate **why-wrong tap** and my spaced **Trap-Retrieval
card** are the _same competitive-MC mechanism at two moments_ — one at answer time, one on an
FSRS schedule — both keyed to the learner's empirical wrong-letter distribution (the
Trap-Profile / "Leech" fingerprint). One mechanism, one substrate (`chosen`), three features.

### 3b. Pre-registered held-out metric for every surviving feature

| Feature                              | Primary held-out metric (equal study time; bootstrap CI excludes 0)                                                                                                                                                                                                                      |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R1 Distractor-Reasoning Engine**   | Δ P(correct) on **unseen same-trap** items; **A/B**: no-tap vs tap vs tap+free-text; 2° repeat-trap rate per study-hour ↓                                                                                                                                                                |
| **R2 Calibration + Hypercorrection** | _Monitor:_ within-user ECE↓ & Resolution AUC(confidence↔correct)↑. _Control:_ delayed correction rate of high-confidence errors (γ target .3–.5) with mandatory spaced re-test; relapse rate ↓. _Honest-mastery:_ does dropping lucky-timed wins improve held-out next-answer prediction |
| **R3 ZPD Selector + Transfer Meter** | _ZPD:_ Δ P(correct) at equal budget vs points-at-stake-only, with calibration ECE ≤ `ECE_MAX`. _Meter (report-only):_ memorization gap = P(correct∣near) − P(correct∣far); structure slope β; abstains until enough new-surface items                                                    |
| **R4 Successive Relearning**         | Delayed P(correct) on relearned **patterns** with **fresh** items at **matched** budget vs FSRS-only (plan d≈0.28, not 4.19)                                                                                                                                                             |
| **R5 Structure Twins (conditional)** | Ships **only** if the Meter shows twins are valid (surface-distinct, same-`struct`) **and** twin-training lifts **far-surface** P(correct) with CI excluding 0                                                                                                                           |

All arms run through `eval/ablation.py` (equal-time, paired synthetic learners first,
`bootstrap_ci`), calibration guarded by `eval/calibration.py` (`ECE_MAX`), transfer by
`eval/leakage.py`. Synthetic today — I will label every number as methodology-pending-A/B, never
present a synthetic lift as a proven score gain.

---

## 4. Revised final set — 4 surviving + 1 conditional

Merged designs, evidence rating (my read of the _weakest necessary link_), pre-registered metric,
and **what changed from my Round 1**. Build order follows the engineer: keystone → cheap
Python wins → AI-pipeline flagship → time-costly relearning.

**Keystone (unanimous).** Per-answer annotation store: `chosen` + `confidence` + `phase` in one
additive schema bump. _Changed:_ I now treat the three fields as one batched migration and defer
`b_difficulty` to the same window only if the psychometric family survives.

**R1 — Distractor-Reasoning Engine** _(merges Round-1 CF1 Trap Autopsy + CF2 Trap Retrieval +
CF3 Trap-Profile/Leech)._ Competitive-distractor retrieval (Adesope 2017 g=0.70; Little/Bjork;
no net RIF, Bjork/Little/Storm 2014) + the structured why-wrong tap (self-explanation g=0.55,
Bisra 2018) + the empirical trap fingerprint from `chosen`.

- **Evidence:** strong (competitive-MC + self-explanation, both meta-analytic; on-target for a
  best-of-five engineered-trap exam).
- **Metric:** Δ P(correct) on unseen same-trap items; A/B tap vs free-text vs none.
- **Changed from R1:** self-explanation is now **select-not-type** (§3a); free-text demoted to
  a measured optional bonus; the standalone Trap-Profile (my old CF3) is **absorbed** here rather
  than shipped separately.

**R2 — Calibration Monitoring + Hypercorrection Spaced Queue** _(merges Round-1 S3 + S4, plus
the Blind-Review honest-mastery filter)._ One-tap confidence → reliability curve, Overconfidence
Index, Resolution AUC; queue leads with high-confidence misses and **re-tests them on a spaced
schedule** (mandatory — Butler, Fazio & Marsh 2011: confident errors _return_ without
re-practice); the `phase` field drops lucky timed wins from mastery.

- **Evidence:** strong (calibration as an _instrument_; hypercorrection robust — Butterfield &
  Metcalfe 2001, Metcalfe 2017).
- **Metric:** ECE↓ & Resolution↑; delayed correction rate γ (target .3–.5); relapse ↓.
- **Changed from R1:** I **merged** calibration and hypercorrection into one stack (they are the
  instrument and its controller), **conceded the `phase` capture**, and folded in the timed↔untimed
  honest-mastery filter as _measurement_. Never invokes the DK mechanism.

**R3 — ZPD Selector + Transfer Meter** _(Round-1 CF18 + CF15)._ Among due cards serve predicted
P(correct)≈0.85 (Metcalfe & Kornell 2005, 8 experiments — the strongest _human_ sequencing result;
Wilson 2019's 85% as a tunable τ, not a law); the Meter reports memorization-vs-transfer per schema.

- **Evidence:** strong (human study-choice) for ZPD; strong (measurement caution) for the Meter.
- **Metric:** Δ P(correct) at equal budget (ZPD); memorization gap & slope β (Meter, report-only).
- **Changed from R1:** essentially intact; I now foreground it as the **daily engine at 85%**,
  explicitly discharging the advocate's P≈0.5 concern, and the Meter is the gate on R5.

**R4 — Successive Relearning** _(Round-1 CF8)._ Retrieve a _pattern/trap_ to criterion across N
spaced sessions with _fresh_ items (Rawson et al. 2018; Janes et al. 2020 ds 0.54–1.10).

- **Evidence:** strong durability, but **planned at time-matched d≈0.28**.
- **Metric:** delayed P(correct) on relearned patterns at matched budget vs FSRS-only.
- **Changed from R1:** **demoted in build priority** (it _consumes_ the scarce prep window —
  engineer/coach were right); cap concurrent loops; **no streak-reset shaming** (advocate);
  the "pattern" is the trap schema so it composes with R1 rather than adding a second loop.

**R5 — Structure Twins (CONDITIONAL, my olive branch to the transfer camp).** Two
surface-different, same-structure arguments; produce the shared skeleton before the label
(Gick & Holyoak 1983; Loewenstein 1999 ~3×; Gentner 2003 47% vs 6%).

- **Evidence:** strong in _adjacent_ domains; unproven on LSAT; top risk is AI content-validity.
- **Metric:** ships **only** when the R3 Meter proves twins are valid _and_ lift far-surface accuracy.
- **Changed from R1:** unchanged in spirit (my 6th pick), now explicitly gated on R3 and on the
  `checker.py` + `gold_set` false-pass bar; **untimed mode only**, fill-by-select (advocate's WM-load
  concern).

**Dropped from my Round-1 straw-man:** none outright — I _merged_ (calibration+hypercorrection
into R2; trap-profile into R1), which tightens five ships to four core. The CUTs stand
(single-user CDM; feedback-timing as doctrine; expressive-writing as a promise).

---

## 5. Remaining disagreements for the moderator to rule on

1. **How much timed-pacing _simulation_ vs untimed _skill-building_?** The coach makes pacing the
   #1 champion (a full Section Simulator + pacing policy); the advocate warns against weaponizing
   the clock (Beilock & Carr: pressure hurts the ablest most). My position: the **format facts are
   STRONG and the Choke-Index diagnostic is evidence-grounded (Beilock 2004: automaticity is the
   anti-choke)**, so the cheap `phase`-based Choke diagnostic should ship — but the **"optimal
   pacing policy" is a heuristic (moderate)** and the heavy Section Simulator is format-engineering,
   not a learning-science novelty deserving a headline _evidence_ slot. **Rule needed:** does the
   Section Simulator earn a Round-1 build slot, or ship the Choke diagnostic now and defer the
   simulator until there's a faithful-length item bank?

2. **Is Structure Twins in the shipping set, or gated behind the Meter?** Coach concedes it as
   phase-2; engineer gates it on the checker false-pass bar; advocate flags WM load. I hold it is
   **conditional on the R3 Meter**, not a Round-1 ship. **Rule needed:** conditional (my position)
   vs a funded parallel track (engineer's Primitive-C plan).

3. **Blind Review: evidence-based _intervention_ or _diagnostic instrument_?** The coach ranks it
   a signature champion; I concede only the `phase` capture + honest-mastery filter as
   _measurement_. **Rule needed:** may Blind Review be marketed as a technique, or must its
   pressure-vs-knowledge routing be _measured_ (does routing actually improve the routed items)
   before any claim? (Adjacent: do Structure Sprints / Fluency Gates — adjacent-domain PLM, LSAT
   transfer unproven — earn a slot, or ship as an ablation arm?)

---

## 6. Summary (revised set + biggest concession + biggest held line)

- **Revised set (4 core + 1 conditional):** (R1) **Distractor-Reasoning Engine** — competitive
  distractor retrieval + a **structured why-wrong tap** + the trap fingerprint; (R2)
  **Calibration + Hypercorrection spaced queue** (merged, now carrying the `phase` honest-mastery
  filter); (R3) **ZPD selector at 85% + Transfer Meter** (the daily engine + the honesty
  instrument); (R4) **Successive Relearning** at the honest d≈0.28, demoted in priority; and
  conditionally (R5) **Structure Twins**, gated on the Meter proving valid twins lift far-surface
  accuracy.
- **Convergence:** I merged five ships into four, adopted the engineer's one-schema-bump keystone
  and evidence-per-build-hour ordering, and made the daily loop run at 85% (never P≈0.5).
- **Biggest concession:** the advocate's **"select-not-type."** My flagship self-explanation moves
  from free-text to a one-tap competitive-MC why-wrong selection (misses-only), with free-text
  demoted to an optional, _measured_ bonus — a real change to my Round-1 headline mechanism.
- **Biggest held line:** **nothing claiming transfer or mastery ships without a held-out,
  equal-time measurement whose CI excludes 0** — which is why the Transfer Meter is a precondition
  (not optional) and the single-user CDM/DKT stays cut. We are still buying honest single-digit
  points, never "2 sigma."
