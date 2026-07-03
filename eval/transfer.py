# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The Transfer Meter (honesty layer): memorization-vs-transfer per schema.

Report-only (not a hard gate), like ``eval/paraphrase.py``. The LSAT is one
argument-structure skill applied across endless surface topics, so a student who
is right on "the vaccine causal flaw" but wrong on "the ad-revenue causal flaw"
has *memorized*, not *learned*. This step refuses to call a ``struct.*`` schema
"transferred" until the learner is right on **new surface topics**, not just the
drilled ones.

The instrument (per ``research/debate/DECISION.md`` §3, Honesty layer):

* **surface distance** ``d = 1 - cosine_surface(item, seen)`` -- the tf-idf/cosine
  machinery is reused verbatim from ``eval/leakage.py``, with logical-marker
  tokens (``if``/``therefore``/``because``...) down-weighted so a shared *structure*
  never counts as shared *surface*;
* **memorization_gap** ``= P(correct | near surface) - P(correct | far surface)``,
  with a percentile ``bootstrap_ci`` (``eval/metrics.py``);
* **transfer_index** ``= P(correct | far surface)`` -- the honest far-transfer number;
* **structure_slope** ``beta`` from a fit ``P(correct) ~ a + beta*d`` (more negative
  = more surface-dependent = more memorized).

Synthetic, seeded learners here (there are no real students yet): P(correct)
depends on schema mastery MINUS a surface-distance penalty, so a pure memorizer
has near-zero far-surface accuracy while a transferrer has a small gap. The
penalty is a documented, adjustable assumption. Transfer is reported as a
**distance-graded curve, never a single far-transfer number** (Barnett & Ceci
2002); structure-vs-surface is the classic expertise read-out (Chi, Feltovich &
Glaser 1981) and schema quality predicts transfer (Gick & Holyoak 1983). A
self-check plants a pure memorizer (large gap, CI excludes 0) against a
transferrer (gap ~0, CI includes 0) so the "learned" badge is trustworthy rather
than a meter that cannot see -- mirroring the leakage detector self-test.
"""

from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import dataclass
from typing import Any

from eval import config
from eval.leakage import _cosine, _idf, _vec  # reuse the tf-idf/cosine machinery
from eval.metrics import bootstrap_ci
from lsat.retrieval import tokenize
from lsat.taxonomy import load_taxonomy

# -- synthetic-item generation (fully determined by schema + grid) -------------
_K = 8  # surface words in the drilled ("anchor") vocabulary of a schema
_FAR_POOL = 40  # distinct far-surface words per schema (rotated across topics)
_LEVELS = 9  # surface-overlap levels: m = 0..8 anchor words kept (f = m / _K)
_BAND_LEVELS = 3  # overlap levels that count as the near (and the far) condition
_TOPICS_PER_LEVEL = 4  # distinct surface topics at each overlap level
_ITEMS_PER_TOPIC = 5  # synthetic attempts per surface topic
_SEEN_REFS = 3  # drilled reference items per schema (pure anchor surface)
_MARKERS_PER_ITEM = 4  # logical-marker tokens injected per item (down-weighted)

# -- measurement knobs ---------------------------------------------------------
# Transfer is a *designed* near/far manipulation (top vs bottom surface-overlap
# levels), with the measured cosine distance kept as the honest covariate for
# the slope/curve and the leakage-gate check (Barnett & Ceci 2002: graded).
_MARKER_DOWNWEIGHT = 0.15  # structure words count this little toward surface
_CURVE_BINS = 8  # bins for the distance-graded transfer curve
_EPS = 1e-12

# Logical-marker (structure) tokens per schema. These are shared *within* a
# schema across every surface, so if they counted as surface, same-structure
# items would look artificially "near". Down-weighting them isolates surface.
_SCHEMA_MARKERS: dict[str, list[str]] = {
    "struct.causal": [
        "causes",
        "because",
        "therefore",
        "effect",
        "leads",
        "results",
        "due",
    ],
    "struct.conditional": [
        "if",
        "then",
        "only",
        "unless",
        "must",
        "necessary",
        "sufficient",
    ],
    "struct.analogy": [
        "like",
        "similar",
        "analogous",
        "resembles",
        "likewise",
        "parallel",
    ],
    "struct.statistical": [
        "sample",
        "most",
        "percent",
        "average",
        "population",
        "generalize",
    ],
    "struct.parts_whole": [
        "each",
        "every",
        "whole",
        "part",
        "composed",
        "collectively",
        "member",
    ],
    "struct.comparison": [
        "than",
        "more",
        "less",
        "versus",
        "proportion",
        "compared",
        "relative",
    ],
    "struct.principle_application": [
        "principle",
        "rule",
        "general",
        "applies",
        "whenever",
        "governs",
    ],
}
_LOGICAL_MARKERS: frozenset[str] = frozenset(
    m for markers in _SCHEMA_MARKERS.values() for m in markers
)
_GENERIC_MARKERS = ["because", "therefore", "if", "then", "thus", "hence"]


@dataclass(frozen=True)
class Learner:
    """A seeded synthetic learner.

    ``surface_penalty`` is the true surface-dependence: ``0.0`` is a pure
    transferrer (accuracy independent of surface distance), a large value is a
    pure memorizer (far-surface accuracy collapses to near zero).
    """

    name: str
    base_ability: float
    surface_penalty: float
    ability_spread: float = 0.06


_DEFAULT_LEARNER = Learner("partial-transfer", base_ability=0.82, surface_penalty=0.35)
_MEMORIZER = Learner("pure-memorizer", base_ability=0.88, surface_penalty=0.95)
_TRANSFERRER = Learner("pure-transfer", base_ability=0.85, surface_penalty=0.0)


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _schema_ability(learner: Learner, idx: int, n: int) -> float:
    """A deterministic per-schema mastery spread around ``base_ability``."""
    if n <= 1:
        offset = 0.0
    else:
        offset = (idx - (n - 1) / 2.0) / ((n - 1) / 2.0)  # in [-1, 1]
    return _clip(learner.base_ability + learner.ability_spread * offset, 0.5, 0.98)


def _markers_for(schema_id: str) -> list[str]:
    markers = _SCHEMA_MARKERS.get(schema_id, []) + _GENERIC_MARKERS
    return markers[:_MARKERS_PER_ITEM]


def _band_for_level(k: int) -> str:
    """Designed transfer condition for overlap level ``k`` (= anchor words kept)."""
    if k >= _LEVELS - _BAND_LEVELS:  # most surface overlap -> drilled/near
        return "near"
    if k < _BAND_LEVELS:  # least surface overlap -> held-out/far
        return "far"
    return "mid"


def _generate(
    schema_index: int, schema_id: str
) -> tuple[list[str], list[dict[str, Any]]]:
    """Return ``(seen_texts, items)`` for one schema.

    Surface overlap with the drilled vocabulary is swept from full (near) to
    none (far); a schema keeps ``m`` of ``_K`` anchor words and fills the rest
    from a disjoint far pool, so the measured tf-idf cosine tracks ``m / _K``.
    Each item records its designed ``band`` and its surface ``topic`` id.
    """
    anchor = [f"s{schema_index}a{i}" for i in range(_K)]
    far_pool = [f"s{schema_index}z{i}" for i in range(_FAR_POOL)]
    markers = _markers_for(schema_id)

    seen_texts = [" ".join(anchor + markers) for _ in range(_SEEN_REFS)]

    items: list[dict[str, Any]] = []
    for k in range(_LEVELS):
        m = k  # anchor words kept; nominal surface overlap f = m / _K
        far_count = _K - m
        band = _band_for_level(k)
        for t in range(_TOPICS_PER_LEVEL):
            start = ((k * _TOPICS_PER_LEVEL + t) * _K) % _FAR_POOL
            far_sel = [far_pool[(start + j) % _FAR_POOL] for j in range(far_count)]
            words = anchor[:m] + far_sel + markers
            text = " ".join(words)
            topic = f"{schema_index}:{k}:{t}"
            for _ in range(_ITEMS_PER_TOPIC):
                items.append({"text": text, "band": band, "topic": topic})
    return seen_texts, items


def _ols_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope of ``y ~ a + beta*x`` (0.0 if x has no spread)."""
    n = len(xs)
    if n == 0:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= _EPS:
        return 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx


def _curve(records: list[dict[str, Any]], n_bins: int) -> list[dict[str, Any]]:
    """Distance-graded accuracy curve (Barnett & Ceci: never a single number)."""
    counts = [0] * n_bins
    sums = [0.0] * n_bins
    for r in records:
        idx = min(n_bins - 1, int(r["d"] * n_bins))
        counts[idx] += 1
        sums[idx] += r["correct"]
    out: list[dict[str, Any]] = []
    for i in range(n_bins):
        c = counts[i]
        out.append(
            {
                "d_lo": round(i / n_bins, 3),
                "d_hi": round((i + 1) / n_bins, 3),
                "mean_correct": round(sums[i] / c, 4) if c else None,
                "n": c,
            }
        )
    return out


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _measure(learner: Learner, seed: int) -> dict[str, Any]:
    """Run the Transfer Meter for one synthetic learner; return the report dict."""
    rng = random.Random(seed)
    tax = load_taxonomy()
    schemas = tax.structures
    n_schemas = len(schemas)

    # Build every item first so the idf (like leakage) spans the whole corpus.
    built: list[tuple[int, Any, list[str], list[dict[str, Any]]]] = []
    all_texts: list[str] = []
    for idx, sc in enumerate(schemas):
        seen_texts, items = _generate(idx, sc.id)
        built.append((idx, sc, seen_texts, items))
        all_texts.extend(seen_texts)
        all_texts.extend(it["text"] for it in items)
    idf = _idf([tokenize(t) for t in all_texts])

    records: list[dict[str, Any]] = []
    for idx, sc, seen_texts, items in built:
        seen_vecs = [_surface_vec(t, idf) for t in seen_texts]
        ability = _schema_ability(learner, idx, n_schemas)
        for it in items:
            vec = _surface_vec(it["text"], idf)
            cos = max((_cosine(vec, sv) for sv in seen_vecs), default=0.0)
            d = _clip(1.0 - cos, 0.0, 1.0)
            p = _clip(ability - learner.surface_penalty * d, 0.02, 0.98)
            correct = 1 if rng.random() < p else 0
            records.append(
                {
                    "schema": sc.id,
                    "name": sc.name,
                    "d": d,
                    "correct": correct,
                    "band": it["band"],
                    "topic": it["topic"],
                }
            )

    return _summarize(learner, schemas, records, seed)


def _surface_vec(text: str, idf: dict[str, float]) -> dict[str, float]:
    """tf-idf vector (via ``eval.leakage._vec``) with logical markers down-weighted.

    Structure words are shared across surfaces within a schema; down-weighting
    them keeps the cosine a measure of *surface* similarity, not *structure*.
    """
    vec = _vec(tokenize(text), idf)
    if not vec:
        return vec
    scaled = {
        t: (w * _MARKER_DOWNWEIGHT if t in _LOGICAL_MARKERS else w)
        for t, w in vec.items()
    }
    norm = math.sqrt(sum(v * v for v in scaled.values())) or 1.0
    return {t: v / norm for t, v in scaled.items()}


def _topic_accuracies(
    records: list[dict[str, Any]],
) -> tuple[dict[str, float], dict[str, tuple[str, str]]]:
    """Collapse item outcomes to one accuracy per surface topic."""
    correct: dict[str, list[float]] = {}
    meta: dict[str, tuple[str, str]] = {}
    for r in records:
        correct.setdefault(r["topic"], []).append(r["correct"])
        meta[r["topic"]] = (r["schema"], r["band"])
    return {tp: _mean(cs) for tp, cs in correct.items()}, meta


def _summarize(
    learner: Learner, schemas: list[Any], records: list[dict[str, Any]], seed: int
) -> dict[str, Any]:
    topic_acc, topic_meta = _topic_accuracies(records)

    # The bootstrap unit is a within-schema (near topic, far topic) pair -- the
    # topic level generalises the paraphrase.py per-card gap, giving many more
    # units than the 7 schemas so the CI actually covers (a schema-only cluster
    # bootstrap undercovers the pure-transfer null). Bands are balanced by
    # construction (equal near/far topics per schema), so the mean of the paired
    # gaps equals near_accuracy - transfer_index exactly.
    per_schema: list[dict[str, Any]] = []
    gap_units: list[float] = []
    all_near: list[float] = []
    all_far: list[float] = []
    for sc in schemas:
        near_tps = sorted(
            tp for tp, (s, b) in topic_meta.items() if s == sc.id and b == "near"
        )
        far_tps = sorted(
            tp for tp, (s, b) in topic_meta.items() if s == sc.id and b == "far"
        )
        near_accs = [topic_acc[tp] for tp in near_tps]
        far_accs = [topic_acc[tp] for tp in far_tps]
        all_near.extend(near_accs)
        all_far.extend(far_accs)
        for na, fa in zip(near_accs, far_accs):  # equal length by construction
            gap_units.append(na - fa)

        srecs = [r for r in records if r["schema"] == sc.id]
        s_near_acc = _mean(near_accs)
        s_far_acc = _mean(far_accs)
        s_gap = s_near_acc - s_far_acc
        per_schema.append(
            {
                "schema": sc.id,
                "name": sc.name,
                "near_accuracy": round(s_near_acc, 4),
                "transfer_index": round(s_far_acc, 4),
                "memorization_gap": round(s_gap, 4),
                "structure_slope": round(
                    _ols_slope([r["d"] for r in srecs], [r["correct"] for r in srecs]),
                    4,
                ),
                "n_near_topics": len(near_accs),
                "n_far_topics": len(far_accs),
                "badge": "memorized-here" if s_gap > 0.15 else "transferred",
            }
        )

    near_acc = _mean(all_near)
    far_acc = _mean(all_far)
    gap = near_acc - far_acc
    lo, hi = bootstrap_ci(gap_units, seed)
    beta = _ols_slope([r["d"] for r in records], [r["correct"] for r in records])

    near_recs = [r for r in records if r["band"] == "near"]
    far_recs = [r for r in records if r["band"] == "far"]
    near_mean_d = _mean([r["d"] for r in near_recs])
    far_mean_d = _mean([r["d"] for r in far_recs])
    # The far/held-out surface must stay below the leakage cosine gate, so no
    # surface wording leaks into the transfer set (DECISION §3.f).
    max_far_cos = max((1.0 - r["d"] for r in far_recs), default=0.0)
    heldout_below_leak_gate = max_far_cos < config.LEAK_COSINE_MAX

    return {
        "name": "transfer",
        "passed": None,  # report-only, never a hard gate
        "gate": False,
        "learner": learner.name,
        "memorization_gap": round(gap, 4),
        "memorization_gap_ci": [round(lo, 4), round(hi, 4)],
        "transfer_index": round(far_acc, 4),
        "near_accuracy": round(near_acc, 4),
        "structure_slope": round(beta, 4),
        "n_schemas": len(schemas),
        "n_items": len(records),
        "n_gap_units": len(gap_units),
        "n_near_topics": len(all_near),
        "n_far_topics": len(all_far),
        "near_mean_distance": round(near_mean_d, 4),
        "far_mean_distance": round(far_mean_d, 4),
        "marker_downweight": _MARKER_DOWNWEIGHT,
        "leak_cosine_max": config.LEAK_COSINE_MAX,
        "max_far_surface_cosine": round(max_far_cos, 4),
        "heldout_below_leak_gate": bool(heldout_below_leak_gate),
        "curve": _curve(records, _CURVE_BINS),
        "per_schema": per_schema,
        "detail": (
            f"near-surface {near_acc:.2f} vs far-surface {far_acc:.2f} -> "
            f"memorization gap {gap:+.2f} (95% CI {lo:+.2f}..{hi:+.2f}); "
            f"transfer index {far_acc:.2f}; structure slope beta={beta:+.2f} over "
            f"{len(schemas)} schemas, {len(records)} synthetic items [{learner.name}]"
        ),
    }


def run(seed: int = config.RANDOM_SEED, **_kwargs: Any) -> dict[str, Any]:
    """Report-only Transfer Meter over the ``struct.*`` schemas (default learner)."""
    return _measure(_DEFAULT_LEARNER, seed)


def _selftest() -> bool:
    seed = config.RANDOM_SEED
    checks: list[tuple[str, bool]] = []

    # (1) Reproducible: two runs must be byte-identical.
    r1 = run(seed=seed)
    r2 = run(seed=seed)
    repro = json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    checks.append(("run() reproducible (byte-identical metrics)", repro))

    # (2) Fully JSON-serialisable with no NaN/Inf.
    try:
        json.dumps(r1, allow_nan=False)
        serialisable = True
    except (ValueError, TypeError):
        serialisable = False
    checks.append(("json.dumps(result, allow_nan=False) works", serialisable))

    # (3) Planted pure memorizer: the gap's CI must EXCLUDE 0 (it has teeth).
    mem = _measure(_MEMORIZER, seed)
    m_lo, m_hi = mem["memorization_gap_ci"]
    mem_ok = m_lo > 0.0 and mem["memorization_gap"] > 0.0
    checks.append(
        (
            f"planted memorizer gap CI excludes 0 "
            f"(gap={mem['memorization_gap']:+.3f}, CI {m_lo:+.3f}..{m_hi:+.3f})",
            mem_ok,
        )
    )

    # (4) Planted pure transferrer: the gap's CI must INCLUDE 0 (no false alarm).
    tra = _measure(_TRANSFERRER, seed)
    t_lo, t_hi = tra["memorization_gap_ci"]
    tra_ok = t_lo <= 0.0 <= t_hi
    checks.append(
        (
            f"planted transferrer gap CI includes 0 "
            f"(gap={tra['memorization_gap']:+.3f}, CI {t_lo:+.3f}..{t_hi:+.3f})",
            tra_ok,
        )
    )

    # (5) The two are separable on both the gap and the (signed) slope.
    teeth = (
        mem["memorization_gap"] > tra["memorization_gap"] + 0.2
        and mem["structure_slope"] < tra["structure_slope"]
    )
    checks.append(("memorizer vs transferrer separated (gap & slope)", teeth))

    # (6) A distance-graded curve is always reported, never a single number.
    populated = sum(1 for b in mem["curve"] if b["n"] > 0)
    checks.append((f"distance-graded curve present ({populated} bins)", populated >= 3))

    # (7) Far/held-out surface stays below the leakage cosine gate.
    checks.append(
        ("far surface below LEAK_COSINE_MAX", bool(r1["heldout_below_leak_gate"]))
    )

    all_ok = all(ok for _, ok in checks)
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    print("TRANSFER_OK" if all_ok else "TRANSFER_FAIL")
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
