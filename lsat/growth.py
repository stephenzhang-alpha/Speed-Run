# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Mastery-Growth Panel (DECISION-round3 #2): CI-gated self-referential progress.

The honesty discipline forbids a fabricated readiness/percentile/σ number. This
panel fills that gap with the *truthful* alternative: a **self-referential**
per-skill mastery delta -- did your accuracy on THIS skill rise between the early
and recent halves of your own timed history? -- never a rank, percentile, or
comparison to other students (Kluger & DeNisi: ego/comparison feedback is the
kind that *hurts*; task/process feedback helps).

Two guards keep it honest:

1. **Difficulty-matched.** A naive early-vs-recent accuracy delta is confounded if
   the deck fed you harder items lately (the ZPD engine targets ~85%, so it does).
   We stratify each skill's events by difficulty band and pool the per-band deltas,
   so a shift in the difficulty *mix* cannot masquerade as improvement/decline.
2. **CI-gated abstention.** We emit "improved"/"slipped" ONLY when a bootstrap 95%
   CI on the pooled delta excludes 0; otherwise we abstain ("not enough evidence
   yet -- keep going"). Sub-threshold noise is never rendered as progress. The
   companion eval (:mod:`eval.growth`) is a HARD gate: on true-no-change learners
   the panel must claim "improved" <5% of the time, and must detect true change.

The core (:func:`growth_for_skill`) is collection-free so it is unit-testable;
:func:`compute_growth` is the thin adapter that reads the event log + item
difficulties. Any downstream score movement from acting on this panel is just the
mechanical value of extra practice -- it is NOT double-counted (mirrors
:mod:`lsat.adherence`).
"""

from __future__ import annotations

import random
import zlib
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anki.collection import Collection

# A skill needs at least this many timed events in EACH half before we attempt a
# readout (below it we abstain -- "keep going"). At 8 the proportion-difference
# bootstrap under-covers (~6% false direction); 12 brings it under the 5% promise.
MIN_PER_WINDOW = 12
# A difficulty band must have at least this many answers in EACH window to be
# "matchable". Without it, a band with as few as 1 answer per window dominates the
# count-weighted pooled delta on a pure easy->hard drift and fabricates a
# direction (the difficulty-matching guarantee's real teeth). See eval/growth.py's
# mix-drift arm.
MIN_PER_BAND = 5
# Even with a CI excluding 0, only claim a direction when the pooled delta is
# MATERIAL (>= this many accuracy points) -- kills small-n noise masquerading as
# progress, mirroring the rush detector's material+significant gate.
MIN_DELTA = 0.08
N_BOOT = 1000
_ALPHA = 0.05

IMPROVED = "improved"
SLIPPED = "slipped"
ABSTAIN = "abstain"

# Skill node -> the concrete next step a non-abstaining readout routes to (the
# debate required "route every non-abstaining readout to a concrete next-step").
_NEXT_STEP = {
    "skill.conditional_logic": "Conditional translation drill (Logic tab)",
    "skill.quantifier_logic": "Quantifier reasoning drill (Logic tab)",
}
_DEFAULT_NEXT_STEP = "A short focused set on this skill, then blind-review the misses"


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _pooled_delta(bands: dict[str, tuple[list[int], list[int]]]) -> tuple[float, float]:
    """Difficulty-matched pooled delta = weight-averaged per-band (recent-early)
    accuracy over the bands present in BOTH windows. Returns (delta, total_weight);
    total_weight 0 means no band overlaps (caller abstains)."""
    num = 0.0
    wsum = 0.0
    for early, recent in bands.values():
        # a band must have enough answers in BOTH windows to be matchable -- a
        # tiny band would otherwise dominate the pooled delta on a mix shift
        if len(early) < MIN_PER_BAND or len(recent) < MIN_PER_BAND:
            continue
        w = float(len(early) + len(recent))
        num += w * (_mean(recent) - _mean(early))
        wsum += w
    return (num / wsum if wsum else 0.0, wsum)


def growth_for_skill(
    ordered: list[tuple[bool, str]], *, seed: int = 0
) -> dict[str, Any]:
    """Compute a difficulty-matched, CI-gated growth readout for one skill.

    ``ordered`` is the skill's timed answers in chronological order as
    ``(correct, difficulty_band)`` pairs. Splits into first/second half, stratifies
    each half by band, pools the per-band deltas, and bootstraps a 95% CI. Emits a
    directional status only when the CI excludes 0.
    """
    m = len(ordered)
    half = m // 2
    early_all, recent_all = ordered[:half], ordered[m - half :]
    if len(early_all) < MIN_PER_WINDOW or len(recent_all) < MIN_PER_WINDOW:
        return {
            "available": False,
            "status": ABSTAIN,
            "reason": "not enough timed answers yet -- keep going",
            "n_early": len(early_all),
            "n_recent": len(recent_all),
        }

    bands: dict[str, tuple[list[int], list[int]]] = {}
    for window, idx in ((early_all, 0), (recent_all, 1)):
        for correct, band in window:
            slot = bands.setdefault(band, ([], []))
            slot[idx].append(1 if correct else 0)

    delta, wsum = _pooled_delta(bands)
    if wsum == 0.0:
        return {
            "available": False,
            "status": ABSTAIN,
            "reason": "difficulty mix not comparable across windows yet",
            "n_early": len(early_all),
            "n_recent": len(recent_all),
        }

    # Bootstrap the pooled delta by resampling within each band's two windows.
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(N_BOOT):
        resampled: dict[str, tuple[list[int], list[int]]] = {}
        for band, (early, recent) in bands.items():
            if len(early) < MIN_PER_BAND or len(recent) < MIN_PER_BAND:
                continue  # resample only the matchable bands (same filter as above)
            e = [early[rng.randrange(len(early))] for _ in early]
            r = [recent[rng.randrange(len(recent))] for _ in recent]
            resampled[band] = (e, r)
        d, _ = _pooled_delta(resampled)
        deltas.append(d)
    deltas.sort()
    lo = deltas[int((_ALPHA / 2) * N_BOOT)]
    hi = deltas[min(N_BOOT - 1, int((1 - _ALPHA / 2) * N_BOOT))]

    # claim a direction only when the effect is MATERIAL (|delta| >= MIN_DELTA)
    # AND significant (CI excludes 0); otherwise abstain.
    if lo > 0.0 and delta >= MIN_DELTA:
        status = IMPROVED
    elif hi < 0.0 and delta <= -MIN_DELTA:
        status = SLIPPED
    else:
        status = ABSTAIN

    return {
        "available": status != ABSTAIN,
        "status": status,
        "delta": round(delta, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "n_early": len(early_all),
        "n_recent": len(recent_all),
        "reason": (
            "not enough evidence yet -- keep going" if status == ABSTAIN else ""
        ),
    }


def _label(node_id: str) -> str:
    return node_id.split(".")[-1].replace("_", " ")


def compute_growth(col: Collection, *, now_ms: int | None = None) -> dict[str, Any]:
    """Assemble the Mastery-Growth panel from the timed event log. JSON-safe;
    abstains per skill until the CI gate is met. ``now_ms`` is unused today (the
    windows are self-referential halves) but accepted for signature symmetry."""
    from lsat.events import read_events

    try:
        from lsat.models.performance import _difficulty_map

        diff_map = _difficulty_map(col)
    except Exception:
        diff_map = {}

    events = [e for e in read_events(col) if (e.phase or "timed") == "timed"]
    # chronological order (HLC string sorts chronologically by construction)
    events.sort(key=lambda e: e.hlc)

    per_skill_events: dict[str, list[tuple[bool, str]]] = {}
    for e in events:
        band = diff_map.get(e.item_id, "medium")
        for node_id in e.node_ids:
            per_skill_events.setdefault(node_id, []).append((bool(e.correct), band))

    skills: list[dict[str, Any]] = []
    for node_id, ordered in sorted(per_skill_events.items()):
        # deterministic per-skill seed -- zlib.crc32 (NOT hash(), which Python salts
        # per process) so the CI-gated readout is reproducible across dashboard loads
        readout = growth_for_skill(ordered, seed=zlib.crc32(node_id.encode()))
        entry = {"node_id": node_id, "label": _label(node_id), **readout}
        if readout.get("available"):
            entry["next_step"] = _NEXT_STEP.get(node_id, _DEFAULT_NEXT_STEP)
        skills.append(entry)

    improved = [s for s in skills if s.get("status") == IMPROVED]
    slipped = [s for s in skills if s.get("status") == SLIPPED]
    available = bool(improved or slipped)
    return {
        "available": available,
        "skills": skills,
        "n_improved": len(improved),
        "n_slipped": len(slipped),
        "n_tracked": len(skills),
        "headline": (
            f"{len(improved)} skill(s) measurably up, {len(slipped)} down"
            if available
            else "No measurable per-skill change yet -- keep going."
        ),
        "note": (
            "Self-referential: your own accuracy on each skill, early vs recent "
            "timed answers, difficulty-matched. Not a rank or a score."
        ),
    }


# -- self-test ----------------------------------------------------------------


def _make(
    n: int, p_early: float, p_recent: float, band: str = "medium", *, seed: int = 1
):
    """A synthetic skill history: n//2 early at accuracy p_early, n//2 recent at
    p_recent, all in one band, in chronological order."""
    rng = random.Random(seed)
    half = n // 2
    early = [(rng.random() < p_early, band) for _ in range(half)]
    recent = [(rng.random() < p_recent, band) for _ in range(half)]
    return early + recent


def _selftest() -> bool:
    import json

    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # 1. Below the floor -> abstain (never claims progress on thin data).
    thin = growth_for_skill(_make(10, 0.5, 0.9), seed=1)
    check(
        "below MIN_PER_WINDOW abstains",
        thin["status"] == ABSTAIN and not thin["available"],
    )

    # 2. A large true improvement over enough events -> 'improved', CI excludes 0.
    up = growth_for_skill(_make(160, 0.45, 0.85, seed=2), seed=7)
    check("true improvement -> improved", up["status"] == IMPROVED)
    check("improved CI excludes 0 (lo>0)", up["ci_low"] > 0.0)

    # 3. A large true decline -> 'slipped', CI excludes 0.
    down = growth_for_skill(_make(160, 0.85, 0.45, seed=3), seed=7)
    check("true decline -> slipped", down["status"] == SLIPPED)
    check("slipped CI excludes 0 (hi<0)", down["ci_high"] < 0.0)

    # 4. FALSE-POSITIVE calibration: on many true-no-change skills, the panel must
    #    claim a direction <5% of the time (the honesty guarantee).
    false_claims = 0
    trials = 300
    for i in range(trials):
        r = growth_for_skill(_make(80, 0.7, 0.7, seed=1000 + i), seed=2000 + i)
        if r["status"] in (IMPROVED, SLIPPED):
            false_claims += 1
    fp_rate = false_claims / trials
    check(f"true-no-change false-direction rate {fp_rate:.3f} < 0.05", fp_rate < 0.05)

    # 5. Difficulty-matching: non-overlapping bands (early all-hard, recent
    #    all-easy) share no matchable band -> abstain, never a spurious readout.
    early_hard = [(random.Random(500 + i).random() < 0.6, "hard") for i in range(20)]
    recent_easy = [(random.Random(600 + i).random() < 0.6, "easy") for i in range(20)]
    mixed = growth_for_skill(early_hard + recent_easy, seed=9)
    check(
        "non-overlapping difficulty bands -> abstain (matched)",
        mixed["status"] == ABSTAIN,
    )

    # 6. Mix-only shift within a SHARED band: same per-band accuracy in both
    #    windows, but the easy/medium proportion differs. A naive pooled accuracy
    #    would rise; the difficulty-matched delta stays ~0 -> abstain.
    early_mix = [
        (random.Random(11 + i).random() < 0.6, "medium") for i in range(20)
    ] + [(random.Random(31 + i).random() < 0.9, "easy") for i in range(20)]
    recent_mix = [(random.Random(51 + i).random() < 0.6, "medium") for i in range(20)]
    shared = growth_for_skill(early_mix + recent_mix, seed=13)
    check(
        "shared-band matched delta abstains on mix-only shift",
        shared["status"] == ABSTAIN,
    )

    # 6b. REGRESSION (adversarial review, Finding 1): a pure difficulty-MIX DRIFT
    #     with NO real change (early: mostly easy; recent: mostly hard; p=0.7
    #     everywhere) must NOT fabricate a direction. Before the per-band floor,
    #     tiny bands dominated the pooled delta and this leaked ~10.7%.
    def _mix_drift(seed: int):
        rng = random.Random(seed)
        early = [(rng.random() < 0.7, "easy") for _ in range(11)] + [
            (rng.random() < 0.7, "hard") for _ in range(3)
        ]
        recent = [(rng.random() < 0.7, "easy") for _ in range(3)] + [
            (rng.random() < 0.7, "hard") for _ in range(11)
        ]
        return early + recent

    mix_false = 0
    mix_trials = 400
    for i in range(mix_trials):
        r = growth_for_skill(_mix_drift(7000 + i), seed=8000 + i)
        if r["status"] in (IMPROVED, SLIPPED):
            mix_false += 1
    mix_rate = mix_false / mix_trials
    check(
        f"difficulty-mix drift false-direction rate {mix_rate:.3f} < 0.05 (Finding 1)",
        mix_rate < 0.05,
    )

    # 7. JSON-safe output.
    try:
        json.dumps(up)
        json.dumps(growth_for_skill(_make(10, 0.5, 0.5), seed=1))
        json_ok = True
    except (TypeError, ValueError):
        json_ok = False
    check("readouts are JSON-safe", json_ok)

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("GROWTH_OK" if ok else "GROWTH_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
