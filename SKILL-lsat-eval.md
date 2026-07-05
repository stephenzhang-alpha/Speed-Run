---
name: anki-lsat-eval
description: "Use this skill whenever building, running, or reporting the model evaluations for the Anki-for-LSAT project: held-out testing, memory calibration (Brier/log loss/ECE, reliability diagram), performance accuracy on held-out questions, score-mapping ranges, the paraphrase test, the leakage check, the AI card check counts, beat-the-baseline comparisons, the 'eval runs before students see anything' gate, or making any of these reproducible (a one-command `make eval`). Read this BEFORE writing eval code or reporting metrics. Pairs with docs/ai-card-pipeline.md (card-check counts) and the PRD (§12)."
---

# Held-out evaluation + leakage check (reproducible)

This is the harness that earns "Score accuracy and honest uncertainty" (20%) and "Fair tests others can re-run" (12%). The governing principle from the brief: we **grade the steps of the bridge, not a fabricated final score**. Reproducibility is non-negotiable — someone else must run one command and get the same numbers.

## Suggested layout

```
eval/
  config.py            # RANDOM_SEED, thresholds (all stated here, see below)
  split.py             # deterministic, content-aware train/heldout split
  calibration.py       # Step 1: memory calibration
  performance.py       # Step 2: held-out question accuracy
  score_map.py         # Step 3: raw -> scaled distribution + range
  paraphrase.py        # the paraphrase gap (7d)
  leakage.py           # the leakage check (7e)
  card_check.py        # the AI card-check counts (7f) — calls ai-card-pipeline
  baselines.py         # beat keyword/vector
  run.py               # runs everything, writes report, EXITS NON-ZERO on any gate fail
data/
  train/  heldout/     # heldout is touched ONLY by eval
  manifest.json        # sha256 of every item + which split it's in
out/eval/              # plots, metrics.json, report.md
```

Entry point (mirrors `make bench`):

```bash
make eval       # -> python -m eval.run
```

## Pre-declared thresholds (state in eval/config.py BEFORE looking at results)

These are proposed defaults — tune and **commit them before running**, because a cutoff chosen after seeing results is not a cutoff.

- `RANDOM_SEED = 1234`
- Memory calibration: `ECE_MAX = 0.05`
- Performance: must beat the memory-only baseline by `PERF_MIN_DELTA_AUC = 0.05`
- Score range: minimum reported width `±3` (the LSAT's own band; never tighter)
- Leakage: `LEAK_COSINE_MAX = 0.90` (above → flagged); **any** leak fails the build
- Card check (7f): cutoff = `verdict == CORRECT_USEFUL`; batch passes if `pass_rate >= 0.70` and `wrong_rate <= 0.02`
- Checker self-validation: checker `false_pass_rate <= 0.02` on the gold set

## The split contract (do this first — it prevents the silent failure mode)

- **Deterministic:** fixed `RANDOM_SEED`; the split is identical on every run.
- **Content-aware, not row-id-based.** Group items by their underlying argument/source so that **paraphrases of the same item land on the same side**. A naive per-row split leaks reworded duplicates across the boundary and inflates every downstream number.
- **Heldout is sacred:** training, FSRS fitting, and card generation never read `data/heldout/`. Only the eval reads it.
- Write `manifest.json` with a sha256 of each item and its split, so reviewers can verify nothing moved.

## Step 1 — Memory calibration (required)

On held-out reviews, does predicted recall match observed recall? When the model says 80%, ~80% should recall.

- Metrics: **Brier score** = mean((p − outcome)²); **log loss** = −mean(y·ln p + (1−y)·ln(1−p)); **ECE** over 10 probability bins.
- Output a **reliability diagram** (predicted vs observed per bin, with the diagonal).
- Gate: `ECE <= ECE_MAX`.
- LSAT caveat to state in the report: a calibrated memory model is necessary but, on a skills test, nearly orthogonal to the score. It's the floor, not the result.

## Step 2 — Performance accuracy (required)

Predict P(correct) on **held-out LSAT-style questions** from skill mastery + item difficulty + recent timing + coverage.

- Report accuracy, AUC, and Brier — **broken out by topic** so thin-coverage skills are visible.
- Compare against a **memory-only baseline** (predict from FSRS recall alone). Gate: performance must beat it by `PERF_MIN_DELTA_AUC`. If it doesn't, you've built a memory model with extra steps — report that honestly.

## Step 3 — Score mapping (required)

Turn per-item P(correct) into a 120–180 projection.

- Monte-Carlo: sample correctness per item across the ~76 scored questions (≈2 LR + 1 RC, weighted by the taxonomy) over many trials → distribution of raw scores → map each raw to scaled via the documented equating-style table → report the **point estimate + range** (width ≥ ±3).
- Document the mapping method in `out/eval/report.md`. If any real practice-test scores exist, sanity-check against them (this is the Step-4 bonus, not required).

## The paraphrase test (7d) — the bridge proof

- 30 cards × 2 reworded LSAT-style items each. Compare **card recall** vs **accuracy on the reworded items**, per skill and overall.
- Report the **gap**. On the LSAT we expect a sizable gap (recognizing a rule ≠ applying it under time). A near-zero gap means the performance model is copying the memory model. **Report the result either way** — "no gap here" is a real, scoring finding, not something to hide.

## The leakage check (7e) — a hard gate

Scan everything used for training/generation for any held-out item or near-copy:

1. **Normalized match:** lowercase, strip punctuation/whitespace → exact and substring matches.
2. **Embedding match:** cosine ≥ `LEAK_COSINE_MAX` → flag (catches paraphrases, the real LSAT risk).

Output flagged pairs. **Any flagged leak fails the build** (leaked test data zeros that score). The goal is to show the result is clean.

## The AI card check (7f)

- Build/keep the **gold set of 50** Q&A pairs (known-correct; original/licensed, not LSAC).
- **Validate the checker first:** run it over the gold set, report agreement and especially `false_pass_rate`; gate at `false_pass_rate <= 0.02`. A gate you haven't validated isn't a gate.
- Generate 50 cards from one source, run the checker, report the three counts (CORRECT_USEFUL / WRONG / CORRECT_BUT_BAD_TEACHING) with the pre-declared cutoff; **block** anything not CORRECT_USEFUL. See `docs/ai-card-pipeline.md`.

## Beat-the-baseline (required side-by-side)

- Retrieval ("drill my weakest skill"): embedding vs **BM25/keyword** on the same queries → precision@k / relevance. AI must win.
- Optionally, AI vs template card generation on three-count pass-rate. Report numbers; the AI must beat the simpler method.

## The gate (the "before students see anything" requirement)

`eval/run.py` runs **all** of the above and **exits non-zero** if any gate fails: calibration above `ECE_MAX`, performance below the baseline delta, **any** leakage, card pass-rate/wrong-rate outside cutoff, or checker false-pass too high. Generated content and the readiness display are enabled **only when the gate passes**. Wire this into CI so a regression can't ship.

## Reproducibility checklist

- Pinned `RANDOM_SEED` and pinned dependencies; `manifest.json` hashes committed.
- One command (`make eval`) reproduces every number, plot, and `report.md`.
- `report.md` includes **results that did not work** (a flat paraphrase gap, an uncalibrated topic, a baseline that wasn't beaten). Honest negative results score well; "feels better" scores nothing.

## Definition of done (maps to the brief)

- **Friday:** the eval runs before any generated card is shown; accuracy + wrong-answer rate on a held-out set with the cutoff; the baseline side-by-side.
- **Sunday:** calibration chart + Brier/log loss on held-out reviews; performance accuracy on held-out questions; score-mapping method + range; the paraphrase gap; a clean leakage result; the three card-check counts; and `report.md` including what didn't work.
