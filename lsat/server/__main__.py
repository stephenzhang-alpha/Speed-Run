# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Run the standalone LSAT backend.

    python -m lsat.server --collection /data/collection.anki2 --port 8000 \
        --token "$LSAT_SERVER_TOKEN"

Env fallbacks: LSAT_COLLECTION, HOST, PORT, LSAT_SERVER_TOKEN, LSAT_WEB_ROOT.

The Anki backend is not thread-safe, so this serves single-worker (Flask's dev
server with threading off). For production put a single-worker waitress/gunicorn
behind an HTTPS reverse proxy (see lsat/server/README.md).
"""

from __future__ import annotations

import argparse
import os
import sys


def _ensure_anki_on_path() -> None:
    """Make the dev ``anki`` package importable when run from the repo (mirrors
    lsat/seed.py); a Docker/installed deploy has the wheel on sys.path already."""
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo not in sys.path:
        sys.path.insert(0, repo)
    for rel in ("pylib", "out/pylib"):
        path = os.path.join(repo, rel)
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LSAT standalone backend server.")
    parser.add_argument(
        "--collection",
        default=os.environ.get("LSAT_COLLECTION"),
        help="path to the .anki2 collection to serve (env LSAT_COLLECTION)",
    )
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument(
        "--token",
        default=os.environ.get("LSAT_SERVER_TOKEN", ""),
        help="bearer token required on API POSTs (env LSAT_SERVER_TOKEN; empty = open, LAN only)",
    )
    parser.add_argument("--web-root", default=os.environ.get("LSAT_WEB_ROOT"))
    args = parser.parse_args(argv)

    if not args.collection:
        parser.error("--collection (or LSAT_COLLECTION) is required")

    _ensure_anki_on_path()
    os.makedirs(os.path.dirname(os.path.abspath(args.collection)), exist_ok=True)

    from lsat.server.app import create_app

    app = create_app(args.collection, token=args.token, web_root=args.web_root)
    if not args.token:
        print("WARNING: no --token set; the API is open. Use only on a trusted LAN.")
    print(f"LSAT server on http://{args.host}:{args.port}/lsat-mobile")
    # threaded=False so requests serialize (Anki backend is not thread-safe).
    app.run(host=args.host, port=args.port, threaded=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
