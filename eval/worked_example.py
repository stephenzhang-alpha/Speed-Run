# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Oracle-Verified Faded Worked Examples (research feature #1) -- a HARD gate.

The feature's promise is "generate-with-a-proof": an LLM may draft a derivation,
but the exact material-entailment oracle (``lsat.conditional_chain.entails``)
blocks anything that does not verify. This gate proves the safety property that
makes that promise real, then reports the (synthetic) equal-time learning arm.

**Hard safety gate (must be exactly 0 false-passes):**

1. *Planted-wrong* derivations (empty, forged citation, illegal jump, truncated,
   affirming-the-consequent) are all BLOCKED by :func:`verify_worked_example`.
2. *Fuzz*: over many random chains, candidates, and random proposed derivations,
   **no derivation the gate ACCEPTS ever corresponds to a non-entailed goal** --
   checked against the independent :func:`entails` oracle (a verify() bug that
   accepted a bogus proof would show up as an accepted-but-not-entailed case).
3. *Build round-trip*: every reachable must-follow item builds an example whose
   steps re-verify; every does-not-follow item abstains (fail-closed).
4. *Malicious drafter*: :func:`draft_and_verify` driven by an adversarial client
   (returns wrong moves) never serves an unverified example -- it degrades to the
   oracle-correct deterministic derivation.

**Report arm (report-only, equal study time, bootstrap CI):** a synthetic IRT
simulation of faded worked examples vs worked-only vs solve-only on held-out
chain-inference accuracy. The GAIN values are disclosed synthetic parameters (a
backward-fading edge over plain worked examples, per Atkinson et al. 2003), never
evidence; the arm demonstrates the equal-time + bootstrap-CI mechanism and is
report-only (no gate rides on it). Real learners settle the magnitude.
"""

from __future__ import annotations

import math
import random
from typing import Any

from eval import config
from eval.metrics import bootstrap_ci

# -- report arm parameters (synthetic; disclosed) -----------------------------
N_LEARNERS = 300
STUDY_TIME_S = 900  # equal WALL-CLOCK budget per learner (faded costs less/step)
N_HELDOUT = 24
DIFFICULTIES = (-0.7, 0.0, 0.7, 1.1)
# Per-event learning gain and per-event time cost. Faded worked examples have a
# small per-event edge over plain worked examples (fading + self-explanation) AND
# cost less time than cold solving -> more events fit the equal budget. Solve-only
# has the highest per-event cost. All are synthetic parameters, not measurements.
GAIN = {"faded": 0.150, "worked": 0.120, "solve": 0.095}
COST_S = {"faded": 40.0, "worked": 45.0, "solve": 70.0}


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def _skill_after(rng: random.Random, arm: str) -> float:
    skill = rng.uniform(-1.3, -0.3)
    events = int(STUDY_TIME_S / COST_S[arm])  # equal TIME -> arm-dependent #events
    g = GAIN[arm]
    for _ in range(events):
        skill += g * rng.uniform(0.6, 1.4) * (1.0 - _sigmoid(skill))
    return skill


def _heldout_accuracy(rng: random.Random, skill: float) -> float:
    correct = 0
    for i in range(N_HELDOUT):
        d = DIFFICULTIES[i % len(DIFFICULTIES)]
        if rng.random() < _sigmoid(0.75 * skill - d):
            correct += 1
    return correct / N_HELDOUT


def _report_arm(seed: int) -> dict[str, Any]:
    per_arm: dict[str, list[float]] = {a: [] for a in GAIN}
    faded_minus_worked: list[float] = []
    for i in range(N_LEARNERS):
        skills = {a: _skill_after(random.Random(seed + i), a) for a in GAIN}
        acc = {
            a: _heldout_accuracy(random.Random(seed + 5000 + i), skills[a])
            for a in GAIN
        }
        for a in GAIN:
            per_arm[a].append(acc[a])
        faded_minus_worked.append(acc["faded"] - acc["worked"])
    means = {a: sum(v) / len(v) for a, v in per_arm.items()}
    lo, hi = bootstrap_ci(faded_minus_worked, seed=seed)
    mean_diff = sum(faded_minus_worked) / len(faded_minus_worked)
    return {
        "means": {a: round(means[a], 4) for a in GAIN},
        "faded_minus_worked": round(mean_diff, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "ship_recommended": lo > 0.0,
        "events": {a: int(STUDY_TIME_S / COST_S[a]) for a in GAIN},
    }


# -- hard safety gate ----------------------------------------------------------


def _planted_false_passes() -> tuple[int, int]:
    """Count planted-wrong derivations the gate wrongly ACCEPTS (must be 0) over a
    total. Uses every curated must-follow item as the substrate."""
    from lsat.conditional_chain import CHAIN_ITEMS, MUST_FOLLOW, Implication
    from lsat.worked_example import build_worked_example, verify_worked_example

    false_pass = total = 0
    for it in CHAIN_ITEMS:
        if it["verdict"] != MUST_FOLLOW:
            continue
        chain, cand = it["chain"], it["candidate"]
        ex = build_worked_example(chain, cand)
        if not ex.get("available"):
            continue
        good = ex["steps"]
        planted: list[Any] = [
            [],  # empty
            good[:-1] if len(good) >= 2 else [],  # truncated -> never reaches goal
            # forged premise citation on the first step
            [
                {**good[0], "impl_index": (good[0]["impl_index"] + 1) % len(chain)},
                *good[1:],
            ],
            # reversed candidate handed a "derivation": affirming the consequent
            [{**s} for s in good],  # (checked below against the reversed goal)
        ]
        for bad in planted[:3]:
            total += 1
            if verify_worked_example(chain, cand, bad)["verified"]:
                false_pass += 1
        # affirming the consequent: the reversed goal must never verify with ANY steps
        rev = Implication(cand.cons, cand.ante)
        total += 1
        if verify_worked_example(chain, rev, good)["verified"]:
            false_pass += 1
    return false_pass, total


def _fuzz_false_passes(seed: int, trials: int = 3000) -> dict[str, int]:
    """Three adversarial streams against the gate, each cross-checked with the
    INDEPENDENT :func:`entails` oracle:

    * *guided-valid* -- a random walk over real edges from a start literal builds a
      derivation that IS a valid proof of ``start -> end`` by construction; the gate
      MUST accept it (positive coverage: proves the gate is not vacuously safe by
      rejecting everything). A rejected valid walk is a false-NEGATIVE bug.
    * *goal-swap* -- feed that same valid walk but with the goal swapped to a
      different literal the walk does not reach; the gate MUST reject. If it
      accepts and the swapped goal is not entailed, that is a false-PASS.
    * *random* -- fully random derivations from the real edge vocabulary against a
      random goal; any accepted-but-not-entailed case is a false-PASS.

    Safety invariant (gated): **no accepted derivation ever corresponds to a
    non-entailed goal** -> ``false_pass == 0``.
    """
    from lsat.conditional_chain import Implication, Lit, entails
    from lsat.worked_example import _provenance_edges, verify_worked_example

    rng = random.Random(seed)
    false_pass = accepted = valid_walks = valid_accepted = 0
    for _ in range(trials):
        nterms = rng.randint(3, 5)
        k = rng.randint(2, 4)
        chain = [
            Implication(Lit(a, rng.random() < 0.3), Lit(b, rng.random() < 0.3))
            for a, b in (rng.sample(range(nterms), 2) for _ in range(k))
        ]
        edges = _provenance_edges(chain)

        # -- stream 1: guided valid walk (positive coverage) ------------------
        start_edge = rng.choice(edges)
        frontier = start_edge[0]
        start = frontier
        walk: list[dict[str, Any]] = []
        for _ in range(rng.randint(1, 4)):
            outgoing = [e for e in edges if e[0] == frontier]
            if not outgoing:
                break
            a, b, idx, contra = rng.choice(outgoing)
            walk.append(
                {"from": a, "to": b, "impl_index": idx, "contrapositive": contra}
            )
            frontier = b
        if walk:
            end = walk[-1]["to"]
            cand = Implication(start, end)
            valid_walks += 1
            v = verify_worked_example(chain, cand, walk)
            if v["verified"]:
                valid_accepted += 1
                accepted += 1
                if not entails(chain, cand):  # must never happen
                    false_pass += 1
            # -- stream 2: goal-swap adversarial --------------------------------
            others = [
                Lit(t, neg)
                for t in range(nterms)
                for neg in (False, True)
                if Lit(t, neg) != end
            ]
            if others:
                bogus = rng.choice(others)
                cand_b = Implication(start, bogus)
                vb = verify_worked_example(chain, cand_b, walk)
                if vb["verified"]:
                    accepted += 1
                    if not entails(chain, cand_b):
                        false_pass += 1

        # -- stream 3: fully random derivation --------------------------------
        ca, cb = rng.sample(range(nterms), 2)
        cand_r = Implication(Lit(ca, rng.random() < 0.3), Lit(cb, rng.random() < 0.3))
        steps = []
        for _ in range(rng.randint(1, 5)):
            a, b, idx, contra = rng.choice(edges)
            steps.append(
                {"from": a, "to": b, "impl_index": idx, "contrapositive": contra}
            )
        if verify_worked_example(chain, cand_r, steps)["verified"]:
            accepted += 1
            if not entails(chain, cand_r):
                false_pass += 1
    return {
        "false_pass": false_pass,
        "accepted": accepted,
        "valid_walks": valid_walks,
        "valid_accepted": valid_accepted,
    }


def _build_and_malicious_ok() -> dict[str, Any]:
    from lsat.conditional_chain import CHAIN_ITEMS, DOES_NOT_FOLLOW, MUST_FOLLOW
    from lsat.worked_example import (
        build_worked_example,
        draft_and_verify,
        verify_worked_example,
    )

    class MaliciousClient:
        """Returns a plausible-but-wrong derivation (all premises, reversed)."""

        def __init__(self, n: int) -> None:
            self._n = n

        def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
            import json

            return json.dumps(
                [
                    {"premise": i, "contrapositive": False}
                    for i in range(self._n - 1, -1, -1)
                ]
            )

    roundtrip_ok = dnf_abstain_ok = malicious_safe = True
    built = 0
    for it in CHAIN_ITEMS:
        chain, cand = it["chain"], it["candidate"]
        if it["verdict"] == MUST_FOLLOW:
            ex = build_worked_example(chain, cand)
            if ex.get("available"):
                built += 1
                if not verify_worked_example(chain, cand, ex["steps"])["verified"]:
                    roundtrip_ok = False
                # malicious drafter must never serve an unverified example
                served = draft_and_verify(
                    chain, cand, client=MaliciousClient(len(chain))
                )
                if (
                    not served.get("available")
                    or not verify_worked_example(chain, cand, served["steps"])[
                        "verified"
                    ]
                ):
                    malicious_safe = False
        elif it["verdict"] == DOES_NOT_FOLLOW:
            if build_worked_example(chain, cand).get("available"):
                dnf_abstain_ok = False
    return {
        "built": built,
        "roundtrip_ok": roundtrip_ok,
        "dnf_abstain_ok": dnf_abstain_ok,
        "malicious_safe": malicious_safe,
    }


def run(seed: int = config.RANDOM_SEED) -> dict[str, Any]:
    planted_fp, planted_total = _planted_false_passes()
    fuzz = _fuzz_false_passes(seed)
    fuzz_fp, fuzz_accepted = fuzz["false_pass"], fuzz["accepted"]
    inv = _build_and_malicious_ok()
    report = _report_arm(seed)

    false_pass_rate = (planted_fp + fuzz_fp) / max(1, planted_total + fuzz_accepted)
    # positive coverage: every guided VALID walk (a proof by construction) must be
    # accepted -- proves the gate is not vacuously safe by rejecting everything.
    coverage_ok = (
        fuzz["valid_walks"] > 0 and fuzz["valid_accepted"] == fuzz["valid_walks"]
    )
    safety_ok = (
        planted_fp == 0
        and fuzz_fp == 0
        and false_pass_rate <= config.WORKED_STEP_FALSE_PASS_MAX
        and coverage_ok
        and inv["roundtrip_ok"]
        and inv["dnf_abstain_ok"]
        and inv["malicious_safe"]
    )
    ship = report["ship_recommended"]
    detail = (
        f"oracle gate: planted false-pass {planted_fp}/{planted_total}, "
        f"fuzz false-pass {fuzz_fp}/{fuzz_accepted} accepted "
        f"(valid-walk coverage {fuzz['valid_accepted']}/{fuzz['valid_walks']}) "
        f"(max {config.WORKED_STEP_FALSE_PASS_MAX}); built {inv['built']} examples "
        f"(round-trip={inv['roundtrip_ok']}, dnf-abstain={inv['dnf_abstain_ok']}, "
        f"malicious-safe={inv['malicious_safe']}). REPORT arm (equal "
        f"{STUDY_TIME_S}s): faded {report['means']['faded']} vs worked "
        f"{report['means']['worked']} vs solve {report['means']['solve']}; "
        f"faded-worked {report['faded_minus_worked']:+.3f} "
        f"(95% CI {report['ci_low']:+.3f}..{report['ci_high']:+.3f}) -> "
        f"{'ship (CI excludes 0)' if ship else 'null at equal time (report-only)'}"
    )
    return {
        "name": "worked_example",
        "passed": bool(safety_ok),
        "gate": True,
        "detail": detail,
        "planted_false_pass": planted_fp,
        "planted_total": planted_total,
        "fuzz_false_pass": fuzz_fp,
        "fuzz_accepted": fuzz_accepted,
        "fuzz_valid_walks": fuzz["valid_walks"],
        "fuzz_valid_accepted": fuzz["valid_accepted"],
        "coverage_ok": coverage_ok,
        "false_pass_rate": round(false_pass_rate, 6),
        "false_pass_max": config.WORKED_STEP_FALSE_PASS_MAX,
        "built": inv["built"],
        "roundtrip_ok": inv["roundtrip_ok"],
        "dnf_abstain_ok": inv["dnf_abstain_ok"],
        "malicious_safe": inv["malicious_safe"],
        "report_means": report["means"],
        "report_events": report["events"],
        "faded_minus_worked": report["faded_minus_worked"],
        "ci_low": report["ci_low"],
        "ci_high": report["ci_high"],
        "ship_recommended": ship,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
