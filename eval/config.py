# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Pre-declared evaluation thresholds.

These are fixed in code BEFORE looking at results -- a cutoff chosen after
seeing results is not a cutoff. They are proposed defaults (per
``SKILL-lsat-eval.md``); tune and commit them before running ``make eval``.
"""

from __future__ import annotations

# Deterministic split / fitting seed; the split must be identical on every run.
RANDOM_SEED = 1234

# Step 1 -- memory calibration: expected calibration error must be at or below.
ECE_MAX = 0.05

# Step 2 -- performance must beat the memory-only baseline by this much AUC.
PERF_MIN_DELTA_AUC = 0.05

# Step 3 -- score mapping: never report a range tighter than the LSAT's own band.
SCORE_MIN_RANGE_POINTS = 3

# Leakage (7e): lexical tf-idf cosine at or above this is flagged; ANY leak fails.
LEAK_COSINE_MAX = 0.90
# Character-n-gram (shingle) Jaccard at or above this flags a reworded near-copy
# that the token-exact cosine misses (morphological variants / light synonym
# swaps that preserve word stems). A fully-synonymized paraphrase with no shared
# stems still needs a real semantic embedder -- see leakage.py's pluggable hook.
LEAK_FUZZY_MAX = 0.45

# AI card check (7f): a card enters the deck only if verdict == CORRECT_USEFUL.
CARD_CHECK_PASS_RATE_MIN = 0.70
CARD_CHECK_WRONG_RATE_MAX = 0.02

# The checker is itself validated against the gold set before we trust it.
CHECKER_FALSE_PASS_MAX = 0.02

# Choke-Index diagnostic validity (DECISION-round2 #24). The paired within-item
# estimator's bootstrap CI must cover the true per-student pressure penalty at
# least this often, and must NOT raise a confident-choke flag more than this
# fraction of the time when the true penalty is zero but the timed/untimed item
# pools are difficulty-mismatched (the exact confound the unpaired estimator
# falls for). Nominal 95%-CI targets.
CHOKE_CI_COVERAGE_MIN = 0.90
CHOKE_FALSE_POSITIVE_MAX = 0.05

# Fatigue Curve (DECISION-round2 #10): a fatigue-aware P(correct) model must beat
# the position-blind model on held-out late-session items by at least this AUC
# (with a bootstrap CI excluding 0) to claim the signal is real; else abstain.
FATIGUE_MIN_DELTA_AUC = 0.02

# Mastery-Growth Panel (DECISION-round3 #2) -- a HARD gate on the panel's honesty.
# On true-no-change synthetic learners the CI-gated panel must claim a direction
# (improved/slipped) no more than this fraction of the time (calibrated
# abstention), AND on true-improvement learners it must detect the rise at least
# this fraction of the time (otherwise the panel is enabled but useless). The
# panel ships ON only if both hold.
GROWTH_FALSE_DIRECTION_MAX = 0.05
GROWTH_DETECTION_MIN = 0.80

# Rush-Error Detector (DECISION-round3 #21) -- estimator-validity gate. On learners
# with a planted rush penalty the per-baseline detector must flag the problem at
# least this often (sensitivity); on naturally-fast-but-accurate learners (the
# confound a naive absolute-clock detector fails) its false-flag rate must stay at
# or below this AND be strictly below the naive detector's (it must earn its
# per-learner baseline).
RUSH_DETECT_MIN = 0.80
RUSH_FALSE_FLAG_MAX = 0.10

# Time-Leak Diagnostic (DECISION-round3 #5) -- reported validity targets (the arm
# is report-only). The reclaimable-seconds estimate must recover a real leak (its
# bootstrap CI excludes 0 on time-pressured learners) while flagging a truly
# WINNABLE item as unwinnable at most this often, and returning ~0 on a
# not-time-pressured null.
TRIAGE_FALSE_UNWINNABLE_MAX = 0.05

# Oracle-Verified Faded Worked Examples (research feature #1) -- HARD gate on the
# generate-with-a-proof safety property. The exact material-entailment oracle
# (lsat.conditional_chain.entails) must BLOCK every planted-wrong / fuzzed
# derivation: no derivation the gate ACCEPTS may correspond to a non-entailed
# goal, and a malicious LLM draft may never cause an unverified example to serve.
# A hallucinated step is admitted at most this fraction of the time (0 by
# construction -- the oracle is a decision procedure, not a heuristic).
WORKED_STEP_FALSE_PASS_MAX = 0.0

# Oracle-Proven "Skill or Luck?" Discrimination Twins (research follow-on) -- HARD
# gate on the twin safety property, cross-checked against an INDEPENDENT oracle
# (higher-cap Venn enumerator + a fresh truth-table). No served/enumerated twin
# may be mislabeled: its verdict must equal the independent re-derivation AND
# differ from the original item's verdict (a genuine discriminator). Mislabel rate
# is admitted at most this fraction (0 by construction -- the oracle decides).
EVIL_TWIN_FALSE_LABEL_MAX = 0.0

# First-Instinct Ledger (DECISION-round4 #17) -- estimator-validity gate on the
# answer-change diagnostic. On a 50/50 changer (changes equally wrong->right and
# right->wrong) it must claim a direction no more than this often (never fabricate
# "changing helps/hurts you"); on a planted ~2:1 wrong->right changer it must
# recover the direction (correct sign, CI excludes 0) at least this often.
ANSWER_CHANGE_FALSE_DIRECTION_MAX = 0.06
ANSWER_CHANGE_DETECTION_MIN = 0.80
