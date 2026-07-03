# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Entry point for the LSAT eval harness (``make eval`` -> ``python -m eval.run``).

Runs every step, writes ``out/eval/report.md`` + ``metrics.json`` +
``manifest.json``, and **exits non-zero if any hard gate fails** -- so generated
content and the readiness display are enabled only when the gate passes ("an
eval that runs before students see anything"). Hard gates: calibration,
performance, score_map, choke_validity, growth, rush, answer_change, leakage,
card_check, worked_example (oracle-verified faded worked examples, research #1),
evil_twin (oracle-proven "skill or luck?" discrimination twins). Report-only (each
maps to a shipped feature, measured at equal study time with a bootstrap CI):
blind_review (F4), feedback (#13 contrast), exam_schedule (#7), fatigue (#10),
adherence (#4), conditional (#19), conditional_chain (r4 #22), quantifier (r3 #1),
triage_leak (r3 #5), stem_polarity (r4 #13), assumption_discrimination (r4 #5),
paraphrase, transfer (H), baselines. The ZPD/interleave ablations run separately
via ``make ablation``.

All step data is seeded synthetic (there are no real students yet); the numbers
demonstrate the metric + gate mechanics, and ``report.md`` says so plainly and
records what did not work.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from eval import config  # noqa: E402


def _adapt_card_check(cc: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "card_check",
        "passed": bool(cc.get("gate_passed")),
        "gate": True,
        "detail": f"counts {cc.get('verdict_counts')} pass_rate={cc.get('pass_rate')} "
        f"wrong_rate={cc.get('wrong_rate')} checker_false_pass="
        f"{cc.get('checker_false_pass_rate')} model={cc.get('model_used')}",
        **cc,
    }


def _adapt_baselines(bl: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "baselines",
        "passed": None,
        "gate": False,
        "detail": f"embedding P@{bl.get('k')}={bl.get('embedding_precision_at_k')} "
        f"vs BM25={bl.get('bm25_precision_at_k')} "
        f"(embedding_wins={bl.get('embedding_wins')})",
        **bl,
    }


def run_all(
    seed: int = config.RANDOM_SEED, out_dir: str | None = None
) -> tuple[list[dict[str, Any]], str]:
    from eval import (
        adherence,
        answer_change,
        assumption_discrimination,
        baselines,
        blind_review,
        calibration,
        card_check,
        choke_validity,
        conditional,
        conditional_chain,
        evil_twin,
        exam_schedule,
        fatigue,
        feedback,
        growth,
        leakage,
        paraphrase,
        performance,
        quantifier,
        rush,
        score_map,
        split,
        stem_polarity,
        transfer,
        triage_leak,
        worked_example,
    )

    out_dir = out_dir or os.path.join(REPO, "out", "eval")
    os.makedirs(out_dir, exist_ok=True)

    results: list[dict[str, Any]] = []
    sp = split.run(out_dir, seed)
    results.append(sp)
    the_split = sp["split"]
    results.append(calibration.run(seed=seed))
    results.append(performance.run(seed=seed))
    results.append(score_map.run(seed=seed))
    results.append(choke_validity.run(seed=seed))
    results.append(blind_review.run(seed=seed))
    results.append(feedback.run(seed=seed))
    results.append(exam_schedule.run(seed=seed))
    results.append(fatigue.run(seed=seed))
    results.append(adherence.run(seed=seed))
    results.append(conditional.run(seed=seed))
    results.append(conditional_chain.run(seed=seed))
    results.append(quantifier.run(seed=seed))
    results.append(growth.run(seed=seed))
    results.append(rush.run(seed=seed))
    results.append(triage_leak.run(seed=seed))
    results.append(stem_polarity.run(seed=seed))
    results.append(assumption_discrimination.run(seed=seed))
    results.append(answer_change.run(seed=seed))
    results.append(paraphrase.run(seed=seed))
    results.append(transfer.run(seed=seed))
    results.append(leakage.run(split=the_split, seed=seed))
    results.append(worked_example.run(seed=seed))
    results.append(evil_twin.run(seed=seed))
    results.append(_adapt_card_check(card_check.run()))
    results.append(_adapt_baselines(baselines.run()))
    return results, out_dir


def _marker(r: dict[str, Any]) -> str:
    if r.get("passed") is True:
        return "PASS"
    if r.get("passed") is False:
        return "FAIL"
    return "----"  # informational / report-only


def _thresholds_md() -> str:
    return (
        "| threshold | value |\n| --- | --- |\n"
        f"| RANDOM_SEED | {config.RANDOM_SEED} |\n"
        f"| ECE_MAX | {config.ECE_MAX} |\n"
        f"| PERF_MIN_DELTA_AUC | {config.PERF_MIN_DELTA_AUC} |\n"
        f"| SCORE_MIN_RANGE_POINTS | {config.SCORE_MIN_RANGE_POINTS} |\n"
        f"| LEAK_COSINE_MAX | {config.LEAK_COSINE_MAX} |\n"
        f"| CARD_CHECK_PASS_RATE_MIN | {config.CARD_CHECK_PASS_RATE_MIN} |\n"
        f"| CARD_CHECK_WRONG_RATE_MAX | {config.CARD_CHECK_WRONG_RATE_MAX} |\n"
        f"| CHECKER_FALSE_PASS_MAX | {config.CHECKER_FALSE_PASS_MAX} |\n"
    )


def _reliability_md(cal: dict[str, Any]) -> str:
    rows = ["| bin | n | predicted | observed |", "| --- | --- | --- | --- |"]
    for b in cal.get("reliability", []):
        rows.append(f"| {b['bin']} | {b['n']} | {b['pred']} | {b['obs']} |")
    return "\n".join(rows)


def _what_didnt_work(results: dict[str, dict[str, Any]]) -> list[str]:
    notes = [
        "All step inputs are **seeded synthetic data** -- there are no real "
        "students yet. The numbers demonstrate the metric + gate mechanics, not "
        "field performance; real held-out reviews/items would replace the "
        "generators unchanged.",
    ]
    cal = results.get("calibration", {})
    if cal:
        notes.append(
            f"The gate has teeth: an **overconfident** predictor scores "
            f"ECE={cal.get('overconfident_ece')} (> {config.ECE_MAX}) and would "
            f"fail calibration, vs the calibrated model's {cal.get('ece')}."
        )
    para = results.get("paraphrase", {})
    if para:
        notes.append(
            f"The paraphrase gap ({para.get('gap')}) is driven by a **modeled** "
            "recognition->application penalty; with real reworded items it may "
            "shrink. A near-zero gap would mean the performance model is copying "
            "the memory model -- reported either way."
        )
    bl = results.get("baselines", {})
    if bl and not bl.get("embedding_wins"):
        notes.append(
            "Retrieval: the offline TF-IDF embedder did **not** beat BM25 here "
            f"({bl.get('embedding_precision_at_k')} vs {bl.get('bm25_precision_at_k')}) "
            "-- an honest negative; a real semantic embedder plugs in to win."
        )
    elif bl:
        notes.append(
            "Retrieval: the offline TF-IDF embedder is lexical; its win over BM25 "
            f"({bl.get('embedding_precision_at_k')} vs {bl.get('bm25_precision_at_k')}) "
            "is modest and would be larger with a real semantic embedder."
        )
    return notes


def write_report(results: list[dict[str, Any]], out_dir: str) -> str:
    by_name = {r["name"]: r for r in results}
    hard_fail = [r for r in results if r.get("gate") and r.get("passed") is False]
    lines: list[str] = []
    lines.append("# Anki for LSAT -- evaluation report\n")
    lines.append(
        f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')} "
        f"(seed {config.RANDOM_SEED}; reproducible via `make eval`)._\n"
    )
    verdict = "GATE FAILED" if hard_fail else "GATE OK"
    lines.append(f"**{verdict}** -- {len(hard_fail)} hard gate(s) failed.\n")

    lines.append("## Pre-declared thresholds\n")
    lines.append(_thresholds_md())

    lines.append("\n## Steps\n")
    lines.append("| step | result | detail |")
    lines.append("| --- | --- | --- |")
    for r in results:
        gate = "gate" if r.get("gate") else "report"
        lines.append(f"| {r['name']} ({gate}) | {_marker(r)} | {r.get('detail', '')} |")

    if "calibration" in by_name:
        lines.append("\n## Calibration reliability diagram\n")
        lines.append(_reliability_md(by_name["calibration"]))

    lines.append("\n## What didn't work / honest negatives\n")
    for note in _what_didnt_work(by_name):
        lines.append(f"- {note}")

    report = "\n".join(lines) + "\n"
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    serialisable = [{k: v for k, v in r.items() if k != "split"} for r in results]
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(serialisable, fh, indent=2, sort_keys=True, default=str)
    return report


def main() -> int:
    results, out_dir = run_all()
    write_report(results, out_dir)

    print("Anki for LSAT -- eval harness\n")
    for r in results:
        print(f"  [{_marker(r)}] {r['name']}: {r.get('detail', '')}")
    hard_fail = [r for r in results if r.get("gate") and r.get("passed") is False]
    print()
    print(f"report: {os.path.join(out_dir, 'report.md')}")
    if hard_fail:
        names = ", ".join(r["name"] for r in hard_fail)
        print(f"\nGATE FAILED: {names}")
        return 1
    print("\nGATE OK: all hard gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
