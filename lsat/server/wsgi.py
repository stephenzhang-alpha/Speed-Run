# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""WSGI entry point for a production server (waitress/gunicorn).

Builds the app from environment variables so a WSGI runner can import
``lsat.server.wsgi:app``. Run SINGLE-worker (the Anki backend is not
thread-safe), e.g.::

    waitress-serve --listen=0.0.0.0:8000 --threads=1 lsat.server.wsgi:app
"""

from __future__ import annotations

import os

from lsat.server.app import create_app

_collection = os.environ.get("LSAT_COLLECTION")
if not _collection:
    raise RuntimeError("LSAT_COLLECTION env var is required (path to the .anki2 file)")

app = create_app(
    _collection,
    token=os.environ.get("LSAT_SERVER_TOKEN", ""),
    web_root=os.environ.get("LSAT_WEB_ROOT"),
)
