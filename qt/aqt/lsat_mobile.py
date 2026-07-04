# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""LSAT Prep: "Study on your phone" pairing.

The mobile PWA (SvelteKit ``lsat-mobile`` route + the ``lsat*`` HTTP endpoints)
is served by this desktop app's own mediasrv. This module builds the pairing
link and a small dialog that shows it.

Security model (documented, opt-in): mediasrv binds to localhost by default, so
a phone cannot reach it. To pair a phone you must launch Anki with
``ANKI_API_HOST=0.0.0.0`` (bind to the LAN). Binding to the LAN *bypasses*
mediasrv's global API gate, so every LSAT endpoint (``lsat_web.py`` +
``lsatDashboardData``) independently requires the per-session bearer token in an
``Authorization: Bearer`` header (``lsat_web.pairing_authorized``); the pairing
link below carries that token in its URL hash, and the PWA replays it on every
request. A request without the token is rejected (403), so the collection is not
exposed unauthenticated on the LAN. Still treat the link like a password and
pair only trusted devices on a trusted network.
"""

from __future__ import annotations

import os
import socket

import aqt
import aqt.main
from aqt.qt import (
    QDialog,
    QGuiApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QVBoxLayout,
)
from aqt.utils import disable_help_button, qconnect

MOBILE_PAGE = "lsat-mobile"


def _lan_ip() -> str:
    """Best-effort LAN IP of this machine (no packets are actually sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def lan_enabled() -> bool:
    return os.environ.get("ANKI_API_HOST") == "0.0.0.0"


def pairing_url() -> str:
    """The URL to open on a phone (LAN host + port + pairing token in the hash).

    SvelteKit pages are served at the bare route (e.g. ``/lsat-mobile``), the
    same URL ``AnkiWebView.load_sveltekit_page`` builds -- NOT the legacy
    ``/_anki/pages/<name>.html`` scheme, which mediasrv rejects for SvelteKit
    routes ("Invalid path: pages/...").
    """
    from aqt.mediasrv import get_api_key

    port = aqt.mw.mediaServer.getPort()
    host = _lan_ip() if lan_enabled() else "127.0.0.1"
    return f"http://{host}:{port}/{MOBILE_PAGE}#token={get_api_key()}"


class LsatMobilePairDialog(QDialog):
    "Shows the phone-pairing link for the LSAT mobile PWA."

    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        disable_help_button(self)
        self.setWindowTitle("Study on Your Phone")
        self.setMinimumWidth(520)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("<b>Study LSAT on your phone</b>")
        layout.addWidget(title)

        if lan_enabled():
            steps = QLabel(
                "On your phone (same Wi-Fi), open this link in the browser, then "
                "use <b>Add to Home Screen</b> to install it as an app:"
            )
        else:
            steps = QLabel(
                "Phone access is <b>off</b>. Quit LSAT Prep and relaunch it with "
                "<code>ANKI_API_HOST=0.0.0.0</code> set, then reopen this dialog. "
                "The link below only works once the app is bound to your network."
            )
        steps.setWordWrap(True)
        layout.addWidget(steps)

        url = pairing_url()
        field = QLineEdit(url)
        field.setReadOnly(True)
        field.setCursorPosition(0)
        layout.addWidget(field)

        copy_btn = QPushButton("Copy link")

        def _copy() -> None:
            cb = QGuiApplication.clipboard()
            if cb is not None:
                cb.setText(url)
            copy_btn.setText("Copied")

        qconnect(copy_btn.clicked, _copy)
        layout.addWidget(copy_btn)

        warn = QLabel(
            "Only pair devices you trust on a network you trust: anyone with this "
            "link can reach your collection while LSAT Prep is running."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("color: palette(mid);")
        layout.addWidget(warn)

        self.setLayout(layout)


def show_pairing_dialog(mw: aqt.main.AnkiQt) -> None:
    LsatMobilePairDialog(mw).exec()
