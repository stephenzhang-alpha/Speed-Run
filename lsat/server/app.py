# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Flask app for the standalone LSAT backend.

Serves, from one origin:

- the built ``lsat-mobile`` SvelteKit PWA (SPA fallback + immutable ``/_app/*``
  assets), and
- ``POST /_anki/lsat*`` -> the framework-agnostic handlers in :mod:`lsat.api`.

Because both live on one origin, the existing PWA client (``ts/lib/lsat/client.ts``,
which POSTs to relative ``/_anki/...`` with a ``#token=`` bearer) works unchanged
-- no CORS. The Android Capacitor WebView simply loads ``<server>/lsat-mobile``.

The Anki backend is not thread-safe, so a single collection is opened once and
every request serializes on a lock (run single-worker).
"""

from __future__ import annotations

import json
import os
import re
import threading
from typing import TYPE_CHECKING, Any, Callable

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    request,
    send_file,
    send_from_directory,
)

from lsat import api

if TYPE_CHECKING:
    from anki.collection import Collection

# Endpoint name -> handler(col, body). Matches lsat.api.ENDPOINTS and the paths
# the PWA client calls.
_HANDLERS: dict[str, Callable[[Any, dict[str, Any]], dict[str, Any]]] = {
    "lsatDashboardData": lambda col, body: api.dashboard(col),
    "lsatNextItem": lambda col, body: api.next_item(col),
    "lsatSubmitAnswer": lambda col, body: api.submit_answer(
        col,
        item_id=body["item_id"],
        chosen=body.get("chosen", ""),
        confidence=body.get("confidence"),
        response_ms=body.get("response_ms", 0),
        phase=body.get("phase", "timed"),
        identified=str(body.get("identified", "") or ""),
    ),
    "lsatSubmitTrap": lambda col, body: api.submit_trap(
        col,
        item_id=body["item_id"],
        chosen=body.get("chosen", ""),
        family=body.get("family", ""),
    ),
    "lsatSubmitClassify": lambda col, body: api.submit_classify(
        col, item_id=body["item_id"], named=body.get("named", "")
    ),
    "lsatConditionalDrill": lambda col, body: api.conditional_drill(col),
    "lsatSubmitConditional": lambda col, body: api.submit_conditional(
        col,
        item_id=body["item_id"],
        sufficient=body.get("sufficient", ""),
        necessary=body.get("necessary", ""),
        response_ms=body.get("response_ms", 0),
    ),
    "lsatQuantifierValidityDrill": lambda col, body: api.quantifier_validity_drill(col),
    "lsatSubmitQuantifierValidity": lambda col, body: api.submit_quantifier_validity(
        col,
        item_id=body["item_id"],
        chosen=body.get("chosen", ""),
        response_ms=body.get("response_ms", 0),
    ),
    "lsatQuantifierNegationDrill": lambda col, body: api.quantifier_negation_drill(col),
    "lsatSubmitQuantifierNegation": lambda col, body: api.submit_quantifier_negation(
        col,
        item_id=body["item_id"],
        chosen=body.get("chosen", ""),
        response_ms=body.get("response_ms", 0),
    ),
    "lsatStemPolarityDrill": lambda col, body: api.stem_polarity_drill(col),
    "lsatSubmitStemPolarity": lambda col, body: api.submit_stem_polarity(
        col,
        item_id=body["item_id"],
        chosen=body.get("chosen", ""),
        response_ms=body.get("response_ms", 0),
    ),
    "lsatAssumptionDrill": lambda col, body: api.assumption_drill(col),
    "lsatSubmitAssumption": lambda col, body: api.submit_assumption(
        col,
        item_id=body["item_id"],
        chosen=body.get("chosen", ""),
        response_ms=body.get("response_ms", 0),
    ),
    "lsatSectionItems": lambda col, body: api.section_items(
        col, n=int(body.get("n", 10) or 10)
    ),
    "lsatSubmitSectionAttempt": lambda col, body: api.submit_section_attempt(
        col, trajectory=body.get("trajectory")
    ),
    "lsatChainDrill": lambda col, body: api.chain_drill(col),
    "lsatSubmitChain": lambda col, body: api.submit_chain(
        col,
        item_id=body["item_id"],
        chosen=body.get("chosen", ""),
        response_ms=body.get("response_ms", 0),
    ),
    "lsatWorkedExampleDrill": lambda col, body: api.worked_example_drill(col),
    "lsatSubmitWorkedStep": lambda col, body: api.submit_worked_step(
        col,
        item_id=body["item_id"],
        move_id=body.get("move_id", ""),
        response_ms=body.get("response_ms", 0),
    ),
    "lsatOracleTheater": lambda col, body: api.oracle_theater(col),
    "lsatEvilTwinDrill": lambda col, body: api.evil_twin_drill(col),
    "lsatSubmitEvilTwin": lambda col, body: api.submit_evil_twin(
        col,
        twin_key=body["twin_key"],
        chosen=body.get("chosen", ""),
        response_ms=body.get("response_ms", 0),
    ),
}

# Fail fast if a new PWA endpoint is added to lsat.api.ENDPOINTS without a handler
# here -- the standalone server must serve exactly what the mobile client calls
# (this guard is why the round-2 conditional gap could not recur silently).
_missing = set(api.ENDPOINTS) - set(_HANDLERS)
assert not _missing, f"lsat/server/app.py missing handlers for: {sorted(_missing)}"

# Read-only endpoints: a failure is a real 500. Submit endpoints mirror the
# desktop adapters and return {"error": ...} with 200 (the client shows it).
_READ_ENDPOINTS = frozenset(
    {"lsatDashboardData", "lsatNextItem", "lsatOracleTheater"}
)

# Generated-backend RPCs the SvelteKit SPA calls at boot that we forward to the
# Rust backend (mirrors mediasrv's raw_backend_request). The root +layout runs
# setupGlobalI18n() -> i18nResources; without it the layout load throws and the
# whole app renders blank. Keep this an allowlist of non-sensitive boot RPCs.
_BACKEND_PASSTHROUGH = frozenset({"i18nResources"})
_CAMEL_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _default_web_root() -> str | None:
    """Locate a directory that contains ``sveltekit/index.html`` (the built PWA).

    Tries the qt-copied bundle then the raw adapter output, relative to the repo
    root (three dirs up from this file)."""
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for rel in ("out/qt/_aqt/data/web", "out"):
        if os.path.isfile(os.path.join(repo, rel, "sveltekit", "index.html")):
            return os.path.join(repo, rel)
    return None


def create_app(
    collection_path: str,
    *,
    token: str = "",
    web_root: str | None = None,
) -> Flask:
    """Build the Flask app: open the collection, ensure the notetypes/migrations,
    and wire the static + API routes.

    ``token`` (if set) is required as ``Authorization: Bearer <token>`` on API
    POSTs; empty disables auth (LAN/dev only). ``web_root`` is the directory
    containing ``sveltekit/`` (auto-detected when omitted)."""
    from anki.collection import Collection

    col: Collection = Collection(collection_path)
    # Make a fresh collection immediately usable (all idempotent).
    from lsat.events import migrate_event_fields
    from lsat.notetypes import (
        ensure_notetypes,
        migrate_card_fields,
        migrate_item_fields,
    )

    ensure_notetypes(col)
    migrate_event_fields(col)
    migrate_item_fields(col)
    migrate_card_fields(col)

    root = web_root or _default_web_root()
    sveltekit = os.path.join(root, "sveltekit") if root else None
    index_html = os.path.join(sveltekit, "index.html") if sveltekit else None

    app = Flask(__name__)
    app.config.update(LSAT_COL=col, LSAT_TOKEN=token, LSAT_LOCK=threading.Lock())

    def _authorized() -> bool:
        want = app.config["LSAT_TOKEN"]
        if not want:
            return True
        return request.headers.get("Authorization") == f"Bearer {want}"

    def _json_body() -> dict[str, Any]:
        try:
            return json.loads(request.get_data() or b"{}")
        except Exception:
            return {}

    @app.route("/_anki/<endpoint>", methods=["POST"])
    def _api_endpoint(endpoint: str):
        handler = _HANDLERS.get(endpoint)
        if handler is None:
            # Forward the SPA's boot-time backend RPCs (e.g. i18nResources) to
            # the Rust backend as raw bytes. Not token-gated: these load before
            # the token flow and carry no user data. Anything not allowlisted 404s.
            if endpoint not in _BACKEND_PASSTHROUGH:
                abort(404)
            snake = _CAMEL_RE.sub("_", endpoint).lower()
            raw = getattr(app.config["LSAT_COL"]._backend, f"{snake}_raw", None)
            if raw is None:
                abort(404)
            with app.config["LSAT_LOCK"]:
                out = raw(request.get_data())
            return Response(out, content_type="application/octet-stream")
        if not _authorized():
            abort(401)
        body = _json_body()
        with app.config["LSAT_LOCK"]:
            try:
                result = handler(app.config["LSAT_COL"], body)
            except Exception as exc:
                if endpoint in _READ_ENDPOINTS:
                    resp = jsonify({"error": str(exc)})
                    resp.status_code = 500
                    return resp
                return jsonify({"error": str(exc)})  # 200, parity with desktop
        return jsonify(result)

    @app.route("/healthz")
    def _health():
        return Response("ok", mimetype="text/plain")

    if sveltekit and index_html:

        @app.route("/")
        def _root():
            return redirect("/lsat-mobile")

        @app.route("/_app/<path:asset>")
        def _immutable(asset: str):
            return send_from_directory(
                os.path.join(sveltekit, "_app"), asset, max_age=31536000
            )

        @app.route("/<path:req_path>")
        def _spa(req_path: str):
            # Serve a real static file if it exists (favicon, etc.); otherwise
            # fall back to the SPA shell so client-side routes (lsat-mobile) load.
            full = os.path.normpath(os.path.join(sveltekit, req_path))
            if full.startswith(os.path.abspath(sveltekit)) and os.path.isfile(full):
                return send_file(full)
            return send_file(index_html)

    return app
