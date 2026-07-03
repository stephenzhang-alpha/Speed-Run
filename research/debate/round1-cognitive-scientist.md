# Round 1 — Opening Position

**Speaker:** Dr. Vera Sorensen — cognitive scientist, evidence purist.
**Charge:** Which *novel* features should the Anki-for-LSAT app ship, ranked by empirical strength, effect size, and eval-measurability.

---

## 0. Stance in one breath

The four memos and two proposals contain ~25 distinct ideas dressed up as ~30 features. Most of the *durable* signal collapses onto a handful of mechanisms the literature has stress-tested for decades: **retrieval practice, self-explanation, successive relearning, and calibration *monitoring*.** I will champion those, ship them behind a **transfer/held-out measurement layer** so we cannot fool ourselves, and I will kill — loudly — the seductive-but-thin ideas (feedback-timing dogma, expressive-writing, learning-styles anything, and single-user latent-attribute models). Above all: **we are not buying "2 sigma." No app does.** The honest ceiling is single-digit-percentile / ~4–7 scaled points (Dustman, Camilli & Gallagher 2021; tutoring d≈0.37, Nickow et al. 2020; ITS median d≈0.66 but only **0.13 on standardized** vs 0.73 on local tests, Kulik & Fletcher 2016). Every claim below is disciplined by that ceiling.

---

## 1. Priorities — how I score every proposal

A feature earns a slot only if it clears **all five** bars. I weight them roughly in this order.

1. **Empirical strength (the gate).** `strong` = meta-analytic or independently replicated; `moderate` = a few consistent labs; `weak` = single study / large CIs; `contested` = the literature actively disagrees. I *start* a feature at its weakest necessary link, not its best headline. Meta-analysis > single lab > one advocate's pre/post gains. A `contested` mechanism cannot be a headline feature — at most a measured knob.
2. **Effect size *with its boundary conditions*.** A number is meaningless without its moderators. I want a quoted `d`/`g`, the comparison condition, and the condition under which it *fails*. A `d=4.19` that shrinks to `d=0.28` when time-on-task is matched (Rawson et al. 2018 vs Higham et al. 2022) is a `d=0.28` feature for our purposes, because our users have fixed prep hours.
3. **Eval-measurability (non-negotiable).** If I cannot name the **held-out, exam-style** metric it should move, at **equal study time**, with a **bootstrap CI that excludes 0**, it is not a feature — it is a vibe. I insist the primary metric be *unseen exam-style items*, never the drilled items, because Kulik & Fletcher (2016) show effects inflate ~6× on local vs standardized outcomes. Our `eval/ablation.py` (equal-time arms, `bootstrap_ci`) and `eval/calibration.py` (`ECE_MAX`) are the courtroom.
4. **LSAT construct fit.** The scored test is now **~2/3 Logical Reasoning + ~1/3 Reading Comprehension**, heavily speeded, best-of-five with *engineered* distractors (LSAC, Aug-2024 format — verified across all memos). Features that train the literal scored construct (structure recognition, trap elimination, calibrated speed) beat generic "study better" tooling.
5. **Resistance to overfitting and overclaiming.** Single-user desktop logs are **sparse**. Any model with many free parameters or an unvalidatable Q-matrix will memorize noise. I favor **bounded, low-parameter, abstaining** estimators, and I refuse any framing that promises broad "critical thinking" or "think faster" transfer.

**Automatic kill list (my allergies, with citations).** Learning-styles/modality matching — debunked (Pashler et al. 2008). Deliberate-practice-as-panacea — DP explains **4% of variance in education, <1% in professions** (Macnamara et al. 2014). Feedback-*timing* as a doctrine — **contested** (Kulik & Kulik 1988 favor immediate; Smith & Kimball 2010: 16 delayed / 12 immediate / 11 null). Expressive/"worry" writing — **d=0.57 then a clean null** (Ramirez & Beilock 2011 vs Myers, Davis & Chan 2021). Far-transfer / brain-training generalization — "little evidence" for distant tasks (Simons et al. 2016; Barnett & Ceci 2002: a single far-transfer effect size is "misguided"). Deep knowledge tracing / cognitive-diagnostic models on one user — DKT's edge is largely an **evaluation artifact** and an extended BKT matches it (Khajah, Lindsey & Mozer 2016).

---

## 2. Consolidated canonical candidate list (I merged the duplicates)

The memos overlap heavily — the same three or four mechanisms reappear under different names. Here is the de-duplicated set. Memo keys: **M1** = `01-memory-retrieval`, **M2** = `02-transfer-schema`, **M3** = `03-metacognition-srl`, **M4** = `04-adaptive-psychometrics`, **B** = `proposals/B-metacognition-blind-review`, **C** = `proposals/C-transfer-argument-schemas`, **R1** = `docs/research/R1-perceptual-learning`, **R2** = `docs/research/R2-error-trap-analysis`.

| # | Canonical feature | Merged from | Core mechanism | Anchor evidence |
|---|---|---|---|---|
| **CF1** | **Trap Autopsy** (prompted self-explanation: why-right / why-each-wrong) | M2-F3, B-F3, articulation steps in M1-F1 & M2-F1 | After a graded item, learner *produces* why the key is right and why each trap is wrong; AI-checker-graded | Bisra et al. 2018 (self-explanation **g=0.55**); Chi et al. 1989 |
| **CF2** | **Trap Retrieval** (spaced competitive-distractor rejection cards) | M1-F1 | One retrieval card per plausible distractor ("why is (C) wrong?"), keyed to the letters you actually pick | Little/Bjork/Bjork/Angello 2012; Little & Bjork 2015; Bjork/Little/Storm 2014 (**no net RIF**); MC practice **g=0.70** (Adesope et al. 2017) |
| **CF3** | **Trap-Susceptibility Profiling / Reasoning-Bug Diagnosis** | R2-F1, M3-F3 | Capture *chosen* distractor → tag to trap family → per-student trap fingerprint across types | Sadler 1998 (distractor = diagnosis); Thissen/Steinberg/Fitzpatrick 1989 (nominal-response IRT) |
| **CF4** | **Minimal-Pair / Predict-the-Trap Contrast Drills** (d′ retirement) | R1-F3, R2-F2 | A/B near-misses differing on *one* structural axis; predict the trap before reveal; retire on sensitivity | Kornell & Bjork 2008; Booth et al. 2013 & 2025 review (Con-ErrEx > CorrEx); Kellman et al. 2023 (d′ retirement) |
| **CF5** | **Confidence-Calibration Monitoring** | M3-F1, B-F2 (calibration half) | One-tap confidence → reliability curve, Overconfidence Index, Resolution (AUC), "sure-and-wrong" list | Nelson & Narens 1990 (framework); Kruger & Dunning 1999 (desc.); Rhodes & Castel 2008; Nelson & Dunlosky 1991 |
| **CF6** | **Hypercorrection-Prioritized *Spaced* Error Queue** | M3-F2, B-F2 (queue half), R2-F3 | Lead the queue with high-confidence misses; **re-test on a spaced schedule** | Butterfield & Metcalfe 2001; Metcalfe 2017; Eich et al. 2013 (**γ≈.51**); Butler/Fazio/Marsh 2011 (returns w/o re-practice) |
| **CF7** | **Blind-Review / Timed↔Untimed Gap Diagnostic** | B-F1 | Second untimed pass; 2×2 pressure-vs-knowledge routing | 7Sage community practice (**not a controlled trial**); mechanistic grounding in Kruger–Dunning, Metcalfe, Dunlosky |
| **CF8** | **Successive Relearning / Pattern Mastery Loops** | M1-F3 | Retrieve a *pattern* to a mastery criterion across **N spaced sessions with fresh items** | Rawson et al. 2018 (**~80% vs ~20% @1wk, d≈4.19**); Janes et al. 2020 (**+≥10%, d 0.54–1.10**); time-matched **d≈0.28** (Higham 2022) |
| **CF9** | **Pretesting / Prime-then-Read** | M1-F4 | Prequestions before an RC passage / new LR concept, then study the answer | Richland/Kornell/Kao 2009; Pan & Carpenter 2023 (**d≈0.44 to >2.0 for tested content**; no generalization to untested) |
| **CF10** | **Productive Failure / Commit-First Drills** | M1-F5 | Commit an answer+rationale to a hard item *before* the worked method | Kornell/Hays/Bjork 2009; Sinha & Kapur 2021 (**g=0.36**, up to **0.87** corrected); generation effect **d=0.40** (Bertsch 2007) |
| **CF11** | **Delayed Elaborated Feedback** (timing knob) | M1-F2 | Decouple grading from explanation; immediate-vs-delayed as a setting | Butler/Karpicke/Roediger 2007 **vs** Kulik & Kulik 1988 **vs** Smith & Kimball 2010 — **CONTESTED** |
| **CF12** | **Analogical-Comparison Schema Building** (Structure Twins / Same-Bones Pairs) | M2-F1, C-Twins | Two surface-different, same-structure arguments; *produce the shared skeleton* before the label | Gick & Holyoak 1983 (**10→30→75%**); Loewenstein et al. 1999 (**~3×**); Gentner et al. 2003 (**47% vs 6%**); Schwartz & Bransford 1998 |
| **CF13** | **Worked-Example Fading** (Faded Parallels) | M2-F2 | Worked → completion → solo ladder, backward fading + name-the-principle | Sweller & Cooper 1985 (**g≈0.48**, Barbieri 2023); Atkinson/Renkl/Merrill 2003; Kalyuga 2003 (expertise reversal) |
| **CF14** | **Argument Mapping / Skeleton Builder** | M2-F4 | Mark conclusion/premises/inferential move/flaw; gradeable map | van Gelder 2005 (**AM≈0.7** vs 0.34 generic CT — *advocate-led, quasi-exp*); Chi et al. 1981 |
| **CF15** | **Transfer Measurement Layer** (Structure Sort + Schema Transfer Meter + variability drill) | M2-F5, C-Sort, C-Meter | Score whether the learner groups by structure; report accuracy-vs-surface-distance curve per schema | Chi et al. 1981 (sorting = expertise readout); Barnett & Ceci 2002 (measure the *curve*); variability: Paas & van Merriënboer 1994 (**contested**) |
| **CF16** | **Structure Sprints** (speeded structural-classification PLM) | R1-F1 | Seconds-long "name the type/flaw/conclusion" drills, RT-scored | Kellman & Kaiser 1994; Kellman et al. 2010; Kellman 2013 (**d 0.84–2.69** adjacent); ultrasound null caveat (2023) |
| **CF17** | **Fluency Gates** (RT-aware mastery, ARTS) | R1-F2 | Retire a skill only when **accurate *and* fast**; RT drives scheduling | Mettler/Massey/Kellman 2016 (ARTS > fixed; yoked controls); Logan 1988 |
| **CF18** | **ZPD / Region-of-Proximal-Learning Item Selector** (~85%) | M4-F1 | Among due cards, serve the one with predicted P(correct)≈0.85 | Metcalfe & Kornell 2005 (**8 experiments**, STRONG); Wilson et al. 2019 (85% rule — *neural-net/theoretical*) |
| **CF19** | **Bayesian Knowledge Tracing** (per-skill mastery posterior) | M4-F2 | 4-param HMM (L0/T/G/S), mastery at ≥0.95 | Corbett & Anderson 1995 (foundational); Khajah et al. 2016 (bounded BKT ≈ DKT) |
| **CF20** | **CDM Attribute Profile** (DINA/G-DINA) | M4-F3 | Infer latent prerequisite-attribute mastery via a Q-matrix | de la Torre 2009/2011 (method STRONG); Rupp & Templin 2008 (Q-matrix misspecification) |
| **CF21** | **Adaptive Measurement Probe** (mini-CAT @ P≈0.5) | M4-F4 | Fisher-information item selection to tighten the readiness band | Weiss 1982 (**~½ items for equal reliability**) |
| **CF22** | **Mastery-Gated Advanced Item Types** (soft prereq gating) | M4-F6 | Down-weight Parallel/Method until prerequisites are mastered | Kulik/Kulik/Bangert-Drowns 1990 (mastery learning **d≈0.52**) |
| **CF23** | **Deliberate-Practice Micro-Loops** | M3-F4 | Bounded, goal-gated, edge-of-ability drill on the single weakest node | Macnamara et al. 2014 (**24% variance in high-predictability** vs 4% education); Zimmerman 2002 |
| **CF24** | **SRL Loop** (forethought → performance → reflection) | M3-F6 | Session goal + score prediction, then predicted-vs-actual reconciliation | Zimmerman 2002 (MODERATE, largely correlational); Nelson & Narens 1990 |
| **CF25** | **Pacing/Choke Trainer + Section Simulator** (+ opt-in anxiety writing) | M3-F5, M4-F5 | Tightening per-item budgets, Choke Index, full timed section, pacing policy | Beilock & Carr 2005; Beilock et al. 2004; format facts STRONG; anxiety-writing **contested** |

Two structural notes the debate must not miss. **(a)** CF4 (minimal pairs — *minimize* surface, isolate one axis, for *discrimination*) and CF12 (Structure Twins — *maximize* surface, isolate shared structure, for *abstraction*) are **opposite manipulations of the same contrasting-cases literature** for opposite goals; they are not duplicates and should not be collapsed. **(b)** CF3/CF5 are *enabling capture* (the `chosen` letter and `confidence` fields) that CF6 and much of the metacognition family depend on — one tiny append-only notetype change unlocks four features.

---

## 3. Ranked verdict

Rating = my read of the *weakest necessary link*, not the headline. Effect = the number I'd actually plan around (i.e., after boundary conditions). Call = **CHAMPION** / **CONDITIONAL** / **CUT**.

| Rank | Feature | Evidence | Effect (planning number) | Call |
|---|---|---|---|---|
| 1 | CF2 Trap Retrieval | **strong** | MC retrieval **g=0.70**; distractor-recall boost, no net RIF | **CHAMPION** |
| 2 | CF1 Trap Autopsy (self-explanation) | **strong** | **g=0.55** [.45,.65] | **CHAMPION** |
| 3 | CF8 Successive Relearning | **strong** | **d≈4.19** unmatched → **d≈0.28** time-matched | **CHAMPION** |
| 4 | CF5 Calibration *Monitoring* | **strong** (as measurement) | n/a — it's an instrument; enables CF6 | **CHAMPION** |
| 5 | CF6 Hypercorrection *Spaced* Queue | **strong** (w/ re-test) | γ≈.51; correction highest for confident errors | **CHAMPION** |
| 6 | CF18 ZPD / Region-of-Proximal-Learning | **strong** (human) / moderate (85%) | faster acquisition; fixes a real queue defect | **CHAMPION** |
| 7 | CF15 Transfer Measurement Layer | **strong** (measurement) | n/a — the honesty instrument | **CHAMPION** |
| 8 | CF12 Structure Twins | **strong** (adjacent domains) | ~3×; **47% vs 6%** transfer | **CONDITIONAL** |
| 9 | CF9 Pretesting / Prime-then-Read | **strong** (tested content only) | **d≈0.44–2.0** for tested items | **CONDITIONAL** |
| 10 | CF13 Worked-Example Fading | strong core / moderate fading | **g≈0.48** | **CONDITIONAL** |
| 11 | CF10 Productive Failure / Commit-First | moderate–strong | **g=0.36** (proc. **g=−0.03**) | **CONDITIONAL** |
| 12 | CF4 Minimal-Pair Contrast | moderate–strong | discrimination/d′ gains | **CONDITIONAL** |
| 13 | CF3 Trap Profiling | method strong / single-user thin | AUC target ≥0.65 (falsifiable) | **CONDITIONAL** |
| 14 | CF16 Structure Sprints (PLM) | moderate–strong adjacent / untested LSAT | large adjacent d; transfer unproven | **CONDITIONAL** |
| 15 | CF19 Bayesian Knowledge Tracing | strong method / sparse single-user | must beat recency fold on held-out AUC | **CONDITIONAL** |
| 16 | CF21 Adaptive Measurement Probe (CAT) | **strong** (efficiency) | ~½ items — but *measures*, not teaches | **CONDITIONAL** |
| 17 | CF17 Fluency Gates (ARTS) | moderate | efficiency gain; calibration-guarded | **CONDITIONAL** |
| 18 | CF25 Pacing / Section Sim | strong (format) / moderate (policy) | format fidelity; policy is heuristic | **CONDITIONAL** |
| 19 | CF23 Deliberate-Practice Micro-Loops | moderate | 24% variance *only* in high-predict. domains | **CONDITIONAL** |
| 20 | CF22 Mastery-Gated Advanced Types | moderate (policy) | d≈0.52 mastery, but gating risk | **CONDITIONAL** |
| 21 | CF24 SRL Loop | moderate (correlational) | thin, connective tissue | **CONDITIONAL** |
| 22 | CF14 Argument Mapping | moderate (advocate-led) | 0.7 claimed, discount heavily | **CONDITIONAL → lean CUT** |
| 23 | CF11 Delayed Elaborated Feedback | **contested** | 16/12/11 delayed/immediate/null | **CUT** (keep as knob only) |
| 24 | CF25b Expressive/anxiety writing | **contested** | d=0.57 then null | **CUT** |
| 25 | CF20 CDM Attribute Profile (single user) | method strong / overfits sparse data | unvalidatable on 1 user | **CUT** (my strongest) |

### CHAMPIONS — justification

**CF2 Trap Retrieval + CF1 Trap Autopsy** (I treat these as one shippable *Distractor-Reasoning Engine*, two evidence bases). This is the single most on-target thing in all six documents, because the LSAT *is* best-of-five with engineered traps and these two mechanisms train exactly that. Competitive multiple-choice practice produces a **large g=0.70** (Adesope, Trevisan & Sundararajan 2017), and — critically — Little, Bjork, Bjork & Angello (2012) show the gain only appears when distractors are *plausible*, because the learner then retrieves *why the right answer is right and why each wrong answer is wrong*, which also improves recall of the distractor-related material; the classroom replication (Bjork, Little & Storm 2014) found **no net retrieval-induced forgetting**. Layer on prompted self-explanation (Bisra et al. 2018, **g=0.55**, whose authors explicitly recommend computer-generated prompts — i.e., our `lsat/ai/` pipeline) and you are training the exact discrimination the test rewards. My one honest reservation: Barbieri et al. (2023) found self-explanation prompts *negatively* moderated the worked-example effect in math, so the autopsy is **not** a free add-on — it must be A/B'd against a no-prompt arm, not assumed from the 0.55 average.

**CF8 Successive Relearning.** The most durable technique in the memos, and a genuinely new construct above per-card FSRS: retrieve a *pattern* to criterion across multiple *spaced* sessions with *fresh* items. Rawson, Vaughn, Walsh & Dunlosky (2018) report **~80% recall at one week from 3 spaced relearning sessions vs ~20% from one** (Cohen's d≈4.19), and Janes et al. (2020) got **≥10% course-exam gains (ds 0.54–1.10)**. I champion it *with my eyes open*: when time-on-task is matched the effect shrinks to **d≈0.28** (Higham et al. 2022, via Rawson et al. 2013), and our users have fixed prep hours — so I plan around 0.28, not 4.19, and I demand the eval hold study time equal.

**CF5 Calibration Monitoring.** I champion calibration *monitoring* precisely because it is measurement, not a model that can overfit. The monitoring/control framework is foundational (Nelson & Narens 1990); confidence≠accuracy is a robust *description* on logic tasks (Kruger & Dunning 1999); and we already ship every metric it needs (`eval/metrics.py`: `reliability_bins`, `ece`, `auc`, `brier`, `bootstrap_ci`). It is cheap, orthogonal to everything built, and the enabler for CF6. My discipline here: I will **not** invoke the Dunning–Kruger *mechanism*, which is mostly a statistical artefact (Gignac & Zajenkowski 2020, near-zero Glejser correlation) — we measure *the individual's* reliability curve, never assume "the weak are uniquely blind," and we guard against degenerate flat ratings with the Resolution/AUC check.

**CF6 Hypercorrection *Spaced* Error Queue.** Highest score-relevant ROI: a confident-and-wrong answer is the highest-yield correction target (Butterfield & Metcalfe 2001; Metcalfe 2017; γ≈.51 in Eich et al. 2013). It becomes a CHAMPION *only* with the word I bolded in the name — Butler, Fazio & Marsh (2011) show high-confidence corrections **return unless re-practiced**, so the spaced re-test is mandatory, which is exactly what our FSRS layer is for. Cap the boost and abstain under small-n to avoid chasing a fluky miss.

**CF18 ZPD / Region-of-Proximal-Learning selector.** The strongest *human* sequencing evidence in the set: Metcalfe & Kornell (2005), across **8 experiments**, show people learn fastest on the *easiest-not-yet-mastered* items and spend most profitable time at *medium* difficulty — the exact opposite of what our current queue does (it serves the hardest card in the weakest topic). It also fixes a real defect: `points = weight·(1−mastery)` ignores item difficulty entirely. I discount the "85%" figure itself (Wilson et al. 2019 is a neural-net/theoretical result, `moderate` for humans) and lean on the human region-of-proximal-learning line, shipping τ as an ablatable config and abstaining to plain ordering when the performance model is thin.

**CF15 Transfer Measurement Layer.** Not an intervention — the *honesty instrument*, and I champion it as a precondition for every transfer claim anyone else makes. Chi, Feltovich & Glaser (1981) established that structure-vs-surface sorting is a direct read-out of expertise, and Barnett & Ceci (2002) insist transfer be reported as a **distance-graded curve, never a single number**. The meter (memorization gap = P(correct|near) − P(correct|far); structure slope β) is what stops us shipping surface-bound drills that *feel* like they teach transfer. Cheap, reuses `eval/leakage.py` + `eval/ablation.py`.

### CONDITIONAL — justification (grouped)

**CF12 Structure Twins** is the best-evidenced way to *build* a transferable schema (Gick & Holyoak 1983; Loewenstein et al. 1999 ~3×; Gentner et al. 2003 47% vs 6%) and it targets ~2/3 of the exam — but the evidence is *adjacent-domain*, not LSAT, and the top risk is real: can our AI reliably mint two arguments that are surface-different yet structurally *identical*? A secretly-mismatched twin teaches the wrong schema. **Ship only behind CF15's meter and the fail-closed `checker.py` + `gold_set` gate.** **CF9 Pretesting** is `strong` but narrowly: benefits are large *for the tested content* (Pan & Carpenter 2023, d≈0.44 to >2.0) and **do not generalize to untested material** — so it's a targeted RC-passage/LR-concept primer, measured on the exact primed items, not a general booster. **CF13 Worked-Example Fading** has a strong core (Sweller & Cooper 1985, g≈0.48) but the *fading* specifics are `moderate` and subject to **expertise reversal** (Kalyuga et al. 2003) — condition it on adaptive entry. **CF10 Productive Failure** is promising (Sinha & Kapur 2021, g=0.36) but has hard boundary conditions — it needs corrective feedback and **did nothing for procedural knowledge (g=−0.03)**; restrict to conceptual LR/RC. **CF4 Minimal-Pair Contrast** and **CF3 Trap Profiling** are the enabling/discrimination layer: valuable and LSAT-native, but CF3 is data-hungry for one user (ship report-only, abstain until AUC≥0.65 on held-out) and CF4's single-axis pairs are a content-validity risk (same checker defense). **CF16 Structure Sprints** rests on large adjacent-domain PLM effects (Kellman 2013, d 0.84–2.69) but LSAT-score transfer is unproven and the honest ultrasound null (2023) bounds it — fund it as an ablation arm, not a headline. **CF19 BKT** is the *correct* modeling choice (bounded, interpretable, and Khajah et al. 2016 show it matches DKT) — I keep it CONDITIONAL only because one user's per-skill sequences are short; it must beat the recency fold on held-out AUC before it's trusted, and abstain otherwise. **CF21 Adaptive Probe / CF17 Fluency Gates / CF25 Pacing-Sim / CF23 DP-Loops / CF22 Gating / CF24 SRL Loop** are all defensible-but-secondary: they *measure* or *sequence* rather than teach, or (DP-loops) rest on a mechanism that explains a minority of variance (Macnamara et al. 2014). Useful; not where I spend my first five slots. **CF14 Argument Mapping** I lean toward cutting as a headline: the AM≈0.7 figure is advocate-led and quasi-experimental (van Gelder 2005), and Willingham (2007) warns that diagramming/generic-CT doesn't transfer without deep-structure content — gate it on the meter showing map-skill predicts item accuracy before investing in the expensive span-selection UI.

### CUTS — justification

**CF20 CDM Attribute Profile — my single strongest cut.** DINA/G-DINA is genuinely strong *psychometrics* (de la Torre 2009/2011), which is exactly why it's seductive — but on a **single user's sparse log** it is the textbook overfitting trap: you cannot validate a Q-matrix on one person, misspecification degrades classification (Rupp & Templin 2008), the posteriors will be wide, and a wrong "attribute not mastered" flag then mis-gates other features (CF22). Even M4 ranks it last and says "report-only first." Kill it as a feature; if we want per-skill mastery, CF19's bounded BKT already does the honest version. **CF11 Delayed Elaborated Feedback** — cut as a headline: feedback timing is `contested` (Butler/Karpicke/Roediger 2007 favor delayed; Kulik & Kulik 1988 favor immediate; Smith & Kimball 2010 split 16/12/11). It survives only as a *measured knob* in `eval/ablation.py`, never as an evidence-based selling point. **Expressive/anxiety writing (part of CF25)** — cut the claim: Ramirez & Beilock (2011) got d=0.57, Myers, Davis & Chan (2021) got a clean null across four authentic exams. Opt-in micro-tool, measured in our harness, promised to no one.

---

## 4. My straw-man ship set (opening bid)

Five features, chosen to be *individually* evidence-backed **and** *jointly* eval-measurable through one shared harness (`eval/ablation.py`, equal study time, paired synthetic learners first, `bootstrap_ci`, primary outcome always **held-out exam-style items** — never the drilled items). They also compose: one tiny append-only capture change (`chosen` letter + `confidence` on the `LSAT PerformanceEvent` notetype, threaded through `qt/aqt/lsat_performance.py` → `lsat/events.py::append_event`) unlocks S1, S3, and S4 at once.

| Ship | Feature (canonical) | The **one metric** it must move | Guardrail |
|---|---|---|---|
| **S1** | **Distractor-Reasoning Engine** = CF2 Trap Retrieval + CF1 Trap Autopsy | Δ held-out **P(correct) on *unseen* same-trap items** at equal study time (CI excludes 0); secondary: repeat-trap rate ↓ | A/B the self-explanation prompt against a no-prompt arm (Barbieri 2023 risk); RIF check via integrate-the-distractor framing |
| **S2** | **Successive Relearning** (CF8) | **Delayed P(correct) on relearned patterns at *matched* study budget** vs FSRS-only | Report the time-matched number (d≈0.28), not the unmatched d≈4.19; cap concurrent loops |
| **S3** | **Calibration Monitoring** (CF5) | Within-user **ECE / Overconfidence Index ↓** and **Resolution (AUC of confidence↔correct) ↑** over practice | Abstain below k events; variance check kills flat ratings; never invoke the DK *mechanism* |
| **S4** | **Hypercorrection *Spaced* Error Queue** (CF6) | **Delayed correction rate of high-confidence errors (γ>0, target .3–.5)**; secondary: repeat-trap rate per study hour | Spaced re-test is mandatory (Butler/Fazio/Marsh 2011); bounded boost |
| **S5** | **ZPD Selector + Transfer Meter** (CF18 + CF15) | Δ held-out **P(correct) at equal budget** (ZPD); **memorization gap** & **structure slope β** (meter) | Calibration `ECE_MAX` must stay green; τ ablatable; meter abstains until enough new-surface items |

Why this five and not, say, Structure Twins in slot 5? Because my charge is *evidence-backed AND jointly measurable now*. S1–S4 are meta-analytically supported and share the capture plumbing; S5 pairs the strongest *human* sequencing result (Metcalfe & Kornell 2005) with the instrument that keeps everyone honest. **Structure Twins (CF12) is my sixth pick and my olive branch to the transfer camp** — I will vote it in *the moment* the transfer meter (S5) shows the AI can mint valid twins and that twin-trained schemas lift far-surface accuracy with a CI excluding 0. Evidence-first, not vibe-first.

### Intellectual-honesty ledger (weaknesses of my own picks)

- **S1:** self-explanation is not universally positive — it *hurt* the worked-example effect in one math meta-analysis (Barbieri et al. 2023); free-text grading is noisy/gameable (mitigate: menu fallback + `checker.py` verbatim-span gate + `gold_set` false-pass bound). Over-drilling the correct answer risks RIF (mitigate: integrate-the-distractor framing, Anderson & McCulloch 1999; the competitive-MC no-net-RIF result, Bjork/Little/Storm 2014).
- **S2:** the headline d≈4.19 is *not* my planning number; time-matched it's **d≈0.28** (Higham 2022), and the whole thing depends on fresh-item supply/quality from the AI pipeline.
- **S3:** calibration monitoring is an *instrument*, not a proven score-mover on its own; its value is realized only through S4's routing. And the Kruger–Dunning story is contested at the mechanism level (Gignac & Zajenkowski 2020) — I use only the individual-curve description.
- **S4:** small-n over-boosting and confidence-gaming are real (cap the boost, cross-check with S3's resolution metric); and confident errors *return* if the spacing lapses.
- **S5:** the "85%" constant is theoretical (Wilson 2019); P̂ is only as good as the performance model (abstain when thin); the meter's surface-distance is a bag-of-words proxy that shared logical-marker words can inflate (down-weight them; flag as a limitation).
- **All five:** every eval is **synthetic today** (documented in `eval/ablation.py`). I am buying *sound methodology + large adjacent-domain effects*, pending a real A/B — I will say so in any claim, and I will not present a synthetic lift as a proven score gain.

---

## 5. Pre-emptive critiques — what I expect, and will resist

### The LSAT-coach (pedagogy / market instincts)
I expect them to champion **Blind Review (CF7)** as *the* signature technique, plus the **Section Simulator + pacing policy (CF25)**, "predict the answer," and **Argument Mapping (CF14)**.
- **Blind Review:** I *like* the timed↔untimed decomposition, but I'll resist any claim that it is *evidence-based* — it is **7Sage community best-practice, not a controlled trial** (Proposal B says so itself). Ship it as a diagnostic and **measure** whether pressure-routed items actually improve after pacing drills and knowledge-routed items after content; do not assert the routing works.
- **Section Simulator / pacing policy:** necessary *product* fidelity (the format facts are LSAC-official and STRONG), but the "optimal pacing policy" is a heuristic (`moderate`) — it's format-engineering, not a learning-science novelty, and it should not consume a headline evidence slot.
- **Argument Mapping / "diagram every argument":** I'll push back hard. The AM≈0.7 figure is advocate-led and quasi-experimental (van Gelder 2005), and Willingham (2007) is explicit that diagramming and generic critical-thinking instruction **don't transfer without deep-structure content**. Gate it on our own meter before building the UI.
- And if anyone reaches for the **expressive-writing "calm your nerves" tool** as a selling point — Myers, Davis & Chan (2021) is a clean null; opt-in, unpromised.

### The engineer (implementability / ROI instincts)
I expect them to favor the cheap Python-only wins (**ZPD re-rank, BKT, queue tweaks**), to want to **defer the notetype schema change**, to **skimp on the AI content-validity gates**, and possibly to argue for a **bigger adaptive model ("use DKT, it's SOTA")**.
- **The `chosen`/`confidence` capture is non-negotiable, not a "later."** It is a one-time, additive, append-only, HLC-clean field change, and *without it* Trap Profiling, Calibration, and the Hypercorrection queue are all impossible. It is the highest-leverage 20 lines in the project.
- **No DKT / no big CDM on one user.** Khajah, Lindsey & Mozer (2016) showed DKT's famous 25% AUC edge was largely an **evaluation artifact** and a bounded, extended BKT is statistically indistinguishable — "a domain that does not require depth." A single user's sequences are far too sparse for an RNN; we'd fit noise. Bounded BKT (CF19), yes; DKT/CDM (CF20), no.
- **The checker/`gold_set` gates are content-validity guards, not polish.** A structurally-mismatched Structure Twin or a two-axis "minimal pair" teaches the *wrong* lesson; the fail-closed independent checker is what makes generated content trustworthy. Cheap-to-ship is not the same as evidence-backed — I will resist shipping something *because* it's a small diff.

### The student-advocate (engagement / UX / motivation instincts)
I expect them to push **gamified Structure Sprints**, to **minimize friction** (kill the confidence tap, kill the doubled blind-review pass), to prefer **drills that feel good**, and possibly to flirt with **"personalize to how I learn."**
- **Felt-fluency is a liar.** Desirable difficulties feel worse but learn better (Soderstrom & Bjork 2015; Bjork & Bjork 2011), and learners *systematically mis-rate* the effective drills — massing and interleaving-avoidance *feel* more productive (Kornell & Bjork 2008; the restudy illusion in Roediger & Karpicke 2006). Re-reading/highlighting are rated **LOW utility** (Dunlosky et al. 2013). So I will resist letting "what students enjoy" drive the study substrate, and I will refuse to reward *re-exposure to explanations* as if it were study.
- **The confidence tap earns its friction.** It's one tap (sampleable every Nth item) and it unlocks the entire calibration + hypercorrection stack — the highest engagement-to-value ratio in the set. Keep it.
- **Frame difficulty honestly, don't dumb it down.** The region-of-proximal-learning target (~85%, Metcalfe & Kornell 2005) *is* the motivation-preserving move — hard-but-surmountable — so we can satisfy the UX concern with evidence rather than by softening the content.
- **Absolutely no learning-styles / modality matching** (Pashler et al. 2008 — debunked). If it appears in any skin, I veto it on sight.

---

## 6. Summary (my championed set + strongest cut)

I champion a tight, meta-analytically-backed core and refuse the seductive tails.

- **Ship first:** a **Distractor-Reasoning Engine** (competitive-distractor *retrieval*, MC **g=0.70**, Adesope 2017 + Little/Bjork; fused with *why-right/why-wrong* **self-explanation**, **g=0.55**, Bisra 2018) — the most on-target feature for an engineered-trap, best-of-five exam.
- **Ship:** **Successive Relearning** of missed patterns with fresh items (Rawson 2018; planned at the honest time-matched **d≈0.28**, not the d≈4.19 headline).
- **Ship:** **Calibration *Monitoring*** (Nelson & Narens 1990; individual reliability curve only) plus a **Hypercorrection *spaced* error queue** (Metcalfe 2017; γ≈.51) — but only *with* the mandatory spaced re-test (Butler/Fazio/Marsh 2011).
- **Ship:** a **ZPD / region-of-proximal-learning selector** (Metcalfe & Kornell 2005, 8 experiments) bundled with a **transfer-measurement layer** (Chi 1981; Barnett & Ceci 2002) so no transfer claim goes unmeasured.
- **Sixth, conditional:** **Structure Twins** — strongest transfer *evidence* (Gentner 47% vs 6%), but adjacent-domain and content-risky; I vote it in only once the meter proves valid twins lift far-surface accuracy.
- **My single strongest cut:** the **DINA/G-DINA cognitive-diagnostic attribute profile on a single user** — strong psychometrics, but the textbook overfitting-sparse-data trap (unvalidatable Q-matrix, Rupp & Templin 2008; mis-gates other features). Runners-up killed: **feedback-*timing* as doctrine** (contested 16/12/11, Smith & Kimball 2010) and **expressive-writing** (d=0.57 → null, Myers 2021). And the whole slate is measured on **held-out exam-style items at equal time** — because we are buying honest single-digit-point gains, never "2 sigma."
