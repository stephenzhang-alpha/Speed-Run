# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Anki for LSAT: server-side idempotency guard for the offline replay queue.

The offline PWA queue drops a queued submission only AFTER the server acks it, so
a lost ack (radio drop during the response, after the event was committed) makes
the client re-POST a submission the server already recorded. Without a guard that
re-POST would append a SECOND ``PerformanceEvent``, breaking the append-only
"one event per submission" invariant. ``lsat.events.idempotent_{lookup,remember}``
record ``id -> result`` in a bounded config ring, and ``submit_answer`` /
``submit_section_attempt`` short-circuit a replayed id to the stored result WITHOUT
re-processing. These paths run before any note/collection access, so a plain fake
collection (dict-backed config) exercises them -- and if the guard did NOT
short-circuit, the fake would fall through to real note access and blow up, so a
clean stored-result return is itself proof that the dedup fired.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


class _FakeCol:
    """A collection stand-in exposing only the synced-config API the idempotency
    ring uses. It deliberately has NO note/backend surface: any handler that falls
    through the dedup guard into real processing raises, which is what we want to
    assert never happens on a replay hit."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        self._config[key] = value


def test_ring_stores_and_looks_up_by_key() -> None:
    from lsat.events import idempotent_lookup, idempotent_remember

    col = _FakeCol()
    assert idempotent_lookup(col, "k1") is None  # unseen
    idempotent_remember(col, "k1", {"graded": True, "correct": True})
    assert idempotent_lookup(col, "k1") == {"graded": True, "correct": True}
    assert idempotent_lookup(col, "k2") is None  # a different key is still unseen


def test_empty_key_is_never_deduped() -> None:
    from lsat.events import idempotent_lookup, idempotent_remember

    col = _FakeCol()
    # An empty key means "no idempotency" -- remember is a no-op and lookup misses,
    # so a caller that passes no key always takes the normal processing path.
    idempotent_remember(col, "", {"graded": True})
    assert idempotent_lookup(col, "") is None
    assert col.get_config("lsat:idempotency", None) is None


def test_first_result_wins_on_repeated_remember() -> None:
    from lsat.events import idempotent_lookup, idempotent_remember

    col = _FakeCol()
    idempotent_remember(col, "k", {"n": 1})
    idempotent_remember(col, "k", {"n": 2})  # must NOT overwrite the first result
    assert idempotent_lookup(col, "k") == {"n": 1}


def test_ring_is_fifo_bounded() -> None:
    from lsat.events import IDEMPOTENCY_CAP, idempotent_lookup, idempotent_remember

    col = _FakeCol()
    total = IDEMPOTENCY_CAP + 5
    for i in range(total):
        idempotent_remember(col, f"k{i}", {"i": i})
    # The 5 oldest keys were evicted (bounded window); the newest CAP survive.
    assert idempotent_lookup(col, "k0") is None
    assert idempotent_lookup(col, "k4") is None
    assert idempotent_lookup(col, "k5") == {"i": 5}
    assert idempotent_lookup(col, f"k{total - 1}") == {"i": total - 1}
    store = col.get_config("lsat:idempotency", None)
    assert store is not None and len(store["order"]) == IDEMPOTENCY_CAP


def test_submit_answer_replay_returns_stored_result_without_reprocessing() -> None:
    from lsat import api
    from lsat.events import idempotent_remember

    col = _FakeCol()
    stored = {
        "graded": True,
        "correct": True,
        "correct_letter": "C",
        "has_traps": False,
    }
    idempotent_remember(col, "dup-1", stored)

    # A replay with the same key must return the stored grade. item_id is bogus and
    # _FakeCol has no note surface -- if the guard failed to short-circuit, the call
    # would raise on note lookup instead of returning `stored`.
    res = api.submit_answer(
        col, item_id="does-not-exist", chosen="C", idempotency_key="dup-1"
    )
    assert res == stored


def test_submit_section_attempt_replay_short_circuits_before_validation() -> None:
    from lsat import api
    from lsat.events import idempotent_remember

    col = _FakeCol()
    stored = {"ok": True, "n_questions": 10, "ledger": {"changed": 0}}
    idempotent_remember(col, "sec-1", stored)

    # trajectory=None would normally fail closed ("must be a non-empty list"); a
    # replay hit must return the stored ledger BEFORE that validation runs.
    res = api.submit_section_attempt(col, trajectory=None, idempotency_key="sec-1")
    assert res == stored


def test_submit_section_attempt_without_key_still_fails_closed() -> None:
    from lsat import api

    col = _FakeCol()
    # No key + a bad payload: dedup is inert, the normal fail-closed guard runs.
    res = api.submit_section_attempt(col, trajectory=None, idempotency_key="")
    assert res.get("ok") is False
