#!/usr/bin/env python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Launch the standalone ``lsat/server`` (the backend the Android app talks to) for
the Playwright offline-sync recording.

Seeds a throwaway collection, then serves the built ``lsat-mobile`` PWA + the
``/_anki/lsat*`` API from one origin with auth DISABLED (``token=""``), so the
Playwright browser can drive the real UI against the real grading + append-only log
without a pairing token. Playwright's ``webServer`` polls ``/healthz`` before tests.

Run indirectly via ``playwright.offline.config.ts``; needs the web built first
(``just rebuild-web``) so ``lsat/server`` has a PWA to serve.
"""

from __future__ import annotations

import os
import sys
import tempfile


def main() -> None:
    # Match lsat/server/selftest.py's path setup so `anki` + `lsat` import cleanly.
    sys.path[:0] = ["pylib", "out/pylib", "."]
    from anki.collection import Collection
    from lsat.seed import seed_deck
    from lsat.server.app import create_app

    port = int(os.environ.get("ANKI_API_PORT", "40100"))

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "collection.anki2")
    seed = Collection(path)
    try:
        seed_deck(seed)  # starter decks so there are LSAT items to review
    finally:
        seed.close()

    # token="" disables the bearer check (dev/LAN only) so the tokenless test browser
    # is authorized; web_root auto-detects the built out/.../sveltekit bundle.
    app = create_app(path, token="")
    print(f"lsat/server e2e: serving /lsat-mobile on 127.0.0.1:{port}", flush=True)
    # The Anki backend is not thread-safe; create_app serializes on a lock, so run
    # single-threaded. use_reloader=False so we don't fork a second collection.
    app.run(host="127.0.0.1", port=port, threaded=False, use_reloader=False)


if __name__ == "__main__":
    main()
