# 02 — Transfer of Learning, Schema Induction & Reasoning Instruction

_Research memo · lens 02 · to be attacked in debate · all URLs opened this pass (2026-07-01)_

## Lens & scope

The LSAT is a **transfer test**: you can never memorize the answer, because every
Logical Reasoning (LR) stimulus is a _new_ argument on a _new_ topic, and the skill
being scored is recognizing the **abstract argument structure** (assumption, flaw,
strengthen/weaken, parallel reasoning, principle, method) beneath an arbitrary
surface, then eliminating trap answers. Novices encode by **surface topic** ("the
vaccine one"); experts encode by **deep structure** ("causal overgeneralization from a
biased sample"). This lens asks: what does learning science actually know about
**moving a learner from surface to structural representation**, and about **teaching
reasoning so it transfers** — and which of those mechanisms can we build on our stack
(`lsat/ai/`, `lsat/notetypes.py`, `lsat/events.py`, the taxonomy tags, the dashboard)?
The honest headline is that _far_ transfer is hard and over-sold, but LSAT
cross-**topic** transfer is **near** on almost every dimension (same domain, same
5-choice format, same modality, same timeframe — differing essentially only in surface
content), so it is a realistic, measurable target if we use the right interventions and
never pretend we are buying broad "critical thinking." (This memo is a sibling to
`research/proposals/C-transfer-argument-schemas.md`; where we converge on
analogical comparison I say so — convergent evidence is a feature — but four of the
five proposals below, worked-example fading, self-explanation elimination,
argument-skeleton mapping, and variability drilling, are distinct.)

## Key findings

Each bullet: **claim · citation · a number/effect size · evidence rating.** Numbers were
read from the source this pass; where a figure comes from a secondary source I say so.

- **Comparing two structurally-identical, surface-different cases induces a
  _transferable_ schema; a single case — even annotated with a diagram or a stated
  principle — usually does not.** Gick & Holyoak (1983): on Duncker's radiation
  problem, the convergence solution was produced by ~**10%** with no analog, ~**30%**
  given one analog _without_ a hint, and ~**75%** given one analog _with_ a hint;
  crucially, giving **two** analogs and asking subjects to describe their similarity
  produced a schema "as an incidental product," "the quality of the induced schema was
  highly predictive of subsequent transfer," and the verbal statements/diagrams that
  had _failed_ with one analog "proved highly beneficial when paired with two." [1]
  **Evidence: STRONG** (foundational, heavily replicated).

- **Active comparison of two cases ≈ _triples_ transfer versus studying the same two
  cases separately — and merely _telling_ the shared principle is not sufficient.**
  Loewenstein, Thompson & Gentner (1999): graduate management students who _compared_
  two negotiation cases were "nearly **three times** more likely" to transfer the
  strategy to a new case than those given the same cases separately (χ²(1,N=58)=6.91,
  p<.01); Gentner, Loewenstein & Thompson (2003) replicated with **47% (15/32)**
  transfer for guided comparison vs **6% (1/16)** without. [2][3] **Evidence: STRONG**
  (multiple experiments, multiple labs/domains).

- **Experts categorize problems by deep structure, novices by surface features, and the
  shift is learnable.** Chi, Feltovich & Glaser (1981): experts sort physics problems
  by underlying principle (a "deep structure," e.g. energy conservation), novices by
  surface objects (inclined plane, spring); "with learning, advanced novices begin to
  categorize problems by the principles with gradual release from dependence on the
  physical characteristics." [4] **Evidence: STRONG.** This makes a _sorting/mapping_
  task a direct read-out of schema/expertise (basis of F4).

- **Analyzing contrasting cases _before_ being told creates "a time for telling."**
  Schwartz & Bransford (1998): students who analyzed contrasting cases and _then_ heard
  a lecture made more accurate predictions on a novel transfer problem a week later than
  those who read the cases + lecture, summarized text + same lecture, or analyzed the
  cases twice with no lecture — i.e. cases-alone and telling-alone both underperform;
  you need **differentiation → then telling**. [5] **Evidence: MODERATE–STRONG**
  (replicated "preparation for future learning" line). Motivates _predict-before-reveal_
  ordering in F1.

- **Worked-example effect: for novices, studying worked solutions beats unguided
  problem-solving, because it frees working memory to build schemas (cognitive load
  theory).** Sweller & Cooper (1985): worked-example learners took ~**half** the
  solution time and made ~**1/5** the errors on later similar problems; a 2023
  meta-analysis puts the math worked-examples effect at Hedges' **g ≈ 0.48**
  (Barbieri et al.). **Caveat baked into the founding study:** the benefit was
  "specific to problems identical in structure" and did **not** extend to _varied_
  post-test problems. [6][7] **Evidence: STRONG** (most-studied cognitive-load effect) —
  but the transfer caveat is exactly why F2/F5 add fading + variability.

- **Worked-example _fading_ plus principle-focused self-explanation extends the benefit
  to transfer.** Renkl, Atkinson & colleagues: **backward fading** (remove the last
  solution step first, then the next-to-last…) beats forward fading and beats
  example–problem pairs for near transfer (Renkl et al. 2000/2002); Atkinson, Renkl &
  Merrill (2003) found fading **alone** reliably helps near transfer but _not_ far
  transfer, whereas **fading + prompts to name the underlying principle at each faded
  step** produced "medium to large effects on near **and** far transfer without
  requiring additional time on task." [8][9] **Evidence: MODERATE** (small-N lab/field
  experiments, consistent direction).

- **Prompted self-explanation reliably improves learning and transfer, and the authors
  explicitly recommend computer-generated prompts.** Chi, Bassok, Lewis, Reimann &
  Glaser (1989): "Good" students spontaneously generate far more self-explanations that
  connect solution steps to principles, yielding _example-independent_ knowledge; Bisra,
  Liu, Nesbit, Salimi & Winne (2018) meta-analysis: **69 effect sizes, 5,917
  participants, random-effects g = 0.55 (95% CI [0.45, 0.65])**, robust across tasks and
  levels. [10][11] **Evidence: STRONG** (meta-analysis). Directly warrants F3 and the
  articulation steps in F1/F2. **Honest tension to respect:** the math worked-examples
  meta-analysis found that _pairing worked examples with self-explanation prompts
  negatively moderated_ the effect (i.e. prompts sometimes hurt in that domain), so
  self-explanation is not a free add-on — it must be tested, not assumed (Barbieri et al.
  2023 [7]).

- **Argument mapping — making an argument's inferential structure explicit (claim,
  premises, objections, links) — raises reasoning skill more than generic
  critical-thinking instruction.** van Gelder (2005) distills six lessons ("acquiring
  CT expertise is hard; practice the skills themselves; **transfer must be practiced**;
  some theory is needed; **diagramming arguments promotes skill**; students preserve
  beliefs"); the argument-mapping meta-analytic summary reports a weighted effect of
  **≈ 0.7** for AM-based instruction (≈ **0.85** for high-intensity courses) versus
  **≈ 0.34** for college CT instruction generally (Abrami et al.). [12][13]
  **Evidence: MODERATE** (largely quasi-experimental pre/post gains; advocate-led — a
  debater should discount for design/selection).

- **Varying surface features aids schema abstraction and transfer — but only when
  cognitive load is managed, and it does not always replicate.** Paas & van Merriënboer
  (1994): **high-variability worked examples** produced better transfer _and_ lower
  cognitive load; an interaction showed variability helped in the **worked-example**
  condition but **not** in the unguided problem-solving condition — variability is "not
  a universal good." At least one recent replication found neither a worked-example nor
  a variability effect. [14] **Evidence: MODERATE / CONTESTED** — use variability _with_
  worked-example scaffolding, not as a free lunch.

- **MYTH / "that-doesn't-work" warnings (all STRONG):**
  - _"Teach generic critical thinking and it will transfer."_ Willingham (2007/2008):
    critical thinking is **not** a domain-general skill; transfer fails because people
    fixate on a problem's **surface structure**, and "there is no proven way to teach"
    general thinking skills directly — you must teach deep structure within content and
    explicitly cue learners to _look for_ deep structure. [15]
  - _"Brain-training generalizes to real cognition."_ Simons et al. (2016, _PSPI_):
    "extensive evidence that brain-training interventions improve performance on the
    trained tasks, less evidence … on closely related tasks, and **little evidence that
    training enhances performance on distantly related tasks** or … everyday cognitive
    performance." [16]
  - _"Far transfer is one thing with one effect size."_ Barnett & Ceci (2002): transfer
    varies along **9 dimensions**; "estimation of a single effect size for far transfer
    is misguided." [17]
  - **Implication for us:** never advertise that LSAT practice makes you "think better"
    broadly. Claim only **near, structure-specific, distance-measured** transfer, and
    _measure the curve_ (F5). Also respect the **expertise-reversal effect** — worked
    examples that help novices can stop helping or even hurt once a learner is skilled
    (Kalyuga, Ayres, Chandler & Sweller 2003), so fading/scaffolding must be adaptive.
    [18]

## Current-LSAT grounding (verified 2026-07-01)

- **The scored LSAT is now two Logical Reasoning sections + one Reading Comprehension
  section; Analytical Reasoning ("Logic Games") was removed as of the August 2024
  exam**, replaced by a second scored LR section, plus one unscored variable section
  (LR or RC). LSAC, "What to Expect Starting With the August 2024 LSAT" and the LSAT FAQ
  / Specifications pages confirm the format. [19][20] **Consequence:** LR is now ~**2/3**
  of the scored exam (our `lsat-taxonomy.yaml` encodes `lr.exam_weight: 0.66`,
  `format_as_of: "2024-08"`), so any LR-transfer feature touches two-thirds of the
  score, and the RC section is heavily argument-analytic too.
- **The highest-skill LR types are literally structure-matching**, and the test-writers
  use surface topic as the distractor: Parallel Reasoning, Parallel Flaw, and
  Method-of-Reasoning ask you to match the abstract _form_ regardless of subject; Flaw
  (the single most common LR type) requires naming an abstract error. Our taxonomy
  already carries `lr.parallel_reasoning`, `lr.parallel_flaw`, `lr.method_of_reasoning`,
  a 15-entry `flaw_catalog`, `skill.argument_parts`, and `rc.application_analogy` — the
  abstract-structure scaffolding exists as tags, but nothing trains or measures
  structural transfer on top of it.

## Proposed features

**Shared substrate (tiny, reuses existing machinery):** a first-class
**argument-structure schema id** — a `struct.*` tag namespace (e.g.
`struct.causal_overgeneralization`, `struct.necessary_sufficient_swap`,
`struct.unrep_sample_to_general`) that groups instances **across surface topics**,
exactly as `flaw_catalog` groups under `lr.flaw`. It rides Anki's tag/sync system
(`lsat/taxonomy.py`, `lsat/events.py`) with **no schema migration** (just more node
ids). Every study feature below reuses the proven Item answer-capture hook — click a
choice → post to Python → grade server-side (correct answer never in the template) →
reveal — so latency and correctness are logged the same way:

```111:121:lsat/notetypes.py
var self = this;
pycmd("lsatAnswer:" + chosen, function (res) {
  if (!res) return;
  self.classList.add(res.correct ? "right" : "wrong");
  if (!res.correct && res.correct_letter) {
    var ok = container.querySelector(
      '.lsat-choice[data-letter="' + res.correct_letter + '"]'
    );
    if (ok) ok.classList.add("right");
  }
});
```

---

### F1 — Same-Bones Pairs (analogical-encoding comparison cards)

- **Pitch.** Show two arguments with **deliberately different topics but one identical
  logical structure**; make the learner _produce_ the shared skeleton **before** any
  label is revealed — the single best-evidenced way to build a transferable schema.
- **Mechanism.** A card presents Stimulus A (say, wildlife conservation) and Stimulus B
  (corporate earnings) side by side. The learner does an **active comparison** in two
  committed steps: (1) _predict_ — "these are the same underneath; how?"; (2) **fill the
  shared skeleton** — a minimal template `Premise pattern → [inferential move] →
  Conclusion`, plus "the move is (un)warranted because…" or the flaw name. Only **after**
  committing does the app "tell": it names the `struct.*`/`flaw.*` schema, shows the
  filled skeleton, and highlights the verbatim source span in each stimulus that anchors
  the shared move. The same schema later returns with a **third, new-topic** twin, so the
  learner re-abstracts rather than recalls the original pair.
- **Theory + citations.** Direct instantiation of schema induction / analogical
  encoding: two disparate analogs + active similarity description → transferable schema,
  and schema quality predicts transfer (Gick & Holyoak 1983 [1]; Loewenstein et al.
  1999 ~3× [2]; Gentner et al. 2003, 47% vs 6% [3]). Predict-before-tell = "a time for
  telling" (Schwartz & Bransford 1998 [5]). The skeleton-articulation step is prompted
  self-explanation (Bisra et al. 2018, g=0.55 [11]). Attaching the diagram/skeleton to a
  **pair** (not a lone item) is exactly what Gick & Holyoak found makes diagrams help.
  **Evidence: STRONG.**
- **LSAT fit.** Parallel Reasoning / Parallel Flaw / Method are _by definition_
  match-the-structure-ignore-the-topic; Flaw (most common type) needs the abstract error
  named. Because every LR stimulus is an argument-with-a-structure, the schema transfers
  across ~2/3 of the exam and into RC argument questions.
- **Implementability.** `lsat/notetypes.py`: add an `LSAT Structure Pair` notetype to
  `_SPECS` (`stimulus_a, stimulus_b, structure_id, flaw_tag, shared_skeleton,
  skeleton_blanks, source_id, source_quote_a, source_quote_b, skill_tags`), reusing the
  Item click/`pycmd`/latency pattern above. `lsat/events.py`: log attempts via
  `append_event(...)` (append-only, HLC-synced), storing produced-skeleton correctness
  and `structure_id` in `skill_tags`. `lsat/ai/`: `generator.py` mints a pair from a
  schema spec (two topics + skeleton + a verbatim `source_quote` per stimulus — the
  existing `quote not in source_text` check drops fabricated citations); the
  **independent** `checker.py` adds criteria _both stimuli instantiate the same
  `structure_id`_ and _their surface topics are genuinely different_ (reuse
  `eval/leakage.py` tf-idf cosine ≤ a `PAIR_SURFACE_COS_MAX`), fail-closed as today;
  `gold_set.py` gates the false-pass rate. UI: a compare screen — a SvelteKit route
  `ts/routes/lsat-pairs/` mirroring `lsat-dashboard`, or a `qt/aqt/` page via `mediasrv`.
  **Effort: M** (AI generator/checker extension + compare UI; data model is additive; no
  Rust/proto for v1).
- **Novelty.** Generic Anki is single-prompt recall — no two-instance comparison, no
  learner-produced schema. Vs our `lsat/interleaving.py` (reorders single items by type)
  this _juxtaposes_ two surface-different, same-structure items and demands the shared
  skeleton. Vs our `eval/paraphrase.py` (rewords _one_ item) it uses two _different_
  items with maximal surface difference. **Convergent with sibling memo C's "Structure
  Twins"** — treat that convergence as corroboration, not duplication; the debate should
  merge them.
- **Risks / failure modes.** _Content validity (top risk):_ a pair that is surface-
  different but secretly structurally _different_ teaches the wrong schema — mitigate
  with the independent structure-match check + surface-distance gate + human `gold_set`,
  shipped behind `card_check` (`CARD_CHECK_PASS_RATE_MIN`, `CARD_CHECK_WRONG_RATE_MAX`).
  _Passive comparison does nothing_ (Gick & Holyoak Part I) — require the produced
  skeleton before reveal (no skeleton → no credit). _Overclaiming transfer_ — never
  assert it; measure it (F5).

---

### F2 — Faded Parallels (worked-example fading for the hardest LR types)

- **Pitch.** Turn Parallel-Reasoning and Method-of-Reasoning from "stare and guess" into
  a **worked-example → completion → solo** ladder that fades support step-by-step,
  backward, with a principle-naming prompt at each faded step.
- **Mechanism.** For a target `struct.*` schema, the learner first sees a **fully worked
  example**: the stimulus, its argument skeleton, and an expert walk-through of _why_ the
  credited parallel answer shares the structure and why two distractors don't. The next
  item is a **completion problem** with the _last_ reasoning step blanked (backward
  fading) — the learner supplies it and names the principle; then the last two steps are
  blank; then it's a normal solo item. Fading is **adaptive**: fast+correct accelerates
  removal of scaffolds; errors add a step back (respecting expertise reversal).
- **Theory + citations.** Worked-example effect for novices (Sweller & Cooper 1985;
  g≈0.48 [6][7]) frees working memory for schema-building; **backward fading** beats
  forward fading and example–problem pairs (Renkl et al. [8]); **fading + name-the-
  principle self-explanation** is what lifts _far_ transfer, not fading alone (Atkinson,
  Renkl & Merrill 2003 [9]); adapt the fade to skill to dodge the **expertise-reversal
  effect** (Kalyuga et al. 2003 [18]). Self-explanation meta-analytic support [11].
  **Evidence: STRONG (worked-example core) / MODERATE (fading specifics).**
- **LSAT fit.** Parallel Reasoning and Method are the types where students most often
  "know the concept" yet can't execute under time; they are multi-step structural
  mappings — the archetypal domain for worked examples and fading. Backward fading maps
  naturally onto "match the conclusion move last."
- **Implementability.** `lsat/notetypes.py`: `LSAT Faded Example` notetype with a
  `fade_level` field (0 = fully worked … N = solo) and a `worked_steps` list; one
  authored schema instance expands into a fade ladder. `lsat/ai/generator.py` produces
  the worked steps + a checkable principle per step; `checker.py` verifies each step is
  supported by a verbatim `source_quote` and that the "parallel" answer truly shares
  `structure_id`. `lsat/events.py`: log each rung, adding a `fade_level` node tag so the
  learning curve across fade levels is analyzable while staying append-only/HLC. Scheduling
  can key off the existing points-at-stake `perf_mastery` scalar (no Rust change).
  `eval/`: an `eval/fading.py` reporting near vs far transfer by fade schedule; a
  `+faded` arm in `eval/ablation.py` (equal study time, `bootstrap_ci`). **Effort: M.**
- **Novelty.** No LSAT product (7Sage, LSAT Demon, PowerScore, LawHub) serves an
  adaptive faded worked-example ladder; they give full timed questions + written
  explanations. Anki has no notion of fading. Distinct from F1 (which compares two
  finished arguments) — F2 scaffolds the _construction_ of one structural match.
- **Risks / failure modes.** _Expertise reversal_ — a strong learner finds full
  worked-outs boring/harmful; mitigate with adaptive entry (start higher on already-
  strong schemas, using existing mastery). _Content cost_ — authoring correct step
  decompositions is hard; guard with the independent checker + `gold_set`. _Fade schedule
  is a hyperparameter_ — expose it as an ablatable config, don't hard-code.

---

### F3 — Trap Autopsy (self-explanation elimination prompts)

- **Pitch.** After every graded item, make the learner **explain why the credited answer
  is right and why each attractive trap is wrong** — the highest-ROI, cheapest-to-build
  transfer intervention we have evidence for (g=0.55).
- **Mechanism.** On the answer side, the app surfaces the credited choice plus the 1–2
  most-chosen distractors and asks the learner to tag _why_ each is right/wrong: a quick
  **menu** of trap categories (reusing `skill.trap.*`: out-of-scope, extreme language,
  reversal, half-right, irrelevant comparison) **and** a one-line free-text
  self-explanation. An AI grader (independent checker) scores the explanation against a
  rubric (did it name the actual flaw / the actual scope mismatch?) and gives targeted
  feedback; weak explanations re-queue the item's _schema_, not just the item.
- **Theory + citations.** Self-explanation effect: prompting learners to explain
  produces example-independent knowledge (Chi et al. 1989 [10]) and a meta-analytic
  **g = 0.55** across 69 effects, with the authors explicitly recommending
  computer-generated prompts (Bisra et al. 2018 [11]) — which our pipeline already does.
  Naming _why a distractor is wrong_ is self-explanation aimed at the exact competence
  the test rewards (trap elimination). **Evidence: STRONG.**
- **LSAT fit.** LSAT scoring is as much about _eliminating_ 4 wrong answers as finding 1
  right one; distractors are engineered around a small set of recurring trap patterns our
  taxonomy already enumerates. Articulating the trap builds the discrimination that
  transfers to new items with the same trap.
- **Implementability.** Smallest footprint: extend the existing `LSAT Item` answer
  template (the `pycmd` hook already reports the chosen letter) to collect the trap tags
  - free text; store them via `lsat/events.py` (add `chosen_option` and a
    `self_explanation_ok` node tag — additive, append-only). `lsat/ai/`: reuse
    `checker.py`/`prompts.py` to grade explanations against a rubric with a cited span;
    `gold_set.py` validates the grader's false-pass rate before it's trusted. Dashboard:
    per-trap accuracy in `lsat/dashboard_data.py` → `qt/aqt/lsat_performance.py` +
    `ts/routes/lsat-dashboard/`. **Effort: S–M** (mostly template + event fields + a grader
    prompt; no Rust/proto).
- **Novelty.** Competitors _show_ written explanations (passive reading); none require
  the learner to _produce and get scored on_ a why-right/why-wrong self-explanation with
  automatic feedback that re-queues the schema. Anki has free-text but no graded
  self-explanation loop. Distinct from sibling memo R2's engineered trap-_pairs_: F3 is a
  metacognitive articulation step layered on normal items, not a new item type.
- **Risks / failure modes.** _Grading free text is noisy / gameable_ — offer the menu as
  the graded fallback, treat free-text as bonus, and validate the grader on `gold_set`
  before trusting it (fail-closed). _Self-explanation is not universally positive_ — in
  math, prompts _negatively_ moderated the worked-example effect (Barbieri et al. 2023
  [7]), so this must be A/B'd against a no-prompt arm rather than assumed from the g=0.55
  average. _Added friction / time_ — keep it one line, make it skippable under a pacing
  mode, and A/B the completion cost. _Feedback could leak the answer to a synced future
  item_ — reuse `eval/leakage.py` cosine gate.

---

### F4 — Skeleton Builder (argument-mapping drill + structural tagging)

- **Pitch.** A drill where the learner **builds the abstract argument skeleton** of a
  stimulus — mark the conclusion, the premises, the inferential move, and name the flaw —
  turning van Gelder's argument mapping into a fast, gradeable LSAT micro-task that also
  _labels_ items with `struct.*` for the rest of the system.
- **Mechanism.** Given a stimulus, the learner drags/clicks to (1) select the sentence
  that is the **conclusion**, (2) mark **premises** vs background, (3) pick the
  **inferential move** from a small set (generalization from sample, cause from
  correlation, conditional chain, appeal to authority…), and (4) name the **flaw** if
  any. The app grades the map against the authored structure and reveals a clean
  box-and-arrow skeleton. Completed maps double as **weak supervision**: a learner- or
  AI-built, checker-verified skeleton becomes the item's `struct.*`/`flaw.*` tag and its
  `shared_skeleton`, feeding F1/F2/F5.
- **Theory + citations.** Argument mapping "promotes skill," and _practicing the skills
  themselves_ + _practicing transfer_ are two of van Gelder's six lessons (2005 [12]);
  AM-based instruction ≈ 0.7 (0.85 high-intensity) vs ≈ 0.34 for generic CT [13].
  Building the structural representation is precisely the novice→expert shift Chi et al.
  (1981) documented [4], and marking conclusion-vs-premise is the `skill.argument_parts`
  competency. **Evidence: MODERATE** (AM evidence is quasi-experimental; discount
  accordingly).
- **LSAT fit.** "Find the conclusion first" and "diagram the argument" are canonical LR
  advice; Main-Conclusion, Role-in-Argument, and Method questions are _literally_ asking
  for pieces of the skeleton. The map is the shared representation every other feature
  needs.
- **Implementability.** `lsat/notetypes.py`: `LSAT Skeleton` notetype (or an overlay on
  `LSAT Item`) storing `conclusion_span, premise_spans, move_id, flaw_tag`. UI: a
  span-selection panel (SvelteKit route or `qt/aqt` via `mediasrv`). `lsat/ai/`:
  `generator.py` proposes a skeleton with verbatim spans; `checker.py` independently
  verifies conclusion/premise assignment and `move_id` (this is the content-validity
  gate that lets maps be trusted as tags). `lsat/taxonomy.py` + `lsat-taxonomy.yaml`: add
  the `struct.*` namespace and a small `move` catalog beside `flaw_catalog`.
  `lsat/events.py`: log map correctness per component (append-only). **Effort: M–L**
  (the span-selection UI is the cost; the tagging payoff is high leverage).
- **Novelty.** No LSAT tool has a gradeable argument-map builder; Anki has nothing
  structural. Unlike a passive "here's the diagram" explanation, the learner _constructs_
  it. It's also the **infrastructure** that makes F1/F2/F5 cheap (every item gains a
  verified `struct.*` label).
- **Risks / failure modes.** _UI complexity_ — start with just conclusion-selection +
  move-naming (S), grow to full maps later. _Ambiguous structure_ — some stimuli have
  defensible alternative parses; let the checker accept a set of valid maps and flag
  genuinely ambiguous items out. _Mapping ≠ answering under time_ — keep it as a training
  drill, and verify (F5) that map skill predicts item accuracy before over-investing.

---

### F5 — One-Skill-Many-Topics (variability drilling + a surface-distance transfer meter)

- **Pitch.** Deliberately drill each schema across **many maximally-different surface
  topics**, and **measure accuracy as a function of surface distance** so we can tell
  "memorized here" from "actually transferred" — the honesty layer that keeps F1–F4
  from fooling us.
- **Mechanism.** _Drill:_ when a `struct.*` schema is due, the queue serves successive
  items whose _surface topics_ are as different as possible (law, biology, art,
  economics) while structure is held constant — variability that forces abstraction.
  _Meter:_ for each schema, compute **surface distance** `d = 1 − cosine_surface(item,
  seen items)` (existing tf-idf vectors in `eval/leakage.py`, with logical-connective /
  stem-cue tokens down-weighted so distance reflects _topic_, not _form_), then report
  the **memorization gap** = P(correct | near) − P(correct | far), the **transfer index**
  = P(correct | far), and the **structure slope** β in `P(correct) ~ ability + β·d +
  difficulty`. A per-schema dashboard badge reads **"Memorized here"** vs
  **"Transferred"**, and refuses to call a schema learned until it's shown on new
  surface.
- **Theory + citations.** High **variability of practice** aids schema abstraction and
  transfer _when load is scaffolded_ (Paas & van Merriënboer 1994 [14]) — so pair
  variability with the F2/F4 scaffolds, not with cold problem-solving. Measure transfer
  as a **distance-graded curve**, never a single number (Barnett & Ceci 2002 [17]); be
  explicit that we are buying **near** transfer, not brain-training's illusory far
  transfer (Simons et al. 2016 [16]) or generic critical thinking (Willingham [15]).
  Schema quality predicts transfer (Gick & Holyoak [1]) — the meter is the observable
  proxy. **Evidence: MODERATE/CONTESTED (variability) + STRONG (measurement caution).**
- **LSAT fit.** The exam _is_ one-skill-across-endless-topics; a student who is right on
  "the vaccine causal flaw" but wrong on "the ad-revenue causal flaw" has memorized, not
  learned. The meter measures the exact thing the test measures and prevents us from
  shipping surface-bound drills.
- **Implementability.** Mostly `eval/` + queue + dashboard, reusing existing plumbing:
  `eval/transfer.py` (report-only first, like `paraphrase.py`) fits the per-schema
  logistic with `bootstrap_ci`; `eval/leakage.py` supplies surface distance;
  `eval/ablation.py` gets the `+variability` arm; `eval/calibration.py` (`ECE_MAX`) stays
  green. The drill orders items by max surface distance within a `struct.*` (a small
  extension to `lsat/interleaving.py` / the points-at-stake weighting — no Rust needed if
  it stays within the per-request mastery scalar). Dashboard badge via
  `lsat/dashboard_data.py` → `qt/aqt/lsat_dashboard.py` + `ts/routes/lsat-dashboard/`,
  abstaining until enough new-surface items exist (reuse the readiness "give-up" gate
  pattern in `lsat-taxonomy.yaml`). **Effort: S–M.**
- **Novelty.** Competitors report accuracy and per-type timing; **none report a
  memorization-vs-transfer separation per argument schema over surface distance**. It
  extends `eval/paraphrase.py` from same-item rewording to cross-item, same-structure,
  distance-graded transfer. Convergent with sibling memo C's "Schema Transfer Meter"
  (merge in debate); the _variability drill_ half is distinct.
- **Risks / failure modes.** _Variability may not help / may not replicate_ — ship it
  as an ablatable arm and let the meter itself adjudicate; only keep it if the far-surface
  index rises. _Bag-of-words distance is a proxy_ — shared logical-marker words inflate
  similarity; down-weight them and flag as a limitation. _Difficulty×distance confound_
  (far items may just be harder) — control with the `difficulty` field on `LSAT Item`.
  _Cold start_ — give-up gate until enough surfaces exist. _Synthetic-learner caveat_ —
  as `eval/ablation.py` documents, this proves the methodology pending a real A/B.

## Ranked shortlist (best first)

1. **F3 — Trap Autopsy (self-explanation elimination).** Best evidence-to-effort ratio:
   meta-analytic g=0.55, trains the exact trap-elimination skill, and is a small
   extension of the existing Item hook + AI checker. **Evidence: STRONG.**
2. **F1 — Same-Bones Pairs (analogical-encoding comparison).** The single
   best-evidenced way to _build_ a transferable schema (Gick & Holyoak; Gentner ~3×,
   47% vs 6%), aimed straight at Parallel/Method/Flaw. **Evidence: STRONG.** (Merge with
   sibling memo C's Structure Twins.)
3. **F5 — One-Skill-Many-Topics + transfer meter.** The honesty layer; cheap, reuses
   eval/leakage/ablation, and is the prerequisite for claiming any of this beats
   memorization. **Evidence: STRONG (measurement) / MODERATE (variability drill).**
4. **F2 — Faded Parallels (worked-example fading).** Strong core theory (worked-example
   effect) with moderate fading specifics; highest instructional value for the types
   students plateau on. **Evidence: STRONG/MODERATE.**
5. **F4 — Skeleton Builder (argument mapping).** High leverage as infrastructure
   (auto-labels items with `struct.*`), but AM evidence is quasi-experimental and the UI
   is the biggest build. **Evidence: MODERATE.**

## Threats to validity (what a debater should attack — and my answers)

- **"Far transfer barely exists."** Conceded for _true_ far transfer (Barnett & Ceci;
  Simons; Willingham). LSAT cross-_topic_ transfer is **near** on ~8 of 9 Barnett–Ceci
  dimensions; I target that gradient and **measure the curve** (F5), never a binary or
  broad-CT claim.
- **"Worked examples don't transfer / expertise reversal."** True — Sweller & Cooper's
  own gains were structure-specific, and scaffolds hurt experts (Kalyuga). That's why F2
  _fades adaptively_ and F5 _varies surface_; the transfer meter is the check.
- **"Argument-mapping evidence is advocate-led and quasi-experimental."** Agreed — F4 is
  ranked last and gated on F5 showing map skill predicts item accuracy before we invest.
- **"AI can't reliably make true structural twins / faded steps."** The biggest real
  risk; guarded by the independent, fail-closed `checker.py` (structure-match +
  surface-distance + verbatim span), the `gold_set` false-pass gate, and `card_check` —
  the same defenses already gating our card pipeline.
- **"The eval is synthetic."** True today (documented in `eval/ablation.py`); I ship
  pre-registered designs with **ablatable** bonus parameters and the same honesty stance
  as the existing `INTERLEAVE_BONUS`.

## Sources

**Learning theory (peer-reviewed / primary).**

1. Gick, M. L., & Holyoak, K. J. (1983). Schema induction and analogical transfer.
   _Cognitive Psychology, 15_(1), 1–38. https://doi.org/10.1016/0010-0285(83)90002-6 ·
   PDF: https://deepblue.lib.umich.edu/bitstream/handle/2027.42/25331/0000776.pdf
2. Loewenstein, J., Thompson, L., & Gentner, D. (1999). Analogical encoding facilitates
   knowledge transfer in negotiation. _Psychonomic Bulletin & Review, 6_(4), 586–597.
   https://doi.org/10.3758/BF03212967 · PDF:
   https://groups.psych.northwestern.edu/gentner/papers/LoewensteinThompsonGentner99.pdf
3. Gentner, D., Loewenstein, J., & Thompson, L. (2003). Learning and transfer: A general
   role for analogical encoding. _Journal of Educational Psychology, 95_(2), 393–408.
   https://groups.psych.northwestern.edu/gentner/papers/GentnerLoewensteinThompson03.pdf
4. Chi, M. T. H., Feltovich, P. J., & Glaser, R. (1981). Categorization and
   representation of physics problems by experts and novices. _Cognitive Science, 5_(2),
   121–152. https://doi.org/10.1207/s15516709cog0502_2 · PDF:
   http://matt.colorado.edu/teaching/highcog/readings/cfg81.pdf
5. Schwartz, D. L., & Bransford, J. D. (1998). A time for telling. _Cognition and
   Instruction, 16_(4), 475–522. https://aaalab.stanford.edu/papers/time_for_telling.pdf
6. Sweller, J., & Cooper, G. A. (1985). The use of worked examples as a substitute for
   problem solving in learning algebra. _Cognition and Instruction, 2_(1), 59–89.
   https://doi.org/10.1207/s1532690xci0201_3
7. Barbieri, C. A., Miller-Cotto, D., Clerjuste, S. N., & Chawla, K. (2023). A
   meta-analysis of the worked examples effect on mathematics performance. _Educational
   Psychology Review, 35_, 11. https://doi.org/10.1007/s10648-023-09745-1 · PDF:
   https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf
8. Renkl, A., Atkinson, R. K., Maier, U. H., & Staley, R. (2002). From example study to
   problem solving: Smooth transitions help learning (fading worked-out solution steps;
   backward > forward fading). _Journal of Experimental Education, 70_(4), 293–315. PDF:
   http://www.davidlewisphd.com/courses/EDD8121/readings/2002-Renkl_et_al.pdf
9. Atkinson, R. K., Renkl, A., & Merrill, M. M. (2003). Transitioning from studying
   examples to solving problems: Effects of self-explanation prompts and fading
   worked-out steps. _Journal of Educational Psychology, 95_(4), 774–783.
   https://doi.org/10.1037/0022-0663.95.4.774 · record: https://eric.ed.gov/?id=EJ678596
   · review: Atkinson, Derry, Renkl & Wortham (2000), _Review of Educational Research,
   70_(2), 181–214, https://doi.org/10.3102/00346543070002181
10. Chi, M. T. H., Bassok, M., Lewis, M. W., Reimann, P., & Glaser, R. (1989).
    Self-explanations: How students study and use examples in learning to solve problems.
    _Cognitive Science, 13_(2), 145–182. https://doi.org/10.1207/s15516709cog1302_1 ·
    PDF: https://files.eric.ed.gov/fulltext/ED296291.pdf
11. Bisra, K., Liu, Q., Nesbit, J. C., Salimi, F., & Winne, P. H. (2018). Inducing
    self-explanation: A meta-analysis. _Educational Psychology Review, 30_(3), 703–725.
    https://doi.org/10.1007/s10648-018-9434-x · record: https://eric.ed.gov/?id=EJ1186664
12. van Gelder, T. (2005). Teaching critical thinking: Some lessons from cognitive
    science. _College Teaching, 53_(1), 41–48. https://doi.org/10.3200/CTCH.53.1.41-48 ·
    PDF: https://people.bath.ac.uk/edspd/Weblinks/PGCES%20ULL%20articles/Learning%20to%20Learn/van%20Gelder%202005%20CT.pdf
13. van Gelder, T. (2015/rev.). Using argument mapping to improve critical thinking
    skills (meta-analytic summary: AM-based CT ≈ 0.7, high-intensity ≈ 0.85; cf. Abrami
    et al. ≈ 0.34 for CT instruction generally; see also Álvarez-Ortiz 2007 thesis).
    PDF: https://reasoninglab.com/wp-content/uploads/2013/10/TvG-Using-argument-mapping-to-improve-critical-thinking-skills-2015.pdf
14. Paas, F. G. W. C., & van Merriënboer, J. J. G. (1994). Variability of worked examples
    and transfer of geometrical problem-solving skills: A cognitive-load approach.
    _Journal of Educational Psychology, 86_(1), 122–133.
    https://doi.org/10.1037/0022-0663.86.1.122 · replication caveat (null):
    https://files.eric.ed.gov/fulltext/ED604512.pdf
15. Willingham, D. T. (2007/2008). Critical thinking: Why is it so hard to teach?
    _American Educator, 31_ / _Arts Education Policy Review, 109_(4), 21–32. PDF:
    https://www.aft.org/sites/default/files/media/2014/Crit_Thinking.pdf · reprint:
    https://people.bath.ac.uk/edspd/Weblinks/MA_ULL/Resources/Learning%20to%20Learn/Willingham%202008%20AEPR.pdf
16. Simons, D. J., Boot, W. R., Charness, N., Gathercole, S. E., Chabris, C. F.,
    Hambrick, D. Z., & Stine-Morrow, E. A. L. (2016). Do "brain-training" programs work?
    _Psychological Science in the Public Interest, 17_(3), 103–186.
    https://doi.org/10.1177/1529100616661983 · PDF:
    https://gwern.net/doc/dual-n-back/2016-simons.pdf
17. Barnett, S. M., & Ceci, S. J. (2002). When and where do we apply what we learn? A
    taxonomy for far transfer. _Psychological Bulletin, 128_(4), 612–637.
    https://doi.org/10.1037/0033-2909.128.4.612
18. Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003). The expertise reversal
    effect. _Educational Psychologist, 38_(1), 23–31.
    https://doi.org/10.1207/S15326985EP3801_4

**LSAT format (primary).**
19. LSAC. What to expect starting with the August 2024 LSAT (Oct 18, 2023).
https://www.lsac.org/blog/what-to-expect-starting-with-august-2024-lsat · Changes
coming Aug 2024: https://www.lsac.org/lsat/lsat-changes-coming-august-2024
20. LSAC. Frequently asked questions about the LSAT / Specifications of the LSAT and LSAT
Argumentative Writing (current format: two scored LR + one RC + one unscored variable).
https://www.lsac.org/lsat/frequently-asked-questions-about-lsat ·
https://www.lsac.org/lsat/register-lsat/accommodations/specifications-lsat-and-lsat-argumentative-writing

**In-repo integration points cited above.** `lsat/notetypes.py` (Item answer-capture
hook), `lsat/events.py` (append-only HLC event log, `append_event`,
`fold_recent_performance`), `lsat/interleaving.py`, `lsat/taxonomy.py` +
`lsat-taxonomy.yaml` (`flaw_catalog`, `lr.parallel_*`, `skill.argument_parts`,
`skill.trap.*`), `lsat/ai/{generator,checker,prompts,gold_set,pipeline}.py` (verbatim
source-span defense; independent fail-closed checker; `validate_checker`),
`eval/{paraphrase,leakage,ablation,calibration,card_check,config}.py` (tf-idf cosine;
`bootstrap_ci`; equal-time arms; `ECE_MAX`; `CARD_CHECK_*`), `lsat/dashboard_data.py`,
`qt/aqt/lsat_dashboard.py`, `qt/aqt/lsat_performance.py`, `ts/routes/lsat-dashboard/`.
