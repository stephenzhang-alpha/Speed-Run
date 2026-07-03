# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Standalone hosted backend for the LSAT mobile app.

Serves the built ``lsat-mobile`` PWA + the ``/_anki/lsat*`` API from one origin,
running the Python ``lsat/`` layer against a directly-opened Anki collection
(no Qt). The Android Capacitor app's WebView points at this server.
"""

from lsat.server.app import create_app

__all__ = ["create_app"]
