# Model description pages (Anki for LSAT)

All three scores are **local, offline, and calibratable** (no LLM dependency),
each shown **with a range**, and each **abstains** under the honesty contract
rather than fabricate a number. Sources: `lsat/models/`, `lsat/events.py`,
`lsat/dashboard_data.py`, `rslib/src/scheduler/points_at_stake.rs`.

---

## 1. Memory — "can I reproduce this taught judgment right now?"

- **Definition:** per-topic probability of recall, read from Anki's **FSRS**
  retrievability (we do not reinvent memory estimation).
- **Method** (`lsat/models/memory.py`): for each taxonomy topic, gather the
  reviewed cards' FSRS recall via the engine's `extract_fsrs_retrievability` SQL
  function, clamp each to `[0,1]` (a probability), and take the mean. The range
  is a **Wilson score interval** that widens honestly with little data. Recall is
  clamped and non-finite values dropped, so memory % can never exceed its range.
- **Give-up:** a topic with fewer than **10** reviews shows *"not enough evidence
  yet,"* never a score.
- **Output:** `memory % (low–high) from N cards`, per topic + an exam-weighted
  overall.

## 2. Performance — "will I get a new, exam-style item right?"

- **Definition:** P(correct) on a held-out item, including items never seen.
- **Model** (`lsat/models/performance.py`): a **Rasch-style logistic GLM**

  ```text
  P(correct) = sigmoid(ability + w0 + w1·difficulty + w2·timing_z)
  ```

  where `ability` is the topic's shrunk log-odds mastery and enters at a **fixed
  coefficient of 1** (a GLM offset), so per-topic ordering follows ability and
  can never invert; only the global intercept and the difficulty/timing effects
  are fit (ridge-regularised IRLS). Ability shrinks toward the global rate
  **clamped to [0.15, 0.85]**, so sparse or degenerate data can't be
  overconfident. Inputs (PRD §5.2): skill mastery, item difficulty
  (easy/medium/hard ordinal), recent timing, coverage.
- **Display:** per topic, `p ± interval` (e.g. *62% ± 7% on Weaken*); the width
  reflects graded-evidence volume.
- **Calibration:** `fit_performance_model` reports **k-fold held-out** ECE /
  Brier / log-loss (ability recomputed from training folds, so no event leaks its
  own label). The readiness give-up rule consumes this ECE.
- **Eval gate:** must beat a memory-only baseline by **AUC ≥ 0.05** (`make eval`).

## 3. Readiness — "what's my projected LSAT score?"

- **Definition:** a projected scaled **120–180** score with a range and a
  confidence note.
- **Method** (`lsat/models/readiness.py`): **Monte-Carlo** per-item P(correct)
  across the ~76 scored questions (≈50 LR + 26 RC, weighted by the taxonomy) →
  a raw-score distribution → map each raw to scaled via a **documented
  equating-style table** (`raw_to_scaled`, a labelled approximation, never a
  precise conversion) → report the distribution.
- **Range:** never tighter than **±3** (the LSAT's own band). When the band would
  clip at 120/180 we shift the window inward so the reported width stays ≥ ±3.
- **Honesty contract (hard gate):** the widget renders a number **only** when all
  eight fields are populated — point estimate, range, % covered, confidence +
  reason, last-updated, top reasons (skills pulling up/down), the single best
  next thing to study, and the **track record of past projections**. Any missing
  field → abstain. Past projections are logged append-only in collection config
  (`lsat/models/projections.py`).
- **Give-up:** no number until ≥ 150 graded items, ≥ 60% LR coverage + ≥ 1 each
  RC type, ≥ 40 timed items, and held-out ECE ≤ 0.05.

## 4. The points-at-stake queue (Rust engine change)

- **What:** a read-only backend RPC ordering due cards by
  `points = weight·(1 − mastery)`, `mastery = 0.5·recall + 0.5·perf_mastery`.
  Surfaces the single most valuable card. Recall is FSRS retrievability (0 = no
  memory state → maximally weak); weight/perf_mastery come from the taxonomy per
  request. Full note: `lsat/docs/points-at-stake-rust-change.md`.

## 5. AI card pipeline (generator + independent checker)

- **Generator** (`lsat/ai/generator.py`): emits cited cards; a **programmatic
  source-span check** drops any card whose `source_quote` is not verbatim in the
  chunk (kills hallucinated/injected citations); defensive JSON parse fails the
  whole batch on bad output.
- **Checker** (`lsat/ai/checker.py`): an **independent** LLM-as-judge (separate
  call, own rubric, never sees the generator's rationale) with three verdicts;
  only `CORRECT_USEFUL` is admitted. Validated against the 50-pair gold set for
  **false-pass rate** before it is trusted as a gate.
- **Injection defense:** the source is always wrapped as untrusted data; the
  offline stand-in checker is purely rule-based and cannot follow embedded
  instructions.
- **Promotion:** generated cards sit in staging; they reach the live deck only
  when every card is `CORRECT_USEFUL` **and** the batch clears the pass-rate /
  wrong-rate gate. **Graceful degradation:** if the AI is unavailable, the batch
  is skipped and human cards keep serving — the review loop never blocks.
- **Retrieval** (`lsat/retrieval.py`): BM25 vs an embedding retriever, reported
  side-by-side with precision@k (`eval/baselines.py`).

## 6. Interleaving study option

- `lsat/interleaving.py`: an option to **interleave** LR question types
  (round-robin) vs **block** them; the points-at-stake queue chooses *which*
  cards, this controls their *order*. The 3-arm ablation (`eval/ablation.py`,
  `make ablation`) measures its effect at equal study time — see the ablation
  output for the primary metric with a bootstrap range.

## The honesty contract, in one line

Every score shows a range, abstains when evidence is thin (per the give-up
rules), and is validated on held-out data by `make eval` before it is trusted —
generated content and the readiness number are enabled only when the gate passes.
