# Research → Debate → Decision → Build

This folder is the full record of how we chose the app's novel, evidence-based
LSAT features: **independent research**, an **adversarial multi-agent debate**,
and a **binding decision** — then the features were implemented in the codebase.

## How to read this folder

1. **[`BRIEF.md`](BRIEF.md)** — the mission, the current app, and the research
   rules (real citations with URLs, effect sizes, evidence ratings, no
   pseudoscience).
2. **Research memos** — four independent lenses, each web-sourced and cited:
   - [`01-memory-retrieval.md`](01-memory-retrieval.md) — retrieval practice,
     feedback timing, successive relearning, pretesting, errorful generation.
   - [`02-transfer-schema.md`](02-transfer-schema.md) — analogical transfer,
     worked examples, self-explanation, schema induction.
   - [`03-metacognition-srl.md`](03-metacognition-srl.md) — calibration,
     hypercorrection, deliberate practice, test anxiety / pacing.
   - [`04-adaptive-psychometrics-lsat.md`](04-adaptive-psychometrics-lsat.md) —
     mastery learning, knowledge tracing, IRT/CAT, the 85% rule, LSAT format.
3. **The debate** ([`debate/`](debate)) — four personas (cognitive scientist,
   LSAT coach, systems engineer, student-advocate), two rounds:
   - `round1-*.md` — opening positions (champion / cut / merge).
   - `round2-*.md` — rebuttals + concessions that produced convergence.
4. **[`debate/DECISION.md`](debate/DECISION.md)** — the authoritative ruling:
   the final feature set, the evidence + effect sizes, the UX constraints, the
   pre-registered eval metric for each, **how the selection evolved**, the
   moderator rulings, and the cut/deferred list with reasons.

## What we shipped

The unifying idea: **capture *how* you got a question wrong, not just whether.**
Plain Anki and every LSAT competitor record only right/wrong; we store, per
answer, the **distractor you picked**, a one-tap **confidence**, and the
**timed-vs-untimed phase** — the keystone that unlocks everything else.

In the shipped app these mechanisms surface as **five prominent headline features**
(see [`../docs/Speedrun_AI_Features.md`](../docs/Speedrun_AI_Features.md)): (1) Reasoning-Primitive
Decks + Identification-First Study, (2) the Logic Drill Suite, (3) the Confidence &
Misconception Engine (the Rust queue), (4) the Timed Section Runner + Execution
Diagnostics, and (5) Three Honest Scores + Readiness. The table below is the
mechanism-level record; each row folds under one of those five.

| Feature | Code | Status |
|---|---|---|
| Keystone: per-answer `chosen`/`confidence`/`phase` store | `lsat/events.py`, `lsat/notetypes.py`, `qt/aqt/lsat_performance.py` | shipped |
| ZPD Daily Engine (~85%) | `lsat/selection.py` | shipped |
| Distractor-Reasoning: trap fingerprint + "which trap?" tap + queue boost | `lsat/error_patterns.py`, item template, `topic_weights_for_queue` | shipped |
| Calibration + Hypercorrection spaced queue | `lsat/models/calibration.py` | shipped |
| Blind-Review "Gap Map" + Choke/Pacing | `lsat/blind_review.py`, `lsat/pacing.py` | shipped |
| Fluency Gates (+ Structure Sprints) | `lsat/models/fluency.py` | shipped |
| Transfer Meter (report-only honesty layer) | `eval/transfer.py`, `struct.*` in taxonomy | shipped |
| Dashboard "How you get questions wrong" panels | `lsat/dashboard_data.py`, `ts/routes/lsat-dashboard/` | shipped |

**Deferred (gated), per the decision:** AI-generated spaced *distractor-rejection*
cards (gated on the checker's false-pass bar), Structure Twins (gated on the
Transfer Meter), a faithful full-section simulator (data-blocked), and BKT
(must beat the recency fold on held-out AUC). CDM/DKT and a daily 50%-difficulty
mini-CAT were **cut**.

**The honest claim:** measured single-digit-point gains on held-out, exam-style
items at equal study time — never "2 sigma." Every effect ships as a measured
`eval/` arm (synthetic learners now, real A/B later).

## Forward-looking research: AI features for faster prep

[`ai-features-for-faster-prep.md`](ai-features-for-faster-prep.md) is a separate,
forward-looking study (same multi-agent research→debate→red-team→critique method)
answering: *what LLM-powered features would help a candidate prep **faster**, without
breaking the honesty discipline?* It ranks six AI features by
`prep-speed × feasibility × honesty`, quantifies the honest per-feature speed ceiling
with cited effect sizes, red-teams each on six risk axes, and lays out a build roadmap —
including the one load-bearing unlock (the dead semantic-leakage signal in
`eval/leakage.py`). This is a **proposal/analysis doc**, not shipped code; the table above
remains the record of what is actually implemented.
