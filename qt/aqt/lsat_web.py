# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""HTTP endpoints for the LSAT mobile PWA (desktop / mediasrv front-end).

The desktop reviewer captures answers through the Qt-only ``pycmd`` bridge
(``lsat_performance.py``); a phone has no ``pycmd``, so the mobile PWA talks to
these mediasrv endpoints over HTTP instead. They run inside the desktop process
(so writes go through the same open collection -- no locking problem).

These are thin adapters: they read ``aqt.mw.col`` + the Flask request body and
delegate to the framework-agnostic handlers in :mod:`lsat.api`, which the
standalone hosted server (``lsat/server/app.py``) also uses -- so both produce
the identical append-only ``PerformanceEvent``. Registered in ``mediasrv.py``'s
``post_handler_list`` as ``lsatNextItem`` / ``lsatSubmitAnswer`` /
``lsatSubmitTrap`` / ``lsatSubmitClassify``.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import flask

import aqt


def _ensure_lsat_on_path() -> None:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.append(root)


def _body() -> dict[str, Any]:
    try:
        return json.loads(flask.request.data or b"{}")
    except Exception:
        return {}


def pairing_authorized() -> bool:
    """True iff the request is authorized to reach an LSAT endpoint.

    The per-session bearer token is the auth layer for **LAN-bound** mode
    (``ANKI_API_HOST=0.0.0.0``, which phone pairing requires): in that mode
    mediasrv's host/origin gate in ``handle_request`` is intentionally bypassed, so
    without the token these collection-reading/-writing endpoints would be reachable
    by anyone on the LAN. In the normal **localhost** mode, that same gate already
    rejects every non-local host/origin, so a same-origin desktop request is already
    authenticated -- including the MAIN window webview that now hosts the dashboard
    *home screen*, which by design does NOT inject the bearer header (it also renders
    untrusted card JS, so it is excluded from the api-access allowlist). Accept the
    token when present (phone / api-access dialogs); otherwise accept only when NOT
    LAN-exposed. This matches Anki's own trusted-localhost posture for its core
    endpoints and adds no LAN exposure.
    """
    import os

    from aqt.mediasrv import get_api_key

    if flask.request.headers.get("Authorization") == f"Bearer {get_api_key()}":
        return True
    # Not LAN-bound => handle_request already enforced localhost host + origin.
    return os.environ.get("ANKI_API_HOST") != "0.0.0.0"


def _unauthorized() -> flask.Response:
    return flask.Response(
        json.dumps({"error": "unauthorized"}),
        status=403,
        mimetype="application/json",
    )


def next_item() -> bytes | flask.Response:
    """Return the next item to study (stem + choices; never the correct letter)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.next_item(aqt.mw.col)).encode()


def submit_answer() -> bytes | flask.Response:
    """Grade a chosen answer, log the event, and report the result."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_answer(
            aqt.mw.col,
            item_id=body["item_id"],
            chosen=body.get("chosen", ""),
            confidence=body.get("confidence"),
            response_ms=body.get("response_ms", 0),
            phase=body.get("phase", "timed"),
            identified=str(body.get("identified", "") or ""),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def submit_classify() -> bytes | flask.Response:
    """Grade the identification-first stage (name the question type)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_classify(
            aqt.mw.col, item_id=body["item_id"], named=body.get("named", "")
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def submit_trap() -> bytes | flask.Response:
    """Grade a "which trap is (X)?" tap against the item's authoritative labels."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_trap(
            aqt.mw.col,
            item_id=body["item_id"],
            chosen=body.get("chosen", ""),
            family=body.get("family", ""),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def conditional_drill() -> bytes | flask.Response:
    """Return the next Conditional Translation Drill (#19; never the answer)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.conditional_drill(aqt.mw.col)).encode()


def submit_conditional() -> bytes | flask.Response:
    """Grade a conditional-translation attempt (#19) and log the graded event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_conditional(
            aqt.mw.col,
            item_id=body["item_id"],
            sufficient=body.get("sufficient", ""),
            necessary=body.get("necessary", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def chain_drill() -> bytes | flask.Response:
    """Return the next Conditional-Chain Drill (r4 #22; never the verdict)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.chain_drill(aqt.mw.col)).encode()


def submit_chain() -> bytes | flask.Response:
    """Grade a conditional-chain judgment (r4 #22) and log the graded event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_chain(
            aqt.mw.col,
            item_id=body["item_id"],
            chosen=body.get("chosen", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def worked_example_drill() -> bytes | flask.Response:
    """Return the next Oracle-Verified Faded Worked Example (research #1; never the
    correct move)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.worked_example_drill(aqt.mw.col)).encode()


def submit_worked_step() -> bytes | flask.Response:
    """Oracle-grade a faded-worked-example move (research #1) and log the event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_worked_step(
            aqt.mw.col,
            item_id=body["item_id"],
            move_id=body.get("move_id", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def oracle_theater() -> bytes | flask.Response:
    """Return the Oracle Proof Theater scenarios (marquee AI demo): a recorded model
    draft checked LIVE, step by step, by the material-entailment oracle. Read-only."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.oracle_theater(aqt.mw.col)).encode()


def prove_step() -> bytes | flask.Response:
    """Interactive "Prove It": oracle-check a learner-built ordered move list against
    a theater scenario (read-only, no LLM). Returns per-step verdicts + a
    counterexample world on an entailment failure."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.prove_step(
            aqt.mw.col,
            scenario_id=body.get("scenario_id", ""),
            moves=body.get("moves"),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def oracle_draft_live() -> bytes | flask.Response:
    """"Draft it live": the real model drafts a derivation and the oracle checks it
    LIVE (read-only; degrades to the recorded scenario when AI is off/unavailable)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.oracle_draft_live(
            aqt.mw.col, scenario_id=body.get("scenario_id", "")
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def evil_twin_drill() -> bytes | flask.Response:
    """Return the next oracle-proven "Skill or Luck?" evil twin (never the verdict)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.evil_twin_drill(aqt.mw.col)).encode()


def submit_evil_twin() -> bytes | flask.Response:
    """Oracle-grade a verdict on an evil twin and log the event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_evil_twin(
            aqt.mw.col,
            twin_key=body["twin_key"],
            chosen=body.get("chosen", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def quantifier_validity_drill() -> bytes | flask.Response:
    """Return the next Quantifier Validity Drill (r3 #1; never the verdict)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.quantifier_validity_drill(aqt.mw.col)).encode()


def submit_quantifier_validity() -> bytes | flask.Response:
    """Grade a quantifier-validity judgment (r3 #1) and log the graded event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_quantifier_validity(
            aqt.mw.col,
            item_id=body["item_id"],
            chosen=body.get("chosen", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def quantifier_negation_drill() -> bytes | flask.Response:
    """Return the next Quantifier Negation Drill (r3 #1; never the answer)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.quantifier_negation_drill(aqt.mw.col)).encode()


def submit_quantifier_negation() -> bytes | flask.Response:
    """Grade a quantifier-negation choice (r3 #1) and log the graded event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_quantifier_negation(
            aqt.mw.col,
            item_id=body["item_id"],
            chosen=body.get("chosen", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def stem_polarity_drill() -> bytes | flask.Response:
    """Return the next Stem-Polarity Micro-Drill (r4 #13; never the answer)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.stem_polarity_drill(aqt.mw.col)).encode()


def submit_stem_polarity() -> bytes | flask.Response:
    """Grade a stem-polarity call (r4 #13) and log the graded event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_stem_polarity(
            aqt.mw.col,
            item_id=body["item_id"],
            chosen=body.get("chosen", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def section_items() -> bytes | flask.Response:
    """Return a batch of distinct LSAT items for a timed section (r4 #17; no answers)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.section_items(aqt.mw.col, n=int(body.get("n", 10) or 10))
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def submit_section_attempt() -> bytes | flask.Response:
    """Persist a timed-section attempt (r4 #17) and return the First-Instinct Ledger."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_section_attempt(
            aqt.mw.col, trajectory=body.get("trajectory")
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()


def assumption_drill() -> bytes | flask.Response:
    """Return the next Necessary/Sufficient Discrimination Drill (r4 #5)."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.assumption_drill(aqt.mw.col)).encode()


def submit_assumption() -> bytes | flask.Response:
    """Grade a four-cell assumption sort (r4 #5) and log the graded event."""
    if not pairing_authorized():
        return _unauthorized()
    _ensure_lsat_on_path()
    from lsat import api

    body = _body()
    try:
        result = api.submit_assumption(
            aqt.mw.col,
            item_id=body["item_id"],
            chosen=body.get("chosen", ""),
            response_ms=body.get("response_ms", 0),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)}).encode()
    return json.dumps(result).encode()
