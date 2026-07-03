# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Shared scoring metrics for the eval harness (pure, dependency-free)."""

from __future__ import annotations

import math

_EPS = 1e-12


def brier(preds: list[float], ys: list[float]) -> float:
    n = len(preds)
    return sum((p - y) ** 2 for p, y in zip(preds, ys)) / n if n else 0.0


def log_loss(preds: list[float], ys: list[float]) -> float:
    n = len(preds)
    if not n:
        return 0.0
    return (
        -sum(
            y * math.log(min(max(p, _EPS), 1 - _EPS))
            + (1 - y) * math.log(min(max(1 - p, _EPS), 1 - _EPS))
            for p, y in zip(preds, ys)
        )
        / n
    )


def reliability_bins(
    preds: list[float], ys: list[float], n_bins: int = 10
) -> list[dict]:
    bins = [
        {
            "lo": i / n_bins,
            "hi": (i + 1) / n_bins,
            "count": 0,
            "sum_p": 0.0,
            "sum_y": 0.0,
        }
        for i in range(n_bins)
    ]
    for p, y in zip(preds, ys):
        idx = min(n_bins - 1, int(p * n_bins))
        b = bins[idx]
        b["count"] += 1
        b["sum_p"] += p
        b["sum_y"] += y
    for b in bins:
        c = b["count"]
        b["mean_p"] = (b["sum_p"] / c) if c else None
        b["mean_y"] = (b["sum_y"] / c) if c else None
    return bins


def ece(preds: list[float], ys: list[float], n_bins: int = 10) -> float:
    n = len(preds)
    if not n:
        return 0.0
    total = 0.0
    for b in reliability_bins(preds, ys, n_bins):
        if b["count"]:
            total += (b["count"] / n) * abs(b["mean_p"] - b["mean_y"])
    return total


def auc(scores: list[float], labels: list[float]) -> float:
    """ROC AUC via the rank statistic (ties get average ranks)."""
    n = len(labels)
    pos = sum(labels)
    neg = n - pos
    if pos == 0 or neg == 0:
        return 0.5
    order = sorted(range(n), key=lambda i: scores[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-based average rank across the tie group
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    sum_pos = sum(ranks[idx] for idx in range(n) if labels[idx] == 1)
    return (sum_pos - pos * (pos + 1) / 2.0) / (pos * neg)


def accuracy(preds: list[float], ys: list[float], threshold: float = 0.5) -> float:
    n = len(preds)
    if not n:
        return 0.0
    return sum(1 for p, y in zip(preds, ys) if (p >= threshold) == (y >= 0.5)) / n


def bootstrap_ci(
    values: list[float], seed: int, n_boot: int = 1000, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of ``values``."""
    import random

    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (lo, hi)
