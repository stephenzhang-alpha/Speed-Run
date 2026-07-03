# Research & Debate Brief — Novel, Evidence-Based LSAT Prep Features

## Mission

We are turning an **Anki fork into a uniquely powerful LSAT preparation app** (desktop).
We want a small set of **genuinely novel features grounded in learning theory** that make
this software different from (a) plain Anki and (b) every other LSAT prep product.

Two-stage process:
1. **Research** (you, if you are a research agent): find real, cited evidence from
   learning science + LSAT pedagogy and propose novel features.
2. **Debate** (later agents): argue the proposals against each other, refine, and select.

## The LSAT (verify current facts via web search — the exam changed recently)

- Scored **120–180**. Heavily **timed** (speed–accuracy tradeoff matters enormously).
- Sections are **Logical Reasoning (LR)** and **Reading Comprehension (RC)**. NOTE: the
  **Analytical Reasoning ("Logic Games") section was removed (Aug 2024)** and replaced with
  an additional scored LR section — **verify this and the current format via web search**.
- LR is the majority of the test. It is a **transfer test**: you cannot memorize answers;
  you must recognize **argument structure** (assumption, flaw, strengthen/weaken, parallel
  reasoning, principle, etc.) across arbitrary surface topics.
- Success depends on: pattern/schema recognition, eliminating trap answers, calibration
  (knowing when you're actually right), and pacing under time pressure.

## What the app ALREADY has (do NOT re-propose these — propose things BEYOND them)

Tech stack: Rust core (`rslib/`), Python lib (`pylib/anki`, `lsat/` package), Qt GUI
(`qt/aqt`), SvelteKit dashboard (`ts/routes/lsat-dashboard`), protobuf RPC, FSRS scheduler.

Already built (in `lsat/`):
- **FSRS spaced repetition** (Anki native) + per-topic **memory model** (`lsat/models/memory.py`).
- **Question-type interleaving** toggle (`lsat/interleaving.py`) — interleaved vs blocked order.
- **Points-at-stake queue** (Rust RPC) — prioritizes cards by weighted "points at stake".
- **Performance model** — Rasch/logistic P(correct) per topic (`lsat/models/performance.py`).
- **Readiness model** — Monte-Carlo projected 120–180 score with intervals (`readiness.py`).
- **Append-only event log** of graded answers with latency (`lsat/events.py`, HLC-ordered).
- **LSAT notetypes**: `LSAT Card` (concept), `LSAT Item` (multiple-choice, captures the
  chosen answer + latency via a template->pycmd hook), `LSAT PerformanceEvent`.
- **AI card pipeline** — LLM generator + independent checker with cited source spans
  (`lsat/ai/`), plus BM25 vs embedding retrieval (`lsat/retrieval.py`).
- **Dashboard** (Svelte + Qt) showing memory/performance/readiness/coverage.
- **Taxonomy** of skills/weights/give-up rules (`lsat-taxonomy.yaml`).

**Data available to any new feature**: per-answer correctness + latency + chosen option
(events log), FSRS memory state + review history (revlog), per-topic tags
(`lsat::lr::weaken` etc.), the AI pipeline (can generate/transform items), the dashboard.

## What "novel" means here

A feature is novel if it is NOT just spacing/interleaving/basic IRT (we have those). Strong
directions tend to involve: **metacognition/calibration**, **transfer/schema abstraction**,
**distractor/error reasoning**, **self-explanation / worked-example fading**, **adaptive
pacing under time pressure**, **error-pattern (reasoning-bug) diagnosis**, **feedback-timing
manipulation**, **successive relearning**, **contrasting cases / analogical comparison**.

## Research rules (STRICT)

1. **Use web search / fetching** to find REAL sources. Every empirical claim needs a real
   citation you actually found: **Author(s), Year, Title, Venue/Journal, and a URL**.
2. **Report specific evidence**: effect sizes (d/g), study design, sample, replication
   status. Quote a number when you can.
3. **Rate evidence strength** for each claim/feature: `strong` (meta-analytic/replicated),
   `moderate`, `weak`, or `contested`.
4. **No pseudoscience.** Do NOT propose debunked ideas (e.g., "learning styles"). If a
   popular idea is weak/debunked, say so and warn against it.
5. Prefer **primary sources and meta-analyses** over blogs. Blogs/secondary sources are ok
   for LSAT-format facts but flag them.
6. Tie every proposal to **LSAT specifically** and to **our stack** (which layer/data).
7. Be honest about **weaknesses / failure modes** — the debate will attack them.

## Deliverable (research agents)

Write your file `research/NN-<lens>.md` with:
- **Lens & scope** (1 short paragraph).
- **Key findings** — bulleted, each with citation(s), a number/effect size, and an evidence
  rating. Include at least one "myth/that-doesn't-work" warning relevant to your lens.
- **Proposed features** — 4–6 proposals. For each:
  - **Name** + one-line pitch.
  - **Mechanism** (what the user actually does / sees).
  - **Theory + citations** (why it should work; evidence rating).
  - **LSAT fit** (why it matters for this exam).
  - **Implementability** in our stack (which files/layers; what data it uses; rough effort S/M/L).
  - **Novelty** (why it's beyond what we/Anki already do; do any competitors do it?).
  - **Risks / failure modes.**
- **Sources** — a numbered reference list with URLs.
