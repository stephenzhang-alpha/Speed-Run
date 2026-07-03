# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Choke Index + pacing read-outs (DECISION.md section 3, Feature 4 -- the
"Choke/Pacing MVP" that falls out of the same ``phase`` data as the Gap Map).

Two JSON-serialisable diagnostics over the graded-answer log:

* :func:`choke_index` -- per skill and overall, the **Choke Index** =
  (relaxed/blind accuracy) - (timed accuracy). A *positive* index means you know
  more than the clock lets you show: a pacing gain to unlock, not a knowledge
  hole. Accuracies are recency-weighted (an answer's weight halves every
  ``half_life_days``), matching :func:`lsat.events.fold_recent_performance`.

* :func:`pacing_stats` -- per skill and overall **median timed response time**
  and a **"slow share"** (the fraction of timed answers slower than ``slow_ms``).
  We only log *answered* items (never skipped/unattempted ones), so this
  approximates speededness from the response-time distribution rather than
  measuring true speededness -- the payload says so explicitly.

Both abstain below a small event floor (DECISION.md 5.v -- diagnosis is passive
and never punitive). This is the analysis layer only; the reviewer's timed/blind
session toggle lives in ``qt/aqt/lsat_performance.py``.
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from eval.metrics import bootstrap_ci
from lsat.events import PerformanceEvent, read_events
from lsat.taxonomy import load_taxonomy

if TYPE_CHECKING:
    from anki.collection import Collection

_MS_PER_DAY = 86_400_000.0
DEFAULT_HALF_LIFE_DAYS = 30.0

# Paired Choke Index (DECISION-round2 #24): abstain floors + bootstrap config.
MIN_PAIRED_CHOKE_ITEMS = 5  # overall: show the estimate + CI at/above this many pairs
MIN_PAIRED_CHOKE_PER_SKILL = 5  # per skill, before a per-skill estimate is shown
# The percentile-bootstrap CI is too narrow below ~10 paired items (CI coverage
# ~0.82 at n=5 vs the >=0.90 target -- see eval/choke_validity.py), so we SHOW the
# estimate + CI from MIN_PAIRED_CHOKE_ITEMS but only raise the *confident* choke
# flag (which drives the warn status + headline) at/above this many pairs, where
# the CI is trustworthy. Honest: display early, claim confidence only when earned.
MIN_CONFIDENT_FLAG_ITEMS = 10
CHOKE_BOOTSTRAP_SEED = 1234  # deterministic bootstrap (percentile CI on paired deltas)
# ~1.5 min. LR now runs at roughly 1:24/question, so this is a generous
# per-item ceiling; answers past it are "slow" for the speededness proxy.
DEFAULT_SLOW_MS = 90_000

# Abstain floors: passive diagnosis, never from a handful of answers.
MIN_PHASE_EVENTS = 5  # choke_index: this many timed AND this many untimed overall
MIN_PHASE_EVENTS_PER_SKILL = 3  # choke_index: per skill, in each phase
MIN_TIMED_EVENTS = 5  # pacing_stats: overall
MIN_TIMED_PER_SKILL = 3  # pacing_stats: per skill
_MIN_HEADLINE_CHOKE = 0.05  # a choke headline needs at least this positive index

# Rush-Error Detector (DECISION-round3 #21). A timed answer is a "rush error" if
# it came in under RUSH_FAST_FRAC of the learner's OWN careful (untimed/relaxed)
# median RT for the skill AND was wrong. The per-learner baseline is the whole
# point: a naturally-fast-but-accurate learner is not flagged, unlike a naive
# absolute-threshold fast-and-wrong count (see eval/rush.py). Purely diagnostic
# and non-punitive -- it makes no learning-effect claim.
DEFAULT_RUSH_FAST_FRAC = 0.5
MIN_RUSH_TIMED = 8  # overall timed answers before a read-out
MIN_RUSH_TIMED_PER_SKILL = 5  # per skill
MIN_RUSH_BASELINE = 5  # untimed/relaxed answers needed to trust a careful-pace median
# We only raise the rush *flag* on the rush EFFECT -- fast answers being
# disproportionately more wrong than the learner's own non-fast answers -- never on
# a raw fast-and-wrong count, which carries the base error rate and false-flags
# accurate-but-fast learners (see eval/rush.py). Both sides of the split need a
# minimum before an excess is trustworthy.
MIN_RUSH_FAST = 5
MIN_RUSH_SLOW = 5
RUSH_EXCESS_MARGIN = 0.15  # flag needs a MATERIAL excess (>= 15pp)...
RUSH_BOOTSTRAP_N = 600  # ...AND a bootstrap CI on the excess that excludes 0
RUSH_BOOTSTRAP_SEED = 1234  # (a small point estimate is within noise at real N)
_RUSH_FRAMING = (
    "A rush pattern = your fast answers (under half your own careful/untimed "
    "pace) are notably MORE wrong than your slower ones -- a cue that slowing "
    "slightly would catch some. Measured against your own baseline and your own "
    "slower answers, so being naturally fast and accurate is never flagged. "
    "Diagnostic and non-punitive."
)

_TIMED = "timed"
_BLIND_PHASES = ("blind", "relaxed")

_CHOKE_FRAMING = (
    "Positive = you know more than the clock lets you show -- a pacing gain to "
    "unlock, not a knowledge hole. Negative or ~0 = the gap is content, not time."
)
_SPEEDEDNESS_NOTE = (
    "Approximate speededness: only answered items are logged (never skipped or "
    "unattempted ones), so this reads the timed response-time distribution -- a "
    "low slow-share does not prove a section was not speeded."
)


# -- shared helpers -----------------------------------------------------------


def _prettify(node_id: str) -> str:
    """Fallback display name (``lr.weaken`` -> ``Weaken``)."""
    leaf = node_id.split(".")[-1]
    return leaf.replace("_", " ").strip().title() or node_id


def _skill_names() -> dict[str, str]:
    """``node_id -> display name`` from the taxonomy (best-effort; empty on error)."""
    try:
        tax = load_taxonomy()
    except Exception:
        return {}
    names: dict[str, str] = {}
    for topic in tax.topics:
        names[topic.id] = topic.name
    for skill in tax.cross_cutting:
        names[skill.id] = skill.name
    return names


def _median(values: list[int]) -> float:
    """Median of ``values`` as a float (mean of the two middle for even n)."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _slow_share(values: list[int], slow_ms: int) -> float:
    if not values:
        return 0.0
    return sum(1 for v in values if v > slow_ms) / len(values)


class _Acc:
    """Recency-weighted accuracy accumulator for one phase of one skill."""

    __slots__ = ("w_correct", "w_total", "n")

    def __init__(self) -> None:
        self.w_correct = 0.0
        self.w_total = 0.0
        self.n = 0

    def add(self, weight: float, correct: bool) -> None:
        self.w_total += weight
        self.w_correct += weight if correct else 0.0
        self.n += 1

    @property
    def accuracy(self) -> float:
        return self.w_correct / self.w_total if self.w_total > 0 else 0.0


# -- Choke Index --------------------------------------------------------------


def _choke_headline(reported: list[dict[str, Any]]) -> str:
    positives = [s for s in reported if s["choke_index"] > _MIN_HEADLINE_CHOKE]
    if positives:
        s = positives[0]
        return (
            f"On {s['name']} you're {s['untimed_accuracy']:.0%} untimed vs "
            f"{s['timed_accuracy']:.0%} timed -- a +{s['choke_index']:.0%} choke "
            f"gap the clock is hiding, and pacing is faster to fix than content."
        )
    return (
        "No sizeable choke gap yet -- your timed and untimed accuracy are close, "
        "so time pressure isn't the main thing costing you points."
    )


def choke_index(
    col: Collection,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Per-skill and overall Choke Index = untimed(blind/relaxed) - timed accuracy.

    Returns a JSON-serialisable dict. ``available`` is False (with a note) until
    there are at least ``MIN_PHASE_EVENTS`` timed AND ``MIN_PHASE_EVENTS`` blind/
    relaxed answers overall. Per-skill entries carry an ``enough_evidence`` flag.
    """
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    half_life_ms = max(1.0, half_life_days * _MS_PER_DAY)

    timed_overall, untimed_overall = _Acc(), _Acc()
    timed_skill: dict[str, _Acc] = defaultdict(_Acc)
    untimed_skill: dict[str, _Acc] = defaultdict(_Acc)
    for ev in read_events(col):
        if ev.phase == _TIMED:
            overall_acc, skill_accs = timed_overall, timed_skill
        elif ev.phase in _BLIND_PHASES:
            overall_acc, skill_accs = untimed_overall, untimed_skill
        else:
            continue
        weight = 0.5 ** (max(0, now_ms - ev.wall_ms) / half_life_ms)
        overall_acc.add(weight, ev.correct)
        for node_id in ev.node_ids:
            skill_accs[node_id].add(weight, ev.correct)

    base: dict[str, Any] = {
        "half_life_days": half_life_days,
        "floor": {
            "min_timed": MIN_PHASE_EVENTS,
            "min_untimed": MIN_PHASE_EVENTS,
            "min_per_skill": MIN_PHASE_EVENTS_PER_SKILL,
        },
        "n_timed": timed_overall.n,
        "n_untimed": untimed_overall.n,
        "framing": _CHOKE_FRAMING,
    }
    if timed_overall.n < MIN_PHASE_EVENTS or untimed_overall.n < MIN_PHASE_EVENTS:
        return {
            **base,
            "available": False,
            "overall": None,
            "skills": [],
            "top_choke_skills": [],
            "headline": "",
            "note": (
                f"Need >= {MIN_PHASE_EVENTS} timed and >= {MIN_PHASE_EVENTS} untimed "
                f"answers (have {timed_overall.n}/{untimed_overall.n}). Do an untimed "
                f"second pass over timed items to measure the Choke Index."
            ),
        }

    names = _skill_names()
    skills: list[dict[str, Any]] = []
    for node_id in sorted(set(timed_skill) | set(untimed_skill)):
        timed_acc, untimed_acc = timed_skill[node_id], untimed_skill[node_id]
        enough = (
            timed_acc.n >= MIN_PHASE_EVENTS_PER_SKILL
            and untimed_acc.n >= MIN_PHASE_EVENTS_PER_SKILL
        )
        skills.append(
            {
                "node_id": node_id,
                "name": names.get(node_id, _prettify(node_id)),
                "n_timed": timed_acc.n,
                "n_untimed": untimed_acc.n,
                "timed_accuracy": timed_acc.accuracy,
                "untimed_accuracy": untimed_acc.accuracy,
                "choke_index": untimed_acc.accuracy - timed_acc.accuracy,
                "enough_evidence": enough,
            }
        )

    reported = sorted(
        (s for s in skills if s["enough_evidence"]),
        key=lambda s: s["choke_index"],
        reverse=True,
    )
    return {
        **base,
        "available": True,
        "overall": {
            "timed_accuracy": timed_overall.accuracy,
            "untimed_accuracy": untimed_overall.accuracy,
            "choke_index": untimed_overall.accuracy - timed_overall.accuracy,
        },
        "skills": skills,
        "top_choke_skills": [
            s["node_id"] for s in reported if s["choke_index"] > _MIN_HEADLINE_CHOKE
        ],
        "headline": _choke_headline(reported),
    }


# -- Paired Choke Index (within-item, with a bootstrap CI) --------------------
#
# The unpaired ``choke_index`` above subtracts timed accuracy from untimed
# accuracy over *different item pools* -- so if the items you happened to answer
# untimed were easier than the ones you answered timed, it reports a "choke" that
# is really an item-difficulty confound, and it offers no uncertainty. The paired
# estimator (DECISION-round2 #24) fixes both: it uses only items answered BOTH
# timed and untimed, takes the per-item delta (untimed_correct - timed_correct in
# {-1, 0, +1}), and bootstraps a 95% CI over those paired deltas. A choke flag is
# raised ONLY when the CI lower bound is > 0; otherwise it abstains. Pairing
# shrinks n and abstains more often -- accepted as the honest trade.


def _pair_by_item(
    events: list[PerformanceEvent],
) -> dict[str, tuple[PerformanceEvent, PerformanceEvent]]:
    """Per ``item_id``: (most-recent timed event, most-recent blind/relaxed event).

    ``read_events`` is HLC-sorted oldest->newest, so the last seen per phase is the
    most recent. Only items with BOTH a timed and an untimed answer are returned.
    """
    latest_timed: dict[str, PerformanceEvent] = {}
    latest_untimed: dict[str, PerformanceEvent] = {}
    for ev in events:
        if ev.phase == _TIMED:
            latest_timed[ev.item_id] = ev
        elif ev.phase in _BLIND_PHASES:
            latest_untimed[ev.item_id] = ev
    return {
        item_id: (latest_timed[item_id], latest_untimed[item_id])
        for item_id in latest_timed
        if item_id in latest_untimed
    }


def _paired_estimate(
    deltas: list[int], seed: int, *, min_flag_n: int = MIN_CONFIDENT_FLAG_ITEMS
) -> dict[str, Any]:
    """Mean paired delta + a percentile bootstrap 95% CI + a confident-choke flag.

    ``flag`` is True only when there are at least ``min_flag_n`` paired items AND
    the CI lower bound is strictly > 0 -- the n-gate keeps us from calling a choke
    "confident" at a sample size where the bootstrap CI under-covers the truth
    (see ``MIN_CONFIDENT_FLAG_ITEMS``). ``deltas`` are per-item
    ``untimed_correct - timed_correct``.
    """
    n = len(deltas)
    mean = sum(deltas) / n if n else 0.0
    lo, hi = bootstrap_ci([float(d) for d in deltas], seed=seed) if n else (0.0, 0.0)
    return {
        "n_paired": n,
        "choke_index": round(mean, 6),
        "ci_low": round(lo, 6),
        "ci_high": round(hi, 6),
        "flag": n >= min_flag_n and lo > 0.0,
    }


def paired_choke_index(
    col: Collection,
    *,
    seed: int = CHOKE_BOOTSTRAP_SEED,
    now_ms: int | None = None,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> dict[str, Any]:
    """Within-item Choke Index with a bootstrap CI (DECISION-round2 #24).

    Pairs each item's most-recent timed answer with its most-recent untimed
    (blind/relaxed) answer, takes the per-item delta, and bootstraps a 95% CI over
    the paired deltas -- overall and per skill. A confident-choke ``flag`` is set
    only when the CI lower bound > 0. ``available`` is False below
    ``MIN_PAIRED_CHOKE_ITEMS`` paired items. The unpaired aggregate is attached as
    an explicitly-labelled low-confidence ``fallback`` so a learner who never does
    an untimed second pass still sees the older read-out (flagged as such).
    """
    events = read_events(col)
    paired = _pair_by_item(events)
    names = _skill_names()

    overall_deltas: list[int] = []
    skill_deltas: dict[str, list[int]] = defaultdict(list)
    for timed_ev, untimed_ev in paired.values():
        delta = (1 if untimed_ev.correct else 0) - (1 if timed_ev.correct else 0)
        overall_deltas.append(delta)
        for node_id in timed_ev.node_ids or untimed_ev.node_ids:
            skill_deltas[node_id].append(delta)

    # Unpaired aggregate, retained as a labelled low-confidence fallback.
    fallback = choke_index(col, half_life_days=half_life_days, now_ms=now_ms)
    fallback["method"] = "unpaired-aggregate (low-confidence: different item pools)"

    base: dict[str, Any] = {
        "method": "paired-within-item",
        "floor": {
            "min_paired_items": MIN_PAIRED_CHOKE_ITEMS,
            "min_paired_per_skill": MIN_PAIRED_CHOKE_PER_SKILL,
        },
        "n_paired_items": len(paired),
        "framing": _CHOKE_FRAMING,
        "fallback": fallback,
    }
    if len(paired) < MIN_PAIRED_CHOKE_ITEMS:
        return {
            **base,
            "available": False,
            "overall": None,
            "skills": [],
            "top_choke_skills": [],
            "headline": "",
            "note": (
                f"Not enough paired timed+untimed items yet "
                f"({len(paired)}/{MIN_PAIRED_CHOKE_ITEMS}). Do an untimed second "
                f"pass over items you answered timed to measure a confident Choke "
                f"Index."
            ),
        }

    overall = _paired_estimate(overall_deltas, seed)
    skills: list[dict[str, Any]] = []
    for node_id in sorted(skill_deltas):
        deltas = skill_deltas[node_id]
        enough = len(deltas) >= MIN_PAIRED_CHOKE_PER_SKILL
        est = _paired_estimate(deltas, seed) if enough else {"n_paired": len(deltas)}
        skills.append(
            {
                "node_id": node_id,
                "name": names.get(node_id, _prettify(node_id)),
                "enough_evidence": enough,
                **est,
            }
        )

    flagged = sorted(
        (s for s in skills if s.get("flag")),
        key=lambda s: s["choke_index"],
        reverse=True,
    )
    if flagged:
        s = flagged[0]
        headline = (
            f"On {s['name']} your untimed edge is a confident +{s['choke_index']:.0%} "
            f"(95% CI {s['ci_low']:+.0%}..{s['ci_high']:+.0%}) -- a real pacing gap "
            f"the clock is hiding, and pacing is faster to fix than content."
        )
    elif overall["flag"]:
        headline = (
            f"Overall you're a confident +{overall['choke_index']:.0%} better untimed "
            f"(95% CI {overall['ci_low']:+.0%}..{overall['ci_high']:+.0%}) -- some of "
            f"your misses are the clock, not the content."
        )
    else:
        headline = (
            "No confident choke gap yet -- the paired timed-vs-untimed difference's "
            "confidence interval still includes zero, so we're not calling it pacing."
        )

    return {
        **base,
        "available": True,
        "overall": overall,
        "skills": skills,
        "top_choke_skills": [s["node_id"] for s in flagged],
        "headline": headline,
    }


# -- Pacing stats -------------------------------------------------------------


def pacing_stats(col: Collection, *, slow_ms: int = DEFAULT_SLOW_MS) -> dict[str, Any]:
    """Per-skill and overall median *timed* response time + a "slow share".

    Only ``phase="timed"`` answers with a positive ``response_ms`` count (pacing
    is about the clock). Returns a JSON-serialisable dict; ``available`` is False
    (with a note) below ``MIN_TIMED_EVENTS`` timed answers. See ``note`` for the
    speededness-approximation caveat.
    """
    overall_times: list[int] = []
    skill_times: dict[str, list[int]] = defaultdict(list)
    for ev in read_events(col):
        if ev.phase != _TIMED or ev.response_ms <= 0:
            continue
        overall_times.append(ev.response_ms)
        for node_id in ev.node_ids:
            skill_times[node_id].append(ev.response_ms)

    base: dict[str, Any] = {
        "slow_ms": slow_ms,
        "floor": {
            "min_timed": MIN_TIMED_EVENTS,
            "min_per_skill": MIN_TIMED_PER_SKILL,
        },
        "n_timed": len(overall_times),
        "note": _SPEEDEDNESS_NOTE,
    }
    if len(overall_times) < MIN_TIMED_EVENTS:
        return {
            **base,
            "available": False,
            "overall": None,
            "skills": [],
        }

    names = _skill_names()
    skills = [
        {
            "node_id": node_id,
            "name": names.get(node_id, _prettify(node_id)),
            "n_timed": len(times),
            "median_response_ms": _median(times),
            "slow_share": _slow_share(times, slow_ms),
            "enough_evidence": len(times) >= MIN_TIMED_PER_SKILL,
        }
        for node_id, times in sorted(skill_times.items())
    ]
    return {
        **base,
        "available": True,
        "overall": {
            "n_timed": len(overall_times),
            "median_response_ms": _median(overall_times),
            "slow_share": _slow_share(overall_times, slow_ms),
        },
        "skills": skills,
    }


# -- Rush-Error Detector ------------------------------------------------------


def _rush_fold(
    timed: list[tuple[int, bool]], threshold_ms: float, *, seed: int
) -> dict[str, Any]:
    """Fold one skill's (rt, correct) timed answers against a fast threshold.

    Reports the descriptive fast-and-wrong count AND the discriminating signal:
    the error rate on fast vs non-fast answers, their excess (fast - non-fast),
    and a bootstrap 95% CI on that excess. The flag fires ONLY when the excess is
    both MATERIAL (>= RUSH_EXCESS_MARGIN) and SIGNIFICANT (CI lower bound > 0) --
    a raw count or a bare point estimate is within noise at realistic N, so this
    is what stops accurate-but-fast learners being false-flagged (see eval/rush.py).
    """
    fast = [c for rt, c in timed if rt < threshold_ms]
    slow = [c for rt, c in timed if rt >= threshold_ms]
    n_fast, n_slow = len(fast), len(slow)
    n_rush = sum(1 for c in fast if not c)  # fast AND wrong (descriptive)
    fast_err = (sum(1 for c in fast if not c) / n_fast) if n_fast else 0.0
    slow_err = (sum(1 for c in slow if not c) / n_slow) if n_slow else 0.0

    excess: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    flag = False
    if n_fast >= MIN_RUSH_FAST and n_slow >= MIN_RUSH_SLOW:
        excess = fast_err - slow_err
        rng = random.Random(seed)
        diffs: list[float] = []
        for _ in range(RUSH_BOOTSTRAP_N):
            fe = sum(not fast[rng.randrange(n_fast)] for _ in range(n_fast)) / n_fast
            se = sum(not slow[rng.randrange(n_slow)] for _ in range(n_slow)) / n_slow
            diffs.append(fe - se)
        diffs.sort()
        ci_low = diffs[int(0.025 * RUSH_BOOTSTRAP_N)]
        ci_high = diffs[min(RUSH_BOOTSTRAP_N - 1, int(0.975 * RUSH_BOOTSTRAP_N))]
        flag = excess >= RUSH_EXCESS_MARGIN and ci_low > 0.0
    return {
        "n_timed": len(timed),
        "n_fast": n_fast,
        "n_slow": n_slow,
        "n_rush": n_rush,
        "fast_error_rate": round(fast_err, 4),
        "nonfast_error_rate": round(slow_err, 4),
        "rush_excess": (round(excess, 4) if excess is not None else None),
        "excess_ci_low": (round(ci_low, 4) if ci_low is not None else None),
        "excess_ci_high": (round(ci_high, 4) if ci_high is not None else None),
        "flag": bool(flag),
        "threshold_ms": round(threshold_ms),
    }


def rush_errors(
    col: Collection,
    *,
    fast_frac: float = DEFAULT_RUSH_FAST_FRAC,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Per-skill and overall **rush-error** read-out (DECISION-round3 #21).

    A timed answer is "fast" when it lands under ``fast_frac`` of the learner's own
    careful (untimed/relaxed) median RT for that skill -- so the threshold is
    *personal*, not an absolute clock. A rush pattern is flagged only when the
    learner's fast answers are both materially and significantly MORE wrong than
    their non-fast ones (CI-gated; see :func:`_rush_fold`). Abstains
    (``available`` False) until there is a trustworthy careful-pace baseline
    (``MIN_RUSH_BASELINE`` untimed answers) and ``MIN_RUSH_TIMED`` timed answers.
    Every logged timed answer counts equally. Purely diagnostic + non-punitive.
    """
    overall_timed: list[tuple[int, bool]] = []
    overall_untimed_rts: list[int] = []
    skill_timed: dict[str, list[tuple[int, bool]]] = defaultdict(list)
    skill_untimed_rts: dict[str, list[int]] = defaultdict(list)
    for ev in read_events(col):
        if ev.response_ms <= 0:
            continue
        if ev.phase == _TIMED:
            overall_timed.append((ev.response_ms, ev.correct))
            for node_id in ev.node_ids:
                skill_timed[node_id].append((ev.response_ms, ev.correct))
        elif ev.phase in _BLIND_PHASES:
            overall_untimed_rts.append(ev.response_ms)
            for node_id in ev.node_ids:
                skill_untimed_rts[node_id].append(ev.response_ms)

    base: dict[str, Any] = {
        "fast_frac": fast_frac,
        "floor": {
            "min_timed": MIN_RUSH_TIMED,
            "min_per_skill": MIN_RUSH_TIMED_PER_SKILL,
            "min_baseline": MIN_RUSH_BASELINE,
        },
        "n_timed": len(overall_timed),
        "n_baseline": len(overall_untimed_rts),
        "framing": _RUSH_FRAMING,
    }
    # Need a trustworthy careful-pace baseline AND enough timed answers. Without an
    # untimed baseline we would fall back to an absolute threshold -- the very
    # thing this estimator is designed to beat -- so we abstain instead.
    if (
        len(overall_untimed_rts) < MIN_RUSH_BASELINE
        or len(overall_timed) < MIN_RUSH_TIMED
    ):
        return {
            **base,
            "available": False,
            "overall": None,
            "skills": [],
            "headline": "",
            "note": (
                "Answer some items timed AND blind-review some untimed to set your "
                "careful-pace baseline -- then rush errors can be measured."
            ),
        }

    overall_baseline = _median(overall_untimed_rts)
    overall = _rush_fold(
        overall_timed, fast_frac * overall_baseline, seed=RUSH_BOOTSTRAP_SEED
    )
    overall["baseline_median_ms"] = round(overall_baseline)

    names = _skill_names()
    skills: list[dict[str, Any]] = []
    for i, (node_id, timed) in enumerate(sorted(skill_timed.items())):
        untimed_rts = skill_untimed_rts.get(node_id, [])
        # per-skill baseline when it is itself trustworthy, else the overall one
        baseline = (
            _median(untimed_rts)
            if len(untimed_rts) >= MIN_RUSH_BASELINE
            else overall_baseline
        )
        fold = _rush_fold(
            timed, fast_frac * baseline, seed=RUSH_BOOTSTRAP_SEED + 1 + i
        )
        fold["baseline_median_ms"] = round(baseline)
        skills.append(
            {
                "node_id": node_id,
                "name": names.get(node_id, _prettify(node_id)),
                "enough_evidence": len(timed) >= MIN_RUSH_TIMED_PER_SKILL,
                **fold,
            }
        )

    flagged = [s for s in skills if s["enough_evidence"] and s["flag"]]
    worst = max(
        flagged, key=lambda s: (s["rush_excess"] or 0.0), default=None
    )
    if worst is not None:
        headline = (
            f"On {worst['name']}, your fast answers are "
            f"{worst['rush_excess']:.0%} more wrong than your slower ones -- a "
            f"rush pattern worth a second look at slowing slightly there."
        )
    else:
        headline = (
            "No rush pattern right now -- your fast answers aren't more wrong "
            "than your slower ones."
        )
    overall["flagged_skills"] = [s["node_id"] for s in flagged]

    return {
        **base,
        "available": True,
        "overall": overall,
        "skills": skills,
        "headline": headline,
    }


# -- self-test ----------------------------------------------------------------


def _json_ok(obj: Any) -> bool:
    """True iff ``obj`` round-trips through strict JSON (no NaN/Infinity)."""
    import json

    try:
        json.dumps(obj, allow_nan=False)
    except (ValueError, TypeError):
        return False
    return True


def _selftest() -> bool:  # noqa: PLR0915 (one linear scenario; clearer inline)
    """Engineer a better-untimed skill + a slow skill and assert both read-outs."""
    import os
    import sys
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in (os.path.join(root, "pylib"), os.path.join(root, "out", "pylib"), root):
        if path not in sys.path:
            sys.path.insert(0, path)

    from anki.collection import Collection
    from lsat.events import append_event

    now = 1_700_000_000_000
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    def add_pair(
        col: Collection,
        item_id: str,
        skill: str,
        timed_correct: bool,
        blind_correct: bool,
        timed_ms: int,
    ) -> None:
        append_event(
            col,
            item_id=item_id,
            skill_tags=[skill],
            correct=timed_correct,
            response_ms=timed_ms,
            phase="timed",
            now_ms=now,
        )
        append_event(
            col,
            item_id=item_id,
            skill_tags=[skill],
            correct=blind_correct,
            response_ms=150_000,
            phase="blind",
            now_ms=now,
        )

    tmp = tempfile.mkdtemp(prefix="pacing-selftest-")

    # (1) both read-outs abstain below their floors -----------------------------
    below = Collection(os.path.join(tmp, "below.anki2"))
    try:
        add_pair(below, "b1", "lr.weaken", False, True, 100_000)
        add_pair(below, "b2", "lr.weaken", True, True, 60_000)
        add_pair(below, "b3", "lr.weaken", False, False, 80_000)  # 3 < floor(5)
        ci_below = choke_index(below, now_ms=now)
        ps_below = pacing_stats(below)
        check("choke_index abstains below floor", ci_below["available"] is False)
        check("pacing_stats abstains below floor", ps_below["available"] is False)
        check(
            "below-floor payloads are JSON-safe",
            _json_ok(ci_below) and _json_ok(ps_below),
        )
    finally:
        below.close()

    # (2) the full engineered scenario ------------------------------------------
    full = Collection(os.path.join(tmp, "full.anki2"))
    try:
        # Weaken: known-under-pressure (2/5 timed, 5/5 untimed) and the slow items
        # are exactly the ones missed timed (ran out of clock, not knowledge).
        add_pair(full, "W1", "lr.weaken", False, True, 120_000)  # slow
        add_pair(full, "W2", "lr.weaken", False, True, 110_000)  # slow
        add_pair(full, "W3", "lr.weaken", False, True, 100_000)  # slow
        add_pair(full, "W4", "lr.weaken", True, True, 60_000)
        add_pair(full, "W5", "lr.weaken", True, True, 50_000)
        # Necessary Assumption: bad even untimed (a content gap, fast answers).
        add_pair(full, "A1", "lr.assumption_necessary", False, False, 80_000)
        add_pair(full, "A2", "lr.assumption_necessary", False, False, 85_000)
        add_pair(full, "A3", "lr.assumption_necessary", True, False, 70_000)

        ci = choke_index(full, now_ms=now)
        by_id = {s["node_id"]: s for s in ci["skills"]}
        check("choke_index available at/above floor", ci["available"] is True)
        check(
            "Choke Index positive for the better-untimed skill (Weaken +0.6)",
            abs(by_id["lr.weaken"]["choke_index"] - 0.6) < 1e-9,
        )
        check(
            "Choke Index non-positive for the content-gap skill (Assumption)",
            by_id["lr.assumption_necessary"]["choke_index"] < 0.0,
        )
        check(
            "Weaken surfaces as a top choke skill",
            "lr.weaken" in ci["top_choke_skills"]
            and "lr.assumption_necessary" not in ci["top_choke_skills"],
        )
        check(
            "overall Choke Index is positive",
            ci["overall"]["choke_index"] > 0.0,
        )
        check("choke_index payload is JSON-safe (allow_nan=False)", _json_ok(ci))

        ps = pacing_stats(full)
        ps_by_id = {s["node_id"]: s for s in ps["skills"]}
        # Timed response_ms overall: sorted -> [50,60,70,80,85,100,110,120]k;
        # median = mean(80k, 85k) = 82500.
        check("pacing_stats available at/above floor", ps["available"] is True)
        check(
            "overall median timed response is sane (82500 ms)",
            ps["overall"]["median_response_ms"] == 82_500.0,
        )
        check(
            "Weaken median timed response is sane (100000 ms)",
            ps_by_id["lr.weaken"]["median_response_ms"] == 100_000.0,
        )
        check(
            "Weaken slow-share = 3/5 (the missed-timed items are the slow ones)",
            abs(ps_by_id["lr.weaken"]["slow_share"] - 0.6) < 1e-9,
        )
        check(
            "Necessary Assumption slow-share = 0 (fast but wrong = content gap)",
            abs(ps_by_id["lr.assumption_necessary"]["slow_share"] - 0.0) < 1e-9,
        )
        check(
            "overall slow-share = 3/8",
            abs(ps["overall"]["slow_share"] - 0.375) < 1e-9,
        )
        check("pacing_stats payload is JSON-safe (allow_nan=False)", _json_ok(ps))

        # -- paired Choke Index (DECISION-round2 #24) --------------------------
        pc = paired_choke_index(full, now_ms=now)
        pc_by_id = {s["node_id"]: s for s in pc["skills"]}
        check("paired_choke_index available at/above floor", pc["available"] is True)
        check("paired counts all 8 paired items", pc["n_paired_items"] == 8)
        check(
            "paired overall choke index = mean delta (2/8 = 0.25)",
            abs(pc["overall"]["choke_index"] - 0.25) < 1e-9,
        )
        check(
            "paired overall CI brackets the mean",
            pc["overall"]["ci_low"]
            <= pc["overall"]["choke_index"]
            <= pc["overall"]["ci_high"],
        )
        wk = pc_by_id["lr.weaken"]
        check(
            "Weaken paired (5 items) has enough evidence + mean +0.6",
            wk["enough_evidence"] and abs(wk["choke_index"] - 0.6) < 1e-9,
        )
        check(
            "Necessary Assumption (3 paired < 5) abstains from a per-skill CI",
            pc_by_id["lr.assumption_necessary"]["enough_evidence"] is False
            and "flag" not in pc_by_id["lr.assumption_necessary"],
        )
        check(
            "any flagged skill has a strictly-positive CI lower bound",
            all(s["ci_low"] > 0.0 for s in pc["skills"] if s.get("flag")),
        )
        check(
            "fallback is the unpaired aggregate, explicitly labelled",
            "unpaired" in pc["fallback"].get("method", ""),
        )
        check("paired_choke_index payload is JSON-safe", _json_ok(pc))
    finally:
        full.close()

    # (3) paired Choke Index abstains below the paired floor (only 3 pairs) ------
    below_paired = Collection(os.path.join(tmp, "below_paired.anki2"))
    try:
        add_pair(below_paired, "p1", "lr.weaken", False, True, 100_000)
        add_pair(below_paired, "p2", "lr.weaken", True, True, 60_000)
        add_pair(below_paired, "p3", "lr.weaken", False, False, 80_000)  # 3 < 5
        pc_below = paired_choke_index(below_paired, now_ms=now)
        check(
            "paired_choke_index abstains below the paired floor",
            pc_below["available"] is False,
        )
        check("below-floor paired payload is JSON-safe", _json_ok(pc_below))
    finally:
        below_paired.close()

    # (4a) Rush-Error Detector: fast answers NOT more wrong than slow ones must
    # NOT flag (the excess + its CI drive the flag, never a raw count) ----------
    rush = Collection(os.path.join(tmp, "rush.anki2"))
    try:
        # baseline: 6 untimed @100s -> median 100s -> fast threshold 50s. Timed:
        # 5 fast(30s), 2 wrong (fast_err 0.4); 5 slow(80s), 3 wrong (slow_err 0.6).
        # excess = -0.2 -> NO flag: the misses aren't concentrated in fast answers.
        for i in range(6):
            append_event(rush, item_id=f"rb{i}", skill_tags=["lr.flaw"],
                         correct=True, response_ms=100_000, phase="blind", now_ms=now)
        for i in range(5):  # fast: 2 wrong (i in {0,1}), 3 correct
            append_event(rush, item_id=f"rf{i}", skill_tags=["lr.flaw"],
                         correct=(i >= 2), response_ms=30_000, phase="timed", now_ms=now)
        for i in range(5):  # slow: 3 wrong (i in {0,1,2}), 2 correct
            append_event(rush, item_id=f"rs{i}", skill_tags=["lr.flaw"],
                         correct=(i >= 3), response_ms=80_000, phase="timed", now_ms=now)
        re_out = rush_errors(rush, now_ms=now)
        rb = {s["node_id"]: s for s in re_out["skills"]}["lr.flaw"]
        check("rush_errors available with baseline + timed", re_out["available"] is True)
        check(
            "rush careful-pace baseline median = 100000 ms",
            re_out["overall"]["baseline_median_ms"] == 100_000,
        )
        check(
            "rush split counts sane (n_fast=5, n_slow=5, n_rush=2)",
            rb["n_fast"] == 5 and rb["n_slow"] == 5 and rb["n_rush"] == 2,
        )
        check(
            "rush error rates: fast 0.4 vs non-fast 0.6 -> excess -0.2",
            abs(rb["fast_error_rate"] - 0.4) < 1e-9
            and abs(rb["nonfast_error_rate"] - 0.6) < 1e-9
            and abs(rb["rush_excess"] + 0.2) < 1e-9,
        )
        check("fast answers no more wrong than slow -> do NOT flag",
              rb["flag"] is False)
        check("rush_errors payload is JSON-safe (allow_nan=False)", _json_ok(re_out))
    finally:
        rush.close()

    # (4b) A genuine rush pattern (fast answers disproportionately wrong) flags --
    rush2 = Collection(os.path.join(tmp, "rush2.anki2"))
    try:
        # baseline 6 @100s -> threshold 50s. Fast: 8 @30s, 6 wrong (fast_err 0.75);
        # slow: 8 @80s, 1 wrong (slow_err 0.125). excess +0.625, CI excludes 0 -> FLAG.
        for i in range(6):
            append_event(rush2, item_id=f"b{i}", skill_tags=["lr.flaw"],
                         correct=True, response_ms=100_000, phase="blind", now_ms=now)
        for i in range(8):  # fast: 6 wrong (i>=2 correct? no) -> correct when i>=6
            append_event(rush2, item_id=f"f{i}", skill_tags=["lr.flaw"],
                         correct=(i >= 6), response_ms=30_000, phase="timed", now_ms=now)
        for i in range(8):  # slow: 1 wrong (i==0), rest correct
            append_event(rush2, item_id=f"s{i}", skill_tags=["lr.flaw"],
                         correct=(i != 0), response_ms=80_000, phase="timed", now_ms=now)
        re2 = rush_errors(rush2, now_ms=now)
        rb2 = {s["node_id"]: s for s in re2["skills"]}["lr.flaw"]
        check(
            "genuine rush pattern flags (fast 0.75 vs slow 0.125, excess +0.625)",
            rb2["flag"] is True and abs(rb2["rush_excess"] - 0.625) < 1e-9,
        )
        check("flagged excess CI excludes 0 (ci_low > 0)", rb2["excess_ci_low"] > 0.0)
        check("flagged skill appears in overall.flagged_skills",
              "lr.flaw" in re2["overall"]["flagged_skills"])
        check("rush headline names the pattern", "rush pattern" in re2["headline"])
        check("rush2 payload is JSON-safe", _json_ok(re2))
    finally:
        rush2.close()

    # (5) rush_errors abstains without a careful-pace baseline ------------------
    rush_nb = Collection(os.path.join(tmp, "rush_nb.anki2"))
    try:
        for i in range(10):
            append_event(rush_nb, item_id=f"t{i}", skill_tags=["lr.flaw"],
                         correct=(i % 2 == 0), response_ms=30_000, phase="timed",
                         now_ms=now)
        re_nb = rush_errors(rush_nb, now_ms=now)
        check(
            "rush_errors abstains without an untimed baseline (no absolute clock)",
            re_nb["available"] is False,
        )
        check("no-baseline rush payload is JSON-safe", _json_ok(re_nb))
    finally:
        rush_nb.close()

    ok = all(passed for _, passed in checks)
    print("PACING_OK" if ok else "PACING_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
