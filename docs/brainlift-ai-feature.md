# BrainLift — The Oracle-Gated AI Layer (Anki for LSAT)

> This BrainLift frames the software's AI feature — the **oracle-gated AI layer**
> (verified worked examples, "skill or luck?" evil twins, the generator +
> independent checker, and grounded misconception hypotheses) — as the deliberate
> result of a Spiky Point of View, and justifies that stance from learning science
> and formal methods. It is written to double as **structured context for AI
> conversations**: paste it in and a model has the curated reasoning behind the
> feature. A companion document, [`brainlift.md`](brainlift.md), covers the
> non-AI diagnostics and scoring.

## Owners

- [Your Name]
- [Name 2]

## Purpose

### Purpose

The purpose of this BrainLift is to explain why the AI in a **career-deciding**
exam-prep tool must be held to a standard the rest of the category does not
accept: **it must be architecturally incapable of teaching a falsehood.** It is
built on the belief that on a high-stakes exam a confidently-wrong AI is not a
convenience with an acceptable error rate — it is a *net-negative* that installs
the exact high-confidence misconceptions the product exists to remove. The
defensible response is to demote the language model to **logically-inert labor**
(drafting an ordering, selecting among options, choosing surface words) behind a
**decision procedure** — or, where no decision procedure exists, an independent,
pre-validated **gate** — that alone owns correctness. In one line: *the AI
proposes, the oracle disposes.*

### In Scope

- The **generate-and-verify** architecture: how an LLM's proposal is re-derived by
  a decision procedure, or judged by an independent checker, before a learner ever
  sees it — and how it fails closed to a deterministic path.
- The **learning-science case** for "a wrong card is worse than no card" (errors as
  signal, confidence, hypercorrection, erroneous-example and contrasting-case
  pedagogy).
- The **formal-methods case** for why verification can be cheaper and more
  trustworthy than generation, and the **decidability boundary** that says where an
  oracle is even possible.
- The **honesty machinery** that makes the claim credible: tiered assurance,
  abstention, a pinned/auditable model, and graceful degradation ("runs with AI
  off").
- Producing this as **direct, structured context** an AI model can consume to
  reason about the feature.

### Out of Scope

- Trusting raw LLM generation as correct, or using AI to *synthesize* the answer
  key. The model never decides what is true.
- A blanket **"provably correct AI"** claim over open natural-language Reading
  Comprehension — we deliberately do not, and cannot honestly, make it.
- Building a **RAG / retrieval** pipeline; this document is direct context, not a
  database for retrieval.
- The **non-AI** diagnostics and scoring — the Blind-Review Delta, the three honest
  scores, the Rust points-at-stake queue — which are argued in
  [`brainlift.md`](brainlift.md).
- Proposed-but-unshipped perceptual-learning / fluency features (see
  [`research/R1-perceptual-learning.md`](research/R1-perceptual-learning.md)); this
  BrainLift is about the AI layer as built.

## DOK 4: Spiky Points of View (SPOVs)

### Spiky POV 1 — On a career-deciding exam, an AI that can be confidently wrong is worse than no AI; therefore correctness must never be the model's job.

**Elaboration.** The industry default treats an LLM tutor as acceptable if its
hallucination rate is "low enough." That calculus quietly fails on the LSAT. A
plausible-but-wrong worked example does not merely waste one review — it teaches a
*false rule*, and it teaches it most efficiently to the strongest students, who
encode it with high confidence. Learning science makes the cost precise: high-
confidence errors are the hardest to remove; they persist and even *return* after
a delay (the hypercorrection literature). So an AI that manufactures a confident
error is doing the single most damaging thing an exam tutor can do. The resolution
has to be **architectural, not statistical**: split the labor so the model only
does *logically inert* work — proposing a step ordering the oracle must bless,
selecting which already-proven item to show, picking fresh surface nouns,
rephrasing already-proven prose — and hand every correctness decision to a
decision procedure that *enumerates and proves* it. A hallucinated step cannot
reach the screen, because it fails entailment and the whole example is withheld.
This is spiky because it contradicts the prevailing "the model is the product"
assumption: here the model is the *least* trusted component.

**How it informs our product decisions.** This is the literal architecture of
[`../lsat/worked_example.py`](../lsat/worked_example.py) and
[`../lsat/evil_twin.py`](../lsat/evil_twin.py). `draft_and_verify()` asks the LLM
for an ordered derivation, then runs `verify_worked_example()`, which re-derives
each step with `entails()` from
[`../lsat/conditional_chain.py`](../lsat/conditional_chain.py) and blocks the whole
draft on any failure — degrading to the deterministic, oracle-derived
`build_worked_example()`. Evil twins invert the same split: the oracle *enumerates*
every minimal single-edit variant and keeps only those whose proven verdict
**flips**, so a mislabeled twin can never be served; the LLM merely picks which
proven twin best targets a misconception and supplies nouns that never enter the
model-checker. The **Oracle Proof Theater** (`theater_scenarios()`, surfaced in
[`../ts/lib/lsat/OracleProofTheater.svelte`](../ts/lib/lsat/OracleProofTheater.svelte))
makes the stance watchable: a recorded (or live) AI draft is checked step by step,
the planted hallucination is vetoed with the oracle's own reason and a
counterexample world, and the oracle substitutes the continuation it can prove.
Nothing is baked — every verdict is recomputed at call time by the same predicate
the self-tests use, which plant forged, truncated, and garbage derivations and
assert a false-pass rate of **0**.

### Spiky POV 2 — When AI makes content free, the product is the verifier, not the generator.

**Elaboration.** Anyone can prompt a model to spin up an LSAT app in an afternoon;
what it ships is *confidently wrong*. If generation is now a commodity, then the
scarce, hard-to-copy artifact is the **verification infrastructure** — and
specifically a checker you have *earned the right to trust*. Ask an LLM to build a
card-checker and it will happily hand you one that returns `PASS`; a gate you have
not validated is not a gate. The consequences are concrete: the checker must be
**independent** (its own rubric, never shown the generator's rationale, ideally a
different/stronger model), and it must be **measured for its false-pass rate**
against a gold set of known-correct/known-wrong items *before* it is trusted, with
the admission cutoff **fixed in code before anyone looks at results**. Because a
wrong card is worse than no card, that cutoff is strict — admit only
`CORRECT_USEFUL`, block everything else. This inverts the usual framing ("AI =
generation"): the model that writes content is replaceable; the validated gate is
the moat.

**How it informs our product decisions.**
[`../lsat/ai/checker.py`](../lsat/ai/checker.py) runs as a *separate* call,
re-derives the verdict from the card plus its cited source span, and **fails
closed** — any unparseable or malformed judge output becomes `WRONG`, never a crash
that could block the review loop. `validate_checker()` computes false-pass,
false-block, and agreement against labelled gold cases, and
[`ai-card-pipeline.md`](ai-card-pipeline.md) pins the `verdict == CORRECT_USEFUL`
cutoff and the "before students see anything" staging gate. Independence is
enforced mechanically: `Card.checker_json()` in
[`../lsat/ai/generator.py`](../lsat/ai/generator.py) deliberately **omits the
generator's `explanation`** so the judge cannot defer to it. And defense-in-depth
sits *below* the LLM judge: the generator programmatically checks that each
`source_quote` is a **verbatim substring** of the chunk it was sent (fabricated or
injection-smuggled citations are dropped) and that every tag is in the taxonomy we
supplied. The reported eval numbers — e.g. `worked_example`: 0 false-passes over
planted + 3,014 fuzz derivations; `evil_twin`: 47 curated twins + 3,500+ fuzz
flips with 0 mislabels cross-checked against an *independent* oracle — are the
deliverable, precisely because the checker, not the generator, is the product (see
[`Speedrun_AI_Features.md`](Speedrun_AI_Features.md)).

### Spiky POV 3 — Trust is earned by admitting where you can't verify; tiered assurance plus abstention beats a blanket "provably correct AI" claim.

**Elaboration.** The tempting pitch is "our AI is always right." It is both false
and — to a skeptical retaker hunting a 170 — *less* persuasive than a product that
visibly refuses to overclaim. So correctness is **proven** only in the decidable
slice where a decision procedure exists (formal-logic LR: conditionals,
quantifiers, chains); everywhere else the AI is held to **grounded-gold plus
verbatim citation**; and where neither is possible, the product **abstains and says
so**. Trust is the *enabling condition*, never the pitch. Two corollaries follow.
First, the model itself must be **pinned and auditable** — any statistical
guarantee about an LLM surface is valid only for the exact model it was measured
on, so a silent provider bump would void the guarantee invisibly. Second, AI must
be **additive, never load-bearing**: the whole product, including every score and
the review loop, must work with the model off.

**How it informs our product decisions.**
[`../lsat/ai/client.py`](../lsat/ai/client.py) pins a concrete `DEFAULT_MODEL`
(never a `-latest` moving alias), records the API-resolved model id on every call
(`model_used`), and publishes a `nutrition_label()` stating the standing "re-gate
on any model bump" rule and which surfaces are model-*independent*. Grounded
misconception hypotheses ([`../lsat/ai/misconception.py`](../lsat/ai/misconception.py))
may only map to a **documented taxonomy label** (the `skill.trap.*` / `flaw.*`
catalog, our encoding of the PowerScore/7Sage error families), gated by
`validate_hypotheses()` (pass rate ≥ 0.9) *before* anything renders; the LLM may
only *rephrase* a catalog entry, and the rephrase is fail-closed (label must
survive, no new content/numbers). Every surface degrades on `LLMUnavailable` to a
deterministic path — the rule-based `OfflineClient`, the deterministic worked
example, the catalog text — so scores and the review loop never block on the model.
And the proof boundary is drawn honestly at **decidability**: we make no "provably
correct" claim over open RC, and the docs say so out loud
([`Speedrun_AI_Features.md`](Speedrun_AI_Features.md), "tiered assurance").

## Experts

- **Expert 1 — Janet Metcalfe**
  - **Who:** Professor of Psychology, Columbia University; leading researcher on
    metacognition and learning from errors.
  - **Focus:** The **hypercorrection effect** — errors made with *high* confidence
    are corrected best after feedback, yet also tend to *return* over a delay unless
    re-tested.
  - **Why Follow:** Her work is the empirical backbone of SPOV 1. It is why a
    confidently-wrong AI output is *maximally* damaging (it installs the hardest-to-
    remove kind of error) and must be prevented by construction, not merely made
    rare.
  - **Where:** <https://www.columbia.edu/cu/psychology/metcalfe/>

- **Expert 2 — Daniel T. Willingham**
  - **Who:** Professor of Psychology, University of Virginia; author of *Why Don't
    Students Like School?*.
  - **Focus:** Cognitive science of education; the argument that "critical thinking"
    is bound to **domain knowledge**, not a free-floating general skill.
  - **Why Follow:** Justifies treating LSAT reasoning as a *domain* with a fixed,
    encodable taxonomy — which is exactly what makes a decision procedure (an oracle)
    possible for the formal-logic slice, and what the grounded-gold tier rests on.
  - **Where:** <http://www.danielwillingham.com/>

- **Expert 3 — John Sweller**
  - **Who:** Emeritus Professor, UNSW Sydney; originator of **Cognitive Load
    Theory**.
  - **Focus:** Working-memory limits; the **worked-example effect** (studying
    worked steps can beat unguided problem-solving for novices).
  - **Why Follow:** Grounds the *faded* worked-example design and explains why a
    *correct* worked example is high-leverage — and, by the same token, why a wrong
    one is uniquely costly.
  - **Where:** Sweller (1988), *Cognitive Science* —
    <https://doi.org/10.1207/s15516709cog1202_4>

- **Expert 4 — Robert A. Bjork & Elizabeth L. Bjork**
  - **Who:** Distinguished Professors of Psychology, UCLA (Bjork Learning and
    Forgetting Lab).
  - **Focus:** **Desirable difficulties**, retrieval practice, and the *fluency
    illusion* (conditions that feel easy often teach worse).
  - **Why Follow:** The "harder-but-honest" stance — make the learner discriminate,
    surface errors, don't smooth them over — descends directly from this work, which
    also warns that learners will *mis-rate* the most effective drills.
  - **Where:** <https://bjorklab.psych.ucla.edu/>

- **Expert 5 — Henry L. Roediger III & Jeffrey D. Karpicke**
  - **Who:** Memory researchers (Washington University in St. Louis; Purdue).
  - **Focus:** The **testing effect** / retrieval-based learning — retrieval
    strengthens memory, and *feedback* amplifies it.
  - **Why Follow:** The entire graded-retrieval loop the AI feeds sits on this base;
    it also frames *feedback quality* (correct, trap-level) as a first-class design
    variable — which is the thing the checker protects.
  - **Where:** Roediger & Karpicke (2006), *Psychological Science* —
    <https://doi.org/10.1111/j.1467-9280.2006.01693.x>

- **Expert 6 — Edmund M. Clarke**
  - **Who:** The late computer scientist (Carnegie Mellon); 2007 ACM Turing Award
    for **model checking**.
  - **Focus:** Automated **verification** — deciding whether a system meets a formal
    specification by exhaustive exploration of its states.
  - **Why Follow:** The intellectual license for "the oracle disposes." A bounded
    model-checker over truth tables is exactly what `entails()`/`classify()` are;
    model checking is the discipline of trusting a *decision procedure* over
    intuition or a confident narrator.
  - **Where:** ACM Turing Award profile —
    <https://amturing.acm.org/award_winners/clarke_1167964.cfm>

- **Expert 7 — Hunter Lightman et al. (OpenAI)**
  - **Who:** Authors of *Let's Verify Step by Step* (2023).
  - **Focus:** **Process supervision** — verifying/rewarding each *reasoning step*,
    not just the final answer.
  - **Why Follow:** The closest published analogue to per-step oracle verification
    of a derivation, and evidence for the generator/verifier separation at the heart
    of the feature (verify the steps, not just the conclusion).
  - **Where:** <https://arxiv.org/abs/2305.20050>

- **Expert 8 — Lianmin Zheng et al.**
  - **Who:** Authors of *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*
    (2023).
  - **Focus:** Using a strong LLM as an evaluator — and the **biases and limits** of
    doing so.
  - **Why Follow:** Names both the promise and the peril of the LLM-judge pattern,
    which is precisely why our checker is *independent* **and** *validated on a gold
    set for false-pass* before it is trusted as a gate (SPOV 2).
  - **Where:** <https://arxiv.org/abs/2306.05685>

- **Expert 9 — J.Y. Ping / 7Sage**
  - **Who:** LSAT instructor; popularized the **blind review** method.
  - **Focus:** Blind review and the **"Confidence Error"** — a miss on a question you
    felt sure about, "the most dangerous case."
  - **Why Follow:** The practitioner vocabulary that maps one-to-one onto the
    confidence/misconception states the AI hypotheses annotate — converging practical
    wisdom the feature automates rather than invents.
  - **Where:** <https://7sage.com/blog/the-blind-review-how-to-correctly-prep-for-lsat-part-2>

- **Expert 10 — David M. Killoran / PowerScore**
  - **Who:** Author of the PowerScore *LSAT Logical Reasoning Bible*.
  - **Focus:** The LR **question-type taxonomy** and the catalog of engineered
    **wrong-answer families** (Shell Game, Exaggerated, Opposite, Reverse, …).
  - **Why Follow:** The documented taxonomy the generator tags against, the checker
    judges against, and the misconception labels trace back to — the human-authored
    ground the "grounded-gold" tier stands on.
  - **Where:** <https://blog.powerscore.com/lsat/>

## DOK 3: Insights

- **Insight 1 — The verifier–generator asymmetry becomes a guarantee only where the
  logic is decidable.** In complexity terms, *checking* a candidate solution is
  routinely cheaper and more reliable than *producing* one. The LSAT's formal-logic
  slice is **decidable** (conditional entailment is a bounded truth-table / graph-
  reachability check; quantifier validity is a small finite-model check), so the
  checker can be made *total and provably sound* while the generator stays fallible.
  That is the exact condition under which "let the unreliable model propose and the
  reliable oracle dispose" stops being a slogan and becomes a theorem-shaped
  guarantee — and it is *why* the feature invests engineering in `entails()` /
  `classify()` rather than in a better prompt.

- **Insight 2 — A wrong AI card manufactures the single worst kind of error.** The
  product's own Thesis 2 says the misses worth deep review are the *confident* ones,
  because hypercorrection shows high-confidence errors persist and return. Read
  forward, the same evidence indicts AI generation: a plausible-but-wrong worked
  example does not just waste a review, it *installs* a high-confidence misconception
  in exactly the students most able to encode it firmly. So the learning science that
  motivates the confidence engine independently *forbids* trusting AI output —
  "a wrong card is worse than no card" is a corollary of hypercorrection, not a
  marketing line.

- **Insight 3 — Erroneous-example pedagogy is only safe when "wrong" is provably
  wrong on one axis.** Contrasting-cases and erroneous-example research shows that
  pairing a correct case with a *wrong* one and asking the learner to find the
  difference produces strong transfer — but *only* if the wrong case is wrong on
  exactly one, correctly-labeled dimension. A mislabeled near-miss teaches the
  opposite lesson. The evil-twin oracle is what makes this pedagogy deployable at
  machine scale: it enumerates minimal single-edits and keeps only proven verdict-
  flips, so the "instructive wrong answer" is *guaranteed* wrong-on-one-axis. The
  LLM's contribution (targeting the learner's misconception, freshening the nouns) is
  precisely the part that is pedagogically useful yet logically inert.

- **Insight 4 — Once content is free, the moat moves from the prompt to the
  validated gate.** A competitor can copy any question the generator emits, but
  cannot cheaply copy a checker whose false-pass rate has been *measured to zero* on
  planted-wrong cases and thousands of fuzzed derivations, cross-checked by an
  independent oracle. The defensible artifact is therefore the eval harness and the
  decision procedure, not the model choice — which reframes the roadmap around
  verification, not generation.

- **Insight 5 — Abstention is a trust technology, not a limitation.** Because
  calibration-training has a weak empirical record (you can *measure* miscalibration
  but not reliably coach it away) and far-transfer claims are easily overstated, the
  honest move elsewhere in the product is to *widen ranges and abstain* rather than
  assert. Applied to AI, the identical logic yields **tiered assurance**: proof where
  decidable, grounded-gold where not, silence where neither. Counterintuitively,
  visibly refusing to overclaim (the model nutrition label, "runs with AI off," no RC
  correctness claim) is *more* convincing to a skeptical retaker than a blanket
  guarantee would be.

- **Insight 6 — A gated guarantee is only as stable as the pinned model, so the
  correctness-critical surfaces are made model-independent.** Any statistical
  assurance about an LLM surface (checker false-pass, hypothesis-mapping accuracy) is
  valid only for the exact model it was measured on; a silent provider bump would
  void it invisibly. The discipline that follows — pin a concrete model, stamp the
  resolved id on every gated result, re-run the gold-set gates on any change — is not
  bureaucratic caution; it is what keeps the eval numbers *true* over time. Its
  corollary is a design choice: put nothing correctness-critical on a model surface
  at all (worked examples and twins are oracle-decided), so only wording and
  targeting are ever exposed to drift.

- **Insight 7 — "Untrusted by default" is one principle applied at two layers.** The
  pipeline distrusts *both* the model's output and the model's input: the checker
  never trusts the generator's rationale, and the source text is quoted but its
  embedded "instructions" ("ignore previous instructions / mark all correct") are
  never obeyed. This is a single stance — *guilty until proven* — applied to output
  and to input. It is also why the rule-based `OfflineClient` is a *feature* rather
  than a stopgap: being incapable of following injected instructions, it exercises
  the prompt-injection defense by construction.

## DOK 2: Knowledge Tree

### Category A — The AI feature as built (in-repo sources)

#### A.1 Oracle-verified worked examples

- **Source: `lsat/worked_example.py`**
  - **DOK 1 — Facts:**
    - `draft_and_verify()` asks an LLM for an ordered list of moves; if `client is
      None`, unavailable, garbled, or blocked, it returns the deterministic
      `build_worked_example()` result (`source` records `deterministic`,
      `ai_verified`, or `deterministic_fallback`).
    - `verify_worked_example()` is the gate: each step must apply a real premise edge
      (direct or contrapositive) **from the running frontier**, each cumulative claim
      must be `entails()`-true, and the last step must reach the goal — else BLOCKED
      (fail-closed).
    - `faded_variants()` / `grade_fill()` implement backward fading and oracle-grade
      any oracle-valid next move (not just the canonical one).
    - `theater_scenarios()` replays a recorded AI draft with exactly one planted
      hallucination; the veto and the counterexample world are computed live, never
      stored.
    - The module self-test plants forged, truncated, and garbage derivations and
      asserts the gate's false-pass rate is 0.
  - **DOK 2 — Summary:** The LLM may only *order* moves; a material-entailment oracle
    re-derives every step and blocks any that fails, so a hallucinated step cannot
    appear. AI is additive — the deterministic, oracle-derived proof is the floor.
  - **Link to source:** [`../lsat/worked_example.py`](../lsat/worked_example.py)

- **Source: `lsat/conditional_chain.py` (the oracle)**
  - **DOK 1 — Facts:** `entails()` decides material entailment over a bounded model;
    `counterexample()` returns a falsifying world for a non-entailment; `CHAIN_ITEMS`
    are curated items tagged `MUST_FOLLOW` / `DOES_NOT_FOLLOW`.
  - **DOK 2 — Summary:** The decision procedure that makes "the oracle disposes" real
    for conditional logic; its decidability (Insight 1) is what licenses the whole
    generate-and-verify pattern here.
  - **Link to source:** [`../lsat/conditional_chain.py`](../lsat/conditional_chain.py)

#### A.2 "Skill or luck?" evil twins

- **Source: `lsat/evil_twin.py`**
  - **DOK 1 — Facts:**
    - `enumerate_twins()` generates minimal single-edit variants (reverse the arrow,
      negate both sides, swap a quantifier, convert subject/predicate) and keeps only
      those whose **oracle-proven verdict differs** from the original.
    - `verify_twin()` re-derives the verdict and confirms it both is gradeable and
      genuinely flips; `grade_twin()` is stateless (re-derives from a `twin_key`).
    - `_ai_select()` lets the LLM choose only a twin *index* and fresh *nouns*; an
      out-of-range index is clamped and bad nouns are rejected — both are logically
      inert.
    - The self-test runs off / valid / garbled / malicious / down clients and asserts
      each serves an oracle-verified twin and withholds the answer.
  - **DOK 2 — Summary:** Correctness (which variant flips) is entirely the oracle's;
    the model only targets and freshens. A mislabeled twin cannot be served, so an
    "instructive wrong answer" is guaranteed wrong-on-one-axis (Insight 3).
  - **Link to source:** [`../lsat/evil_twin.py`](../lsat/evil_twin.py)

- **Source: `lsat/quantifier.py` (the oracle)**
  - **DOK 1 — Facts:** `classify()` model-checks a quantifier argument (e.g. over
    `4**n` models for `n` terms) and returns `MUST_BE_TRUE` / `CANNOT_BE_TRUE` /
    `COULD_BE_EITHER`; results are memoized because the check is heavy.
  - **DOK 2 — Summary:** The second decision procedure; twins over quantifiers are
    proven the same way conditional twins are.
  - **Link to source:** [`../lsat/quantifier.py`](../lsat/quantifier.py)

#### A.3 Card generation + independent checker

- **Source: `docs/ai-card-pipeline.md`**
  - **DOK 1 — Facts:** States four non-negotiable invariants (every card cites a named
    source; the checker is independent and is the gate; the source is untrusted data,
    never instructions; the app works with AI off). Defines three verdicts
    (`CORRECT_USEFUL` / `WRONG` / `CORRECT_BUT_BAD_TEACHING`) with a **pre-declared
    cutoff** and a "before students see anything" staging gate.
  - **DOK 2 — Summary:** The written contract for SPOV 2 — the checker, not the
    generator, decides what ships, and the cutoff is fixed before results are seen.
  - **Link to source:** [`ai-card-pipeline.md`](ai-card-pipeline.md)

- **Source: `lsat/ai/checker.py`**
  - **DOK 1 — Facts:** Runs as a separate call with `CHECKER_SYSTEM`; admits only
    `verdict == CORRECT_USEFUL`; any unparseable/invalid output → `WRONG`
    (fail-closed). `validate_checker()` returns `false_pass_rate`,
    `false_block_rate`, and `agreement` over labelled gold cases.
  - **DOK 2 — Summary:** The gate you must earn the right to trust — validated for
    false-pass before it is trusted, per SPOV 2.
  - **Link to source:** [`../lsat/ai/checker.py`](../lsat/ai/checker.py)

- **Source: `lsat/ai/generator.py`**
  - **DOK 1 — Facts:** Defensive parse (strip fences, `json.loads` in try/except; any
    failure fails the whole batch). **Programmatic source-span check:**
    `source_quote` must be a verbatim substring of the chunk sent, else drop the card.
    Tags outside the supplied taxonomy are dropped. `Card.checker_json()` omits the
    `explanation` so the judge cannot defer to the generator.
  - **DOK 2 — Summary:** Defense-in-depth *below* the LLM judge; catches fabricated
    citations and prompt-injection-smuggled sources deterministically.
  - **Link to source:** [`../lsat/ai/generator.py`](../lsat/ai/generator.py)

#### A.4 Client discipline

- **Source: `lsat/ai/client.py`**
  - **DOK 1 — Facts:** `LLMClient` is a `Protocol`; `OfflineClient` is a purely rule-
    based stand-in that *cannot* follow embedded instructions; `ClaudeClient` raises
    `LLMUnavailable` on missing key/SDK or API error so callers degrade. `DEFAULT_MODEL`
    is a pinned concrete id (never `-latest`); `model_used` records the API-resolved
    id; `nutrition_label()` publishes the re-gate policy and notes that worked
    examples/twins are model-independent.
  - **DOK 2 — Summary:** Encodes SPOV 3's honesty machinery — a pinned, auditable
    model and a deterministic offline path that makes "runs with AI off" literally
    true.
  - **Link to source:** [`../lsat/ai/client.py`](../lsat/ai/client.py)

#### A.5 Grounded misconception hypotheses

- **Source: `lsat/ai/misconception.py`**
  - **DOK 1 — Facts:** `HYPOTHESIS_CATALOG` maps documented taxonomy node ids →
    fixably-framed text; `hypothesis_for()` returns a hypothesis only when a distractor's
    trap family or a `flaw.*` tag matches a catalog label (carrying `source_label`).
    `validate_hypotheses()` gold-gates the mapper (pass rate ≥ `HYPOTHESIS_GOLD_PASS_MIN`
    = 0.9) *before* anything renders; `rephrase_with_ai()` is fail-closed (label
    survives, no new content/numbers) and degrades silently.
  - **DOK 2 — Summary:** The "grounded-gold" tier — the AI may only *rephrase* a
    human-documented label, never free-generate a diagnosis; with AI off it is fully
    deterministic.
  - **Link to source:** [`../lsat/ai/misconception.py`](../lsat/ai/misconception.py)

- **Source: `docs/Speedrun_AI_Features.md` (product framing)**
  - **DOK 1 — Facts:** Frames the wedge ("content is free now… what it ships is
    confidently wrong") and **tiered assurance** (proof only in the decidable slice;
    grounded-gold + citation elsewhere; abstain otherwise; no blanket "provably
    correct AI").
  - **DOK 2 — Summary:** The market and honesty framing behind SPOVs 2 and 3.
  - **Link to source:** [`Speedrun_AI_Features.md`](Speedrun_AI_Features.md)

### Category B — Learning-science foundation

*(Compiled with DOIs in [`Speedrun_Research_Support.md`](Speedrun_Research_Support.md)
and the memos in [`research/`](research/R2-error-trap-analysis.md).)*

#### B.1 Errors and confidence (hypercorrection)

- **Source: Metcalfe (2017), "Learning from Errors," *Annual Review of Psychology* 68.**
  - **DOK 1 — Facts:** Errorful retrieval + corrective feedback out-learns error-free
    study; *analysis of the reasoning behind the error* is crucial; corrected high-
    confidence errors can revert if the correction is forgotten.
  - **DOK 2 — Summary:** Errors are signal, and the highest-value correction is a
    confident one — which is exactly the item an AI must never fabricate (Insight 2).
  - **Link to source:** <https://doi.org/10.1146/annurev-psych-010416-044022>

- **Source: Butterfield & Metcalfe (2001), *JEP:LMC* 27(6).**
  - **DOK 1 — Facts:** The hypercorrection effect — errors committed with *high*
    confidence are the most likely to be corrected after feedback.
  - **DOK 2 — Summary:** Confidence × correctness is a real, measurable signal; the
    confident-wrong state is special.
  - **Link to source:** <https://doi.org/10.1037/0278-7393.27.6.1491>

- **Source: Butler, Fazio & Marsh (2011); Metcalfe & Miele (2014).**
  - **DOK 1 — Facts:** High-confidence errors *return* over a week; a retrieval test
    after feedback "blocks the return of the errors."
  - **DOK 2 — Summary:** The cost of a confident error is durable, which raises the
    stakes on never manufacturing one (SPOV 1).
  - **Link to source:** <https://doi.org/10.3758/s13423-011-0173-y> ·
    <https://doi.org/10.1016/j.jarmac.2014.04.001>

#### B.2 Erroneous examples and contrasting cases

- **Source: Große & Renkl (2007), *Learning and Instruction* 17(6); Booth et al. (2013).**
  - **DOK 1 — Facts:** Mixing correct + *incorrect* worked examples improved transfer
    when the error was **highlighted and explained**; contrasting correct-vs-incorrect
    beat correct-only in a majority of studies.
  - **DOK 2 — Summary:** "Here's the trap; explain why it's wrong" works — but only if
    the wrong case is genuinely and correctly wrong (Insight 3).
  - **Link to source:** <https://doi.org/10.1016/j.learninstruc.2007.09.008> ·
    <https://doi.org/10.1016/j.learninstruc.2012.11.002>

- **Source: Schwartz & Bransford (1998); Loewenstein, Thompson & Gentner (1999).**
  - **DOK 1 — Facts:** Comparing two minimally-different cases *before* being told the
    rule roughly **tripled** transfer vs studying them separately.
  - **DOK 2 — Summary:** The transfer engine behind minimal-pair discrimination — the
    pedagogy the evil-twin oracle makes safe to automate.
  - **Link to source:** <https://doi.org/10.3758/BF03212967>

#### B.3 Worked examples and cognitive load

- **Source: Sweller (1988); Sweller, van Merriënboer & Paas (1998).**
  - **DOK 1 — Facts:** Working memory is sharply limited; studying worked steps can
    beat unguided solving for novices (the worked-example effect).
  - **DOK 2 — Summary:** Justifies the faded worked-example format and raises the cost
    of a *wrong* worked step (it consumes scarce load teaching a falsehood).
  - **Link to source:** <https://doi.org/10.1207/s15516709cog1202_4>

#### B.4 Domain-specific reasoning

- **Source: Willingham (2007, 2009).**
  - **DOK 1 — Facts:** "Critical thinking" is largely domain-bound; people reason well
    about structures they recognize.
  - **DOK 2 — Summary:** Licenses encoding LSAT reasoning as a fixed taxonomy — the
    precondition for both an oracle (decidable slice) and grounded-gold labels.
  - **Link to source:** *American Educator* (2007) —
    <https://www.aft.org/ae/summer2007/willingham>

#### B.5 Testing effect and desirable difficulties

- **Source: Roediger & Karpicke (2006); Bjork & Bjork (2011); Dunlosky et al. (2013).**
  - **DOK 1 — Facts:** Retrieval strengthens learning (61% vs 40% at one week);
    "desirable difficulties" produce stronger durable learning though they feel
    harder; practice testing rated a top-utility technique.
  - **DOK 2 — Summary:** The base the graded-retrieval loop rests on, and the through-
    line for measuring/surfacing gaps rather than smoothing them over.
  - **Link to source:** <https://doi.org/10.1111/j.1467-9280.2006.01693.x>

### Category C — AI verification / formal methods

#### C.1 Model checking / decision procedures

- **Source: Clarke, Grumberg & Peled, *Model Checking* (MIT Press, 1999); ACM Turing
  Award 2007.**
  - **DOK 1 — Facts:** Model checking exhaustively verifies whether a (finite-state)
    system satisfies a formal specification; it is a *decision procedure*, not a
    heuristic.
  - **DOK 2 — Summary:** The formal license for "the oracle disposes." `entails()` /
    `classify()` are bounded model-checkers; trusting them over a confident narrator is
    the model-checking discipline (Insight 1).
  - **Link to source:** <https://amturing.acm.org/award_winners/clarke_1167964.cfm>

#### C.2 Generator/verifier separation (process supervision)

- **Source: Lightman et al. (2023), "Let's Verify Step by Step" (OpenAI).**
  - **DOK 1 — Facts:** Process supervision (rewarding each correct *step*) outperforms
    outcome-only supervision on hard reasoning; verifying steps is more reliable than
    trusting the final answer.
  - **DOK 2 — Summary:** Published analogue of per-step oracle verification of a
    derivation; supports checking the *steps*, not just the conclusion.
  - **Link to source:** <https://arxiv.org/abs/2305.20050>

#### C.3 LLM-as-judge (promise and peril)

- **Source: Zheng et al. (2023), "Judging LLM-as-a-Judge with MT-Bench and Chatbot
  Arena."**
  - **DOK 1 — Facts:** A strong LLM can approximate human judgment at scale, but
    exhibits position, verbosity, and self-enhancement biases.
  - **DOK 2 — Summary:** Why the checker is *independent and gold-validated* — an
    unvalidated LLM judge is not a gate (SPOV 2).
  - **Link to source:** <https://arxiv.org/abs/2306.05685>

#### C.4 Prompt injection (the source is untrusted data)

- **Source: Greshake et al. (2023), indirect prompt injection; OWASP Top 10 for LLM
  Applications (LLM01).**
  - **DOK 1 — Facts:** Untrusted content fed to an LLM-integrated app can hijack it
    with embedded instructions; injection is the top-ranked LLM application risk.
  - **DOK 2 — Summary:** Grounds the "source is data, never instructions" invariant and
    the injection-safe-by-construction `OfflineClient` (Insight 7).
  - **Link to source:** <https://arxiv.org/abs/2302.12173> ·
    <https://owasp.org/www-project-top-10-for-large-language-model-applications/>

### Category D — LSAT domain and practitioner method

#### D.1 Blind review / the Confidence Error

- **Source: 7Sage / J.Y. Ping, "The Blind Review."**
  - **DOK 1 — Facts:** Flag uncertain questions during a timed run, re-answer untimed
    before checking, and study hardest the ones you were *confident about yet missed*
    (the "Confidence Error").
  - **DOK 2 — Summary:** The practitioner vocabulary the AI hypotheses annotate;
    converging practical wisdom the feature automates.
  - **Link to source:** <https://7sage.com/blog/the-blind-review-how-to-correctly-prep-for-lsat-part-2>

#### D.2 Reasoning primitives and engineered traps

- **Source: PowerScore / Killoran (LR taxonomy + wrong-answer families); Sadler
  (1998), distractor-as-diagnosis.**
  - **DOK 1 — Facts:** LR items sort into a fixed question-type taxonomy with a
    prescribed attack; wrong answers are *engineered* along known axes; a chosen
    distractor maps to a specific misconception (a measurement, not a mistake).
  - **DOK 2 — Summary:** The human-authored ground the generator tags against, the
    checker judges against, and the grounded misconception labels trace back to.
  - **Link to source:** <https://blog.powerscore.com/lsat/> ·
    <https://doi.org/10.1002/(SICI)1098-2736(199803)35:3%3C265::AID-TEA3%3E3.0.CO;2-P>
