# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The pre-registered ablation (spec section 8): B3, the misconception queue.

Chosen feature: the **misconception-priority review queue** (SPOV 2 / B3). It
isolates cleanly as a single scheduler flag (in the app:
``lsat.events.set_misconception_queue`` -- on = confident-wrong weighting + the
mandatory spaced re-test; off = errors weighted uniformly), and it is the same
code path as the queue change, so the effort compounds.

PRE-REGISTERED CLAIM (stated before running): *prioritizing high-confidence
errors raises accuracy on related novel questions at equal study time.* The
result is reported with a range **even if the feature makes no difference** --
a fair test that could have failed is the deliverable.

Arms (identical review budget each):
  * full            = confident-wrong items prioritized + spaced re-test
                      (re-tests consume the same budget; nothing is free)
  * feature-off     = same app, misconception weighting off -- all *missed*
                      items reviewed uniformly, no deliberate re-test
  * plain           = uniform selection over everything (vanilla Anki)

Primary metric = held-out P(correct) on unseen related items, per arm with a
bootstrap 95% range across paired synthetic learners.

SIMULATION CAVEAT: there are no real students. The learner model is synthetic
and documented: misconceptions are buggy rules that (a) fire confidently on
related items, (b) are fixed well by targeted corrective study (hypercorrection
-- Butterfield & Metcalfe 2001), and (c) RETURN unless re-tested (Butler, Fazio
& Marsh 2011; the re-test blocks the return, Metcalfe & Miele 2014). All rates
are explicit parameters below; zero them and the arms tie. This proves the
*methodology* (equal-time, 3-arm, primary-metric-with-range), not a field
result.

``run_interleaving()`` keeps the earlier interleaving simulation available as a
secondary analysis; per the spec, interleaving is NOT a second ablation -- its
effect is demonstrated through the paraphrase gap (C2) instead. It also carries a
secondary ``+zpd`` arm (a ZPD ~0.85 difficulty re-rank at equal study time,
reported alongside the selection effect) -- likewise a simulation, not the
pre-registered ablation.
"""

from __future__ import annotations

import math
import random
from typing import Any

from eval import config
from eval.metrics import bootstrap_ci
from lsat.interleaving import blocked_order, interleaved_order, interleaving_degree
from lsat.selection import zpd_weight

STUDY_EVENTS = 120  # equal study-time budget per arm
N_LEARNERS = 400
GAIN = 0.5  # ability gain per study event, with diminishing returns (see _simulate)
INTERLEAVE_BONUS = (
    0.5  # transfer bonus (logit) from fully-interleaved practice (0 = none)
)
# Secondary +zpd arm: practicing in the ~tau (~0.85) desirable-difficulty band
# retains/transfers better (Metcalfe & Kornell 2005; Wilson et al. 2019). Modeled
# as a transfer bonus (logit) scaled by how in-band the study sat and by a
# per-learner responsiveness spread (heterogeneous benefit -> a real CI). 0 = off.
ZPD_BONUS = 0.2
ZPD_SENS_SPREAD = 0.6
DIFFICULTIES = (-1.0, 0.0, 1.0)
ARMS = ("full", "interleaving-off", "plain", "+zpd")

# -- B3 misconception-queue ablation parameters (all explicit) ---------------
B3_ARMS = ("full", "feature-off", "plain")
N_MISCONCEPTIONS = 6  # buggy rules per learner
MISCONCEPTION_SEVERITY = (0.10, 0.25)  # share of related items a bug corrupts
# EQUAL STUDY TIME: every arm spends exactly this many events on its error-review
# phase (the full arm on confident-wrong fixes + mandatory re-tests, the others on
# uniform review-of-misses), so the remaining generic-study budget is identical
# across arms. If the arms spent different amounts here, the full arm would get
# extra ability-building generic study and the ablation would report a
# budget-artifact effect even when the misconception mechanic is inert.
ERROR_REVIEW_BUDGET = 12
P_FIX = 0.75  # hypercorrection: targeted corrective study fixes a confident bug
P_RELAPSE = 0.40  # fixed-but-not-retested bugs RETURN (Butler/Fazio/Marsh 2011)
P_RELAPSE_AFTER_RETEST = 0.05  # the spaced re-test blocks the return (M&M 2014)


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _lr_types() -> list[str]:
    from lsat.taxonomy import load_taxonomy

    tax = load_taxonomy()
    return [t.id for t in tax.question_types if t.section == "lr"]


def _select(
    arm: str, types: list[str], start: dict[str, float], n: int, rng: random.Random
) -> tuple[list[str], float]:
    """Which types get studied, and how in-band (~tau) that study sat.

    points-at-stake studies the currently-weakest type (rebalances coverage);
    plain Anki selects uniformly at random. ``+zpd`` shares points-at-stake's
    weakest-first coverage (so study time is equal) -- the ZPD re-rank changes
    only the *difficulty* surfaced within a type, captured by ``zpd_align``: the
    mean, over the session, of the best ~tau fit reachable across the difficulty
    pool. Only the ``+zpd`` arm consumes ``zpd_align``; it is inert otherwise.
    """
    scratch = dict(start)
    seq: list[str] = []
    zpd_align = 0.0
    for _ in range(n):
        if arm in ("full", "interleaving-off", "+zpd"):
            chosen = min(types, key=lambda t: scratch[t])
        else:
            chosen = rng.choice(types)
        seq.append(chosen)
        # How close to the ~tau band the ZPD re-rank could surface this type now
        # (best fit across the difficulty pool). Uses NO rng, so the other arms'
        # streams -- hence their results -- are unchanged.
        zpd_align += max(
            zpd_weight(_sigmoid(scratch[chosen] - d)) for d in DIFFICULTIES
        )
        scratch[chosen] += GAIN * (1.0 - _sigmoid(scratch[chosen]))
    return seq, (zpd_align / n if n else 0.0)


def _simulate(seed: int, arm: str, types: list[str]) -> float:
    rng = random.Random(seed)
    ability = {t: rng.uniform(-1.5, -0.5) for t in types}  # start weak, varied
    seq, zpd_align = _select(arm, types, ability, STUDY_EVENTS, rng)

    # Order the session; the interleaving benefit is tied to the ACTUAL order
    # produced by the shared ordering functions (measured degree), not a flag.
    # +zpd layers its ZPD difficulty re-rank on top of full's interleaved order.
    tagged = [(t, t) for t in seq]
    ordered = (
        interleaved_order(tagged) if arm in ("full", "+zpd") else blocked_order(tagged)
    )

    # Selection (counts) drives per-type ability with DIMINISHING RETURNS, so
    # studying the weakest type is more efficient than re-studying an already
    # strong one -- this is where points-at-stake beats uniform selection.
    for t in seq:
        ability[t] += GAIN * (1.0 - _sigmoid(ability[t]))

    # Interleaving adds a transfer bonus on held-out items, proportional to how
    # interleaved the actual study order was (0 for blocked practice).
    bonus = INTERLEAVE_BONUS * interleaving_degree(ordered)
    if arm == "+zpd":
        # ZPD (~tau) re-rank: in-band practice retains/transfers better. Credited
        # as a transfer bonus, scaled by the session's in-band alignment and a
        # per-learner responsiveness (heterogeneous benefit). Drawn HERE (only for
        # +zpd, whose selection uses no rng) so no other arm's stream shifts.
        zpd_sensitivity = rng.uniform(1.0 - ZPD_SENS_SPREAD, 1.0 + ZPD_SENS_SPREAD)
        bonus += ZPD_BONUS * zpd_sensitivity * zpd_align
    accs = [_sigmoid(ability[t] + bonus - d) for t in types for d in DIFFICULTIES]
    return sum(accs) / len(accs)


def run_interleaving(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    """Secondary analysis: the earlier 3-arm interleaving simulation (kept for
    reference; interleaving's effect is demonstrated via the paraphrase gap)."""
    types = _lr_types()
    per_arm: dict[str, list[float]] = {arm: [] for arm in ARMS}
    for i in range(N_LEARNERS):
        # Paired: the same learner (seed) is run through every arm.
        for arm in ARMS:
            per_arm[arm].append(_simulate(seed + i, arm, types))

    arms: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        vals = per_arm[arm]
        mean = sum(vals) / len(vals)
        lo, hi = bootstrap_ci(vals, seed)
        arms[arm] = {"mean": round(mean, 4), "ci": [round(lo, 4), round(hi, 4)]}

    interleave_effect = arms["full"]["mean"] - arms["interleaving-off"]["mean"]
    selection_effect = arms["interleaving-off"]["mean"] - arms["plain"]["mean"]
    # +zpd is layered on full; its effect gets its own paired bootstrap range.
    zpd_diffs = [z - f for z, f in zip(per_arm["+zpd"], per_arm["full"])]
    zpd_lo, zpd_hi = bootstrap_ci(zpd_diffs, seed)
    zpd_effect = arms["+zpd"]["mean"] - arms["full"]["mean"]
    return {
        "name": "ablation-interleaving",
        "primary_metric": "held-out P(correct) on unseen LR items (transfer)",
        "study_events_per_arm": STUDY_EVENTS,
        "n_learners": N_LEARNERS,
        "n_lr_types": len(types),
        "interleave_bonus_param": INTERLEAVE_BONUS,
        "zpd_bonus_param": ZPD_BONUS,
        "arms": arms,
        "interleaving_effect": round(interleave_effect, 4),
        "selection_effect": round(selection_effect, 4),
        "zpd_effect": round(zpd_effect, 4),
        "zpd_effect_ci": [round(zpd_lo, 4), round(zpd_hi, 4)],
    }


# -- the pre-registered B3 ablation ------------------------------------------


def _simulate_b3(seed: int, arm: str, types: list[str]) -> float:
    """One synthetic learner through one arm at an equal study budget.

    Bugs (misconceptions) corrupt a share of held-out items on their type until
    fixed; targeted corrective study fixes them at ``P_FIX`` (hypercorrection);
    fixed bugs relapse at ``P_RELAPSE`` unless deliberately re-tested
    (``P_RELAPSE_AFTER_RETEST``). Every corrective review and every re-test
    consumes the same budget generic study would -- prioritizing errors is a
    trade, not a free lunch.
    """
    rng = random.Random(seed)
    ability = {t: rng.uniform(-1.5, -0.5) for t in types}
    bugs: list[dict[str, Any]] = [
        {
            "type": rng.choice(types),
            "severity": rng.uniform(*MISCONCEPTION_SEVERITY),
            "active": True,
            "fixed_once": False,
            "retested": False,
        }
        for _ in range(N_MISCONCEPTIONS)
    ]

    # Every arm spends EXACTLY ERROR_REVIEW_BUDGET events on its error-review
    # phase, so the generic-study budget below is identical across arms (equal
    # study time). The arms differ only in WHAT those events do.
    budget = STUDY_EVENTS - ERROR_REVIEW_BUDGET
    if arm == "full":
        # The misconception queue leads with confident-wrong items, then
        # schedules each fix's mandatory spaced re-test. Both cost from the same
        # fixed phase budget; leftover phase budget (if fewer bugs than the
        # budget) is spent with no effect -- the honest cost of the trade.
        spent = 0
        for bug in bugs:
            if spent >= ERROR_REVIEW_BUDGET:
                break
            spent += 1
            if rng.random() < P_FIX:
                bug["active"] = False
                bug["fixed_once"] = True
        for bug in bugs:
            if spent >= ERROR_REVIEW_BUDGET:
                break
            if bug["fixed_once"] and not bug["retested"]:
                spent += 1
                bug["retested"] = True
    else:
        # Errors weighted uniformly: a study event hits a given bug's item only
        # when uniform selection happens to land on it. feature-off reviews
        # only *missed* items (small pool); plain reviews everything (large
        # pool). No deliberate re-test in either.
        pool = 20 if arm == "feature-off" else 40
        for _ in range(ERROR_REVIEW_BUDGET):
            active = [b for b in bugs if b["active"]]
            if not active:
                break
            if rng.random() < len(active) / pool:
                bug = rng.choice(active)
                if rng.random() < P_FIX:
                    bug["active"] = False
                    bug["fixed_once"] = True

    # Remaining budget = generic study on the weakest types (all arms alike).
    for _ in range(max(0, budget)):
        weakest = min(types, key=lambda t: ability[t])
        ability[weakest] += GAIN * (1.0 - _sigmoid(ability[weakest]))

    # Delayed test: fixed-but-unretested errors return (Butler/Fazio/Marsh).
    for bug in bugs:
        if bug["fixed_once"] and not bug["active"]:
            p_back = P_RELAPSE_AFTER_RETEST if bug["retested"] else P_RELAPSE
            if rng.random() < p_back:
                bug["active"] = True

    # Held-out accuracy: base ability minus the share each active bug corrupts.
    penalty: dict[str, float] = {t: 0.0 for t in types}
    for bug in bugs:
        if bug["active"]:
            penalty[bug["type"]] = min(
                0.9, penalty[bug["type"]] + float(bug["severity"])
            )
    accs = [
        _sigmoid(ability[t] - d) * (1.0 - penalty[t])
        for t in types
        for d in DIFFICULTIES
    ]
    return sum(accs) / len(accs)


def run(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    """The pre-registered B3 ablation: misconception queue on / off / plain."""
    types = _lr_types()
    per_arm: dict[str, list[float]] = {arm: [] for arm in B3_ARMS}
    for i in range(N_LEARNERS):
        for arm in B3_ARMS:  # paired: same learner seed through all arms
            per_arm[arm].append(_simulate_b3(seed + i, arm, types))

    arms: dict[str, dict[str, Any]] = {}
    for arm in B3_ARMS:
        vals = per_arm[arm]
        mean = sum(vals) / len(vals)
        lo, hi = bootstrap_ci(vals, seed)
        arms[arm] = {"mean": round(mean, 4), "ci": [round(lo, 4), round(hi, 4)]}

    # Paired per-learner differences give the effect its own bootstrap range.
    diffs = [f - o for f, o in zip(per_arm["full"], per_arm["feature-off"])]
    d_lo, d_hi = bootstrap_ci(diffs, seed)
    feature_effect = arms["full"]["mean"] - arms["feature-off"]["mean"]
    return {
        "name": "ablation",
        "feature": "B3 misconception-priority queue + mandatory spaced re-test",
        "preregistered_claim": (
            "prioritizing high-confidence errors raises accuracy on related "
            "novel questions at equal study time"
        ),
        "primary_metric": "held-out P(correct) on unseen related items",
        "study_events_per_arm": STUDY_EVENTS,
        "n_learners": N_LEARNERS,
        "params": {
            "n_misconceptions": N_MISCONCEPTIONS,
            "p_fix": P_FIX,
            "p_relapse": P_RELAPSE,
            "p_relapse_after_retest": P_RELAPSE_AFTER_RETEST,
        },
        "arms": arms,
        "feature_effect": round(feature_effect, 4),
        "feature_effect_ci": [round(d_lo, 4), round(d_hi, 4)],
        "claim_supported": bool(d_lo > 0),
    }


def main() -> int:
    r = run()
    print("Anki for LSAT -- pre-registered ablation (equal study time; SIMULATION)\n")
    print(f"  feature        : {r['feature']}")
    print(f"  claim (pre-reg): {r['preregistered_claim']}")
    print(f"  primary metric : {r['primary_metric']}")
    print(
        f"  study events/arm: {r['study_events_per_arm']} | learners: "
        f"{r['n_learners']}\n"
    )
    for arm in B3_ARMS:
        a = r["arms"][arm]
        print(f"  {arm:16} {a['mean']:.3f}  (95% CI {a['ci'][0]:.3f}-{a['ci'][1]:.3f})")
    print()
    print(
        f"  feature effect (full - feature-off): {r['feature_effect']:+.3f} "
        f"(95% CI {r['feature_effect_ci'][0]:+.3f}..{r['feature_effect_ci'][1]:+.3f})"
    )
    print(
        f"  pre-registered claim supported: {r['claim_supported']} "
        "(reported either way)"
    )

    ri = run_interleaving()
    print("\n  -- secondary analysis: interleaving simulation (not the ablation) --")
    for arm in ARMS:
        a = ri["arms"][arm]
        print(f"  {arm:16} {a['mean']:.3f}  (95% CI {a['ci'][0]:.3f}-{a['ci'][1]:.3f})")
    print(
        f"  interleaving effect: {ri['interleaving_effect']:+.3f} | "
        f"selection effect: {ri['selection_effect']:+.3f}"
    )
    print(
        f"  +zpd (ZPD ~tau re-rank) effect vs full: {ri['zpd_effect']:+.3f} "
        f"(95% CI {ri['zpd_effect_ci'][0]:+.3f}..{ri['zpd_effect_ci'][1]:+.3f}; "
        "secondary sim, not the pre-registered B3 ablation)"
    )
    print(
        "\n  NOTE: synthetic learners; every rate is an explicit parameter. "
        "This proves the methodology, not a field result."
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
