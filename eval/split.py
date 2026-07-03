# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Step 0: deterministic, content-aware train/heldout split + manifest.

Groups items by a normalized content key (lowercased, punctuation/whitespace
stripped) so exact or near-exact duplicates land on the SAME side -- a naive
per-row split leaks such duplicates across the boundary. Genuinely reworded
paraphrases (different wording) are additionally caught by the leakage check's
embedding-cosine scan, not by this key. The split is identical on every run
(fixed seed), and ``manifest.json`` records a sha256 of every item and its side
so reviewers can verify nothing moved. Heldout is touched only by eval.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from eval import config


def _content_key(item: dict[str, Any]) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(item.get("question", "")).lower()).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _sha256(item: dict[str, Any]) -> str:
    payload = json.dumps(item, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_split(
    items: list[dict[str, Any]],
    seed: int = config.RANDOM_SEED,
    heldout_frac: float = 0.2,
) -> dict[str, str]:
    """Return ``{item_id: "train" | "heldout"}``, grouping by content key."""
    import random

    groups: dict[str, list[str]] = {}
    for item in items:
        groups.setdefault(_content_key(item), []).append(item["id"])
    keys = sorted(groups)  # deterministic order before the seeded shuffle
    rng = random.Random(seed)
    rng.shuffle(keys)
    n_heldout_groups = max(1, round(len(keys) * heldout_frac))
    heldout_keys = set(keys[:n_heldout_groups])
    split: dict[str, str] = {}
    for key, ids in groups.items():
        side = "heldout" if key in heldout_keys else "train"
        for item_id in ids:
            split[item_id] = side
    return split


def run(out_dir: str, seed: int = config.RANDOM_SEED) -> dict[str, Any]:
    from lsat.ai.gold_set import load_gold_set

    items = load_gold_set()
    split = make_split(items, seed)
    manifest = {
        "seed": seed,
        "n_items": len(items),
        "items": [
            {"id": it["id"], "sha256": _sha256(it), "split": split[it["id"]]}
            for it in items
        ],
    }
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    n_train = sum(1 for s in split.values() if s == "train")
    n_heldout = len(split) - n_train
    return {
        "name": "split",
        "passed": None,  # informational, not a gate
        "split": split,
        "n_train": n_train,
        "n_heldout": n_heldout,
        "manifest_path": manifest_path,
        "detail": f"content-aware split: {n_train} train / {n_heldout} heldout "
        f"(seed={seed}); manifest.json written",
    }
