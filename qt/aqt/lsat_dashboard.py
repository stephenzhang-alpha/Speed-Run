# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Anki for LSAT: the dashboard dialog and its data endpoint.

Hosts the SvelteKit ``lsat-dashboard`` page in a webview. The page fetches its
data from the ``lsatDashboardData`` mediasrv endpoint (see ``mediasrv.py``),
which calls :func:`dashboard_json` here.

The LSAT models live in the top-level ``lsat`` package (a sibling of ``pylib``
and ``qt``), which is not on the app's sys.path, so we add the repo root on
first use.
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING

import aqt
import aqt.main
from aqt.qt import QDialog, Qt, QVBoxLayout
from aqt.utils import disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView, AnkiWebViewKind

if TYPE_CHECKING:
    from anki.collection import Collection


def _ensure_lsat_on_path() -> None:
    # qt/aqt/lsat_dashboard.py -> repo root is three directories up.
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.append(root)


def dashboard_json(col: Collection) -> bytes:
    """Build the dashboard payload as JSON bytes (used by the mediasrv endpoint).

    Delegates to :func:`lsat.api.dashboard` -- the SAME framework-agnostic handler
    the standalone server (``lsat/server/app.py``) serves for ``lsatDashboardData``
    -- so the desktop and the Android app compute the dashboard from one code path.
    """
    _ensure_lsat_on_path()
    from lsat import api

    return json.dumps(api.dashboard(col)).encode("utf-8")


class LsatDashboardDialog(QDialog):
    "LSAT Prep dashboard: three honestly-bounded scores + coverage map."

    TITLE = "lsatDashboard"
    silentlyClose = True

    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.mw.garbage_collect_on_dialog_finish(self)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        disable_help_button(self)
        restoreGeom(self, self.TITLE, default_size=(1200, 900))
        self.setWindowTitle("LSAT Dashboard")

        self.web = AnkiWebView(kind=AnkiWebViewKind.LSAT_DASHBOARD)
        self.web.load_sveltekit_page("lsat-dashboard")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)
        self.show()

    def reject(self) -> None:
        self.web.cleanup()
        self.web = None  # type: ignore
        saveGeom(self, self.TITLE)
        aqt.dialogs.markClosed("LSATDashboard")
        QDialog.reject(self)
