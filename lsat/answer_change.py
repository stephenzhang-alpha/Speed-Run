# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""First-Instinct Ledger (DECISION-round4 #17): the answer-change diagnostic.

Test-takers agonize over the "never change your first answer" folk rule. The
research (Kruger, Wong & Kwong 2005; Benjamin et al.) is that changes are, on
average, ~2:1 wrong->right -- but that is a POPULATION base rate, and applying it
to an individual is the ecological fallacy. So this read-out refuses the
always/never dogma and reports the LEARNER'S OWN tally, on their own timed
sections, WITH a confidence interval:

    net = (wrong->right changes) - (right->wrong changes)

A positive net (CI excludes 0) means *for you*, on the evidence so far, changing
has paid off; negative means it has cost you; a CI spanning 0 means there isn't
enough evidence to say -- and we say exactly that, rather than parrot the base
rate. It is a DIAGNOSTIC: it makes no learning-effect claim, only reports what the
learner's captured section trajectories show, and abstains below a min-changes
floor. Its estimator validity (recovers a planted tendency, never fabricates one
on a 50/50 student) is gated by :mod:`eval.answer_change`.

The core (:func:`answer_change_ledger`) is collection-free so it is unit-testable;
:func:`compute_answer_change` reads the captured section trajectories.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anki.collection import Collection

# Answer-change categories among CHANGED questions (first answer != final answer).
WRONG_TO_RIGHT = "wr"
RIGHT_TO_WRONG = "rw"
WRONG_TO_WRONG = "ww"

MIN_CHANGES = 12  # need at least this many answer changes before a directional read
N_BOOT = 1000
_ALPHA = 0.05

_FRAMING = (
    "Your OWN answer-change record on timed sections -- not the folk 'never "
    "change' rule and not the population ~2:1 base rate (applying either to you "
    "is the ecological fallacy). A direction is claimed only when your CI excludes "
    "0; otherwise: not enough evidence yet. Diagnostic, not a prescription."
)


def _contribution(cat: str) -> int:
    if cat == WRONG_TO_RIGHT:
        return 1
    if cat == RIGHT_TO_WRONG:
        return -1
    return 0  # wrong->wrong is neutral for the net


def answer_change_ledger(changes: list[str], *, seed: int = 0) -> dict[str, Any]:
    """Net answer-change tally + a bootstrap 95% CI over per-change contributions
    (+1 wrong->right, -1 right->wrong, 0 wrong->wrong). Emits a direction only when
    the CI excludes 0; abstains below :data:`MIN_CHANGES`."""
    n = len(changes)
    wr = sum(1 for c in changes if c == WRONG_TO_RIGHT)
    rw = sum(1 for c in changes if c == RIGHT_TO_WRONG)
    ww = sum(1 for c in changes if c == WRONG_TO_WRONG)
    base = {
        "n_changes": n,
        "wrong_to_right": wr,
        "right_to_wrong": rw,
        "wrong_to_wrong": ww,
        "floor": MIN_CHANGES,
        "framing": _FRAMING,
    }
    if n < MIN_CHANGES:
        return {
            **base,
            "available": False,
            "direction": "abstain",
            "reason": "not enough answer changes yet -- keep taking timed sections",
        }

    contribs = [_contribution(c) for c in changes]
    net = sum(contribs)
    rng = random.Random(seed)
    boot_nets: list[float] = []
    for _ in range(N_BOOT):
        s = sum(contribs[rng.randrange(n)] for _ in range(n))
        boot_nets.append(s)  # net over a resample of the same size
    boot_nets.sort()
    lo = boot_nets[int((_ALPHA / 2) * N_BOOT)]
    hi = boot_nets[min(N_BOOT - 1, int((1 - _ALPHA / 2) * N_BOOT))]

    if lo > 0:
        direction = "changing_helps_you"
    elif hi < 0:
        direction = "changing_costs_you"
    else:
        direction = "abstain"

    return {
        **base,
        "available": direction != "abstain",
        "direction": direction,
        "net": net,
        "ci_low": round(lo, 2),
        "ci_high": round(hi, 2),
        "headline": _headline(direction, wr, rw, net, lo, hi),
    }


def _headline(direction: str, wr: int, rw: int, net: int, lo: float, hi: float) -> str:
    if direction == "changing_helps_you":
        return (
            f"Your answer changes went {wr} wrong->right vs {rw} right->wrong "
            f"(net +{net}, 95% CI +{lo:.0f}..+{hi:.0f}) -- on your evidence, "
            f"trusting a considered change has paid off. Not a rule; your data."
        )
    if direction == "changing_costs_you":
        return (
            f"Your answer changes went {wr} wrong->right vs {rw} right->wrong "
            f"(net {net}, 95% CI {lo:.0f}..{hi:.0f}) -- on your evidence, changes "
            f"have cost you more than they gained. Slow the second-guessing."
        )
    return (
        f"{wr} wrong->right vs {rw} right->wrong so far (net {net:+d}, 95% CI "
        f"{lo:.0f}..{hi:.0f}) -- not enough to call either way. Keep going."
    )


def compute_answer_change(
    col: Collection, *, now_ms: int | None = None
) -> dict[str, Any]:
    """Assemble the First-Instinct Ledger from captured section-attempt trajectories.
    JSON-safe; abstains until the min-changes floor. ``now_ms`` accepted for
    signature symmetry (the ledger is not time-windowed)."""
    from lsat.section_runner import read_answer_changes

    changes, n_sections = read_answer_changes(col)
    ledger = answer_change_ledger(changes, seed=1234)
    ledger["n_sections"] = n_sections
    return ledger


# -- self-test ----------------------------------------------------------------


def _make_changes(n: int, p_wr: float, p_rw: float, seed: int) -> list[str]:
    """n changes: each is wrong->right w.p. p_wr, right->wrong w.p. p_rw, else
    wrong->wrong. (p_wr + p_rw <= 1.)"""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        r = rng.random()
        if r < p_wr:
            out.append(WRONG_TO_RIGHT)
        elif r < p_wr + p_rw:
            out.append(RIGHT_TO_WRONG)
        else:
            out.append(WRONG_TO_WRONG)
    return out


def _selftest() -> bool:
    import json

    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: object) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # below the floor -> abstain
    thin = answer_change_ledger(_make_changes(8, 0.6, 0.3, 1), seed=1)
    check(
        "below MIN_CHANGES abstains",
        thin["direction"] == "abstain" and not thin["available"],
    )

    # a strong wrong->right tendency over many changes -> changing_helps_you, CI>0
    helps = answer_change_ledger(_make_changes(120, 0.6, 0.2, 2), seed=7)
    check(
        "strong wrong->right -> changing_helps_you",
        helps["direction"] == "changing_helps_you",
    )
    check("helps CI excludes 0 (lo>0)", helps["ci_low"] > 0)

    # a strong right->wrong tendency -> changing_costs_you, CI<0
    costs = answer_change_ledger(_make_changes(120, 0.2, 0.6, 3), seed=7)
    check(
        "strong right->wrong -> changing_costs_you",
        costs["direction"] == "changing_costs_you",
    )
    check("costs CI excludes 0 (hi<0)", costs["ci_high"] < 0)

    # a balanced 50/50 changer -> abstain most of the time (never fabricate)
    false_dir = 0
    trials = 300
    for i in range(trials):
        r = answer_change_ledger(_make_changes(40, 0.35, 0.35, 1000 + i), seed=2000 + i)
        if r["direction"] != "abstain":
            false_dir += 1
    fp = false_dir / trials
    check(f"balanced changer false-direction {fp:.3f} < 0.05", fp < 0.05)

    # JSON-safe
    try:
        json.dumps(helps)
        json.dumps(thin)
        json_ok = True
    except (TypeError, ValueError):
        json_ok = False
    check("readouts JSON-safe", json_ok)

    passed = sum(1 for _, ok in checks if ok)
    print(f"\n{passed}/{len(checks)} checks passed")
    ok = passed == len(checks)
    print("ANSWER_CHANGE_OK" if ok else "ANSWER_CHANGE_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
