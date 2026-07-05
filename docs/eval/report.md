# Anki for LSAT -- evaluation report

_Generated 2026-07-05 04:05:14 (seed 1234; reproducible via `make eval`)._

**GATE OK** -- 0 hard gate(s) failed.

## Pre-declared thresholds

| threshold                 | value |
| ------------------------- | ----- |
| RANDOM_SEED               | 1234  |
| ECE_MAX                   | 0.05  |
| PERF_MIN_DELTA_AUC        | 0.05  |
| SCORE_MIN_RANGE_POINTS    | 3     |
| LEAK_COSINE_MAX           | 0.9   |
| CARD_CHECK_PASS_RATE_MIN  | 0.7   |
| CARD_CHECK_WRONG_RATE_MAX | 0.02  |
| CHECKER_FALSE_PASS_MAX    | 0.02  |

## Steps

| step                               | result | detail                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| split (report)                     | ----   | content-aware split: 40 train / 10 heldout (seed=1234); manifest.json written                                                                                                                                                                                                                                                           |
| calibration (gate)                 | PASS   | ECE=0.0198 (max 0.05); an overconfident predictor scores ECE=0.1097 and would fail                                                                                                                                                                                                                                                      |
| performance (gate)                 | PASS   | performance AUC 0.786 vs memory-only 0.685 (delta +0.101, min 0.05); null-signal control (difficulty removed) delta +0.000 < 0.05 -> gate has teeth                                                                                                                                                                                     |
| score_map (gate)                   | PASS   | projected 141 range 137-145 (>= +/-3); endpoints 120.0->180.0; gate-teeth: constant & inverted equating tables both fail responsive (False, False), shipped passes (True); method: Monte-Carlo raw->scaled via documented equating table                                                                                                |
| choke_validity (gate)              | PASS   | paired CI coverage 0.92 (min 0.9); false-positive under difficulty-mismatched pools: paired 0.03 (max 0.05) vs unpaired 1.00                                                                                                                                                                                                            |
| blind_review (report)              | ----   | routing recovers the true cause 0.93 of the time (95% CI 0.91-0.95, n=720); honest-mastery drop improves held-out Brier by +0.0117 (95% CI +0.0090..+0.0143: 0.2435 -> 0.2318); SYNTHETIC learners -- validates the mechanism, not a field result.                                                                                      |
| feedback (report)                  | ----   | held-out P(correct) at equal 1680s: ef 0.800 (84 items) vs kcr 0.793 (105 items) vs kr 0.781 (140 items); ef-kcr +0.007 (95% CI +0.007..+0.007) -> ship (CI excludes 0)                                                                                                                                                                 |
| exam_schedule (report)             | ----   | weighted exam-day retrievability at equal reviews (4/day x 28d, 60 cards): deadline 0.870 vs fixed 0.863; delta +0.007 (95% CI +0.006..+0.007) -> deadline-aware wins; daily-studier null delta +0.000 (95% CI +0.000..+0.000)                                                                                                          |
| fatigue (report)                   | ----   | held-out within-session AUC: fatigue-aware 0.651 vs position-blind 0.628; dAUC +0.024 (95% CI +0.005..+0.041; min 0.02) -> signal is real                                                                                                                                                                                               |
| adherence (report)                 | ----   | MECHANICS ONLY (unproven until a live cohort): planned-completion rate plan 0.66 vs no-plan 0.50; diff +0.159 (95% CI +0.141..+0.176, excludes 0=True); guardrail accuracy diff -0.007 (95% CI -0.021..+0.008, includes 0=True -> no score cannibalization)                                                                             |
| conditional (report)               | ----   | held-out P(correct) on conditional-tagged LR items at equal 60 events: drill 0.767 vs generic 0.680 vs plain 0.638; drill-generic +0.087 (95% CI +0.086..+0.088) -> ship (CI excludes 0)                                                                                                                                                |
| conditional_chain (report)         | ----   | held-out P(correct) on unseen 3+ arrow chain inferences at equal 60 events (24-item bank): drill 0.760 vs generic 0.648 vs plain 0.586; drill-generic +0.112 (95% CI +0.105..+0.119) -> ship (CI excludes 0)                                                                                                                            |
| quantifier (report)                | ----   | held-out P(correct) on quantifier judgments (novel terms) at equal 60 events: drill 0.767 vs generic 0.680 vs plain 0.638; drill-generic +0.087 (95% CI +0.086..+0.088) -> ship (CI excludes 0); SECONDARY speeded drill-generic +0.101 (95% CI +0.100..+0.101)                                                                         |
| growth (gate)                      | PASS   | true-no-change false-direction 0.033, difficulty-mix-drift false-direction 0.000 (both max 0.05); true-improvement detection 0.938 (min 0.8) -> panel ON                                                                                                                                                                                |
| rush (gate)                        | PASS   | planted-rush detection 0.870 (min 0.8); naturally-fast false-flag: per-baseline 0.013 (max 0.1) vs naive absolute-clock 0.860 -> valid (beats naive)                                                                                                                                                                                    |
| triage_leak (report)               | ----   | reclaimable seconds recover true wasted time: est 468s vs true 800s (recovery 58%); 95% CI 452-482s excludes 0; false-unwinnable 0.026 (max 0.05); true-leak-0 null mean 0.0s -> valid                                                                                                                                                  |
| stem_polarity (report)             | ----   | held-out P(correct) on unseen inverted-stem items at equal 60 events (24-item bank): drill 0.852 vs generic 0.738 vs plain 0.679; drill-generic +0.114 (95% CI +0.107..+0.122) -> ship (CI excludes 0); SECONDARY speeded drill-generic +0.148 (95% CI +0.141..+0.157)                                                                  |
| assumption_discrimination (report) | ----   | held-out four-cell sort accuracy (chance 0.25) at equal 60 events (24-item bank): drill 0.872 vs generic 0.769 vs plain 0.706; drill-generic +0.102 (95% CI +0.095..+0.110) -> ship (CI excludes 0)                                                                                                                                     |
| answer_change (gate)               | PASS   | 50/50-changer false-direction 0.050 (max 0.06); planted 2:1 detection 0.863 (min 0.8) -> ledger ON                                                                                                                                                                                                                                      |
| paraphrase (report)                | ----   | card recall 0.86 vs reworded-item accuracy 0.82 -> gap +0.04 (95% CI -0.05..+0.15) over 30 cards x2; per-topic gaps -0.11..+0.26; distance-graded companion: transfer step                                                                                                                                                              |
| transfer (report)                  | ----   | near-surface 0.75 vs far-surface 0.49 -> memorization gap +0.26 (95% CI +0.20..+0.32); transfer index 0.49; structure slope beta=-0.37 over 7 schemas, 1260 synthetic items [partial-transfer]                                                                                                                                          |
| leakage (gate)                     | PASS   | 0 leak(s) in 40x10 pairs; detector self-test OK (verbatim+reworded caught, unrelated clean)                                                                                                                                                                                                                                             |
| worked_example (gate)              | PASS   | oracle gate: planted false-pass 0/20, fuzz false-pass 0/3014 accepted (valid-walk coverage 3000/3000) (max 0.0); built 5 examples (round-trip=True, dnf-abstain=True, malicious-safe=True). REPORT arm (equal 900s): faded 0.5717 vs worked 0.5161 vs solve 0.4189; faded-worked +0.056 (95% CI +0.050..+0.061) -> ship (CI excludes 0) |
| evil_twin (gate)                   | PASS   | curated: 47 twins over 16 items, mislabel 0, non-flip 0, unverified 0 (indep. oracle cross-check); fuzz: 0 disagreements over 3512 independently-checked flips (max 0.0); malicious-safe=True. LLM does inert targeting/nouns; the oracle proves every verdict.                                                                         |
| card_check (gate)                  | PASS   | counts {'CORRECT_USEFUL': 49, 'WRONG': 0, 'CORRECT_BUT_BAD_TEACHING': 0} pass_rate=1.0 wrong_rate=0.0 checker_false_pass=0.0 model=offline-rule-based                                                                                                                                                                                   |
| baselines (report)                 | ----   | NOT statistically distinguishable on this query set: reciprocal_rank 0.9238 vs 0.9162 (P@3 0.3519 vs 0.3333); paired bootstrap 95% CI on mean diff [0.0, 0.0222] includes 0 -- an honest negative. A real semantic embedder (not this lexical TF-IDF stand-in) would be needed to win decisively.                                       |

## Calibration reliability diagram

| bin     | n   | predicted | observed |
| ------- | --- | --------- | -------- |
| 0.0-0.1 | 198 | 0.054     | 0.056    |
| 0.1-0.2 | 194 | 0.152     | 0.129    |
| 0.2-0.3 | 186 | 0.25      | 0.172    |
| 0.3-0.4 | 196 | 0.347     | 0.352    |
| 0.4-0.5 | 217 | 0.45      | 0.456    |
| 0.5-0.6 | 205 | 0.551     | 0.566    |
| 0.6-0.7 | 198 | 0.647     | 0.657    |
| 0.7-0.8 | 197 | 0.749     | 0.701    |
| 0.8-0.9 | 191 | 0.844     | 0.832    |
| 0.9-1.0 | 218 | 0.95      | 0.945    |

## What didn't work / honest negatives

- All step inputs are **seeded synthetic data** -- there are no real students yet. The numbers demonstrate the metric + gate mechanics, not field performance; real held-out reviews/items would replace the generators unchanged.
- The gate has teeth: an **overconfident** predictor scores ECE=0.1097 (> 0.05) and would fail calibration, vs the calibrated model's 0.0198.
- The paraphrase gap (0.043) is driven by a **modeled** recognition->application penalty; with real reworded items it may shrink. A near-zero gap would mean the performance model is copying the memory model -- reported either way.
- Retrieval: the offline TF-IDF embedder did **not** beat BM25 here (0.3519 vs 0.3333) -- an honest negative; a real semantic embedder plugs in to win.
