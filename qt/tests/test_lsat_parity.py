# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Anki for LSAT: desktop <-> Android endpoint-parity guard.

The LSAT app ships as two front-ends -- the desktop (MacBook) PyQt app and the
Android Capacitor WebView -- that deliberately share one brain: the ``lsat/``
Python logic, the ``ts/lib/lsat/`` Svelte components, and the framework-agnostic
handlers in :mod:`lsat.api`. The one surface that is hand-maintained in several
places, and can therefore silently drift between the two versions, is the HTTP
endpoint contract:

1. ``lsat.api.ENDPOINTS``                  -- the canonical list (source of truth)
2. ``lsat.server.app._HANDLERS``           -- the Android transport (standalone Flask)
3. ``aqt.mediasrv.post_handlers`` (lsat*)  -- the desktop transport (mediasrv)
4. ``ts/lib/lsat/client.ts``               -- the shared front-end caller

If a feature is added to one version's transport but not the other, a phone
paired to the desktop (or the Android app) 404s on an endpoint the other version
has. This test asserts all four sets are identical, so such drift fails ``just
check`` instead of surfacing at runtime. (The standalone server additionally
self-guards at import; this test also covers the desktop side and the TS client.)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# The top-level ``lsat`` package is a sibling of ``qt``/``pylib`` (not installed
# into the pyenv), so put the repo root on sys.path the way the app does at runtime.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lsat import api  # noqa: E402


def _canonical() -> set[str]:
    return set(api.ENDPOINTS)


def _server_handlers() -> set[str]:
    # Importing the module also runs its own import-time subset/superset assert.
    from lsat.server import app as server_app

    return set(server_app._HANDLERS)


def _desktop_handlers() -> set[str]:
    # mediasrv registers each post handler under stringcase.camelcase(fn.__name__);
    # the LSAT endpoints are exactly the "lsat"-prefixed keys.
    from aqt import mediasrv

    return {name for name in mediasrv.post_handlers if name.startswith("lsat")}


# Match a PWA endpoint call in ANY valid form the front-end uses:
#   post("lsatX")            post<T>("lsatX")        post<Record<string,T>>("lsatX")
#   post('lsatX')            postDurable<T>("lsatX")  fetch("/_anki/lsatX")  (raw)
# The `[A-Za-z]*` after `post` matches the durable-queue wrapper `postDurable(...)`
# (used by submitAnswer/submitSectionAttempt): without it the scan was BLIND to
# those two endpoints and falsely reported them as having no front-end caller. The
# generic is optional (T only appears in the return type, so `post("x")` is legal
# TS); `<[^(]*>` spans nested generics; both quote styles are accepted. A purely
# width/one-form regex previously missed real callers -> false-pass drift.
_POST_CALL_RE = re.compile(
    r"""\bpost[A-Za-z]*\s*(?:<[^(]*>)?\(\s*['"](lsat[A-Za-z0-9]+)['"]"""
)
_RAW_FETCH_RE = re.compile(r"""fetch\(\s*[`'"]/_anki/(lsat[A-Za-z0-9]+)""")


def _frontend_endpoint_calls() -> set[str]:
    # Scan EVERY front-end caller of /_anki/lsat*, not just client.ts: the dashboard
    # route posts directly via raw fetch(), so a client.ts-only scan is blind to it.
    roots = [_REPO_ROOT / "ts" / "lib" / "lsat"]
    roots += sorted((_REPO_ROOT / "ts" / "routes").glob("lsat-*"))
    found: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix in (".ts", ".svelte") and path.is_file():
                text = path.read_text(encoding="utf-8")
                found.update(_POST_CALL_RE.findall(text))
                found.update(_RAW_FETCH_RE.findall(text))
    return found


def test_canonical_list_is_nonempty_and_unique() -> None:
    # ENDPOINTS is a tuple; guard against an accidental duplicate collapsing the set.
    assert api.ENDPOINTS, "lsat.api.ENDPOINTS is empty"
    assert len(api.ENDPOINTS) == len(set(api.ENDPOINTS)), (
        "lsat.api.ENDPOINTS has duplicates"
    )


def test_server_matches_canonical() -> None:
    canonical, server = _canonical(), _server_handlers()
    assert server == canonical, (
        "Android transport (lsat/server/app.py::_HANDLERS) drifted from "
        f"lsat.api.ENDPOINTS.\n  missing on server: {sorted(canonical - server)}\n"
        f"  extra on server:   {sorted(server - canonical)}"
    )


def test_desktop_matches_canonical() -> None:
    canonical, desktop = _canonical(), _desktop_handlers()
    assert desktop == canonical, (
        "Desktop transport (qt/aqt/mediasrv.py::post_handler_list) drifted from "
        "lsat.api.ENDPOINTS -- a paired phone would 404 on the missing ones.\n"
        f"  missing on desktop: {sorted(canonical - desktop)}\n"
        f"  extra on desktop:   {sorted(desktop - canonical)}"
    )


def test_client_ts_matches_canonical() -> None:
    canonical, client = _canonical(), _frontend_endpoint_calls()
    assert client == canonical, (
        "Front-end callers (ts/lib/lsat + ts/routes/lsat-*) drifted from "
        "lsat.api.ENDPOINTS.\n"
        f"  called by front-end but no handler: {sorted(client - canonical)}\n"
        f"  handler with no front-end caller:   {sorted(canonical - client)}"
    )


def test_all_four_layers_identical() -> None:
    # Belt-and-suspenders: one assertion that pins every layer to the same set.
    layers = {
        "lsat.api.ENDPOINTS": _canonical(),
        "lsat/server/app.py": _server_handlers(),
        "qt/aqt/mediasrv.py": _desktop_handlers(),
        "ts/lib/lsat + ts/routes/lsat-*": _frontend_endpoint_calls(),
    }
    canonical = layers["lsat.api.ENDPOINTS"]
    drifted = {name: s for name, s in layers.items() if s != canonical}
    assert not drifted, (
        "LSAT endpoint contract is not identical across all four layers: "
        f"{sorted(drifted)}"
    )
