# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Performance model: P(correct on a NEW exam-style item), with intervals.

PRD section 5.2 / section 12 step 2: a *logistic / lightweight IRT* over skill
mastery, item difficulty, and recent timing that predicts whether the student
gets a held-out, exam-style question right -- including questions never seen.

Design (a Rasch-style logistic GLM; the PRD leaves the parameterisation to us):

    P(correct) = sigmoid(ability + w0 + w1*difficulty + w2*timing_z)

- ``ability`` is the item's topics' shrunk log-odds mastery and enters at a
  FIXED coefficient of 1 (Rasch-style / used as a GLM offset). Only the global
  intercept ``w0`` and the difficulty/timing effects are fit, so the per-topic
  ordering follows ability directly and can never invert on sparse data.
- ``ability`` shrinks toward the global accuracy **clamped to [0.15, 0.85]**, so
  a topic with little or degenerate (all-correct/all-wrong) data cannot yield an
  extreme, overconfident estimate; confidence grows only as evidence grows.
- ``difficulty`` is the categorical easy/medium/hard label as an ordinal
  (+1/0/-1); ``timing_z`` is the z-scored log response time (pacing).

The three fit weights use L2-regularised IRLS (ridge on all three, incl. the
intercept, so tiny data cannot overfit the base rate). Per-topic display gives
``p +/- interval`` whose width grows as graded evidence shrinks (binomial
log-odds standard error on ability). :func:`fit_performance_model` also computes
a k-fold held-out calibration report (ECE / Brier / log loss); the readiness
give-up rule consumes the ECE (PRD section 5.4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lsat.events import read_events
from lsat.taxonomy import Taxonomy

if TYPE_CHECKING:
    from anki.collection import Collection

DIFFICULTY_ORD = {"easy": 1.0, "medium": 0.0, "hard": -1.0}
SHRINKAGE_K = 4.0  # pseudo-observations pulling a topic toward the global rate
SHRINK_TARGET_MIN = 0.15  # clamp the shrink target away from 0/1 (anti-overconfidence)
SHRINK_TARGET_MAX = 0.85
RIDGE_LAMBDA = 1.0  # L2 on all three fit weights (incl. intercept) for stability
Z_95 = 1.96
_EPS = 1e-6
_INTERVAL_FLOOR = 0.15  # min log-odds sigma, so even rich topics show a range


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _logit(p: float) -> float:
    p = _clamp(p, _EPS, 1.0 - _EPS)
    return math.log(p / (1.0 - p))


def _difficulty_ord(label: str | None) -> float:
    return DIFFICULTY_ORD.get((label or "medium").strip().lower(), 0.0)


def _shrink_target(p0: float) -> float:
    return _clamp(p0, SHRINK_TARGET_MIN, SHRINK_TARGET_MAX)


@dataclass
class _Row:
    ability: float  # leave-one-out shrunk log-odds mastery (GLM offset)
    difficulty: float
    timing_z: float
    y: float


@dataclass(frozen=True)
class PerfTopic:
    node_id: str
    name: str
    tag: str
    n_events: int
    n_correct: int
    p: float | None
    low: float | None
    high: float | None
    enough_evidence: bool
    note: str


@dataclass
class PerformanceModel:
    available: bool
    weights: tuple[float, float, float]  # (intercept, difficulty, timing); ability@1
    theta: dict[str, float]  # node_id -> shrunk log-odds ability (all events)
    counts: dict[str, tuple[int, int]]  # node_id -> (n_events, n_correct)
    p0: float
    n_events: int
    n_timed: int
    calibration: dict[str, float | None]

    def _ability(self, node_id: str) -> float:
        return self.theta.get(node_id, _logit(_shrink_target(self.p0)))

    def predict(
        self, node_id: str, difficulty: str = "medium", timing_z: float = 0.0
    ) -> float:
        """P(correct) for a new item in ``node_id`` at the given difficulty/pace."""
        w0, w_diff, w_time = self.weights
        z = (
            self._ability(node_id)
            + w0
            + w_diff * _difficulty_ord(difficulty)
            + w_time * timing_z
        )
        return _sigmoid(z)

    def predict_interval(
        self, node_id: str, difficulty: str = "medium"
    ) -> tuple[float, float, float]:
        """``(p, low, high)`` at average pace; the band widens with less evidence."""
        p = self.predict(node_id, difficulty, 0.0)
        n, c = self.counts.get(node_id, (0, 0))
        eff_n = n + SHRINKAGE_K
        m0 = _shrink_target(self.p0)
        pt = _clamp((c + SHRINKAGE_K * m0) / eff_n, _EPS, 1.0 - _EPS)
        se_ability = 1.0 / math.sqrt(max(eff_n * pt * (1.0 - pt), _EPS))
        se_z = math.sqrt(se_ability**2 + _INTERVAL_FLOOR**2)
        center = _logit(p)
        low = _sigmoid(center - Z_95 * se_z)
        high = _sigmoid(center + Z_95 * se_z)
        return (p, min(p, low), max(p, high))


def _difficulty_map(col: Collection) -> dict[str, str]:
    """``str(item_note_id) -> difficulty label`` for every LSAT Item."""
    from lsat.notetypes import LSAT_ITEM

    out: dict[str, str] = {}
    if col.models.by_name(LSAT_ITEM) is None:
        return out
    for nid in col.find_notes(f'note:"{LSAT_ITEM}"'):
        note = col.get_note(nid)
        out[str(int(nid))] = (note["difficulty"] or "medium").strip().lower()
    return out


def _solve(matrix: list[list[float]], rhs: list[float]) -> list[float] | None:
    """Solve ``A x = b`` by Gauss-Jordan elimination with partial pivoting."""
    n = len(rhs)
    a = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        piv = a[col][col]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col] / piv
            for k in range(col, n + 1):
                a[r][k] -= factor * a[col][k]
    return [a[i][n] / a[i][i] for i in range(n)]


def _fit_irls(rows: list[_Row], iters: int = 30) -> tuple[float, float, float]:
    """Ridge logistic regression of [intercept, difficulty, timing] with the
    per-row ``ability`` as a fixed offset (Rasch-style; ability coefficient 1)."""
    k = 3
    ridge = [RIDGE_LAMBDA, RIDGE_LAMBDA, RIDGE_LAMBDA]
    features = [[1.0, r.difficulty, r.timing_z] for r in rows]
    offsets = [r.ability for r in rows]
    labels = [r.y for r in rows]
    w = [0.0] * k
    for _ in range(iters):
        grad = [0.0] * k
        hess = [[0.0] * k for _ in range(k)]
        for xi, off, yi in zip(features, offsets, labels):
            z = off + sum(w[j] * xi[j] for j in range(k))
            p = _sigmoid(z)
            weight = max(p * (1.0 - p), 1e-9)
            resid = p - yi
            for a in range(k):
                grad[a] += resid * xi[a]
                for b in range(k):
                    hess[a][b] += weight * xi[a] * xi[b]
        for a in range(k):
            grad[a] += ridge[a] * w[a]
            hess[a][a] += ridge[a]
        delta = _solve(hess, grad)
        if delta is None:
            break
        w = [w[a] - delta[a] for a in range(k)]
        if max(abs(d) for d in delta) < 1e-8:
            break
    return (w[0], w[1], w[2])


def _mean_ability(
    node_ids: list[str], table: dict[str, float], fallback: float
) -> float:
    if not node_ids:
        return fallback
    return sum(table.get(nid, fallback) for nid in node_ids) / len(node_ids)


def _metrics(preds: list[float], ys: list[float]) -> dict[str, float | None]:
    """ECE (10 bins), Brier, log loss over paired predictions/outcomes."""
    n = len(preds)
    if n == 0:
        return {"ece": None, "brier": None, "log_loss": None, "n": 0}
    brier = sum((p - y) ** 2 for p, y in zip(preds, ys)) / n
    log_loss = (
        -sum(
            y * math.log(_clamp(p, _EPS, 1 - _EPS))
            + (1 - y) * math.log(_clamp(1 - p, _EPS, 1 - _EPS))
            for p, y in zip(preds, ys)
        )
        / n
    )
    bins = [[0.0, 0.0, 0] for _ in range(10)]  # sum_p, sum_y, count
    for p, y in zip(preds, ys):
        idx = min(9, int(p * 10))
        bins[idx][0] += p
        bins[idx][1] += y
        bins[idx][2] += 1
    ece = sum((cnt / n) * abs(sp / cnt - sy / cnt) for sp, sy, cnt in bins if cnt)
    return {"ece": ece, "brier": brier, "log_loss": log_loss, "n": n}


def _kfold_calibration(
    raw: list[tuple[list[str], float, float, float]],
    k_folds: int = 5,
) -> dict[str, float | None]:
    """Fully held-out calibration: within each fold, BOTH the per-topic ability
    AND the three logistic weights are (re)fit on that fold's TRAINING rows only,
    then used to predict the held-out test rows. So neither an event's own outcome
    (via its ability) nor the regression coefficients ever leak into their own
    evaluation. (The leave-one-out per-event ability feature is anti-correlated
    within a topic and inflates ECE, hence the per-fold retraining.)"""
    n = len(raw)
    if n < 2:
        return {"ece": None, "brier": None, "log_loss": None, "n": n}
    k = min(k_folds, n)
    preds: list[float] = []
    ys: list[float] = []
    for fold in range(k):
        train = [raw[i] for i in range(n) if i % k != fold]
        test = [raw[i] for i in range(n) if i % k == fold]
        if not train or not test:
            continue
        counts: dict[str, list[int]] = {}
        n_correct = 0.0
        for node_ids, _d, _tz, y in train:
            n_correct += y
            for nid in node_ids:
                cell = counts.setdefault(nid, [0, 0])
                cell[0] += 1
                cell[1] += int(y)
        m0 = _shrink_target(n_correct / len(train))
        default = _logit(m0)
        table = {
            nid: _logit((c + SHRINKAGE_K * m0) / (cn + SHRINKAGE_K))
            for nid, (cn, c) in counts.items()
        }
        # Refit the three logistic weights on this fold's training rows only, so
        # the coefficients are held out from the test fold too (a degenerate fold
        # is regularised by the ridge, so IRLS still returns finite weights).
        train_rows = [
            _Row(_mean_ability(node_ids, table, default), d, tz, y)
            for (node_ids, d, tz, y) in train
        ]
        w0, w_diff, w_time = _fit_irls(train_rows)
        for node_ids, d, tz, y in test:
            ability = _mean_ability(node_ids, table, default)
            preds.append(_sigmoid(ability + w0 + w_diff * d + w_time * tz))
            ys.append(y)
    return _metrics(preds, ys)


def fit_performance_model(
    col: Collection, taxonomy: Taxonomy | None = None
) -> PerformanceModel:
    """Fit the performance model from the graded-event log."""
    events = read_events(col)
    if not events:
        return PerformanceModel(
            available=False,
            weights=(0.0, 0.0, 0.0),
            theta={},
            counts={},
            p0=0.5,
            n_events=0,
            n_timed=0,
            calibration={"ece": None, "brier": None, "log_loss": None, "n": 0},
        )

    diff_map = _difficulty_map(col)
    counts: dict[str, list[int]] = {}
    n_correct = 0
    log_times: list[float] = []
    for event in events:
        if event.correct:
            n_correct += 1
        if event.response_ms > 0:
            log_times.append(math.log(event.response_ms))
        for node_id in event.node_ids:
            cell = counts.setdefault(node_id, [0, 0])
            cell[0] += 1
            cell[1] += 1 if event.correct else 0

    n = len(events)
    p0 = n_correct / n
    m0 = _shrink_target(p0)
    lt_mean = sum(log_times) / len(log_times) if log_times else 0.0
    if len(log_times) > 1:
        var = sum((x - lt_mean) ** 2 for x in log_times) / len(log_times)
        lt_sd = math.sqrt(var) or 1.0
    else:
        lt_sd = 1.0

    theta = {
        node_id: _logit((c + SHRINKAGE_K * m0) / (cn + SHRINKAGE_K))
        for node_id, (cn, c) in counts.items()
    }
    default_ability = _logit(m0)

    # Raw per-event features (node_ids, difficulty, timing_z, y): used both to fit
    # the three global weights and for k-fold held-out calibration.
    raw: list[tuple[list[str], float, float, float]] = []
    for event in events:
        timing_z = (
            (math.log(event.response_ms) - lt_mean) / lt_sd
            if event.response_ms > 0
            else 0.0
        )
        raw.append(
            (
                event.node_ids,
                _difficulty_ord(diff_map.get(event.item_id, "medium")),
                timing_z,
                1.0 if event.correct else 0.0,
            )
        )

    rows = [
        _Row(_mean_ability(nids, theta, default_ability), d, tz, y)
        for (nids, d, tz, y) in raw
    ]
    weights = _fit_irls(rows)
    calibration = _kfold_calibration(raw)
    return PerformanceModel(
        available=True,
        weights=weights,
        theta=theta,
        counts={k: (v[0], v[1]) for k, v in counts.items()},
        p0=p0,
        n_events=n,
        n_timed=len(log_times),
        calibration=calibration,
    )


def performance_summary(
    model: PerformanceModel, taxonomy: Taxonomy, min_events: int
) -> list[PerfTopic]:
    """Per-question-type ``p +/- interval`` (or an abstaining note)."""
    topics: list[PerfTopic] = []
    for topic in taxonomy.question_types:
        n, c = model.counts.get(topic.id, (0, 0))
        if model.available and n >= min_events:
            p, low, high = model.predict_interval(topic.id, "medium")
            half = round((high - low) / 2 * 100)
            topics.append(
                PerfTopic(
                    topic.id,
                    topic.name,
                    topic.tag,
                    n,
                    c,
                    p,
                    low,
                    high,
                    True,
                    f"{p * 100:.0f}% ± {half}% from {n} graded items",
                )
            )
        else:
            topics.append(
                PerfTopic(
                    topic.id,
                    topic.name,
                    topic.tag,
                    n,
                    c,
                    None,
                    None,
                    None,
                    False,
                    f"not enough graded items ({n}/{min_events})",
                )
            )
    return topics
