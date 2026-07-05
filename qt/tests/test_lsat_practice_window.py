# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Anki for LSAT: guards for the desktop "Practice" window (Tier-2 parity).

Tools > LSAT > Practice opens the ``lsat-mobile`` route (the Logic drills / timed
sections / Oracle Theater the Android app runs) in a desktop webview, so those
features are reachable on the computer without pairing a phone. That window POSTs
to ``/_anki/lsat*``, which mediasrv only allows for webviews whose ``AnkiWebViewKind``
is in the api-access tuple in ``qt/aqt/webview.py::_profileForPage`` (they get an
``AuthInterceptor`` that injects the bearer). If ``LSAT_MOBILE`` is ever dropped from
that tuple, the drills window silently breaks with an "Unexpected API access" 403 --
these tests fail loudly instead.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def test_lsat_mobile_kind_exists() -> None:
    from aqt.webview import AnkiWebViewKind

    assert hasattr(AnkiWebViewKind, "LSAT_MOBILE"), (
        "AnkiWebViewKind.LSAT_MOBILE was removed; the desktop Practice window needs it"
    )


def _api_access_kinds_block() -> str:
    """The exact text of the `have_api_access = kind in ( ... )` tuple in webview.py."""
    src = (_REPO_ROOT / "qt" / "aqt" / "webview.py").read_text(encoding="utf-8")
    # Anchor on the closing paren that sits on its own line, so a ')' inside an
    # inline comment within the tuple doesn't truncate the capture.
    m = re.search(r"have_api_access\s*=\s*kind\s+in\s*\((.*?)\n\s*\)", src, re.DOTALL)
    assert m, "could not find the api-access kind tuple in qt/aqt/webview.py"
    return m.group(1)


def test_lsat_mobile_has_api_access() -> None:
    block = _api_access_kinds_block()
    assert "LSAT_MOBILE" in block, (
        "AnkiWebViewKind.LSAT_MOBILE must be in _profileForPage's api-access tuple, "
        "or the desktop Practice window's /_anki/lsat* POSTs get a 403."
    )
    # Sanity: the dashboard (the other first-party PWA webview) is still there too.
    assert "LSAT_DASHBOARD" in block


def test_practice_dialog_registered() -> None:
    # The menu opens the window via aqt.dialogs.open("LSATPractice", mw), which
    # requires the dialog to be in the DialogManager registry.
    from aqt import DialogManager

    assert "LSATPractice" in DialogManager._dialogs, (
        'aqt.dialogs registry is missing "LSATPractice"; Tools > LSAT > Practice would raise'
    )


def test_practice_dialog_loads_mobile_route() -> None:
    # Cheap source check (constructing the dialog needs a running Qt app): the
    # dialog must load the lsat-mobile route with the api-access kind.
    src = (_REPO_ROOT / "qt" / "aqt" / "lsat_mobile.py").read_text(encoding="utf-8")
    assert "class LsatPracticeDialog" in src
    assert "AnkiWebViewKind.LSAT_MOBILE" in src
    assert "load_sveltekit_page(MOBILE_PAGE)" in src
