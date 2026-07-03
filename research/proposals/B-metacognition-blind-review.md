# Metacognition, Calibration & Blind Review — Research & Feature Proposals

**Researcher B lens:** metacognition & calibration (Dunlosky, Metcalfe, Koriat), judgments of
learning / illusion of competence, confidence–accuracy calibration & overconfidence, the
error/hypercorrection effect, self-explanation, and deliberate practice — mapped to the LSAT
community practice of **Blind Review**.

**Research-integrity note.** Every empirical source below was retrieved and read (via WebFetch
or a full-text file capture), not cited from memory. Effect sizes/findings are quoted from the
retrieved text. Two *foundational* papers (Ericsson 1993; Chi 1989) are named for provenance but
were **not** independently retrieved — their claims here are carried by retrieved sources
(Macnamara 2014; Bisra 2018) and are labelled `[provenance-only]`. Community practice (7Sage) is
strong as a *description of what top scorers do*, but is **not** a controlled empirical result and
is labelled accordingly.

---

## Learning-theory foundations

Each bullet: **claim** · citation · specific finding · **evidence strength**.

- **Learners are systematically overconfident, and the weakest are the most miscalibrated.**
  Kruger & Dunning (1999), *Unskilled and Unaware of It*, *J. Personality & Social Psych.* 77(6):1121–1134.
  <https://doi.org/10.1037/0022-3514.77.6.1121>. Across 4 studies (incl. a **logical-reasoning**
  test), bottom-quartile performers scored at the **12th percentile but rated themselves at the
  62nd**; miscalibration tracked deficits in metacognitive skill, and *training the skill improved
  the self-assessment*. **STRONG** as a robust, repeatedly-observed description (the causal
  *mechanism* is debated — part of the pattern is regression-to-mean / better-than-average, per the
  entry we read at <https://en.wikipedia.org/wiki/Dunning–Kruger_effect>). Relevance: an LSAT app
  must **measure** confidence against outcomes rather than trust learners' self-reports.

- **High-confidence errors are corrected *more* readily than low-confidence errors (hypercorrection).**
  Metcalfe (2017), *Learning from Errors*, *Annual Review of Psychology* 68:465–489.
  <https://doi.org/10.1146/annurev-psych-010416-044022> (full text read at
  columbia.edu/cu/psychology/metcalfe). Finding: "errors committed with high confidence are
  corrected more readily than low-confidence errors"; the effect holds at **immediate and delayed
  retest**, and is driven by **surprise** (a feedback-locked P3a ERP) plus greater semantic
  proximity to the correct answer. Also: "corrective feedback, **including analysis of the reasoning
  leading up to the mistake**, is crucial," and "considering ways in which they could be wrong …
  offsets overconfidence." **STRONG** (replicated lab effect + mechanistic review). Relevance:
  the "I was sure and wrong" moment is the single highest-ROI review target — and it is *exactly*
  what Blind Review surfaces.

- **Retrieval/practice testing beats passive re-exposure; re-reading breeds an illusion of competence.**
  Dunlosky, Rawson, Marsh, Nathan & Willingham (2013), *Improving Students' Learning With Effective
  Learning Techniques*, *Psychological Science in the Public Interest* 14(1):4–58.
  <https://doi.org/10.1177/1529100612453266>. Finding: **practice testing** and **distributed
  practice** earned **HIGH** utility (generalize across ages, materials, criterion tasks);
  self-explanation and interleaving = **MODERATE**; **re-reading, highlighting, summarization =
  LOW**. **STRONG** (comprehensive best-evidence review). Relevance: graded LSAT *items* (not
  re-reading explanations) are the right substrate; the danger is students mistaking fluency for
  mastery — which calibration measurement catches.

- **Self-explanation ("why is the right answer right and each wrong answer wrong?") is a robust booster.**
  Bisra, Liu, Nesbit, Salimi & Winne (2018), *Inducing Self-Explanation: A Meta-Analysis*,
  *Educational Psychology Review* 30(3):703–725. <https://doi.org/10.1007/s10648-018-9434-x>.
  Finding: random-effects **g = 0.55, 95% CI [0.45, 0.65]** over **69 effect sizes / 64 reports /
  5,917 participants**; comparable to peer tutoring (d=.55) and mastery learning (d=.50); the
  authors' own experiment found **generic** prompts improved **reading comprehension**. **STRONG**
  (meta-analysis). Originating paradigm: Chi et al. (1989), *Cognitive Science* 13:145–182
  `[provenance-only]`. Relevance: 7Sage Blind Review's "articulate both paths to the answer" is a
  self-explanation protocol; we can capture and quality-gate it.

- **Metacomprehension accuracy causally improves reading-comprehension learning (RC-specific).**
  Thiede, Anderson & Therriault (2003), *Accuracy of Metacognitive Monitoring Affects Learning of
  Texts*, *J. Educational Psychology* 95(1):66–73. <https://doi.org/10.1037/0022-0663.95.1.66>.
  Finding: manipulating monitoring accuracy (delayed-keyword generation) raised the
  judgment↔performance **gamma correlation**, which drove **better restudy choices** and higher
  **second-test RC accuracy** (delayed-keyword **.69/.66** on old/new items vs immediate **.53/.51**
  and no-keyword **.56/.55**); baseline metacomprehension accuracy for texts is "quite low."
  **STRONG-MODERATE** (well-cited single-lab causal chain). Relevance: RC is now a larger share of
  the scored LSAT (see below); a *per-passage* confidence signal that feeds restudy is directly
  supported.

- **Deliberate practice matters, but *volume alone* explains little in academic domains — quality/targeting is the lever.**
  Macnamara, Hambrick & Oswald (2014), *Deliberate Practice and Performance…: A Meta-Analysis*,
  *Psychological Science* 25(8):1608–1618. <https://doi.org/10.1177/0956797614535810>. Finding:
  deliberate practice explained **26% (games), 21% (music), 18% (sports), 4% (education), <1%
  (professions)** of performance variance; overall r≈.35 (~12% variance, "88% unexplained").
  **STRONG** (meta-analysis of 157 effect sizes). Origin of the construct: Ericsson, Krampe &
  Tesch-Römer (1993), *Psychological Review* 100:363–406 `[provenance-only]`. Relevance: "just do
  more PrepTests" is weak; the win comes from **structured, feedback-rich, error-focused,
  edge-of-ability** practice — precisely what calibration + blind review target.

**Synthesis for the app.** Learners can't see their own gaps (Kruger–Dunning); the most valuable
gap is a *confident* error (Metcalfe); the cure is *retrieval + self-explanation with feedback*
(Dunlosky, Bisra), tracked by *accurate monitoring* (Thiede), inside *targeted* practice
(Macnamara). Blind Review is the LSAT community's folk-implementation of this entire loop — we can
make it **quantitative, honest, and personalized**.

---

## Current-LSAT grounding (verified 2026)

**Scored-section structure (verified official LSAC).** As of the August 2024 change and continuing
through the 2025–26 and 2026–27 cycles, the multiple-choice LSAT is **two scored Logical Reasoning
sections + one scored Reading Comprehension section + one unscored variable section** (LR or RC).
The **Analytical Reasoning ("Logic Games") section was permanently removed** and replaced by the
second LR section.
- LSAC, *What to Expect Starting With the August 2024 LSAT* — <https://www.lsac.org/blog/what-to-expect-starting-with-august-2024-lsat>
- LSAC, *FAQ about the LSAT* (retrieved full page): "two scored Logical Reasoning sections and one
  scored Reading Comprehension section, plus one unscored section"; the test is **four 35-minute
  sections with a 10-minute intermission** after section 2 — <https://www.lsac.org/lsat/frequently-asked-questions-about-lsat>
- LSAC, *Specifications of the LSAT…* — three scored (2 LR + 1 RC) + variable; **from August 2026,
  in-center testing at Prometric for almost all test takers** (limited accommodation exceptions);
  **LSAT Argumentative Writing** is separate and remote — <https://www.lsac.org/lsat/register-lsat/accommodations/specifications-lsat-and-lsat-argumentative-writing>
- LSAC, *Changes are coming to the LSAT in August 2024* — <https://www.lsac.org/lsat/lsat-changes-coming-august-2024>

**Implications for this lens.** (1) **LR is now ~2/3 of the scored test** (two of three scored
sections) — reasoning-error calibration is worth double. (2) **RC is ~1/3 and rising in relative
weight** — metacomprehension monitoring (Thiede) matters more than in the Logic-Games era. (3) The
test is a **speeded** test (35 min/section) and, from Aug 2026, taken under **in-center, high-stakes
conditions** — so *separating "too slow / cracked under pressure" from "don't actually understand"*
is the central diagnostic problem. Our taxonomy already encodes this reality: it is
`format_as_of: "2024-08"`, sections `["LR","LR","RC"]`, and it carries a cross-cutting
`skill.pacing` competency fed by response timing (`lsat-taxonomy.yaml`).

**Blind Review, as used by the LSAT community (7Sage), verified by reading the source pages.**
- *Perfecting Blind Review* (Piliero, 2022, retrieved): "Blind Review (BR) is 7Sage's way of
  **separating fundamentals from technique, or untimed from timed performance**… see if your problem
  is knowing the material or simply **not knowing it fast enough**." Protocol: **(1)** take the
  section timed and **flag every question you're at all unsure about**; **(2)** take a break; **(3)**
  re-solve flagged/guessed questions **untimed** (cap ~20 min/question); **(4)** score, and log
  misses/flags to a **Wrong Answer Journal**. Decision rule: **BR ≫ timed ⇒ drill speed**; **BR ≈
  timed and low ⇒ fundamentals** (review core curriculum). — <https://7sage.com/blog/lsat-tips-perfecting-blind-review>
- *The Blind Review… Part 3* (Ping, 2013, retrieved): **"do not look at the answer key,"** then for
  each flagged item commit an answer **at 100% certainty** and **"talk out the rationale that makes
  that answer right and the rationale that makes each of the other four answers wrong"** (the "two
  paths": recognize the right answer *or* eliminate the other four). Purpose is explicitly stated as
  **(a)** "**takes the timing out of the equation**… can you get the question right without the time
  constraint?" and **(b)** forces you to "**articulate a reason for your choices**" instead of
  "placing bets." Students **record when a BR answer differs from the timed answer** for later
  analysis. — <https://7sage.com/blog/the-blind-review-how-to-correctly-prep-for-lsat-part-3>

This community protocol *is* the theory above, un-instrumented: flagging = a judgment of learning
(Koriat/Metcalfe); the timed↔untimed gap = a calibration/speed-accuracy decomposition
(Kruger–Dunning; Dunlosky); "why each wrong answer is wrong" = self-explanation (Bisra/Chi); the
Wrong Answer Journal = error-focused deliberate practice (Metcalfe/Macnamara). **Evidence strength:
community best-practice (widely taught, plausibly mechanism-backed), NOT a controlled trial.** Our
opportunity is to make it measured, honest, and adaptive — and to prove it in the eval harness.

---

## Proposed novel features

All three extend (not re-propose) what's built: the append-only `LSAT PerformanceEvent` log
(`lsat/events.py`), the logistic/IRT performance model with a `timing_z` covariate
(`lsat/models/performance.py`), the points-at-stake queue
(`rslib/src/scheduler/points_at_stake.rs`, fed by `lsat/events.topic_weights_for_queue`), the
readiness honesty contract (`lsat/models/readiness.py`), and the reproducible eval harness
(`eval/`, whose `eval/metrics.py` already ships `ece`, `brier`, `log_loss`, `reliability_bins`,
`auc`, `bootstrap_ci`).

> **Shared enabling change (small, one-time).** The event notetype currently stores
> `[item_id, skill_tags, correct, response_ms, answered_at_hlc, device_id]` (`lsat/notetypes.py`).
> Add two fields — **`phase`** (`timed` | `blind`) and **`confidence`** (0–100, or a 3-point
> sure/likely/guess mapped to a probability). This is a notetype *schema* change (fields, not just
> template HTML), done once in `ensure_notetypes`; it keeps every event append-only and
> sync-clean (one note per attempt, HLC-ordered), so a blind-review pass is simply a *second event*
> for the same `item_id`. Everything below reads these two fields.

---

### Feature 1 — Blind-Review Loop with a Timed↔Untimed Gap Diagnostic ("Two-Pass Items")

- **What it is (learner POV).** You do a session of graded LSAT items under a per-item timed budget.
  When you answer, one tap records confidence (and auto-flags low-confidence/guessed items). At
  session end **the answer key stays hidden**; the app drops you into **Blind Review**, re-serving
  your flagged + low-confidence + skipped items **untimed**. You must commit a *final, confident*
  answer to each **before** anything is graded. Only then does the app grade **both passes** and show
  a per-skill **Gap Map**: your **timed accuracy vs blind-review accuracy** for LR flaw, assumption,
  RC inference, etc., with each item bucketed into a 2×2:
  - **timed ✗ / blind ✓ → Pressure/Technique gap** ("you *know* this; you ran out of time or rushed").
  - **timed ✗ / blind ✗ → Knowledge gap** ("fundamentals — this needs teaching").
  - **timed ✓ / blind ✗ → Fragile/Lucky** ("right under time, can't justify it — not real mastery").
  - **timed ✓ / blind ✓ (high-confidence) → Mastered.**
  The app then routes: **Pressure** items → pacing drills (not more content); **Knowledge** items →
  the points-at-stake queue + card generation; **Fragile** items → flagged, *not* credited as mastery.

- **Why NOVEL vs generic Anki AND vs our built features.** Vanilla Anki has a *single* graded pass,
  a prospective ease button (Again/Hard/Good/Easy), no confidence capture, and no notion of an
  untimed counterfactual. Our own performance model already uses **`timing_z` as a covariate**, but
  it never captures a **second, untimed attempt**, so it *cannot* tell "slow-but-capable" from
  "incapable" — it only knows you were slow. This feature adds the missing counterfactual and turns
  the built `timing_z`/`skill.pacing` machinery into an actionable *diagnosis*. It also makes the
  **points-at-stake queue honest**: today `fold_recent_performance` counts any correct timed answer
  as mastery, so a lucky guess suppresses a topic that still needs work; blind review lets us
  exclude "Fragile/Lucky" wins from `perf_mastery`.

- **Learning-theory basis.** Speed–accuracy decomposition of competence (the timed↔untimed gap is
  the 7Sage practice, mechanistically grounded in overconfidence/miscalibration: Kruger–Dunning
  1999; Metcalfe 2017). Retrieval practice with delayed, withheld feedback = high-utility practice
  testing (Dunlosky 2013). Withholding the key until a committed blind answer prevents the
  "illusion of competence" from re-reading the correct choice (Dunlosky 2013; the 7Sage warning that
  peeking "gives a false sense of security").

- **Why LSAT-specific / differentiating.** Blind Review is *the* signature technique of high LSAT
  scorers (7Sage), and it exists because the LSAT is a **speeded** test (35 min/section; in-center
  from Aug 2026). No general SRS app models the timed/untimed distinction; a general medical-flashcard
  user has no analogous "pressure vs knowledge" split. This is a defensible, LSAT-shaped moat.

- **How it works in our app (data / model / UI).**
  - *Data:* the shared `phase`/`confidence` fields. Timed answer → `append_event(phase="timed",
    confidence=…)`; blind answer → `append_event(phase="blind", confidence=…)` for the same
    `item_id`. Both are append-only and HLC-ordered, so device sync + the existing conflict rules
    (`resolve_lww`) are untouched.
  - *Model:* new `lsat/blind_review.py` builds the BR set (flagged ∪ low-confidence ∪ skipped),
    joins the two phases per `item_id`, and emits the 2×2 label + per-skill `gap = blind_acc −
    timed_acc`. Feed results back two ways: (1) a `mastery_source` filter so
    `fold_recent_performance` can exclude Fragile/Lucky wins (an opt-in "honest mastery" mode);
    (2) a **pressure-index** per skill that raises `skill.pacing`'s `study_weight` contribution to
    the queue when the gap is large. Optionally expose `blind_acc` as an **untimed ceiling** the
    readiness Monte-Carlo can report alongside the timed projection ("floor 154 / ceiling 161 —
    the difference is pacing").
  - *UI:* extend the Item template (`_ITEM_QFMT` in `lsat/notetypes.py`) with a one-tap confidence
    control and a `pycmd("lsatConfidence:…")`; add a session "Blind Review" phase in the reviewer
    (qt hook via `qt/aqt/mediasrv.py` / `qt/aqt/lsat_*`), and a **Timed vs Blind** panel in the
    Svelte dashboard (`ts/routes/lsat-dashboard/`) showing per-skill gap bars + the 2×2 counts.

- **Implementation sketch (layer + effort).** Python `lsat/` (events schema + `blind_review.py`),
  qt reviewer flow (`qt/aqt/`), Svelte panel (`ts/routes/lsat-dashboard/`), plus an eval step. The
  queue change is *Python-only* (weights are computed in `topic_weights_for_queue` and passed to the
  Rust RPC), so **no Rust change is required**. **Effort: L** (spans data model, reviewer UX, UI, eval).

- **Risks / failure modes + measurement.**
  - *Key-leakage / non-blind BR* (student remembers their timed pick). Mitigate structurally: grading
    is deferred until the blind answer is committed (the 7Sage "don't peek" rule enforced in code);
    treat a **changed** answer as higher-signal, matching community priority weighting.
  - *Friction / doubled session time.* Scope BR to flagged/low-confidence/skipped only; cap per-item
    time; make the second pass optional per session.
  - *Confidence gaming / flat ratings.* Detected by Feature 2's calibration/resolution metrics.
  - **How we'd measure it works:** add `eval/blind_review.py` as an **ablation arm** in the style of
    `eval/ablation.py` — equal study budget, primary metric = **held-out *timed* P(correct) on unseen
    items**, comparing "gap-routing + honest-mastery" vs the current "all-correct = mastery." Secondary
    metrics: (a) reduction over time in the **Fragile/Lucky rate** (timed ✓ / blind ✗); (b) that
    **pressure-gap** items improve after *pacing* drills while **knowledge-gap** items improve after
    *content* — a routing-validity check; (c) convergence of timed→blind accuracy for coached skills.
    (Synthetic learners first, per the harness's honesty convention.)

---

### Feature 2 — Confidence-Calibration Engine + Hypercorrection-Prioritized Error Queue

- **What it is (learner POV).** Every graded item takes a one-tap confidence ("sure / likely /
  guess," or a 0–100% slider). A **Calibration** dashboard panel shows your **reliability curve**
  (stated confidence vs actual accuracy), a per-skill **Overconfidence Index**, and a **Resolution**
  score (does your confidence actually *separate* your right from wrong answers?). Your review queue
  then leads with **"you were sure and wrong"** items — the confident errors — because those are
  where correction pays off most.

- **Why NOVEL vs generic Anki AND vs our built features.** Anki's ease buttons are a *prospective*
  self-rating that is **never scored against outcomes**; nothing measures whether you *knew* you knew.
  Our built ECE (in `lsat/models/performance.py` / `eval/calibration.py`) measures **model**
  calibration — does *the app's* predicted P(correct) match reality. This feature measures **human**
  calibration — does *the student's* confidence match reality — an orthogonal axis, plus a **new
  study-priority signal** (hypercorrection) absent from the recency-weighted points-at-stake queue.

- **Learning-theory basis.** Kruger–Dunning (1999): overconfidence is largest for the weakest, on
  logic tasks, and shrinks as skill/metacognition improve — so calibration is both a *diagnostic* and
  a *trainable target*. Metcalfe (2017): **high-confidence errors are hypercorrected** (corrected more
  than low-confidence errors, immediately and at delay), so scheduling confident errors for near-term
  re-test is the highest-yield ordering; "considering how you could be wrong offsets overconfidence."
  Dunlosky (2013): guards against the fluency illusion that flat "everything felt easy" ratings encode.

- **Why LSAT-specific / differentiating.** The LSAT is scored on a tight 120–180 curve where a
  handful of confident errors move the score; the answer format (best of 5, with seductive "trap"
  choices already in our taxonomy: `skill.trap.*`) is engineered to produce *confident* errors. A
  calibration coach that says "your Necessary-Assumption confidence is 30 points hotter than your
  accuracy — and here are the traps you fall for" is a uniquely LSAT-shaped intervention.

- **How it works in our app (data / model / UI).**
  - *Data:* the shared `confidence` field on every event (timed and blind).
  - *Model:* new `lsat/models/calibration.py` reuses `eval/metrics.py` verbatim — **ECE** over
    (confidence-as-probability, correct); **Brier**/**log-loss**; **Overconfidence Index** =
    mean(confidence) − mean(accuracy) per skill; **Resolution** = `auc(confidence, correct)`; small-n
    honesty via `bootstrap_ci` + shrinkage (mirror the abstention pattern already in
    `performance.py`). *Hypercorrection term:* add a bounded boost in
    `lsat/events.topic_weights_for_queue` so a skill (or specific item) with **recent high-confidence
    misses** gains queue priority and those items get a scheduled near-term re-test — implemented in
    Python, no Rust change.
  - *Readiness coupling (careful):* surface a **"self-assessment miscalibrated"** coaching flag when
    the student's ECE is high; keep it *advisory* and do **not** silently alter the projected score
    (preserve the honesty contract in `readiness.py`). Optionally widen the reported band only via a
    documented, gated rule.
  - *UI:* a Calibration panel in `ts/routes/lsat-dashboard/` (reliability diagram — the harness
    already computes `reliability_bins`; overconfidence + resolution gauges; "sure-and-wrong" list).

- **Implementation sketch (layer + effort).** Mostly Python (`lsat/models/calibration.py`,
  `dashboard_data.py`, queue-weight tweak) + a Svelte panel; reuses existing metrics and UI patterns.
  **Effort: M.**

- **Risks / failure modes + measurement.**
  - *Prompt fatigue.* One tap, optionally sampled (every Nth item), skippable.
  - *Degenerate/flat confidence.* Caught by the **Resolution (AUC)** metric and low variance checks;
    nudge the learner.
  - *Small-sample instability* of overconfidence/hypercorrection boosts. Require ≥k events; cap the
    boost; abstain below threshold (same philosophy as the readiness give-up rule).
  - **How we'd measure it works:** `eval/calibration_student.py` gate on synthetic learners with a
    built-in overconfidence parameter (mirroring `INTERLEAVE_BONUS` in `ablation.py`), asserting the
    metric recovers it and improves under a "consider-why-wrong" intervention; an ablation comparing
    the **hypercorrection-prioritized** queue vs the recency queue on **correction rate of
    high-confidence errors at delayed re-test** (the in-app replication of Metcalfe); and a
    within-user trend showing **ECE / Overconfidence Index decline** with practice.

---

### Feature 3 — Blind-Review Error Autopsy: guided self-explanation, verified by the independent checker

- **What it is (learner POV).** When you finish Blind Review on a **missed** or **confident-wrong**
  item, the app runs a 60-second structured **autopsy**: pick the **trap** that snared you (from the
  taxonomy's `skill.trap.*`), write **one line on why the right answer is right**, and **one line each
  on why the four wrong answers are wrong** (7Sage's "both paths"). Your rationale is saved as a
  durable **`LSAT Card`** (a reusable judgment) tagged to that skill/trap — but only after the
  **existing independent AI checker** confirms your explanation **cites a verbatim span of the
  stimulus** (injection-resistant), so you can't bank a hand-wavy or hallucinated reason.

- **Why NOVEL vs generic Anki AND vs our built features.** Generic Anki review is passive re-reading
  of the back of a card. Our AI pipeline generates cards **from source texts**; this generates and
  quality-gates cards **from the student's own reasoning about their own errors** — closing the loop
  from *error → explanation → verified reusable card → spaced review*. It reuses `lsat/ai/checker.py`
  (verbatim-span requirement) and the `LSAT Card` notetype (`front/back/explanation/skill_tags/
  source_id/source_quote`) rather than adding new machinery.

- **Learning-theory basis.** Self-explanation meta-analysis: Bisra et al. (2018), **g = 0.55 [.45,
  .65]**, with generic prompts improving **reading comprehension** — directly relevant to RC. Metcalfe
  (2017): corrective feedback **"including analysis of the reasoning leading up to the mistake" is
  crucial**, and confident errors (the ones this feature targets) hypercorrect. Chi et al. (1989)
  `[provenance-only]` is the originating paradigm. Honest caveat: Dunlosky (2013) rates
  self-explanation **moderate** (promising but less in-situ evidence than practice testing) — so we
  ship it as an *augment* to Features 1–2, not a standalone claim.

- **Why LSAT-specific / differentiating.** It operationalizes the two most-cited 7Sage habits — "say
  why each of the other four is wrong" and the Wrong Answer Journal — with automatic **source-grounding
  and trap-tagging**, so the autopsy feeds the same points-at-stake queue at the **trap** granularity
  (e.g., you keep losing to `skill.trap.reversal` on Sufficient-Assumption).

- **How it works in our app (data / model / UI).** New `lsat/blind_review.py` hook creates a draft
  `LSAT Card` from the autopsy; `lsat/ai/checker.py` validates the cited span before `add_note`;
  tags apply `skill.trap.*` + the question-type node so `topic_weights_for_queue` can surface the
  pattern. UI: a compact autopsy form appended to the Blind-Review result screen.

- **Implementation sketch (layer + effort).** Python (`lsat/blind_review.py` + reuse
  `lsat/ai/checker.py`, `lsat/notetypes.py`) + a small reviewer form. **Effort: M** (**S** if the
  first version stores the self-explanation text without AI verification and adds the checker later).

- **Risks / failure modes + measurement.**
  - *Writing burden.* Micro-prompts (one line/choice), optional, only on confident-wrong/missed items.
  - *Checker false-passes* on free-text rationales. The harness already tracks
    `checker_false_pass_rate` (`eval/card_check.py`, a hard gate in `eval/run.py`) — reuse it to keep
    verification honest; start conservative and require the verbatim span.
  - **How we'd measure it works:** matched comparison (autopsy vs no-autopsy) on **future error rate
    for the same skill/trap** and on **correction of the specific confident errors** at delayed
    re-test; plus a card-quality gate so autopsy-authored cards clear the same
    `CARD_CHECK_PASS_RATE_MIN` bar as AI-generated ones.

---

## Ranked shortlist (best first)

1. **Blind-Review Loop + Timed↔Untimed Gap Diagnostic (Feature 1).** The signature LSAT technique,
   made quantitative — it uniquely separates *pressure* from *knowledge* gaps, makes our
   points-at-stake mastery **honest** (drops lucky guesses), and gives readiness a floor/ceiling
   band. Highest differentiation, biggest score-relevant payoff.
2. **Confidence-Calibration Engine + Hypercorrection Queue (Feature 2).** Cheap (reuses
   `eval/metrics.py`), orthogonal to everything built (human vs model calibration), and adds a
   theory-backed *new* study-priority signal (confident errors first). Strong evidence base
   (Kruger–Dunning, Metcalfe), and it also enables Feature 1's confidence capture.
3. **Blind-Review Error Autopsy (Feature 3).** Robust self-explanation gains (Bisra g=.55) with
   source-grounded, trap-tagged cards via the existing AI checker; smaller and best shipped as an
   augment layered on Features 1–2.

---

## Sources (all retrieved & read unless marked `[provenance-only]`)

1. LSAC — *What to Expect Starting With the August 2024 LSAT.* <https://www.lsac.org/blog/what-to-expect-starting-with-august-2024-lsat>
2. LSAC — *Frequently Asked Questions about the LSAT.* <https://www.lsac.org/lsat/frequently-asked-questions-about-lsat>
3. LSAC — *Specifications of the LSAT and LSAT Argumentative Writing.* <https://www.lsac.org/lsat/register-lsat/accommodations/specifications-lsat-and-lsat-argumentative-writing>
4. LSAC — *Changes are coming to the LSAT in August 2024.* <https://www.lsac.org/lsat/lsat-changes-coming-august-2024>
5. Piliero, R. (2022) — *LSAT Tips: Perfecting Blind Review*, 7Sage. <https://7sage.com/blog/lsat-tips-perfecting-blind-review>
6. Ping, J.Y. (2013) — *The Blind Review: How to correctly prep for LSAT (Part 3)*, 7Sage. <https://7sage.com/blog/the-blind-review-how-to-correctly-prep-for-lsat-part-3>
7. Kruger, J. & Dunning, D. (1999) — *Unskilled and Unaware of It*, JPSP 77(6):1121–1134. <https://doi.org/10.1037/0022-3514.77.6.1121>
8. Metcalfe, J. (2017) — *Learning from Errors*, Annual Review of Psychology 68:465–489. <https://doi.org/10.1146/annurev-psych-010416-044022>
9. Dunlosky, J. et al. (2013) — *Improving Students' Learning With Effective Learning Techniques*, PSPI 14(1):4–58. <https://doi.org/10.1177/1529100612453266>
10. Bisra, K. et al. (2018) — *Inducing Self-Explanation: A Meta-Analysis*, Educ. Psych. Review 30(3):703–725. <https://doi.org/10.1007/s10648-018-9434-x>
11. Thiede, K.W., Anderson, M.C.M. & Therriault, D. (2003) — *Accuracy of Metacognitive Monitoring Affects Learning of Texts*, J. Educ. Psych. 95(1):66–73. <https://doi.org/10.1037/0022-0663.95.1.66>
12. Macnamara, B.N., Hambrick, D.Z. & Oswald, F.L. (2014) — *Deliberate Practice and Performance…: A Meta-Analysis*, Psych. Science 25(8):1608–1618. <https://doi.org/10.1177/0956797614535810>
13. Ericsson, K.A., Krampe, R.T. & Tesch-Römer, C. (1993) — *The Role of Deliberate Practice…*, Psych. Review 100(3):363–406. `[provenance-only]`
14. Chi, M.T.H. et al. (1989) — *Self-explanations…*, Cognitive Science 13(2):145–182. `[provenance-only]`
