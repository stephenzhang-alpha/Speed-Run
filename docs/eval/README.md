# Evaluation outputs (committed for review)

These are the **actual committed outputs** of the reproducible eval harness, so the
review side can be verified without running anything. Regenerate them any time with:

```bash
make eval        # == out/pyenv/bin/python -m eval.run   (writes out/eval/*, exits non-zero on any gate fail)
cp out/eval/{report.md,metrics.json,manifest.json} docs/eval/   # refresh this snapshot
```

- **[`report.md`](report.md)** — the human-readable report: pre-declared thresholds, every
  gate/arm with its result + 95% CI, the calibration reliability diagram, and an honest
  "what didn't work" section. Generated `2026-07-04` at seed `1234`.
- **[`metrics.json`](metrics.json)** — the machine-readable per-arm metrics (26 arms).
- **[`manifest.json`](manifest.json)** — the content-aware train/held-out split manifest
  (40 train / 10 held-out at seed 1234), so the split is auditable and leak-checkable.
- **[`console.txt`](console.txt)** — the raw run console.

**Headline: `GATE OK` — 0 of the hard gates failed.** Gates: calibration (ECE 0.0198 ≤ 0.05),
performance (AUC Δ +0.101 ≥ 0.05), score_map (range ±4 ≥ ±3), choke_validity, growth, rush,
answer_change, leakage, worked_example (oracle false-pass 0/3014), evil_twin (0/3512),
card_check (checker false-pass 0.0).

## Baseline output (retrieval — `baselines` arm)

An **honest negative**, reported as-is:

```
metric: reciprocal_rank over n_queries=36, k=3
  embedding (offline TF-IDF stand-in): reciprocal_rank 0.9238, P@3 0.3519
  BM25:                                reciprocal_rank 0.9162, P@3 0.3333
  mean_diff 0.0076; paired bootstrap 95% CI [0.0, 0.0222]  -> includes 0
  embedding_wins: false  ->  NOT statistically distinguishable on this query set.
```

The lexical TF-IDF stand-in does **not** beat BM25 decisively; a real semantic embedder
would be needed to win. Reported rather than hidden — the CI includes 0.

## Leakage output (`leakage` gate)

```
n_train 40, n_heldout 10  ->  40x10 = 400 train/held-out pairs checked
cosine_threshold 0.9, fuzzy_threshold 0.45
n_flagged: 0        (no held-out item is a near-duplicate of any training item)
gate: PASS
detector self-test: OK
  verbatim duplicate      -> caught
  reworded duplicate      -> caught (cosine 0.481, fuzzy 0.472, shingle)
  unrelated item          -> not flagged
```

The gate has teeth (the self-test proves the detector catches both verbatim and reworded
near-duplicates and leaves unrelated items alone), and **0 leaks** were found in the split.

> All eval inputs are **seeded synthetic** data — these numbers demonstrate the metric + gate
> mechanics, not field performance. Real held-out reviews/items drop into the same generators
> unchanged. See the "What didn't work / honest negatives" section of `report.md`.
