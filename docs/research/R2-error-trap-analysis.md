# R2 — Error-Driven Learning & Engineered-Trap Analysis for Anki-LSAT

**Research memo · Round 2 · Feature proposals grounded in learning theory**

> **Persona.** I am a learning-sciences researcher specializing in _error-driven
> learning_, _contrasting-cases / "cases" pedagogy_, and _diagnostic (formative)
> assessment with distractor/misconception analysis_. My working thesis: on the
> LSAT, most missed points are not knowledge gaps — they are **predictable pulls
> toward engineered wrong answers**. If we can name the trap, measure _which_
> traps a _particular_ student is pulled toward, and drill exactly those, we can
> convert diffuse "practice more" study into targeted deliberate practice.

---

## Lens & why it matters

The LSAT is a skills test whose wrong answers are **manufactured**, not random.
Each incorrect choice is engineered to be attractive along a known dimension:
_out-of-scope, reversed conditional, too-strong/absolute, premise-vs-conclusion
confusion, opposite, half-right, sufficient-vs-necessary,_ and so on. PowerScore
teaches these as "wrong-answer families" (Shell Game, Exaggerated, Opposite,
Reverse, New Information; Contenders vs Losers), and LSAT Demon's own coaching
insists that "the wrong answers are 100% wrong … you'll get burned on an
identical issue next time" ([PowerScore](https://blog.powerscore.com/lsat/lsat-logical-reasoning-and-some-of-its-challenges/);
[LSAT Demon](https://lsatdemon.com/resources/lsat-tips-and-strategies/go-deeper-on-each-mistake)).
That is a strong claim from the market that **trap patterns recur and are
learnable** — but neither product _measures a per-student trap profile_ or
_generates practice targeted at it_.

The learning sciences say this is exactly the high-leverage move:

- **Errors are the signal, not noise.** Errorful retrieval _followed by
  corrective feedback_ out-learns error-free study, and the benefit is _largest
  for high-confidence errors_ (the **hypercorrection effect**). Avoiding errors
  is a "counterproductive strategy" in low-stakes practice (Metcalfe, 2017).
- **A distractor is a diagnosis.** Since Sadler (1998), a chosen wrong answer
  that maps to a specific misconception is a _measurement_, not a mistake — and
  the psychometrics for modeling _which distractor_ a learner picks already
  exist (Thissen, Steinberg & Fitzpatrick, 1989).
- **Contrasting cases build the discrimination the LSAT tests.** Comparing two
  minimally-different cases before being told the rule produces markedly better
  transfer than studying cases separately or being told first (Schwartz &
  Bransford, 1998; Loewenstein, Thompson & Gentner, 1999).

Our fork already _records_ answers and prioritizes _topics_. It does **not** yet
record **which trap a student fell for**, model **trap susceptibility**, or drill
**the student's specific error profile**. That is the gap this memo attacks.

---

## Evidence base

Ten peer-reviewed anchors (effect sizes / designs noted). URLs verified via web
search on 2026-06-30; where I cite an effect size I did not read in the primary
PDF, I say "as reported in."

1. **Roediger & Karpicke (2006), _Psychological Science_ 17(3), 249–255.**
   [PDF](http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Roediger-Karpicke-2006_PsychSci-1.pdf) ·
   [DOI](https://doi.org/10.1111/j.1467-9280.2006.01693.x).
   _Design/finding:_ prose-recall experiments; repeated **testing** beat repeated
   **studying** on 1-week retention (61% vs 40%) despite less exposure and **no
   feedback**. _LSAT relevance:_ our graded `LSAT Item` cards _are_ retrieval
   practice; the testing effect is the base rate we build on, and it grows with
   corrective feedback (below).

2. **Rowland (2014) meta-analysis, _Psychological Bulletin_ 140(6), 1432–1463.**
   [DOI](https://doi.org/10.1037/a0037559) (effect sizes as reported in
   [Karpicke, 2017 review](https://learninglab.psych.purdue.edu/downloads/2017/2017_Karpicke_Retrieval_Based_Learning_Review.pdf)).
   _Finding:_ across **159 studies**, retrieval vs restudy **g = 0.50**, favoring
   retrieval in **81%** of comparisons; **feedback enlarges** the effect and,
   without feedback, the effect needs practice accuracy > 50%. _LSAT relevance:_
   justifies making _feedback quality_ — specifically trap-level feedback — a
   first-class design variable, not an afterthought.

3. **Butterfield & Metcalfe (2001), _JEP:LMC_ 27(6), 1491–1494.**
   [DOI](https://doi.org/10.1037/0278-7393.27.6.1491).
   _Finding (the hypercorrection effect):_ counter to interference predictions,
   **errors committed with high confidence were the most likely to be corrected**
   after feedback; learners "know what is correct" once surprised. _LSAT
   relevance:_ a student who confidently picks a trap is the _best_ correction
   opportunity — if we capture confidence and route it to feedback.

4. **Eich, Stern & Metcalfe (2013), _hypercorrection in younger & older adults_.**
   [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3604148/).
   _Design/finding:_ gamma correlation between confidence-in-error and later
   correction was **γ = .51** (younger) vs **γ = .14** (older) — a concrete,
   replicable effect-size target. _LSAT relevance:_ gives us a _measurable_
   success criterion (a positive γ) for the hypercorrection feature in our eval.

5. **Metcalfe (2017), _Learning from Errors_, _Annu. Rev. Psychol._ 68, 465–489.**
   [DOI](https://doi.org/10.1146/annurev-psych-010416-044022) ·
   [open PDF](https://www.columbia.edu/cu/psychology/metcalfe/PDFs/Learning%20from%20errorsAnnual%20ReviewMetcalfe2016.pdf).
   _Finding:_ review concludes errorful learning + corrective feedback beats
   error-avoidance; **analysis of the reasoning that led to the error is
   crucial**; also cautions that corrected high-confidence errors can **revert**
   if the correction is later forgotten. _LSAT relevance:_ mandates _why-this-
   trap-is-wrong_ feedback and _spaced_ re-testing of corrected traps.

6. **Sadler (1998), _J. Research in Science Teaching_ 35(3), 265–296.**
   [PDF](https://lweb.cfa.harvard.edu/smgphp/mosart/images/sadler_article.pdf) ·
   [DOI](https://doi.org/10.1002/%28SICI%291098-2736%28199803%2935:3%3C265::AID-TEA3%3E3.0.CO;2-P).
   _Design/finding:_ **distractor-driven** multiple-choice items (distractors =
   documented misconceptions) administered to 1,250 students; **option
   probability curves** show a misconception's pull rise then fall as ability
   grows. Sadler et al. (2013) further found teachers who _know misconceptions_
   produce higher student gains. _LSAT relevance:_ the direct precedent for
   tagging each distractor to a trap and modeling its pull as a function of
   ability.

7. **Thissen, Steinberg & Fitzpatrick (1989), _J. Educational Measurement_
   26(2), 161–176.** [DOI](https://doi.org/10.1111/j.1745-3984.1989.tb00326.x)
   (referenced in Sadler, 1998).
   _Finding:_ "the distractors are also part of the item" — the **nominal-
   response / multiple-choice IRT** model gives a principled way to model the
   probability of each _specific_ wrong choice, not just right/wrong. _LSAT
   relevance:_ the psychometric backbone for a _trap-susceptibility_ model that
   is more than a tally.

8. **Große & Renkl (2007), _Learning and Instruction_ 17(6), 612–634.**
   [PDF](https://iwm-tuebingen.de/workshops/sim2004/pdf_files/Grosse_et_al.pdf) ·
   [ERIC EJ780439](https://eric.ed.gov/?id=EJ780439).
   _Design/finding:_ 2×3 experiments on **erroneous worked examples**. An
   aptitude–treatment interaction: mixing correct + incorrect solutions improved
   **far transfer** for learners with favorable prior knowledge; **highlighting
   the error + prompting explanation/correction** was needed to help lower-
   knowledge learners (math-grade prior-knowledge effect η² ≈ .11–.20). _LSAT
   relevance:_ erroneous-example ("here's the trap; explain why it's wrong")
   cards work — but must be _scaffolded by ability_, which our Rasch model
   already estimates.

9. **Booth, Lange, Koedinger & Newton (2013), _Learning and Instruction_ 25,
   24–34.** [ERIC ED543090 PDF](https://files.eric.ed.gov/fulltext/ED543090.pdf) ·
   [DOI](https://doi.org/10.1016/j.learninstruc.2012.11.002).
   _Design/finding:_ in Algebra tutors, **explaining incorrect examples** (alone
   or combined with correct) improved conceptual understanding and **reduced
   persistent misconceptions**, especially for struggling students. Reinforced by
   a 2025 systematic review ([_Educational Psychology Review_, DOI
   10.1007/s10648-025-10071-x](https://link.springer.com/article/10.1007/s10648-025-10071-x)):
   **contrasting** correct-vs-incorrect examples (Con-ErrEx) beat correct-only in
   more than half of studies, with **none** favoring correct-only. _LSAT
   relevance:_ the strongest support for _pairing_ a trap answer against the
   correct answer and asking the student to explain the difference.

10. **Contrasting cases / analogical encoding (transfer):**
    - **Schwartz & Bransford (1998), _A Time for Telling_, _Cognition and
      Instruction_ 16(4), 475–522.** [PDF](https://aaalab.stanford.edu/papers/time_for_telling.pdf).
      Analyzing **contrasting cases** _before_ a lecture produced differentiated
      knowledge that made the later "telling" far more effective.
    - **Loewenstein, Thompson & Gentner (1999), _Psychon. Bull. & Rev._ 6(4),
      586–597.** [DOI](https://doi.org/10.3758/BF03212967). Management students
      who **compared two cases** were **~3× more likely** to transfer the
      principle than students who studied the same cases separately; Gentner,
      Loewenstein & Thompson (2003, _JEP_ 95(2), 393–408,
      [PDF](https://groups.psych.northwestern.edu/gentner/papers/GentnerLoewensteinThompson03.pdf))
      show comparison beats being given the principle. Schwartz & Martin (2004,
      _Cognition and Instruction_ 22(2), 129–184,
      [PDF](https://aaalab.stanford.edu/assets/papers/2004/Inventing_to_prepare_for_future_learning.pdf))
      add that **inventing** (predicting) with contrasting cases _before_ telling
      boosts transfer. _LSAT relevance:_ the theoretical engine for **minimal-pair
      trap contrasts** with **predict-the-trap** before the reveal.

_Supporting anchors (cited inline in features):_ **Black & Wiliam (1998)**,
formative assessment ES ≈ 0.4–0.7, largest for low achievers
([Kappan](https://kappanonline.org/inside-the-black-box-raising-standards-through-classroom-assessment/)) —
_note: the exact 0.4–0.7 range has been methodologically contested (Kingston &
Nash, 2011; Bennett, 2011), so I lean on the qualitative claim (diagnostic
feedback helps, most for the weakest) rather than the point estimate_; and
**Ericsson, Krampe & Tesch-Römer (1993)**, deliberate practice = tasks
"invented to overcome weaknesses" with feedback, _Psychological Review_ 100(3),
363–406 ([PDF](https://www.krigolsonteaching.com/uploads/4/3/8/4/43848243/ericssondeliberatepracticepr93.pdf)).

---

## Candidate features

All three share one new substrate: **the trap is captured, named, and modeled per
student.** Feature 1 builds that substrate (and is independently useful as a
diagnostic); Features 2 and 3 are interventions that consume it. They can ship
incrementally.

### Feature 1 — Trap-tagged distractors + a per-student "Trap-Susceptibility Profile"

**(a) Student-facing description.** Every practice item's wrong answers are
labeled behind the scenes with the _engineered trap_ they exploit (e.g.
`too_strong`, `reversed_conditional`, `out_of_scope`, `sufficient_vs_necessary`).
As you answer, the app quietly records _which_ wrong answer you picked — not just
that you missed. Your dashboard grows a **"Trap Profile"**: a confusion-matrix
heatmap of _trap family × question type_ showing the traps you personally fall
for most, each with an honesty-contract confidence band ("Reversal traps in
Necessary-Assumption: you pick them 42% ± 9% of the time you see them, from 31
items"). It abstains until it has enough evidence, exactly like the readiness
panel.

**(b) Mechanism + citations.** A chosen distractor is a _diagnosis of a specific
misconception_ (Sadler, 1998; option probability curves), and the probability of
picking a _particular_ wrong answer is formally modelable (Thissen et al., 1989,
nominal-response IRT). Surfacing that pattern is **formative assessment** — the
lever Black & Wiliam (1998) argue helps most for the lowest performers — and it
operationalizes Metcalfe's (2017) point that _error analysis_, not just the
right answer, is what drives learning.

**(c) Novelty.** _Vs our app:_ the event log records only `correct` (bool) +
`item_id` + `response_ms`; the chosen letter is received in
`qt/aqt/lsat_performance.py` and **thrown away**, and trap types exist only as 5
coarse cross-cutting tags (`skill.trap.*`) that are never attached to individual
answer choices. There is no per-choice capture and no trap model. _Vs market
(per public product pages, 2026):_ 7Sage "Virtual Tutor Pick" / adaptive smart
drills and LSAT Demon "Smart Drilling" both target **question-type** weakness and
adapt **difficulty** ([7Sage](https://7sage.com/discussion/57373/new-feature-adaptive-smart-drills);
[Demon](https://lsatdemon.com/resources/frequently-asked-questions/why-lsat-demon));
PowerScore names wrong-answer families but as **static book content taught to
everyone** ([PowerScore](https://blog.powerscore.com/lsat/bid-153562-five-steps-to-approaching-the-answer-choices-in-lsat-logical-reasoning-questions/)).
None, to my knowledge, tags each distractor to an engineered trap in structured
data and models **which trap family a given student is repeatedly pulled toward,
across question types.** That cross-type profile is the novel object.

**(d) LSAT-specificity.** Only works because LSAT distractors are _engineered_
along a small, stable set of axes — the traps recur across items and even across
question types (a "reversal" pull in Weaken predicts a "reversal" pull in
Necessary Assumption). A domain with random distractors would have nothing to
model.

**(e) Implementation sketch (this fork).**

- **`lsat-taxonomy.yaml` + `lsat/taxonomy.py`:** promote the 5 `skill.trap.*`
  entries to a full `trap_catalog` (out_of_scope, reversed_conditional,
  too_strong, opposite, half_right, sufficient_vs_necessary,
  premise_vs_conclusion, irrelevant_comparison, …), each with the question types
  it infests (prevalence weights), anchored to LSAC skill descriptions.
- **`lsat/notetypes.py`:** add a `distractor_tags` field to `ITEM_FIELDS`
  (JSON map `{"A":"too_strong","C":"out_of_scope",…}`). Adding a field is a
  _schema change_ (the existing `_sync_templates` only refreshes HTML), so
  guard it with a one-time `mm.add_field` migration in `ensure_notetypes` — the
  sensitive step, flagged below.
- **Answer capture — `qt/aqt/lsat_performance.py`:** the handler already has
  `chosen` and the note; look up `distractor_tags[chosen]` and pass
  `chosen_letter` + `chosen_trap` into `append_event`. No template change needed
  for capture (the letter is already posted via `pycmd("lsatAnswer:…")`).
- **`lsat/events.py`:** extend `EVENT_FIELDS`/`append_event` with
  `chosen_letter`, `chosen_trap` (backward-compatible: old events default
  empty). Add `fold_trap_susceptibility()` beside `fold_recent_performance()`.
- **`lsat/models/traps.py` (new):** mirror `models/performance.py` — shrinkage
  toward a clamped base rate (`SHRINKAGE_K`), ridge-IRLS fit, k-fold held-out
  ECE — but predict **P(pick trap _t_ | _t_ present & answer wrong)** per
  student, with intervals. A give-up gate (min events per trap) mirrors the
  readiness honesty contract.
- **Dashboard — `lsat/dashboard_data.py`, `qt/aqt/lsat_dashboard.py`,
  `ts/routes/lsat-dashboard/+page.svelte`:** add a `trap_profile` payload and a
  confusion-matrix heatmap panel (abstains when under-evidenced).
- **Content:** seed a few trap-tagged items in `lsat/seed.py`; bulk trap tags
  come from Feature-1's AI extension (see Feature 2 pipeline).

**(f) Measurable-impact hypothesis + eval design.**

- _Hypothesis:_ the trap model predicts _which distractor_ a student picks on
  **held-out** items with **AUC ≥ 0.65** and **ECE ≤ `config.ECE_MAX` (0.05)**,
  beating a question-type-only baseline by **≥ `config.PERF_MIN_DELTA_AUC`**;
  profiles are reliable (split-half r ≥ 0.6).
- _Eval:_ new `eval/traps.py` step reusing `eval/metrics.py` (`auc`, `brier`,
  `ece`, `bootstrap_ci`) and the k-fold pattern from `eval/performance.py`; wire
  it as a **hard gate** in `eval/run.py`. _Falsifiable:_ if trap choice is not
  predictable beyond question type, the model won't clear the AUC delta and the
  feature is parked — the honest negative the harness is built to surface.

**(g) Cost/risk & dependencies.** **Cost 3/5, Risk 3/5.** Main risk is the
`LSAT Item` **notetype schema migration** (field addition) and the cold-start
data requirement (mitigated by the give-up gate). Deps: expanded trap taxonomy;
trap-tagged content; the tiny answer-capture change. No proto/Rust change.

---

### Feature 2 — Contrasting trap-pairs with "predict-the-trap" (invention-first)

**(a) Student-facing description.** A new card type shows **two near-identical
items side by side** that differ on _exactly one_ trap dimension — e.g., a
Strengthen stem where choice (C) is the correct strong-support answer, paired
with a twin stem where the _same-looking_ (C) is now a **too-strong** trap.
Before any reveal, you **predict** which one is the trap and **name the trap
type**. Only then does the app tell you the rule and why the trap is engineered
to attract you. These pairs are drawn preferentially from _your_ weak traps
(Feature 1).

**(b) Mechanism + citations.** This is **analogical encoding via contrasting
cases**: comparing two minimally-different cases abstracts the underlying
relational structure and roughly **tripled transfer** vs studying cases
separately (Loewenstein, Thompson & Gentner, 1999; Gentner et al., 2003).
Withholding the rule until after comparison creates the **"time for telling"**
(Schwartz & Bransford, 1998), and asking students to **invent/predict** first
adds a further transfer boost (Schwartz & Martin, 2004). Pairing a _correct_ with
an _engineered-incorrect_ case is precisely the **Con-ErrEx** manipulation that
beat correct-only examples (Booth et al., 2013; 2025 review), and the
predict-then-explain step is the error analysis Metcalfe (2017) calls crucial.

**(c) Novelty.** _Vs our app:_ we have single items + an interleaving toggle
(`lsat/interleaving.py`) that controls _order_, not _comparison_; nothing pairs
minimally-different items or asks for a pre-reveal prediction. _Vs market:_
PowerScore/Demon teach "predict the answer" and "why is the wrong answer wrong"
as **human self-review habits** ([Demon "Go deeper"](https://lsatdemon.com/resources/lsat-tips-and-strategies/go-deeper-on-each-mistake)),
and 7Sage/Demon serve _individual_ questions adaptively — but none _auto-
generates matched minimal-pair contrasts isolating one trap axis_ and forces an
_invention-first_ comparison targeted to the learner's trap profile. The
**structured single-axis contrast** is the novel artifact.

**(d) LSAT-specificity.** Minimal pairs are only meaningful because LSAT traps
are single-axis and swappable: you can hold the stimulus almost constant and flip
_one_ engineered feature (scope, conditional direction, strength) to turn a right
answer into a classic trap. This mirrors how LSAC actually writes distractors.

**(e) Implementation sketch (this fork).**

- **Notetype:** add an `LSAT Contrast Pair` notetype (or a `contrast_group` +
  `contrast_axis` field on `LSAT Item`) in `lsat/notetypes.py`; a template with
  a prediction step (two buttons "left is trap / right is trap" + a trap-type
  picker) that posts via the existing `pycmd` channel before revealing.
- **AI pipeline — `lsat/ai/prompts.py`, `generator.py`, `checker.py`,
  `pipeline.py`:** extend the generator to emit a _pair_ with a declared single
  differing axis and per-distractor `distractor_tags`, each justified by a
  **verbatim `source_quote`** (the existing substring check in `generator.py`
  already drops fabricated citations). Extend the independent `checker` with a
  new criterion: _the pair must differ on exactly one trap axis and both trap
  labels must be correct_ — fail-closed like today. Reuse `gold_set.py` +
  `validate_checker` to measure a **trap-label / contrast-validity false-pass
  rate**.
- **Study surface:** the points-at-stake queue selects _which_ pairs (weight by
  the student's susceptibility on the pair's axis — see Feature 3 wiring); order
  via the existing interleaving functions.
- **`eval/`:** extend `eval/card_check.py` to gate contrast-validity false-pass ≤
  `config.CHECKER_FALSE_PASS_MAX`; add a transfer sim (structured like
  `eval/paraphrase.py`) reporting Δ transfer, contrast-pair vs matched single
  item, with `bootstrap_ci`.

**(f) Measurable-impact hypothesis + eval design.**

- _Hypothesis:_ invention-first contrast pairs raise **held-out trap-avoidance on
  new items** vs matched single-item drills at **equal study time**, with a
  bootstrap 95% CI that **excludes 0**; conservative target **d ≈ 0.3–0.5**
  (deliberately below analogical encoding's ~3× odds, since our items are
  shorter).
- _Eval:_ first as a 4th arm sensitivity sim in the ablation harness (an explicit
  `CONTRAST_BONUS` parameter, reported as a parameter — same honesty stance as
  `INTERLEAVE_BONUS` in `eval/ablation.py`); then, with real users, an equal-time
  A/B on `Δ P(avoid trap)` with `bootstrap_ci`. A near-zero effect is reported,
  not hidden.

**(g) Cost/risk & dependencies.** **Cost 4/5, Risk 3/5.** Hardest part is
_trustworthy_ auto-generated single-axis pairs (a pair that secretly differs on
two axes teaches the wrong lesson) — mitigated by the independent checker,
verbatim-span gate, and human spot-checks before admission. Deps: Feature 1
taxonomy + `distractor_tags`; AI pipeline extension; new study UI.

---

### Feature 3 — Hypercorrection drills: confidence-weighted targeting of your worst traps

**(a) Student-facing description.** When you answer an item, a one-tap
**confidence** control ("sure / unsure") appears. If you were **confident and
wrong**, the app flags it and immediately runs a **hypercorrection drill**: the
correct reasoning, an **erroneous-example** card ("here's _why_ the trap you
picked is built to fool you"), and then — crucially — a **spaced re-test** of the
_same trap on a new item_ a few days later, so the correction sticks. Your study
queue is re-weighted so the traps you're **overconfident** about surface first.

**(b) Mechanism + citations.** Directly operationalizes the **hypercorrection
effect**: high-confidence errors are corrected _best_ after feedback (Butterfield
& Metcalfe, 2001; γ ≈ .51 in Eich et al., 2013), because the belief–feedback
mismatch drives attention. This is retrieval practice **with corrective
feedback** — the condition Rowland (2014) shows maximizes the testing effect —
and it targets weaknesses with feedback, the definition of **deliberate
practice** (Ericsson et al., 1993). The erroneous-example card is Große & Renkl's
(2007) scaffolded incorrect example (highlight + explain the error), and the
**spaced** re-test guards against the **reversion** Metcalfe (2017) warns of.

**(c) Novelty.** _Vs our app:_ the points-at-stake queue
(`rslib/src/scheduler/points_at_stake.rs`) weights by `exam_weight × (1 −
mastery)` where mastery blends FSRS recall + recent accuracy — it has **no
concept of confidence, of which trap, or of the hypercorrection window.** We
don't capture confidence at all today. _Vs market:_ "blind review"
(7Sage/Demon) is a cousin — redo untimed before seeing the answer — but it is a
_manual habit_, doesn't record a per-choice confidence signal, doesn't detect the
_high-confidence-error_ case specifically, and doesn't drill the _trap family_
you're overconfident on ([7Sage blind review](https://7sage.com/discussion/46176/new-to-7sage-but-not-new-to-the-lsat-where-should-i-focus)).
Confidence-weighted, trap-specific hypercorrection routing is the novel
mechanism.

**(d) LSAT-specificity.** Confident errors on the LSAT are almost always
_trap captures_ (you were sure because the trap was well-built), so confidence ×
trap is a far sharper signal here than in fact-recall domains — and it directly
attacks the "I understood it but still picked the wrong one" failure Demon
describes.

**(e) Implementation sketch (this fork).**

- **Capture:** add a confidence tap to `_ITEM_QFMT` in `lsat/notetypes.py`
  (extend the payload to `pycmd("lsatAnswer:<LETTER>:<CONF>")`); parse it in
  `qt/aqt/lsat_performance.py` and store `confidence` on the event
  (`lsat/events.py`).
- **Queue weighting (MVP, no proto change):** feed trap tags into the _existing_
  `GetPointsAtStakeQueue` RPC as `TopicWeight` rows — `tag = trap`, `weight =
  host exam_weight × trap prevalence`, `perf_mastery = 1 − susceptibility`
  (Feature 1) — so overweighted traps surface without touching Rust.
- **Higher-fidelity path (optional):** add a `confidence_penalty` term to
  `TopicWeight`/`PointsAtStakeEntry` in `proto/anki/scheduler.proto` +
  `points_at_stake.rs` so _confidence-miscalibration_ (high confidence, low
  accuracy) boosts priority directly. This needs a **full build** (proto change)
  — hence the cost split below.
- **Hypercorrection drill:** on a high-confidence miss, enqueue the
  erroneous-example card (a Feature-2 contrast pair with the picked trap as one
  side) and schedule a spaced re-test on a _new_ item sharing the trap, reusing
  FSRS scheduling.
- **`eval/`:** (i) report the **gamma correlation** between confidence-in-error
  and later correction (success = γ > 0, replicating Butterfield & Metcalfe);
  (ii) add an ablation arm — confidence-weighted trap queue vs current
  points-at-stake vs plain — with `repeat-trap rate per unit study time` as the
  primary metric and `bootstrap_ci`; (iii) a **delayed-retest** check that
  corrected high-confidence traps don't revert below immediate performance.

**(f) Measurable-impact hypothesis + eval design.**

- _H1 (mechanism):_ γ(confidence-on-error, later correction) **> 0** on our
  events (target ≈ .3–.5, cf. Eich et al.).
- _H2 (product):_ the confidence-weighted trap queue **reduces repeat-trap rate
  per unit study time** faster than the current queue — bootstrap CI excludes 0
  in the equal-time ablation.
- _H3 (guard):_ delayed re-test accuracy on corrected high-confidence traps ≥
  immediate — i.e., spacing prevents reversion.

**(g) Cost/risk & dependencies.** **Cost 3/5** (MVP reusing the queue) **→ 4/5**
(proto/Rust confidence term); **Risk 3/5.** Risks: confidence-capture friction
(mitigated by a single optional tap) and reversion (mitigated by the H3 guard +
spacing). Deps: Feature 1 (`chosen_trap`) + confidence capture; optional proto
change.

---

## Boldest bet

**Stop scoring topics and start scoring _traps_: capture the exact wrong answer a
student was _confident_ about, model their cross-question-type trap profile, and
spend every study minute on hypercorrecting the specific engineered traps they
keep falling for.**

---

## Sources

**Learning theory (peer-reviewed).**

- Roediger, H. L., III, & Karpicke, J. D. (2006). Test-enhanced learning. _Psychological Science, 17_(3), 249–255. https://doi.org/10.1111/j.1467-9280.2006.01693.x · [PDF](http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Roediger-Karpicke-2006_PsychSci-1.pdf)
- Rowland, C. A. (2014). The effect of testing versus restudy on retention: A meta-analytic review. _Psychological Bulletin, 140_(6), 1432–1463. https://doi.org/10.1037/a0037559 (effect sizes as reported in Karpicke, 2017, [review PDF](https://learninglab.psych.purdue.edu/downloads/2017/2017_Karpicke_Retrieval_Based_Learning_Review.pdf))
- Butterfield, B., & Metcalfe, J. (2001). Errors committed with high confidence are hypercorrected. _JEP:LMC, 27_(6), 1491–1494. https://doi.org/10.1037/0278-7393.27.6.1491
- Eich, T. S., Stern, Y., & Metcalfe, J. (2013). The hypercorrection effect in younger and older adults. https://pmc.ncbi.nlm.nih.gov/articles/PMC3604148/
- Metcalfe, J. (2017). Learning from errors. _Annual Review of Psychology, 68_, 465–489. https://doi.org/10.1146/annurev-psych-010416-044022 · [open PDF](https://www.columbia.edu/cu/psychology/metcalfe/PDFs/Learning%20from%20errorsAnnual%20ReviewMetcalfe2016.pdf)
- Sadler, P. M. (1998). Psychometric models of student conceptions in science. _J. Research in Science Teaching, 35_(3), 265–296. https://doi.org/10.1002/%28SICI%291098-2736%28199803%2935:3%3C265::AID-TEA3%3E3.0.CO;2-P · [PDF](https://lweb.cfa.harvard.edu/smgphp/mosart/images/sadler_article.pdf)
- Thissen, D., Steinberg, L., & Fitzpatrick, A. R. (1989). Multiple-choice models: The distractors are also part of the item. _J. Educational Measurement, 26_(2), 161–176. https://doi.org/10.1111/j.1745-3984.1989.tb00326.x
- Große, C. S., & Renkl, A. (2007). Finding and fixing errors in worked examples. _Learning and Instruction, 17_(6), 612–634. https://doi.org/10.1016/j.learninstruc.2007.09.008 · [PDF](https://iwm-tuebingen.de/workshops/sim2004/pdf_files/Grosse_et_al.pdf)
- Booth, J. L., Lange, K. E., Koedinger, K. R., & Newton, K. J. (2013). Using example problems to improve student learning in algebra. _Learning and Instruction, 25_, 24–34. https://doi.org/10.1016/j.learninstruc.2012.11.002 · [ERIC ED543090](https://files.eric.ed.gov/fulltext/ED543090.pdf)
- _Conditions for effective learning from erroneous examples: A systematic review_ (2025). _Educational Psychology Review._ https://doi.org/10.1007/s10648-025-10071-x (Con-ErrEx > CorrEx; cites Barbieri et al., 2023 meta-analysis)
- Schwartz, D. L., & Bransford, J. D. (1998). A time for telling. _Cognition and Instruction, 16_(4), 475–522. [PDF](https://aaalab.stanford.edu/papers/time_for_telling.pdf)
- Loewenstein, J., Thompson, L., & Gentner, D. (1999). Analogical encoding facilitates knowledge transfer in negotiation. _Psychonomic Bulletin & Review, 6_(4), 586–597. https://doi.org/10.3758/BF03212967
- Gentner, D., Loewenstein, J., & Thompson, L. (2003). Learning and transfer: A general role for analogical encoding. _J. Educational Psychology, 95_(2), 393–408. [PDF](https://groups.psych.northwestern.edu/gentner/papers/GentnerLoewensteinThompson03.pdf)
- Schwartz, D. L., & Martin, T. (2004). Inventing to prepare for future learning. _Cognition and Instruction, 22_(2), 129–184. [PDF](https://aaalab.stanford.edu/assets/papers/2004/Inventing_to_prepare_for_future_learning.pdf)
- Black, P., & Wiliam, D. (1998). Inside the black box. _Phi Delta Kappan, 80_(2), 139–148. [Kappan](https://kappanonline.org/inside-the-black-box-raising-standards-through-classroom-assessment/) _(0.4–0.7 effect range methodologically contested; see Kingston & Nash, 2011; Bennett, 2011)_
- Ericsson, K. A., Krampe, R. T., & Tesch-Römer, C. (1993). The role of deliberate practice in the acquisition of expert performance. _Psychological Review, 100_(3), 363–406. https://doi.org/10.1037/0033-295X.100.3.363 · [PDF](https://www.krigolsonteaching.com/uploads/4/3/8/4/43848243/ericssondeliberatepracticepr93.pdf)

**Market / competitor capabilities (public product pages, accessed 2026-06-30).**

- 7Sage — adaptive smart drills & analytics target _question type_ + difficulty: [adaptive drills](https://7sage.com/discussion/57373/new-feature-adaptive-smart-drills), [smart drilling](https://7sage.com/discussion/56016/smart-drilling-how-does-it-work), [analytics](https://7sage.com/discussion/734/how-to-use-7sage-analytics), [blind review](https://7sage.com/discussion/46176/new-to-7sage-but-not-new-to-the-lsat-where-should-i-focus)
- LSAT Demon — Smart Drilling + "go deeper on each mistake" (human self-review): [why Demon](https://lsatdemon.com/resources/frequently-asked-questions/why-lsat-demon), [purpose of drilling](https://lsatdemon.com/resources/demon-daily/the-purpose-of-drilling), [go deeper](https://lsatdemon.com/resources/lsat-tips-and-strategies/go-deeper-on-each-mistake)
- PowerScore — static wrong-answer families (Shell Game, Exaggerated, Opposite, Reverse, New Information; Contenders/Losers): [answer-choice challenges](https://blog.powerscore.com/lsat/lsat-logical-reasoning-and-some-of-its-challenges/), [5 steps to answer choices](https://blog.powerscore.com/lsat/bid-153562-five-steps-to-approaching-the-answer-choices-in-lsat-logical-reasoning-questions/)

**In-repo grounding (integration points cited above).** `lsat/events.py`,
`lsat/notetypes.py`, `lsat/taxonomy.py` + `lsat-taxonomy.yaml`,
`lsat/models/performance.py`, `lsat/models/readiness.py`,
`qt/aqt/lsat_performance.py`, `rslib/src/scheduler/points_at_stake.rs`,
`proto/anki/scheduler.proto`, `lsat/ai/{prompts,generator,checker,pipeline}.py`,
`eval/{run,metrics,card_check,ablation,paraphrase}.py`.
