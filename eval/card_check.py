# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Challenge 7f: the AI card-check counts + checker validation (an eval gate).

Reports the three verdict counts over a generated batch with the pre-declared
cutoff (``verdict == CORRECT_USEFUL``), and validates the checker against the
gold set first (false-pass rate). The gate passes only when the checker's
false-pass rate is within ``CHECKER_FALSE_PASS_MAX`` AND the batch clears the
pass-rate/wrong-rate thresholds. Runs offline by default (``OfflineClient``).
"""

from __future__ import annotations

from typing import Any


def _ensure_repo_on_path() -> None:
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


def run(client: Any = None) -> dict[str, Any]:
    _ensure_repo_on_path()
    from eval.config import (
        CARD_CHECK_PASS_RATE_MIN,
        CARD_CHECK_WRONG_RATE_MAX,
        CHECKER_FALSE_PASS_MAX,
    )
    from lsat.ai.checker import validate_checker
    from lsat.ai.client import DEFAULT_MODEL, OfflineClient
    from lsat.ai.gold_set import checker_validation_cases, load_gold_set
    from lsat.ai.pipeline import run_batch

    client = client or OfflineClient()
    # Record which model the checker gate ran against. Offline default is the
    # rule-based stand-in; a live run records the API-resolved id (drift-visible).
    model_used = getattr(client, "model_used", None) or (
        DEFAULT_MODEL
        if type(client).__name__ == "ClaudeClient"
        else "offline-rule-based"
    )

    # 1) Validate the checker before trusting it as a gate.
    validation = validate_checker(checker_validation_cases(), client)
    checker_ok = validation["false_pass_rate"] <= CHECKER_FALSE_PASS_MAX

    # 2) Generate a batch from an original source and count the three verdicts.
    gold = load_gold_set()
    source = " ".join(item["principle"] for item in gold)
    nodes = sorted({item["skill"] for item in gold})
    batch = run_batch([("goldsrc", source)], nodes, client, n_per_source=50)

    passed = checker_ok and batch.gate_passed and not batch.degraded
    return {
        "cutoff": "verdict == CORRECT_USEFUL",
        "verdict_counts": batch.verdict_counts,
        "checked": batch.checked,
        "pass_rate": round(batch.pass_rate, 4),
        "wrong_rate": round(batch.wrong_rate, 4),
        "pass_rate_min": CARD_CHECK_PASS_RATE_MIN,
        "wrong_rate_max": CARD_CHECK_WRONG_RATE_MAX,
        "dropped_unsupported": batch.dropped_unsupported,
        "checker_false_pass_rate": round(validation["false_pass_rate"], 4),
        "checker_false_pass_max": CHECKER_FALSE_PASS_MAX,
        "checker_agreement": round(validation["agreement"], 4),
        "degraded": batch.degraded,
        "model_used": model_used,  # pinned id (never '-latest'); re-gate on change
        "gate_passed": passed,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
