# AI Features to Help LSAT Candidates Prepare Faster — Research

**Question.** What _AI (LLM/model-powered)_ features would help an LSAT candidate
prepare **faster** — learn more per study hour, or reach a target score in fewer
hours — that this app could add _without breaking its honesty discipline_?

**Method.** A multi-agent research loop (the project's established pattern): a broad
fan-out over nine AI-feature areas, critiqued by a four-lens panel (cognitive
scientist · LSAT coach · AI/ML engineer · student-advocate) and ranked by
`prep-speed × feasibility × honesty-safety`, then four deep-dive agents (prior-art
landscape · adversarial red-team · honest speed quantification · build roadmap +
the load-bearing unlock). Sources are the learning-science literature cited inline
and the project's own code. This doc **revises the AI-feature proposals**; the
learning-science corpus in `docs/Speedrun_Research_Support.md` and `research/` is the
backing and is unchanged.

**The honesty constraints an AI feature must meet here** (from the project spec):
runtime AI must be _traceable + checkable_ (an independent checker + a
human-spot-checked gold set before a learner sees output); every learning-effect
claim ships behind a **measured `eval/` arm at equal study time** with a bootstrap
CI excluding 0 (honest single-digit-point ceiling; no fabricated
readiness/percentile/"2-sigma"); the app **runs fully with AI OFF** (AI is additive,
never load-bearing for a grade/score); and no leaked/copyrighted test content.

---

## The one-paragraph answer

AI accelerates LSAT prep **fastest when it is a _constrained transform over
authoritative artifacts_, never an authority.** The four transform shapes that all
top features share: **generate-with-a-proof** (an LLM drafts, a decidable oracle
verifies), **classify-onto-a-closed-label-set** (grade a learner's free text into
the documented trap/flaw taxonomy), **point-at-a-verbatim-span** (ground an
explanation in the exact words of _this_ item), and **tie-break-a-deterministic
ranking** (allocation, not authorship). Correctness/score/grade always stays with
deterministic code, a complete oracle, or checker-passed gold. Within that shape,
the biggest honest speed lever is **turning passive reading into active production
that is cheap to _grade_** (self-explanation, worked-example fading) — "cheap" here
means the _grading_ is a bounded closed-set/oracle check, **not** that it is cheap in
student _time_: production costs seconds per item, so "faster" only holds at **equal
study time** and must be _measured_, not asserted. The lowest-risk, broadest lever is **AI for
targeting and allocation of a fixed study hour** (diagnosis → routing → next-action),
not manufacturing raw content — LR content is abundant in the market, so "content
scarcity" is mostly app-internal, and content _generation_ is gated by a
copyright/originality wall that is currently open offline.

---

## Two organizing principles (the intellectual core)

**1. The verification-strength ladder.** How far an AI feature can be trusted is set
by how its output is checked, strongest to weakest:

> complete oracle (a _proof_) ▸ deterministic substring / label equality ▸
> gold-set-gated independent LLM-entailment judge ▸ free prose (**never** shown as fact)

Rank AI features by where their correctness claim sits on this ladder. The #1 feature
tops the list precisely because formal-logic LR is _decidable_ and its oracle already
ships in this repo.

**2. Confident-wrong is the danger zone.** The costliest AI failure is not a refusal
— it is **validating a wrong answer or a wrong diagnosis** (sycophancy / checker
false-pass), which cements the exact confident-wrong misconception the app exists to
fix. So every generative/grading feature must measure its **false-"correct" / false-
pass rate** against a pre-declared ceiling on a gold set (with an adversarial slice)
and stay **OFF until it clears** — mirroring the shipped `validate_checker`.

---

## The prep-speed bottlenecks AI can attack

- **Slow feedback loops** — a miss becomes a slow read of a generic explanation the
  learner must re-map onto _this_ item.
- **Weak, flat error diagnosis** — "you miss 30% of Strengthen" without _which_
  confusion or _what to do about it_.
- **Passive review** — re-reading an explanation invites the illusion of explanatory
  depth; nothing makes the learner _produce_ the diagnosis and grades it.
- **Non-transferring reps** — practice that builds item-specific familiarity, not the
  reusable schema.
- **RC comprehension** (~1/3 of the scored exam, least-served) — the slow loop of
  answering 5–7 questions and reverse-engineering that the _mental map_ was broken.
- **"What do I do next"** — novices skip the SRL-forethought step and default to a
  low-yield full PrepTest.

Note the bottleneck AI does **not** need to solve for LR: raw _content scarcity_.
Official + commercial LR content is abundant; the scarce thing is _targeted,
verified_ practice and _fast, grounded_ feedback.

---

## What the app already has (the scaffolding new AI features reuse)

The repo already ships a mature, honesty-safe AI subsystem — new features plug into
it rather than reinventing safety:

- **An independent checker** (`lsat/ai/checker.py`) that re-derives a card's verdict
  from its cited source span, never trusting the generator, and is itself validated
  against a **50-pair gold set** for false-pass rate (`lsat/ai/gold_set.py`).
- **A generator** with a _defensive parse_ + a **verbatim source-span check** (a
  citation must be a substring of the sent chunk, or the card is dropped) and a
  rule-based **OfflineClient** that _cannot_ follow injected instructions
  (`lsat/ai/generator.py`, `client.py`) — prompt-injection defense by construction.
- **Graceful AI-OFF degradation** everywhere (`pipeline.py`): if the LLM is
  unavailable, the batch is skipped and human content keeps serving; the review loop
  never blocks.
- **Label-grounded misconception hypotheses** (`misconception.py`): the LLM may only
  _rephrase_ a catalog entry, fail-closed (the label must survive, no new content),
  with the deterministic text as fallback — the template for grounded LLM feedback.
- **An equal-study-time eval harness** (`eval/feedback.py`: `TIME_BUDGET_S`, per-arm
  `COST_S`, `bootstrap_ci`, ship-only-if-CI-excludes-0) — the adjudicator for every
  "prepares faster" claim.

Because of this, the disciplined pattern for a _new_ AI feature is: LLM
transforms/classifies/points, an existing oracle/checker/gold-gate certifies, and the
whole thing degrades to a deterministic fallback with AI off.

---

## Ranked AI features (Wave-1 panel, composite of prep-speed × feasibility × honesty)

_Ordered by the Wave-1 composite; the Wave-2 deep-dives (below) refine this — notably,
the quantification revealed #2 and #6 are **allocation aids** with no borrowable effect
size (so #6's composite is revised down to a near-tie with #5), and the red-team's
**residual-risk** order is a different axis (safety, not speed) in which #6 ranks high.
Also note **#3's Wave-1 composite (≈7.7) predates the red-team's "High-risk / ship-AI-off"
finding** — its high per-item effect is real, but its _shipping_ form is the AI-off
ungraded-self-explanation default, with the LLM grader gated behind the two-sided
adversarial+ESL gate. Feature numbers here are stable identifiers used throughout the doc._

### 1 — Oracle-Verified Faded Worked Examples (formal-logic LR) · composite ≈ 9

> **✅ SHIPPED (2026-07-02).** Implemented for the multi-arrow-chain case in
> `lsat/worked_example.py` (LLM drafts → `conditional_chain.entails` oracle
> verifies/blocks; deterministic AI-off floor; backward fading), gated by
> `eval/worked_example.py` (**0 false-passes** over planted + 3014 fuzz cases,
> full valid-proof coverage; `make eval` GATE OK), and reachable via the mobile
> Logic tab (`WorkedExampleDrill.svelte`). See `docs/improvements-log.md`.

The only proposal whose correctness check is a **mathematical proof**, not an LLM
opinion. An LLM drafts a step-by-step worked solution for a conditional / quantifier
/ multi-arrow-chain item; each logical step carries a structured trace (translation /
contrapositive / quantifier-negation / chain-entailment) and the **shipped
model-checkers** (`lsat/quantifier.py` enumerates all Venn models; `conditional_chain.py`
grades by exact truth-table material entailment; `conditional.py` computes
contrapositives) **re-derive every step and BLOCK the example unless all steps
verify** — a hallucinated inference literally cannot pass. **The shipping variant
renders narration from the proven structure via template** (referencing only verified
terms/arrows) — this template-only path is what earns the "lowest residual risk" rating
in the red-team below; a free-prose LLM rephrase of the hint is an _optional_ extra that
must clear the fail-closed rephrase gate and never touches step correctness. Steps
**fade** as mastery rises (backward fading), and the oracle's answer is the AI-off
fallback.

- _Faster, honestly:_ fewer study events to build the formal-logic procedural schema
  than repeated cold solving (worked-example effect, Sweller & Cooper 1985) + transfer
  from backward fading + self-explanation (Atkinson et al. 2003). Ceiling: single-digit
  scaled points **for that slice only**, shrinking as fluency rises (expertise
  reversal), claimed only if the faded-minus-solve equal-time CI excludes 0.
- _Eval:_ new `eval/worked_example.py` — a hard step-verification gate (oracle
  false-pass ~0 by construction, reported) + a 3-arm equal-time ablation
  {adaptive-faded, worked-only, solve-only} with an expertise-reversal guard.
- _Build:_ new `lsat/worked_example.py` (assemble trace → call the three oracles →
  fade by the existing `perf_mastery` fold); reuse `ai/{generator,checker,client,
  gold_set}` + the drill notetype + `DrillPicker`/`ConditionalDrill` reveal surfaces.
  No Rust/proto for v1. Feasibility **M**.

### 2 — Directed Confusion-Pair Diagnosis + drill routing · composite ≈ 8

The best error-diagnosis play _and_ statistically tractable: a **2-way directed
matrix** (the stem-type the item actually was × the structural family of the
distractor the learner chose) avoids the sparse high-dimensional fragility that sinks
compound cross-tab diagnosis. The LLM does bounded **classification into a CLOSED set**
of documented directional confusions (e.g. "over-selects sufficient-strength answers
on necessary-assumption stems"), then **routes to an existing discrimination drill** —
so a worst-case misroute is a valid-but-suboptimal drill, never a wrong grade. No new
content generated → no leakage surface.

- _Faster:_ turns a direction-blind "reversal owns 30% of your misses" bucket into a
  routed decision — one of ~4 discrimination drills instead of all four — so equal
  study time hits the drill that fixes the actual confusion. Bounded: helps only where
  a real directional confusion exists (abstains under thin evidence); equal-time CI decides.
- _Honesty:_ closed confusion-pair set pre-mapped to catalog nodes + a named existing
  drill; the asserted direction is programmatically consistent with the cited items;
  an independent checker re-derives it; a synthetic-trajectory gold set with a KNOWN
  injected direction validates directional-recovery vs a pre-declared misroute cutoff.
- _Build:_ deterministic directed-confusion-matrix builder over `lsat/events.py` folds
  - a closed confusion→drill map + the classifier + checker + synthetic gold; reuse the
    four discrimination drills + their eval arms. Feasibility **S–M**. _(Quick win: the
    deterministic matrix + route-by-dominant-off-diagonal-cell needs no LLM at all and
    already beats the flat trap histogram — ship that floor first.)_

### 3 — "Say why B is wrong": self-explanation graded by closed-set classification · ≈ 7.7

Adds the one ICAP _constructive/interactive_ tier the app lacks — the learner
**produces** the error diagnosis instead of reading one. Self-explanation is the
single largest per-item learning multiplier in the cited literature (g≈0.55, Bisra et
al. 2018), and grading it directly counters the illusion of explanatory depth. The
LLM does **classification only** onto a fixed enum (`TRAP_FAMILY_LABELS` + flaw
catalog + off-target) + a verbatim quote of the learner's own phrase; the authoritative
`distractor_traps` family is the gold label; corrective _content_ is always the
gold-gated `contrast.py` catalog, so a misclassification can only mis-score a
diagnosis, never teach a fabricated fact — and the grade touches no score.

- _Faster:_ converts each miss from a read into a retrieval-plus-self-explanation rep.
  Honest catch: it costs the _most_ seconds/item, so "faster to target" holds only if
  the per-item gain beats the item-count penalty — exactly what the equal-time eval
  adjudicates.
- _Eval:_ an `se` arm in `eval/feedback.py`; ship only if `bootstrap_ci(se − ef)`
  excludes 0. Separately gate the classifier's false-"correct" rate on a labelled +
  human-spot-checked gold set (with an adversarial prompt-echo/keyword-stuffing slice).
- _Build:_ one classification prompt + the gold set + false-"correct" gate + a small
  input UI (the item template already has choice-tap + pycmd plumbing). Feasibility **M**
  (S for the deterministic fallback).

### 4 — Verdict-locked, span-grounded "Why not B?" tutor · ≈ 7.3

Complements #3: where #3 grades the learner's _produced_ diagnosis, #4 supplies a
grounded explanation to _read_ — and **never lets the model decide correctness**. The
credited letter + authoritative trap family are **locked inputs**; the model returns
only (a) the family name verbatim, (b) an `evidence_span` that is a verbatim substring
of the chosen choice, (c) a `stimulus_span` verbatim substring of the stimulus, (d)
≤2 connective sentences banned from asserting any new fact/number. A mostly-**deterministic**
checker (exact-substring containment + label equality + banned-content regex + an
independent entailment call that fails the answer if it claims a non-credited choice
is right) fluent prose cannot fool. It converts the generic contrast-card clause into
a pointer to the exact words in _this_ item (signaling / cognitive-load reduction).

- _Faster:_ fewer seconds to process feedback per item. Honest ceiling: the
  elaborated-feedback-over-KCR increment is only ~g=0.17, and this is EF-over-EF
  (span-specific vs generic template), so the true increment is plausibly _smaller_ and
  could be null — the equal-time `ge` arm decides; report the honest negative.
- _Build:_ one "why?" button + one endpoint (the render path already exists — a miss
  already returns the contrast card via pycmd). Reuse `checker.py`'s independent
  re-derivation call (the generate-then-independently-check _pipeline_ pattern)
  - `contrast.py` as fail-closed fallback + eval baseline. Feasibility **M**.

### 5 — Passage-Map Coach: graded free-response comprehension recall (RC) · ≈ 7

The honest way to attack RC (~1/3 of the exam, least-served). The two RC-_generation_
proposals are **disqualified** (see _Avoid_) by the copyright wall; #5 sidesteps it by
**grading a learner's free-text main-point + viewpoint-attribution recall against a
per-passage HUMAN gold map on _licensed_ passages** — no passage is generated, so
there is no leakage surface. It creates the fast active-recall of _comprehension_ the
app entirely lacks (today `grading.py` handles only letters/taps). The grader emits
only fixed rubric labels (`{thesis_captured, author_stance_captured, main_contrast_captured}`

- error labels each carrying the contradicted span), fail-closing to "here is the gold
  map — self-compare."

* _Faster:_ one ~30s graded recall surfaces a broken situation-model immediately,
  replacing the slow answer-5-questions-then-reverse-engineer loop; an actively
  generated, feedback-corrected gist is more durable per minute than re-reading.
  Bounded: single-digit RC-accuracy gain at equal time, only if the CI excludes 0.
* _Eval:_ new `eval/rc_map_grader.py` — HARD false-pass gate (mirrors `card_check`) +
  a planted-wrong-map self-test it must catch + a report arm (read+questions vs
  read+graded-map-recall+questions).
* _Build:_ an RC rubric label set + a per-passage gold-map field on a passage notetype
  - the grader + a map-input UI. Feasibility **M**; the real cost is the human-authored
    gold maps.

### 6 — Next-Best-Action Router · ≈ 7.0 (Wave-1 ≈ 7.3, revised down)

The dashboard already computes ~7 uncorrelated insight panels but leaves the learner to
synthesize "what do I do next" (the SRL forethought step novices skip). Here the
**ranking stays 100% deterministic** (eligibility preconditions read from existing
panels + an expected-yield score = points-at-stake × that panel's own effect estimate);
the LLM only **tie-breaks within a tolerance band** and writes a rationale whose every
number is regex-verified against the computed panel value and every `item_id` verified
against the ledger (extending `misconception.py`'s digit-ban). Low risk, broad leverage,
cheap.

- _Faster:_ reallocates each session to the highest-expected-yield activity and
  collapses "decide what to do next" latency to seconds. Honestly bounded by Macnamara
  et al. — deliberate practice is a _minority_ of performance variance — so this is an
  _allocation_ aid ("same hour, higher-yield activity"), not a multiplier; advisory,
  overridable, abstains when evidence is thin. **Cold-start caveat:** like #2, this is
  data-hungry — the eligibility/yield signals need many logged events per skill before
  they are signal not noise, so #6 (and #2) contribute ≈0 speed for the very early-prep
  novice with no history (the same population #1 helps most). Abstention keeps it _honest_
  when thin; "faster" only accrues once the log fills.
- _Build:_ closed action menu + deterministic eligibility/yield + LLM tie-break/rationale
  - a grounding checker (number/item_id/banned-phrase). Reuse every dashboard panel + its
    abstain/CI gate. Feasibility **S–M**; no Rust/proto. _(Quick win: ship the deterministic
    ranking + templated rationale first — it needs no LLM and is the baseline the AI layer
    must beat.)_

---

## Quick wins (lowest effort, high value)

1. **Wire a real semantic embedder into `eval/leakage.py`'s `_semantic_sim` hook** (it
   returns `None` offline today). It is pluggable by design; this single change is the
   load-bearing gap that disqualifies _every_ "generate original content" feature on
   the copyright constraint — fixing it first unlocks the whole safe-generation category
   (RC especially). _(Design + validation in the roadmap section below.)_
2. **Ship the AI-OFF deterministic floors first** — the contrast card (#3/#4 fallback),
   the deterministic confusion-matrix router (#2), and a deterministic eligibility+yield
   ranking with a templated rationale (#6). Immediate value, zero AI risk, and a
   ready-made eval baseline the AI layer must beat.
3. **Add the eval arms before any UI** — `se` (#3) and `ge` (#4) arms in the existing
   equal-time `eval/feedback.py` are a few lines each and are a cheap go/no-go on whether
   the feature can clear the bar at all.
4. **Extend `lsat/ai/gold_set.py`** with small per-item explanation/diagnosis gold sets
   once — a shared asset serving #3 and #4's false-pass gates.

## What to avoid (and why)

- **Generating original RC passages (or LR items) while the leakage gate is lexical-only**
  — a reworded copyrighted passage passes every lexical signal undetected. Disqualified
  until the semantic embedder is wired _and_ validated with a planted-reworded-passage
  self-test.
- **Live "teach-the-confused-student" / open persona chat** — the one runtime surface
  emitting unbaked prose; "structurally cannot assert facts" is not guaranteeable for an
  LLM under adversarial input, and sycophancy (praising a wrong explanation) reinforces
  the confident-wrong error — the worst case here. Prefer static, checker-gated Socratic
  ladders if the family is wanted at all.
- **Compound cross-tab diagnosis / emergent error-clustering** on a single learner's
  sparse logs — statistically fragile (attribute diagnosis needs many items per
  attribute; clustering tens of misses in TF-IDF is noise-prone). Prefer #2's tractable
  2-way directional confusion.
- **Any feature that lets the LLM decide correctness or author corrective facts shown to
  the learner.** The disciplined inverse is the whole point.

---

## Deep-dives (Wave 2)

_(The four sections below are filled from the Wave-2 deep-dive agents: competitive
differentiation, adversarial red-team + residual-risk ranking, an honest quantification
of "how much faster," and the sequenced build roadmap + the semantic-embedder unlock.)_

### Competitive landscape & differentiation

**The market is a trust barbell.** (Sources: vendor pages + review sites, via
WebSearch; raw-LLM failure claims are well-documented.)

- _Trusted-but-AI-shy incumbents_ keep generative AI **away from question content**.
  **7Sage** — the closest competitor — ships a grounded **"AI Coach"** that explains
  using 7Sage's _own human-written explanations_ as the source and **refuses to
  analyze official LSAT items directly** (LSAC prohibits AI analysis of official
  content); its AI is positioned as a data-cruncher ("what should I study next?").
  **Blueprint** ("Smart Qbank" ML adaptivity + Smart Study Planner), **LSAT Lab**
  (adaptive plan + "AI Analytics Assistant"), **LSATMax/Kaplan/PR** (analytics +
  human tutoring, minimal generative AI). **AdeptLR** is the sharpest AI-native-_done-
  right_: adaptive drilling wrapped around **official** questions (not generated),
  advertising efficiency gains (vendor: "~486 vs ~1,053 questions to gain 3 points").
- _AI-forward-but-unverified entrants_ (GPT-wrapper tutors — Jenova, LSAT Genie, Law
  Tutor AI; generic "paste notes → deck" card generators) lead with "24/7 AI tutor"
  and inherit the raw-LLM failure profile.

**The documented raw-LLM failure modes** (why the unverified tier is dangerous):
**overconfident wrong answers** (a confident, detailed rationale for the _wrong_
choice), **sycophancy** (validating the student's wrong reasoning — the opposite of
the pushback LSAT prep needs), **flawed self-generated items** (ChatGPT produced
"Necessary Assumption" questions with _no_ uniquely-required answer, violating the
one-correct-answer standard), **stale content** (explaining the LSAT _with Logic
Games_, removed in 2024), and generic AI flashcard generators producing **~36%
unusable cards** that are _structurally plausible but wrong_ and survive a glance.
Note the context: GPT-4-class models can now often _solve_ LSAT items (~163/88th
percentile, and a 2026 paper claims a perfect score) — but **solving is not
teaching, verifying, or generating** them without hallucination.

**Two structural facts that bound the design:**

1. **The empty middle.** Almost nobody occupies _verified generative/transform AI
   over authoritative content_ — incumbents rely on **human** gold (strong, but not
   machine-verifiable and not held to a measured error bar); AI-native tools rely on
   the model's word. That middle is exactly this project's target.
2. **The LSAC content wall.** AI analysis of official LSAT content is prohibited (and
   generative AI is banned in the Writing section). So the "generate-and-prove" story
   must live on **our own checker-passed gold** and the **student's own performance
   data**, _not_ on LSAC's copyrighted items — which is also what makes it legally
   clean.

**Where this project is genuinely differentiated (nobody else credibly claims it):**

1. **Correctness gated by a _proof / deterministic check / checker-passed gold_,** not
   by human authority or model assertion — uniquely strong for the **formal-logic
   families where a true oracle exists** (the #1 feature). _Honest seam:_ open-ended
   RC / natural-language argument have **no** clean oracle, so there the guarantee
   degrades to _checker-passed gold + verbatim-span grounding_ — call it **tiered
   assurance** (proof for formal families; grounded-gold for the rest), never "proof"
   across the board.
2. **Runs fully with AI OFF** — the single cleanest answer to the market's #1 failure:
   the LLM can never inject hallucinated/sycophantic content into the _core_ loop,
   because turning it off leaves a complete deterministic product. Every Category-2/3
   tool _is_ the AI; turn it off and there's no product.
3. **Every AI claim behind a published equal-time eval CI** — a credibility moat where
   competitors publish only marketing multipliers ("52% faster") with no interval.
4. **Verbatim-span grounding** as the explanation primitive — a more checkable, less
   hallucination-prone _form_ of the explanations everyone ships (and it dovetails with
   the LSAC wall: point at spans of _our own_ gold, not paraphrase LSAC's).

**Table stakes (execute well; don't sell as the story):** question-type
classification, next-best-question ranking, weakness analytics, study planners, and
spaced repetition itself. The edge here is _measured reliability_, not the feature's
existence.

**Out-position the benchmark — 7Sage's AI Coach** (grounded, content-shy,
human-verified gold): the edge is **not** "we also ground" — it's "we **prove**, we
**measure**, and we work with the model **turned off**."

### Adversarial red-team & residual-risk ranking

A Wave-2 agent read the actual `lsat/ai/` code and stress-tested each feature on
six axes: sycophancy/false-pass, prompt injection, the LLM-entailment weak link,
latency/cost/offline, privacy, and gold-set burden. It also surfaced **two
cross-cutting weaknesses** that gate several features regardless of individual
design:

1. **The gold set can't certify a rare-event false-pass gate.**
   `checker_validation_cases()` builds one correct **and** one wrong card per gold
   item, so `validate_checker` divides false-passes by **50** wrong cards. The
   smallest observable non-zero rate is therefore **1/50 = 2%** — which is _exactly_
   `CHECKER_FALSE_PASS_MAX = 0.02`. So the gate's floor **equals** its ceiling: the
   only way to pass is to observe **zero** false-passes on 50 items, and the CI around
   "true rate ≤ 2%" from a single zero-count sample of n=50 is enormous (the rule-of-3
   upper bound alone is ~6%). Any feature gated on a _measured_ false-pass rate (3, 4,
   5, and the card checker itself) needs a far larger, **adversarially-constructed**
   set of confident-wrong exemplars per skill, with the gate expressed as an
   **upper CI bound**, not a "observed zero" point estimate. Today's gate would pass an
   unsafe feature simply because the test can't see the tail.
2. **Unverified "connective glue" is the real exposure.** The extractive/proven
   parts are sound; the danger lives in the _free natural-language framing_ stitched
   around them (a worked example's narration, a "why not B?" feature's ≤2 connective
   sentences). And the repo's own precedent for validating such glue is weak —
   `misconception.rephrase_with_ai` "checks" fidelity with a **substring** label-survival
   test that text which _negates_ the label satisfies trivially ("This is NOT about
   absolute wording…"). Lexical checks don't detect **semantic inversion**. Treat any
   "the LLM's prose survived a keyword check" claim as unproven.
3. **Provider model-version drift silently voids every gated-checker guarantee.**
   The entire trust story is "the checker cleared its gold-set false-pass gate" — but
   `ClaudeClient` pins the **moving alias** `claude-3-5-sonnet-latest`. A silent
   provider update changes the checker's behavior with **no code change, no re-gate,
   and no diff**, and the eval's reproducibility machinery (`RANDOM_SEED`, deterministic
   train/heldout split) covers everything _except_ the LLM. For an honesty-first design
   this is the largest unguarded surface. Fix: pin **dated snapshots** (never `-latest`),
   record the exact model id in every gate result, and **re-run the gold-set gates on
   any model bump** — a passed gate is only valid for the model id it was measured on.

| Rank | Feature                            | Residual risk                                                                                                                                                                                                                                                                                           | Ship posture                                                                                                                                                                                                                                                                                             |
| ---- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | **Oracle-verified faded examples** | **Lowest** — sound decision procedures _decide_; a wrong drafted step fails to verify and the example is withheld. Real failure mode is _over-abstention_ (thin yield), not false-pass.                                                                                                                 | **AI-on / pre-generated offline.** Guards: verify **inter-step entailment** (not just per-step truth — individually-true lines can still be a non-sequitur); render narration **from the proven structure via template**, not free prose.                                                                |
| 2    | **Next-best-action router**        | **Low** — deterministic expected-yield ranking; LLM only tie-breaks + narrates. A bad call is a suboptimal _action_, never a wrong grade.                                                                                                                                                               | **AI-on.** Guards: tight tie-break tolerance (log when LLM pick ≠ deterministic argmax); **closed rationale template**; require every digit in the rationale to be a verbatim panel value (inverse of the `\d`-ban — permit digits, but check set-membership).                                           |
| 3    | **Confusion-pair routing**         | **Low-moderate** — classifies onto a _closed_ set and routes to a drill that itself grades deterministically, so the correctness gate lives downstream. A misroute wastes time, never asserts a wrong truth.                                                                                            | **AI-on.** Guard: cap the measured misroute rate; the gate can be looser than a grading gate.                                                                                                                                                                                                            |
| 4    | **Verdict-locked "why not B?"**    | **Moderate** — verdict is _locked_ (input, not LLM decision) and spans are verbatim-checked, but the connective glue is unconstrained, and an **entailment judge shares the failure class of what it judges** (sycophantic to fluent glue; "entailed-ish" ≠ "correct trap rationale").                  | **Ship the extractive/templated-glue variant AI-on** — it's essentially the already-safe `contrast.py` card. The **runtime-entailment variant stays off** until that judge clears a _"true-spans / wrong-glue"_ adversarial set at a pre-declared catch rate. Prefer pre-generation to any runtime call. |
| 5    | **Self-explanation grading**       | **High** — the pass/fail judgment _is_ an LLM correctness decision over **adversarial learner free text** (injection + sycophancy coincide here), and a confident-wrong explanation waved through as "correct family" corrupts the confident+wrong signal the whole app is built on. High privacy cost. | **Ship AI-OFF as default** (ungraded self-explanation + deterministic gold reveal — the effect works _ungraded_). Grading only behind an **on-device** classifier clearing a **two-sided** (false-pass _and_ false-fail) gate on an adversarial set; must **abstain** on low confidence, not affirm.     |
| 6    | **Passage-Map Coach (RC)**         | **Highest** — open NL-vs-NL _semantic_ grading with **no decision procedure**; paraphrase-heavy recall is exactly what lexical-similarity graders false-pass; per-passage human gold that never amortizes; highest privacy cost.                                                                        | **Ship AI-OFF-only** (write map → reveal human gold map → self-score). Enable grading only once a grader clears a pre-declared false-pass gate on an adversarial per-passage set **and** gold-map authoring throughput is solved.                                                                        |

The ranking is sobering in a specific way: **safety and speed-defensibility are not the
same axis, and only one feature scores top on both.** The features that lean hardest on
a **deterministic oracle** (1, 2, 6) are the _safest_ — but of those, only **#1
(faded worked examples) is also speed-defensible** (a real effect size pointing the
right way on both magnitude and time). **#2 and #6 are safe-but-speed-uncertain
_allocation_ aids** — the quantification gives them no borrowable effect size; their
benefit is entirely how misallocated the baseline hour was, settled only by their
equal-time arms. The features that lean on an **LLM to judge free text** (3, 5) are
simultaneously the _riskiest_ and the ones whose per-hour benefit is _least certain_ —
risk and evidentiary weakness are correlated, which is why the honest default for 3 and
5 is **AI-off**, shipping the (genuinely useful) ungraded self-explanation / gold-reveal
path and letting the graded LLM layer earn its way in through the gates.

One equity caveat cuts across the two free-text graders (3 and 5): a classifier judging
learner prose is prone to **false-FAIL on non-native / ESL phrasing** — telling a student
their _correct_ diagnosis is wrong. On a language-heavy exam with a large ESL population
that is the confident-wrong harm inverted _onto the student_, so the two-sided gate for
3 and 5 must include an explicit **non-native-phrasing slice**, not just an adversarial
confident-wrong slice.

### How much faster, honestly (bounded estimates)

**Currency + ceiling.** Report effects as the literature does (Cohen's _d_ / Hedges'
_g_ on a learning/transfer outcome), translated only to _more learning per hour /
fewer reps to a transfer criterion / a better-allocated hour_ — never asserted scaled
points. Context for legibility: the exam is ~75–77 scored items (LR ≈ 2/3, RC ≈ 1/3;
LSAC 2024), and near the median **~1 extra correct item ≈ ~1 scaled point** (PowerScore/
Kaplan curves). So converting a _whole feature_ into even 3–5 scaled points means
reliably winning 3–5 more items on test day, after transfer decay, when each feature
touches only a _slice_ of ~76 items — hence the committed **single-digit ceiling**.

**Five deflators apply to every feature:** equal-study-time accounting (most cited
effects didn't hold minutes constant; several features cost extra seconds/item →
per-item ≠ per-hour); expertise reversal (guidance helps novices, can _harm_ the
advanced — Kalyuga et al. 2003); near→far transfer decay; simulation-until-real-
students (every number below is a _borrowed prior_ from other domains/populations —
**none is measured on LSAT-takers**); and individual variance.

| Feature                          | Cited effect (source)                                                                                                                                                          | Honest per-hour read                                                                                                                                                                                                               |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 Faded worked examples**      | worked-example **g≈0.48** (Barbieri 2023, 55 math studies); backward-fading + self-explanation → near **and** far transfer _"without additional time on task"_ (Atkinson 2003) | **Strongest case.** The one feature the literature supports on _both_ effect size _and_ time-efficiency — but concentrated in **novices** on formal-logic LR; expertise reversal caps duration. Low-single-digit, novice-weighted. |
| **2 Confusion-pair routing**     | **no clean d** — contrasting-cases / targeted-practice logic only                                                                                                              | **Allocation gain**, ceiling = how misallocated the baseline hour is. Fraction of a point typically; _entirely eval-dependent_ (no borrowable number).                                                                             |
| **3 Self-explanation grading**   | **g=0.55** (Bisra 2018, 69 effects) — largest raw effect                                                                                                                       | **But the most time-expensive** → per-_item_ strong, per-_hour_ uncertain and possibly modest. The make-or-break equal-time claim on the list.                                                                                     |
| **4 Span-grounded "why not B?"** | EF **d≈0.49** vs KCR **d≈0.32** → **+0.17** increment (Van der Kleij 2015)                                                                                                     | **This is EF-over-EF** (span vs generic explanation), so the true increment is _below_ 0.17 and **may be undetectable**. Honest value is **fidelity/trust** (no hallucinated rationale), not speed.                                |
| **5 RC passage-map**             | text-structure instruction **g≈0.56** (Hebert 2016, K-12 expository)                                                                                                           | Sharp **transfer risk** (K-12 expository → adult adversarial RC), shrinks vs strong comparisons (Bogaerds-Hazenberg 2021), and **1/3 dilution**. Moderate-at-best, transfer-limited.                                               |
| **6 Next-best-action router**    | bounded by deliberate-practice variance: **~4–7% in education** (Macnamara 2014)                                                                                               | **Allocation aid, not a multiplier** — can't route past the (small, in education) share practice-quality explains. Small; eval-dependent.                                                                                          |

**Synthesis.** The clearest, most-defensible "faster" win is **Feature 1 for genuine
novices on formal-logic LR** — the only one where the evidence points the right way on
_both_ magnitude and time-efficiency, and it targets the two-thirds LR share.
**Feature 3** has the biggest raw effect but its per-hour value is genuinely uncertain
(time cost). **Feature 5** has a good proximal prior but the sharpest transfer risk.
**Features 2 and 6 are allocation gains** with no borrowable effect size — quantitatively
_entirely_ eval-dependent. **Feature 4 is the smallest** (EF-over-EF, possibly
zero-distinguishable); its worth is trust, not speed. The bottom line a skeptic accepts:
a **single-digit scaled-point aggregate ceiling** for a marginal diligent student,
front-loaded onto novices; every magnitude is a _borrowed prior_, and the honest posture
is a bounded prior + waiting for the equal-time bootstrap CI — which is exactly the
posture the project's `eval/feedback.py` harness enforces.

**Faster _for whom, at what price_.** Two economics shape who actually gets the gain.
(1) **Cold-start:** #2/#6's allocation gains are ≈0 until enough events accrue, so the
earliest-prep novice — who benefits most from #1 — gets nothing from the routers yet.
(2) **Unit cost:** the oracle-verified features (#1) pre-generate **offline** (zero
per-review cost, AI-off at review time), but the free-text graders (#3, #5) imply a
**per-call cost on live learner text** that can't be pre-computed — which is a second
reason (beyond risk) their default is AI-off / on-device, and a real input to "faster
_at what price_" at scale.

### Build roadmap & the load-bearing unlock (semantic leakage gate)

A Wave-2 agent traced the shippability of each feature to the actual eval gates and
found one **load-bearing gap** plus a clean sequencing that reuses what already exists.

**The load-bearing unlock — the semantic-leakage gate.** `eval/leakage.py` is a _hard_
build gate (exits non-zero) that scans every generated item against the corpus with
four signals — normalized substring, TF-IDF cosine, char-4-gram Jaccard, and a
`_semantic_sim` hook. **The fourth signal is dead: `_semantic_sim` returns `None`
unconditionally.** So the copyright/originality gate is **lexical-only**, while
PRD §12.2 explicitly promised an _embedding-cosine_ threshold "to catch reworded
duplicates — a real risk on the LSAT." A pretrained model can emit a synonym-swapped,
clause-reordered paraphrase that shares _no stems_ ("lowering prices increases revenue"
vs "cutting costs boosts earnings") — it passes all three lexical signals and the build
stays green.

Why this matters unevenly: the generator already drops any card whose `source_quote`
isn't a **verbatim substring** of the supplied chunk, so **card-level features (#1–#4)**
cite short spans and have a small copyright surface. **RC passage generation (#5) is the
exception** — it emits multi-sentence _original prose_, and the only thing between the
model and a laundered LSAC passage is this gate. So the dead semantic signal is precisely
what **disqualifies generating original RC prose** today, and fixing it is the single
unlock for #5.

The honest fix (and its real tension): the project has **zero ML dependencies** and the
eval harness is pure-stdlib, deterministic, network-free. So "import sentence-transformers"
isn't a one-liner — it drops a heavyweight runtime + an 80–400 MB model into a reproducible
CI gate. It resolves more cleanly than it looks because **leakage runs at build/ingest
time, not review time** — the shipped wheel and on-device serving are untouched; students
never run the embedder. The design: a small MiniLM-class encoder via onnxruntime-CPU,
**vendored as a hash-pinned asset** (never a live API call), behind an optional
`eval-semantic` dependency group; the core wheel stays pure-Python. The one
non-negotiable: when RC-gen is enabled but the embedder is absent, the gate must
**fail loud**, not silently `return None` and fall back to lexical — today's silent
fallback _is_ the bug. Do **not** reuse the existing `TfidfEmbedding` (that just
re-implements signal 2 — it can't see disjoint-token paraphrases). Give it a
**separately calibrated `LEAK_SEMANTIC_MAX`** (MiniLM cosine distributes completely
differently from TF-IDF), pre-declared before looking at results, calibrated on a
three-stratum set where the **hard negatives are the crux**: same-skill same-type but
_different content_ items must **not** flag (else every causal-flaw card reads as a
"copy" of every other). Extend `detector_self_test` with a semantic-only planted case
caught with `reason=="semantic"` (mirroring how the reword case must be caught by
`fuzzy_shingle`) — that's the trust anchor.

**The three-layer contract the roadmap just applies feature-by-feature** (already the
house style): **L1** an AI-off deterministic floor that fails closed; **L2** an eval arm
at _equal study time_ that ships iff its bootstrap CI excludes 0; **L3** an LLM that may
only _beat or rephrase_ the floor, behind a gold-set false-pass gate, degrading to L1 on
`LLMUnavailable`. The sequence:

- **Phase 0 — shared foundations (unblock everything).**
  **P0a:** extend `lsat/ai/gold_set.py` _once_ with `explanation_gold`,
  `wrong_explanations`, `confusion_pair`, `distractor_gold` + `explanation_grading_cases()`
  / `diagnosis_cases()` — the shared asset #2/#3/#4 all consume. **P0b:** the
  semantic-leakage unlock above (`eval/leakage.py`, `eval/config.py`, new
  `lsat/embedding.py`, optional dep group) — gates _only_ #5, so start it early and in
  parallel.
- **Phase 1 — AI-off floors (the baselines each AI feature must beat).** Most exist.
  New: `confusion_pairs.py` (#2 — fold events into a skill×skill matrix, route to the
  matching drill via the existing points-at-stake queue boost), `next_action.py` (#6 —
  rank actions from signals already in `dashboard_data._insights`), `worked_example.py`
  (#1 — faded steps _derived and checked by the `quantifier`/`conditional`/`conditional_chain`
  oracles_, exactly like `assumption_discrimination.py`). #3/#4's floor is already built:
  `contrast.build_contrast` (AI-off, gold-gated, abstains).
- **Phase 2 — eval arms, before any UI.** Each mirrors `eval/feedback.py` (paired synthetic
  learners, `bootstrap_ci`, `ship = lo > 0`). The pivotal one: **add `se`/`ge` arms to
  `eval/feedback.py`** — self-explanation costs more seconds/item so it does _fewer_ items.
  **Honest limit of the sim:** `eval/feedback.py`'s own `GAIN`/`COST` are _assumed_
  parameters (its docstring admits they're set so EF wins), so the synthetic arm can
  **falsify a methodology and kill an obvious loser, but it cannot _certify_ a feature
  ships** — that still needs real learners. Use it as a cheap go/no-go gate on obvious
  failure, not as proof of benefit. Plus `eval/worked_example.py` (#1) and
  `eval/confusion_routing.py` (#2).
- **Phase 3 — the LLM layer, each behind its own false-pass gate.** Only features whose
  Phase-2 arm said "go" proceed. `explanation_grader.py` (#3, two-sided gate),
  `span_tutor.py` (#4, verdict _locked_ to the deterministic answer, fail-closed like the
  checker), optional #1 hint-prose rephrase (step grading stays oracle-only), and
  **`rc_passage.py` (#5) LAST** — the only feature needing _both_ the P0b semantic unlock
  _and_ a net-new human asset (per-passage gold maps), plus its own correctness checker.

**Topological order:** P0a → the `se`/`ge` arms + #3/#4 validators; P0b (parallel) → #5;
#2 floor → #6 floor; #1 oracles already exist → #1 arm → optional #1 prose; the Phase-2
arms are the literal go/no-go for the Phase-3 features they precede. The reassuring finding:
most of the deterministic floors (#1 oracles, #3/#4 `contrast.py`, #2/#6 fold + queue
primitives) **already exist** — the net-new work is the gold-set fields, the embedder, three
floor modules, the eval arms, and three gated LLM modules, in that dependency order.
