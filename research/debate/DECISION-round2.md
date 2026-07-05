# DECISION (Round 2) — Anki-for-LSAT: Second Design Ruling

**Chair:** neutral synthesis of a second four-lens design debate (cognitive
scientist · LSAT coach · engineer · student-advocate), two rounds, over **29
proposals** researched across 10 LSAT-relevant learning-science areas (RC skills,
adherence, exam-date scheduling, stamina/fatigue, elaborative feedback, SRL,
conditional logic, retrieval formats, anxiety, difficulty progression).

**Status:** authoritative for the _second_ wave of features. It builds on
`DECISION.md` (round 1, which shipped the keystone + F1–F5 + Transfer Meter) and
pushes into ground round 1 left open — **adherence** (no shipped feature touches
"did the session happen"), **exam-date-aware scheduling**, **stamina**, and
**conditional-logic drilling**.

**The discipline is unchanged.** Every claimed effect ships as a measured
`eval/` arm at **equal study time** with a **bootstrap CI excluding 0**; honest
ceiling ~4–7 scaled points / single-digit percentile; **never "2 sigma."** Scores
abstain when evidence is thin. No Rust/proto/schema migration is required by any
winner (the additive notetype-field winners reuse the existing idempotent
`migrate_missing_fields` pattern).

---

## The SHIP set (ranked by evidence-per-build-hour)

### Stage 1 — #24 Paired within-item Choke Index with bootstrap CI + abstention

**Refines shipped F4 (`lsat/pacing.py`).** Highest debate score (**9.0, unanimous,
zero required changes**).

- **Problem it fixes:** the current Choke Index is `all-timed-accuracy −
  all-untimed-accuracy` over _different_ item pools → bakes in an item-difficulty
  confound and can flag "choke" from noise.
- **Mechanism:** pair events by `item_id` that have BOTH a timed and a
  blind/relaxed answer; per-item delta ∈ {−1,0,+1} = untimed − timed; **bootstrap
  a 95% CI** per skill + overall (reusing `eval.metrics.bootstrap_ci`); emit a
  choke flag **only when CI lower bound > 0**, else abstain. Keep the unpaired
  aggregate as an explicitly-labelled low-confidence fallback.
- **Honest claim:** diagnostic-validity only (fewer false positives, correct
  abstention). No scaled-point claim.
- **Eval:** new `eval/choke_validity.py` (synthetic ground-truth pressure penalty;
  penalty=0 and difficulty-mismatched arms). CI coverage ≥ 90%; false-positive
  flag rate ≤ 5% vs the unpaired estimator. **No Rust/proto/notetype.**

### Stage 1 — #4 If-Then Study Plan (implementation intentions + context-cued restart)

**New adherence layer.** Top-tier (9.0 advocate / 8.0 technical). Strongest
external evidence in the set (implementation intentions **d≈0.65**, Gollwitzer),
and it attacks the #1 real failure mode no shipped feature touches — _not showing
up_.

- **Mechanism:** one if-then sentence at onboarding ("If it's `<time>` after
  `<habit>` at `<place>`, then I do `<N>` cards"), stored as config; a single
  daily cue restatement + one-tap Start. **Locked constraints:** auto-silence after
  completion; easy snooze/re-plan; **explicit prohibition on streak counters /
  loss-aversion**; after ≥2 missed planned days a _neutral_ re-plan prompt (never
  shame). Append-only session/plan events.
- **Honest claim:** an adherence lift (more completed planned sessions); **no**
  score claim; any score effect is only the mechanical value of extra practice and
  is **not** double-counted against F1–F5. Held UNPROVEN until a live cohort.
- **Eval:** `eval/adherence.py` — 14-day planned-completion rate plan vs no-plan
  (CI excludes 0); **guardrail:** accuracy-per-item CI must _include_ 0
  (no cannibalization). **No Rust.**

### Stage 2 — #13+#14 Elaborated Contrast Card (+ gated Trap Autopsy)

**Upgrades shipped F2 one-tap why-wrong.** #13 = 8.0 unanimous.

- **Mechanism:** on a miss, after reveal, a two-column contrast — LEFT a
  deterministic "why-credited" clause keyed to the item's skill/flaw node; RIGHT
  the trap family of the chosen letter + a one-line "minimal edit" that would make
  that trap correct. Every clause is **gold-set-gated and abstains** when no
  documented label applies; AI is rephrase-only under the fail-closed
  label-must-survive guard. Stage-2 (#14, default OFF): a pre-reveal one-tap
  trap self-diagnosis in untimed phase only; mismatch re-queues via the existing
  points-at-stake trap boost.
- **Honest claim:** ≤ small (~2–4 pt) held-out gain on unseen same-trap items,
  only if EF−KCR CI excludes 0. No additive-stacking-on-F2 claim.
- **Eval:** `eval/feedback.py` — 3-arm equal-_time_ (KR / KCR+label / EF-contrast);
  EF costs more seconds so does fewer items (penalized honestly). **No Rust/proto,
  no new notetype.**

### Stage 2 — #7 Exam-Day Retrievability Targeting (deadline-aware DR ramp)

**Only exam-DATE-aware winner** (8.0, ship-with-changes). Becomes the single owner
of the shared `exam_date` config (consolidating the deferred #5/#8/#9/#16 cluster —
one module, not forked schedulers).

- **Mechanism:** user sets `exam_date` once; a pure-Python layer computes
  `days_until_exam` and a deadline-adjusted desired-retention curve (low floor ~0.80
  when far → ramp to ~0.92–0.95 in the final ~14–21 days, Cepeda ridgeline);
  projects each card's **exam-day** retrievability from FSRS stability; surfaces a
  consolidation queue ranked by `exam_weight·(DR − projected_R)`; flags cards whose
  next due lands after the exam. **Abstains** to the current queue when stability is
  thin or no date; **hard daily cap** (never "more is better"); calm feasibility
  note.
- **Honest claim:** ~3–6 pt from **reallocating the same** review minutes; explicit
  daily-studier **null** case reported.
- **Eval:** `eval/exam_schedule.py` — equal-review-count sim, deadline-aware vs
  fixed-DR; projected exam-day R + simulated test-day accuracy, CI excludes 0;
  daily-studier null arm reported. **No Rust.**

### Stage 3 — #10 Fatigue Curve (time-on-task decay meter)

**New ground** (7.3–8.0) — no shipped feature captures session position /
cumulative time-on-task (F4 measures per-item _time pressure_, orthogonal).

- **Mechanism:** tag each answer with session id + active minutes elapsed; bin by
  cumulative minutes; recency-weighted accuracy + median RT per bin; OLS slope
  ("% accuracy lost / 30 min"). **Prereqs:** robust pause/idle-aware active-time
  accumulation; eval regresses out item difficulty; surface a headline **only** if
  the fatigue-aware model beats the position-blind model by dAUC ≥ 0.02 (CI excludes
  0) on held-out last-third items, else abstain loudly.
- **Honest claim:** measures a real decrement; the diagnostic does not raise scores.
- **Eval:** `eval/fatigue.py`. Adds `session_id`/`session_pos`/`session_elapsed_ms`
  to the event notetype via the **idempotent `migrate_missing_fields` pattern**
  (old events default to unknown). **No Rust/proto.**

### Stage 4 — #19 Conditional Translation Drill (backward-faded diagramming)

**Drills `skill.conditional_logic`** — the taxonomy's highest `study_weight` (0.9)
cross-cutting LR primitive, today only _tagged_, never _drilled_. 7.3,
ship-with-changes. Ranked last: Effort **L** with a parser-correctness dependency.

- **Mechanism:** a `conditional_translate` card mode; identification-first (tap
  sufficient vs necessary, assemble `A→B`, generate contrapositive `¬B→¬A`);
  backward fading (worked → blank contrapositive → blank arrow → blank tagging).
  **Fully deterministic Python grader** (no LLM at grade time) behind a unit-tested
  phrasing/normalization table, with a **mandatory hard abstain** (show the worked
  answer) on any sentence it cannot confidently normalize. `fade_level` advances
  only when the skill clears the ZPD band AND the F5 automaticity gate.
- **Honest claim:** modest lift on the conditional-dependent LR subset (CI excludes
  0) + faster translation; no broad "reasoning" claim; ship the null if flat.
- **Eval:** `eval/conditional.py` — equal-events, faded vs generic-review vs plain;
  held-out P(correct) on unseen conditional-tagged LR items. **No Rust.**

---

## Deferred (gated) and Cut

**Deferred / gated** (build only when the gate clears): the rest of the exam-date
cluster (#5/#8/#9/#16 → fold into #7's one module), Choke→Automaticity routing
(#26, gated on #24), Conditional Mis-Translation taxonomy (#20, gated on #19),
Break-Placement planner (#11) + Fatigue-Adjusted Readiness (#12) (gated on #10),
**RC Structural-Read Protocol (#1)** and RC Elaborative-Interrogation (#22) —
**data-blocked** on RC passage supply (top RC priority once a checker-gated passage
bank exists), Prephrase Gate (#21), Arousal-reappraisal (#25, opt-in default-off),
faded scaffolds (#15/#27), progression rungs (#28), adaptive-τ (#29, an ablation
experiment, adopt only if it beats fixed-0.85), process-feedback tile (#6),
forethought/reflection wrapper (#18), RC pretest-prime (#23).

**Cut:** #17 Adherence Meter (dup of #4 + invites the exact gaming the discipline
forbids), #3 Comparative-Passage Map (data-blocked, ~2% of exam), #2
Viewpoint-Attribution Drill (weak evidence, tiny slice, overlaps F2).

---

_Full per-proposal research memos, evidence ratings, and round-by-round scores are
archived in the workflow journal; this document is the binding synthesis for the
round-2 build order._
