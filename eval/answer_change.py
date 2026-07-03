# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""First-Instinct Ledger validity gate (DECISION-round4 #17), a HARD gate.

The answer-change diagnostic (:func:`lsat.answer_change.answer_change_ledger`)
makes no learning claim, so the gate is an estimator-validity gate (like
``eval/rush.py``):

  * FALSE-DIRECTION -- on a 50/50 changer (answer changes equally likely to be
    wrong->right or right->wrong), the CI-gated ledger must claim a direction at
    most ``ANSWER_CHANGE_FALSE_DIRECTION_MAX`` of the time. This is the guarantee
    that it never fabricates "changing helps/hurts you" out of noise, and never
    parrots the population base rate.
  * DETECTION -- on a planted ~2:1 wrong->right changer, it must recover the
    correct direction (changing_helps_you, CI excludes 0) at least
    ``ANSWER_CHANGE_DETECTION_MIN`` of the time.

Ships ON only if both hold. No learning-effect claim here; any score benefit of
practicing on the section runner is a separately-deferred equal-study-time arm.
All inputs are seeded synthetic.
"""

from __future__ import annotations

import random

from eval import config
from lsat.answer_change import (
    RIGHT_TO_WRONG,
    WRONG_TO_RIGHT,
    WRONG_TO_WRONG,
    answer_change_ledger,
)

N_LEARNERS = 400
# Detection (power) is measured at a MATURE volume (~100 answer changes ~= many
# timed sections): the CI-gated ledger deliberately abstains on thin data, so on a
# handful of changes it neither detects nor false-flags -- the honest failure mode.
# The false-direction arm holds at ANY volume (it is CI-gated), which is the
# property that actually protects the learner from a fabricated verdict.
N_CHANGES = 100
# 50/50 null and a planted ~2:1 wrong->right tendency.
NULL = (0.35, 0.35)
PLANTED = (0.50, 0.25)


def _changes(rng: random.Random, p_wr: float, p_rw: float) -> list[str]:
    out = []
    for _ in range(N_CHANGES):
        r = rng.random()
        if r < p_wr:
            out.append(WRONG_TO_RIGHT)
        elif r < p_wr + p_rw:
            out.append(RIGHT_TO_WRONG)
        else:
            out.append(WRONG_TO_WRONG)
    return out


def run(seed: int = config.RANDOM_SEED) -> dict:
    rng = random.Random(seed)
    false_dir = 0
    for _ in range(N_LEARNERS):
        r = answer_change_ledger(_changes(rng, *NULL), seed=rng.randrange(1 << 30))
        if r["direction"] != "abstain":
            false_dir += 1
    fp_rate = false_dir / N_LEARNERS

    detected = 0
    for _ in range(N_LEARNERS):
        r = answer_change_ledger(_changes(rng, *PLANTED), seed=rng.randrange(1 << 30))
        if r["direction"] == "changing_helps_you":
            detected += 1
    detect_rate = detected / N_LEARNERS

    passed = (
        fp_rate <= config.ANSWER_CHANGE_FALSE_DIRECTION_MAX
        and detect_rate >= config.ANSWER_CHANGE_DETECTION_MIN
    )
    detail = (
        f"50/50-changer false-direction {fp_rate:.3f} "
        f"(max {config.ANSWER_CHANGE_FALSE_DIRECTION_MAX}); planted 2:1 detection "
        f"{detect_rate:.3f} (min {config.ANSWER_CHANGE_DETECTION_MIN}) -> "
        f"{'ledger ON' if passed else 'ledger OFF (mechanics unmet)'}"
    )
    return {
        "name": "answer_change",
        "passed": bool(passed),
        "gate": True,
        "detail": detail,
        "false_direction_rate": round(fp_rate, 4),
        "detection_rate": round(detect_rate, 4),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
