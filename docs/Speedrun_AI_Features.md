# Speedrun — Feature Specification for Implementation

**Exam:** LSAT (scored 120–180). Two Logical Reasoning sections, one Reading
Comprehension section. Logic games are out of scope (removed August 2024).

## The wedge — why buy this when AI can build software?

**Content is free now.** Anyone can prompt an AI to spin up an LSAT app in an
afternoon — and what it ships is _confidently wrong_: hallucinated questions,
sycophantic grading that says "close enough," a fabricated "+15 points!" readiness
number. On a career-deciding exam, that's not a nuisance; it's the failure mode
that costs you points. **That afternoon-app is exactly the tier this product is the
inverse of.**

> **The scarce good isn't more questions — it's the _proven truth about your own
> test_: which points you're leaking under the clock, which "right" answers were
> luck, which misses were confident misconceptions. And we're the only LSAT tool
> whose AI _can't lie to you about it_.**

What can't be vibe-coded is the **verification infrastructure**: decision procedures
that re-derive every formal-logic answer (`lsat/quantifier.py`,
`lsat/conditional_chain.py`), a fail-closed checker whose false-pass gate is
fuzz-tested to **0** (`eval/`), an equal-study-time bootstrap-CI harness, and
diagnostics that measure _your_ leaked points on _your_ real answers. Ask an LLM to
build the checker and it hands you one that returns `PASS`. Trust is the _enabling
condition_, never the pitch.

**Tiered assurance (the honest version — we do not overclaim).** Correctness is
_proven_ only where a decision procedure exists (formal-logic LR: conditionals,
quantifiers, chains). Everywhere else the AI is held to **grounded-gold + verbatim
citation**, and where we can't verify, we **abstain** and say so. We never ship a
"provably correct AI" blanket claim across RC or open natural-language LR — because
it wouldn't be true.

**How to read this doc.** The same work is organized as prominent, demonstrable
features (nothing dropped — the Rust change, the ablation, the honesty rules and
grading coverage are all preserved below). Each opens with its **Spike**: the
contrarian, defensible one-liner most competitors can't honestly say. The
learning-science research is unchanged (`Speedrun_Research_Support.md`, `research/`);
this doc revises the _proposals_. The two design theses — the original Spiky Points
of View — still anchor it:

- **SPOV 1 — The LSAT is a knowledge test wearing a reasoning test's costume.** The
  memorizable knowledge base is _reasoning primitives_ — precise diction,
  formal-logic rules and named fallacies, and the question-type taxonomy with its
  prescribed attack. Knowing them is necessary, not sufficient, so we must also
  measure the gap between knowing and applying.
- **SPOV 2 — The misses worth deep review are the ones you were confident about.** A
  confident wrong answer signals a recurring misconception; an unsure wrong answer
  signals a plain gap. Capture confidence _before_ the reveal, treat confident-wrong
  as the highest-value review, and let miscalibration widen the readiness range.

Runtime AI (card generation, misconception hypotheses, oracle-verified worked
examples + evil twins) is confined to the parts marked **[AI]**; everything else
runs with model calls off, and every [AI] surface degrades to a deterministic path
("runs with AI off"). The pinned model id is recorded on every gated result and
re-gated on any change (`lsat/ai/client.py` — never `-latest`).

---

## The features, lead with the spike (what a user sees)

Ordered by how sharply each answers "why buy this": the trust-anchoring diagnostics
and the oracle-backed AI first; the (excellent, but table-stakes) primitive decks
last. Every row states the contrarian one-liner a competitor can't honestly copy.

| Feature                                                    | **Spike** (the defensible one-liner)                                                                                                                                                                                                                                |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Blind-Review Delta + Timed Runner** (the hero)           | _"Trust your first instinct" is folklore. We prove — on YOUR paired timed-vs-untimed answers, with a bootstrap CI — which points you leak to the clock vs don't know, and stay silent when the CI can't call it._                                                   |
| **Oracle-Verified Worked Examples + Evil Twins** [AI]      | _Every other AI tutor asks you to trust the model. Ours lets the model draft, then a proof-checker deletes any step that doesn't verify — you watch it get caught, and it still works with the AI off._                                                             |
| **Confidence & Misconception Engine**                      | _Reviewing every miss equally wastes your hour. The only miss that costs you again is the one you were SURE about — we capture confidence before the reveal, shove confident-wrong to the front (a real Rust scheduler change), and prove the fix stuck with a CI._ |
| **Three Honest Scores + Readiness**                        | _A study app that always shows a readiness score is lying. Ours refuses to draw a number until eight gates pass — and when you're overconfident it makes the range WIDER, not the number higher._                                                                   |
| **The Logic Drill Suite**                                  | _Every other drill's answer key was typed by a human who can have a bad day. Ours is re-derived by a model-checker on every build — physically incapable of teaching a wrong rule._                                                                                 |
| **Reasoning-Primitive Decks + Identification-First Study** | _"Do more practice tests" is advice for people who already know why they miss. We make you name the question type before you may solve it — so "didn't recognize the stem" stops hiding inside one 70% number._                                                     |

Everything is reachable from the **Tools ▸ LSAT** menu (Dashboard, **Load Starter
Decks**, Study on Your Phone) or the mobile shell's three tabs (Study / Logic /
Progress). The Logic tab now includes the **Worked example** and **Skill or luck?**
(evil-twin) drills. "Load Starter Decks" is the front door: it seeds original
diction/logic/qtype flashcards + graded practice items so every feature has content
to work on immediately.

---

## The AI flagship — Oracle-Verified Worked Examples + Evil Twins [AI]

**Spike.** _Every other AI tutor asks you to trust that the model is usually right.
Ours lets the model draft, then a decision procedure deletes any step that doesn't
verify — you can watch it get caught and overruled, and you can switch the AI off
and still ship the correct answer._

**What the user sees.** In the Logic tab, two drills built on the same guarantee:

- **Worked example** — a conditional-chain proof with the first steps shown and the
  last blanked to complete. A green **proof receipt** marks every shown step
  "✓ verified" with the footer _"re-derived by a decision procedure, not a language
  model,"_ plus a provenance badge (**AI-drafted → oracle-verified**, or
  **AI draft rejected → oracle-derived** when a draft fails to check out).
- **Skill or luck?** — an _evil twin_: a one-edit variant of an item you'd get right
  whose correct answer **flips** (reverse the arrow, swap a quantifier, convert
  subject/predicate). Nail it and you understood; miss it and you pattern-matched.

**How the AI is load-bearing without ever risking correctness.** The oracle
(`lsat/conditional_chain.py::entails`, `lsat/quantifier.py::classify`) _enumerates
and proves_ every step / every candidate twin; the LLM does only **logically inert**
work — drafting a step ordering the oracle must bless, or selecting which proven
twin best targets your misconception and picking fresh surface nouns. A hallucinated
step or a mislabeled twin **cannot reach the screen** (`draft_and_verify`,
`evil_twin.verify_twin` fail closed; deterministic fallback on `LLMUnavailable`).
This is the one place generation earns its keep: the oracle can _verify_ but can't
_choose the sharpest, freshly-phrased discriminator_ — that's the model's job.

**Why a competitor can't cheaply copy it.** A pure-LLM tutor can't _guarantee_
correctness; a pure-template tool can't _target or vary_. Doing both requires the
verification engine + the discipline of gating generation behind it — precisely what
a one-shot AI build omits (it ships the plausible-but-unverified version).

**Eval (hard gates, in `make eval`).** `worked_example`: 0 false-passes over planted

- 3,014 fuzz derivations, full valid-proof coverage. `evil_twin`: 47 curated twins +
  3,500+ fuzz flips, **0 mislabels** cross-checked against an _independent_ oracle,
  malicious-drafter-safe. Both `GATE OK`.

**Honesty.** Correctness is a _proof_ here (the decidable formal-logic slice), not a
model opinion; the equal-time learning arm is disclosed **report-only** synthetic —
real learners settle the magnitude. Code: `lsat/worked_example.py`,
`lsat/evil_twin.py`, `eval/worked_example.py`, `eval/evil_twin.py`.

---

## Feature 1 — Reasoning-Primitive Decks + Identification-First Study (SPOV 1)

**Spike.** _"Do more practice tests" is advice for people who already know why they
miss. We make you name the question type before you're allowed to solve it — so
"didn't recognize the stem" and "couldn't do the reasoning" stop hiding inside one
70% number._ (Identification is graded as a separate, stored stage.)

**What the user sees.** A one-click _starter deck_ of original content, split into
three first-class primitive families, plus a graded practice deck:

- `LSAT::Drills::Diction` — precise meanings of terms/connectives whose misreading
  costs working memory mid-passage (_some_, _unless_, _only if_, _except_, …).
- `LSAT::Drills::Logic` — formal rules + the named-fallacy catalog (sufficient vs.
  necessary, contrapositive, quantifiers, causal/sampling/equivocation/circular …).
- `LSAT::Drills::Question Types` — the LR/RC taxonomy, drilled **identification-first**
  (A2): show a stem cue, name the type _before_ solving, so identification accuracy
  is analyzable separately from solution accuracy.
- `LSAT::Practice` — graded multiple-choice items that feed the performance signal;
  on a miss, the **Elaborated Contrast Card** shows _why the credited answer wins_
  vs _why the trap you picked is a trap + the minimal edit that would fix it_ — the
  Distractor-Reasoning Engine (F2), deterministic and AI-off.

**Prominence fix.** Seeding is wired into the app (`Tools ▸ LSAT ▸ Load Starter
Decks`, and offered when the dashboard is first opened) — previously the decks
existed only behind a CLI script, so a fresh profile had nothing to study.

**Data model.** Cards carry exactly one `primitive_type` + a `topic_weight`; items
carry per-distractor trap labels. Every taxonomy node gets ≥1 card, so coverage (A3)
can measure ~100% of the primitive taxonomy and readiness abstains when it is thin.

**Acceptance.** Loading the starter decks creates the four decks; a `qtype` card
shows the classify prompt first and stores both stage grades; the coverage map shows
percent of the taxonomy covered; readiness abstains below the declared threshold.

---

## Feature 2 — The Logic Drill Suite

**Spike.** _Every other logic drill's answer key was typed by a human who can have a
bad day. Ours is re-derived by a model-checker on every build — the drill is
physically incapable of teaching a wrong rule._ (Proof, not assertion:
`quantifier.classify`, `conditional_chain.entails`.)

**What the user sees.** A mobile **Logic** tab whose Drill Launcher groups short,
deterministic, instantly-graded micro-drills under Conditionals / Quantifiers /
Question-tactics. Each drill hands a fresh prompt, grades on tap, and reveals the
teaching point:

- **Conditional translation** — English → `sufficient → necessary` arrow + contrapositive.
- **Conditional chains** — does a candidate inference _must-follow_ from a 3+ arrow chain?
- **Quantifier validity / negation** — _must / cannot / could be true_; the exact negation.
- **Stem polarity** — catch inverted stems (EXCEPT / LEAST / negated).
- **Necessary vs sufficient** — sort a candidate assumption into the four cells.

**Why it's the best demo.** Every drill works on first use with zero prior data,
loops forever, and its answer key is _proven_, not hand-typed — a bounded Venn /
truth-table model-checker verifies every verdict in the test suite, so a drill can
never teach a wrong rule; grading fails closed on anything outside the verified set.
These are SPOV 1's primitives made _drillable to automaticity_.

**Acceptance.** Each drill grades deterministically; every served item's verdict is
proven correct by an independent oracle in that module's self-test; each drill logs
a graded event under its skill node so it feeds mastery/fluency.

---

## Feature 3 — Confidence & Misconception Engine (SPOV 2)

**Spike.** _Reviewing every wrong answer equally wastes your hour. The only miss that
costs you again on test day is the one you were SURE about — so we capture confidence
before the reveal (un-fakeable), shove your confident-wrong misses to the front of a
real Rust scheduler queue, then prove the fix stuck with a before/after CI._

**What the user sees.** Before the answer is revealed, a one-tap confidence control
(Sure / Likely / Guess). Each graded review resolves to a state — **confident+correct
= mastery**, unsure+wrong = honest gap, unsure+right = fragile, **confident+wrong =
misconception (the danger zone)** — and confident-wrong items are surfaced (the
misconception ledger + grounded hypotheses) and _scheduled first_.

**The required Rust change (B3).** A new review order sorts due cards by
`topic_weight × student_weakness × misconception_penalty`, the penalty rising with a
card/topic's confident-wrong history. This is a real engine change
(`rslib/src/scheduler/points_at_stake.rs`), shipped to the phone via the shared
engine. Mandatory, all satisfied: a protobuf message for the queue request/response;
≥3 Rust unit tests + 1 that calls it from Python; undo/no-corruption verified; a note
on why it belongs in Rust; the upstream files touched; runs on the phone build.

**[AI] Grounded hypothesis (B4).** A confident-wrong state may show a short _why_
("you may be treating a necessary condition as sufficient") — but only mapped to a
label in a documented flaw taxonomy, validated against a gold set (§7f), fully
removable, scores unaffected with AI off.

**Data model.** `chosen` + `pre_answer_confidence` + `phase` live in the shared
append-only event store (the keystone, K), written before reveal, sync-safe.

**Acceptance.** Confidence is recorded before reveal and round-trips through sync;
each review resolves to exactly one state; confident-wrong cards rank ahead of
equal-weight cards without that history; every AI hypothesis carries a source label;
with AI off the flow and scores are unaffected.

---

## Feature 4 — Timed Section Runner + Execution Diagnostics (SPOV 1: necessary ≠ sufficient, under the clock)

**Spike (the hero number).** _"Trust your first instinct" and "never change your
answer" are folklore. We prove them right or wrong with YOUR data: a paired
timed-vs-untimed **Blind-Review Delta** with a bootstrap CI tells you which points
you leak to the clock (pacing, fixable fast) vs don't know (content) — and stays
silent when the CI can't call it._ This is the number a 170-hunting retaker actually
pays for, computed on their own answers, not a synthetic sim.

**What the user sees.** A "Start a timed section" flow: ~10 items on an LSAT-pace
clock with a question palette, flag/jump, and no mid-section answer leak (the server
grades on submit). It produces the **First-Instinct Ledger** — _your own_ answer
changes went wrong→right N vs right→wrong M, with a CI, refusing the folk "never
change" rule. Doing a timed pass and then a **blind-review** pass (a study-mode
toggle) then lights up the execution diagnostics: the Blind-Review **Gap Map**
(timed×untimed 2×2), the **Choke Index**, **Rush errors**, **Time-leak**, and the
**Stamina** curve — each a distinct signal about _applying_ the primitives under
pressure, not knowing them.

**Prominence fix.** These diagnostics used to render as a wall of nine ghost cards;
the dashboard now shows only the ones you've _earned_ and folds the rest into a
single "unlocks as you study" line that names them and what to log.

**Acceptance.** The runner grades server-side (correctness never leaves mid-section);
the ledger claims a direction only when its CI excludes 0; every execution diagnostic
abstains below its floor and is a report-only estimator whose validity is gated by an
`eval/` arm (no learning-effect claim).

---

## Feature 5 — Three Honest Scores + Readiness (SPOV 1 bridge + honesty)

**Spike.** _A study app that always shows a readiness score is lying to you. Ours
refuses to draw a number until eight gates pass — and when you're overconfident it
makes the range WIDER, not the number higher._ Abstention isn't the pitch; it's what
makes the measured numbers believable.

**What the user sees.** Three separate, ranged, abstaining numbers on the dashboard:

- **Memory** — FSRS recall over the primitive decks (a Wilson interval per topic).
- **Performance** — P(correct) on a _new, exam-style_ item, from topic mastery,
  difficulty and timing — architecturally distinct from Memory (C1). The **transfer /
  paraphrase harness** (C2 / H) reports the recall-vs-application gap so SPOV 1's
  bridge is proven or falsified honestly — the gap is the deliverable, not a grade.
- **Readiness** — a Monte-Carlo scaled-score projection that shows a point estimate,
  a likely range, percent of taxonomy covered, a "how sure" indicator, the top
  reasons, and the single best next thing to study.

**Honesty (D1/D2/D3).** The student calibration chart makes the confident-wrong
region visible; measured miscalibration _widens_ the readiness range (D2); and the
**give-up rule** shows _no_ readiness number until enough graded reviews + taxonomy
coverage, and abstains when miscalibration is too high — constants written in the
README and enforced in code. A per-skill **Mastery-Growth** readout shows your own
early-vs-recent change, CI-gated (never a rank or a fabricated number).

**Acceptance.** Memory / Performance / Readiness are stored and displayed as separate
ranged numbers; no readiness number appears without all honesty fields; below-threshold
data yields an explicit abstain; the widening rule and give-up constants are documented.

---

## Implementation order, the ablation, and grading coverage

**Build order (unchanged intent).** _Core, no AI:_ the primitive decks + identification
format (F1), the shared confidence/`phase` event store (K/B1) early because everything
depends on it, the misconception-priority Rust queue (B3), the memory/performance split
(C1), calibration + readiness honesty (D1/D2/D3). _AI, checked:_ grounded hypotheses
(B4), paraphrase generation (C2), AI card generation with the §7f check, held-out eval

- beat-a-baseline. _Prove it, ship both:_ Brier/log-loss, performance accuracy, the
  paraphrase gap reported honestly, the ablation, packaged desktop + phone, sync docs.

**The ablation (spec §8).** One study feature, three builds at equal study time: full
app, that feature off, and plain Anki. Chosen feature: the **B3 misconception-priority
queue** — it isolates as a single scheduler flag, shares the required Rust change's
code path, and is the more novel SPOV. Pre-registered claim (before running):
_prioritizing high-confidence errors raises accuracy on related novel questions at
equal study time._ Report a range, and report it even if the feature makes no
difference. (SPOV 1's identification-first design is demonstrated via the C2 paraphrase
gap, not a second ablation.)

**Grading-area coverage.**

| Grading area                                 | Where it's satisfied                                                        |
| -------------------------------------------- | --------------------------------------------------------------------------- |
| Rust change + fit with Anki (20%)            | Feature 3 (the B3 misconception-priority queue)                             |
| Score accuracy + honest uncertainty (20%)    | Feature 5 (C1, C2, D2, D3)                                                  |
| Study feature on learning science (15%)      | Feature 3 ablation · Feature 1 identification-first (A2) · Feature 2 drills |
| AI checking + safety (15%)                   | Feature 3 (B4) · Feature 5 (C2) · §7f card check                            |
| Fair, re-runnable tests (12%)                | Feature 5 (C2, calibration) · the ablation · every `eval/` arm              |
| One engine, desktop + phone, with sync (10%) | Feature 3 (confidence/`phase` in the shared engine)                         |
| Useful product + clean UX (8%)               | Feature 1 study flow · Feature 2 Drill Launcher · Feature 5 dashboard       |

**Hard limits this doc satisfies:** a real Rust change (Feature 3), a phone companion
sharing the engine with synced confidence (K/B1), held-out testing (Feature 5), no
made-up readiness numbers (D3 abstain), no leaked test data (§7e), and every AI claim
traceable to a source (B4).
