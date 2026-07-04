# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from __future__ import annotations

import enum
import re
from collections.abc import Callable
from typing import Any, cast

import aqt
from anki.sync import SyncStatus
from aqt import gui_hooks, props
from aqt.qt import *
from aqt.sync import get_sync_status
from aqt.theme import theme_manager
from aqt.utils import tr
from aqt.webview import AnkiWebView, AnkiWebViewKind


class HideMode(enum.IntEnum):
    FULLSCREEN = 0
    ALWAYS = 1


# wrapper class for set_bridge_command()
class TopToolbar:
    def __init__(self, toolbar: Toolbar) -> None:
        self.toolbar = toolbar


# wrapper class for set_bridge_command()
class BottomToolbar:
    def __init__(self, toolbar: Toolbar) -> None:
        self.toolbar = toolbar


class ToolbarWebView(AnkiWebView):
    hide_condition: Callable[..., bool]

    def __init__(
        self, mw: aqt.AnkiQt, kind: AnkiWebViewKind = AnkiWebViewKind.DEFAULT
    ) -> None:
        AnkiWebView.__init__(self, mw, kind=kind)
        self.mw = mw
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.disable_zoom()
        self.hidden = False
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.reset_timer()

    def reset_timer(self) -> None:
        self.hide_timer.stop()
        self.hide_timer.setInterval(2000)

    def hide(self) -> None:
        self.hidden = True

    def show(self) -> None:
        self.hidden = False


class TopWebView(ToolbarWebView):
    def __init__(self, mw: aqt.AnkiQt) -> None:
        super().__init__(mw, kind=AnkiWebViewKind.TOP_TOOLBAR)
        self.web_height = 0
        qconnect(self.hide_timer.timeout, self.hide_if_allowed)

    def eventFilter(self, obj, evt):
        if handled := super().eventFilter(obj, evt):
            return handled

        # prevent collapse of both toolbars if pointer is inside one of them
        if evt.type() == QEvent.Type.Enter:
            self.reset_timer()
            self.mw.bottomWeb.reset_timer()
            return True

        return False

    def on_body_classes_need_update(self) -> None:
        super().on_body_classes_need_update()

        if self.mw.state == "review":
            if self.mw.pm.hide_top_bar():
                self.eval("""document.body.classList.remove("flat"); """)
            else:
                self.flatten()

        self.adjustHeightToFit()
        self.show()

    def _onHeight(self, qvar: int | None) -> None:
        super()._onHeight(qvar)
        if qvar:
            self.web_height = int(qvar)

    def hide_if_allowed(self) -> None:
        if self.mw.state != "review":
            return

        # Invariant: The `hide_if_allowed` method ensures that the fullscreen state is checked
        # and the menubar will be hidden if necessary
        # Note: The `eventFilter` and `_reviewState` methods in `qt/aqt/main.py` rely on this invariant
        if self.mw.fullscreen:
            self.mw.hide_menubar()

        if self.mw.pm.hide_top_bar():
            if (
                self.mw.pm.top_bar_hide_mode() == HideMode.FULLSCREEN
                and not self.mw.windowState() & Qt.WindowState.WindowFullScreen
            ):
                self.show()
                return

            self.hide()

    def hide(self) -> None:
        super().hide()

        self.hidden = True
        self.eval(
            """document.body.classList.add("hidden"); """,
        )

    def show(self) -> None:
        super().show()

        self.eval("""document.body.classList.remove("hidden"); """)

    def flatten(self) -> None:
        self.eval("""document.body.classList.add("flat"); """)

    def elevate(self) -> None:
        self.eval(
            """
            document.body.classList.remove("flat");
            document.body.style.removeProperty("background");
            """
        )

    def update_background_image(self) -> None:
        if self.mw.pm.minimalist_mode():
            return

        def set_background(computed: str) -> None:
            # remove offset from copy
            background = re.sub(r"-\d+px ", "0%", computed)
            # ensure alignment with main webview
            background = re.sub(r"\sfixed", "", background)
            # change computedStyle px value back to 100vw
            background = re.sub(r"\d+px", "100vw", background)

            self.eval(
                f"""
                    document.body.style.setProperty("background", '{background}');
                """
            )
            self.set_body_height(self.mw.web.height())

            # offset reviewer background by toolbar height
            if self.web_height:
                self.mw.web.eval(
                    f"""document.body.style.setProperty("background-position-y", "-{self.web_height}px"); """
                )

        self.mw.web.evalWithCallback(
            """window.getComputedStyle(document.body).background; """,
            set_background,
        )

    def set_body_height(self, height: int) -> None:
        self.eval(
            f"""document.body.style.setProperty("min-height", "{self.mw.web.height()}px"); """
        )

    def adjustHeightToFit(self) -> None:
        self.eval("""document.body.style.setProperty("min-height", "0px"); """)
        self.evalWithCallback("document.documentElement.offsetHeight", self._onHeight)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)

        self.mw.web.evalWithCallback(
            """window.innerHeight; """,
            self.set_body_height,
        )


class BottomWebView(ToolbarWebView):
    def __init__(self, mw: aqt.AnkiQt) -> None:
        super().__init__(mw, kind=AnkiWebViewKind.BOTTOM_TOOLBAR)
        qconnect(self.hide_timer.timeout, self.hide_if_allowed)

    def eventFilter(self, obj, evt):
        if handled := super().eventFilter(obj, evt):
            return handled

        if evt.type() == QEvent.Type.Enter:
            self.reset_timer()
            self.mw.toolbarWeb.reset_timer()
            return True

        return False

    def on_body_classes_need_update(self) -> None:
        super().on_body_classes_need_update()
        if self.mw.state == "review":
            self.show()

    def animate_height(self, height: int) -> None:
        self.web_height = height

        if self.mw.pm.reduce_motion() or height == self.height():
            self.setFixedHeight(height)
        else:
            # Collapse/Expand animation
            self.setMinimumHeight(0)
            self.animation = QPropertyAnimation(
                self, cast(QByteArray, b"maximumHeight")
            )
            self.animation.setDuration(int(theme_manager.var(props.TRANSITION)))
            self.animation.setStartValue(self.height())
            self.animation.setEndValue(height)
            qconnect(self.animation.finished, lambda: self.setFixedHeight(height))
            self.animation.start()

    def hide_if_allowed(self) -> None:
        if self.mw.state != "review":
            return

        if self.mw.pm.hide_bottom_bar():
            if (
                self.mw.pm.bottom_bar_hide_mode() == HideMode.FULLSCREEN
                and not self.mw.windowState() & Qt.WindowState.WindowFullScreen
            ):
                self.show()
                return

            self.hide()

    def hide(self) -> None:
        super().hide()

        self.hidden = True
        self.animate_height(1)

    def show(self) -> None:
        super().show()

        self.hidden = False
        if self.mw.state == "review":
            # delay to account for reflow
            def cb(height: int | None):
                # "When QWebEnginePage is deleted, the callback is triggered with an invalid value"
                if height is not None:
                    self.animate_height(height)

            self.mw.progress.single_shot(
                50,
                lambda: self.evalWithCallback(
                    "document.documentElement.offsetHeight", cb
                ),
                False,
            )
        else:
            self.adjustHeightToFit()


class Toolbar:
    def __init__(self, mw: aqt.AnkiQt, web: AnkiWebView) -> None:
        self.mw = mw
        self.web = web
        self.link_handlers: dict[str, Callable] = {
            "study": self._studyLinkHandler,
        }
        self.web.requiresCol = False

    def draw(
        self,
        buf: str = "",
        web_context: Any | None = None,
        link_handler: Callable[[str], Any] | None = None,
    ) -> None:
        web_context = web_context or TopToolbar(self)
        link_handler = link_handler or self._linkHandler
        self.web.set_bridge_command(link_handler, web_context)
        body = self._body.format(
            toolbar_content=self._centerLinks(),
            left_tray_content=self._left_tray_content(),
            right_tray_content=self._right_tray_content(),
        )
        self.web.stdHtml(
            body,
            css=["css/toolbar.css"],
            js=["js/vendor/jquery.min.js", "js/toolbar.js"],
            head=self._lsat_head,
            context=web_context,
        )
        self.web.adjustHeightToFit()

    def redraw(self) -> None:
        self.set_sync_active(self.mw.media_syncer.is_syncing())
        self.update_sync_status()
        gui_hooks.top_toolbar_did_redraw(self)

    # Available links
    ######################################################################

    def create_link(
        self,
        cmd: str,
        label: str,
        func: Callable,
        tip: str | None = None,
        id: str | None = None,
    ) -> str:
        """Generates HTML link element and registers link handler

        Arguments:
            cmd {str} -- Command name used for the JS → Python bridge
            label {str} -- Display label of the link
            func {Callable} -- Callable to be called on clicking the link

        Keyword Arguments:
            tip {Optional[str]} -- Optional tooltip text to show on hovering
                                   over the link (default: {None})
            id: {Optional[str]} -- Optional id attribute to supply the link with
                                   (default: {None})

        Returns:
            str -- HTML link element
        """

        self.link_handlers[cmd] = func

        title_attr = f'title="{tip}"' if tip else ""
        id_attr = f'id="{id}"' if id else ""

        return (
            f"""<a class=hitem tabindex="-1" aria-label="{label}" """
            f"""{title_attr} {id_attr} href=# onclick="return pycmd('{cmd}')">"""
            f"""{label}</a>"""
        )

    def _centerLinks(self) -> str:
        links = [
            self.create_link(
                "decks",
                tr.actions_decks(),
                self._deckLinkHandler,
                tip=tr.actions_shortcut_key(val="D"),
                id="decks",
            ),
            self.create_link(
                "add",
                tr.actions_add(),
                self._addLinkHandler,
                tip=tr.actions_shortcut_key(val="A"),
                id="add",
            ),
            self.create_link(
                "browse",
                tr.qt_misc_browse(),
                self._browseLinkHandler,
                tip=tr.actions_shortcut_key(val="B"),
                id="browse",
            ),
            self.create_link(
                "stats",
                tr.qt_misc_stats(),
                self._statsLinkHandler,
                tip=tr.actions_shortcut_key(val="T"),
                id="stats",
            ),
        ]

        links.append(self._create_sync_link())

        gui_hooks.top_toolbar_did_init_links(links, self)

        return "\n".join(links)

    # Add-ons
    ######################################################################

    def _left_tray_content(self) -> str:
        left_tray_content: list[str] = []
        gui_hooks.top_toolbar_will_set_left_tray_content(left_tray_content, self)
        return self._process_tray_content(left_tray_content)

    def _right_tray_content(self) -> str:
        right_tray_content: list[str] = []
        gui_hooks.top_toolbar_will_set_right_tray_content(right_tray_content, self)
        return self._process_tray_content(right_tray_content)

    def _process_tray_content(self, content: list[str]) -> str:
        return "\n".join(f"""<div class="tray-item">{item}</div>""" for item in content)

    # Sync
    ######################################################################

    def _create_sync_link(self) -> str:
        name = tr.qt_misc_sync()
        title = tr.actions_shortcut_key(val="Y")
        label = "sync"
        self.link_handlers[label] = self._syncLinkHandler

        return f"""
<a class=hitem tabindex="-1" aria-label="{name}" title="{title}" id="{label}" href=# onclick="return pycmd('{label}')"
>{name}<img id=sync-spinner src='/_anki/imgs/refresh.svg'>
</a>"""

    def set_sync_active(self, active: bool) -> None:
        method = "add" if active else "remove"
        self.web.eval(
            f"document.getElementById('sync-spinner').classList.{method}('spin')"
        )

    def set_sync_status(self, status: SyncStatus) -> None:
        self.web.eval(f"updateSyncColor({status.required})")

    def update_sync_status(self) -> None:
        get_sync_status(self.mw, self.mw.toolbar.set_sync_status)

    # Link handling
    ######################################################################

    def _linkHandler(self, link: str) -> bool:
        if link in self.link_handlers:
            self.link_handlers[link]()
        return False

    def _deckLinkHandler(self) -> None:
        self.mw.moveToState("deckBrowser")

    def _studyLinkHandler(self) -> None:
        # if overview already shown, switch to review
        if self.mw.state == "overview":
            self.mw.col.startTimebox()
            self.mw.moveToState("review")
        else:
            self.mw.onOverview()

    def _addLinkHandler(self) -> None:
        self.mw.onAddCard()

    def _browseLinkHandler(self) -> None:
        self.mw.onBrowse()

    def _statsLinkHandler(self) -> None:
        self.mw.onStats()

    def _syncLinkHandler(self) -> None:
        self.mw.on_sync_button_clicked()

    # HTML & CSS
    ######################################################################

    # LSAT Prep brand lockup (turnstile mark + wordmark) sits at the far left of
    # the toolbar's left tray. It is decorative only: no id, no href, no pycmd,
    # so it cannot affect navigation, and it lives in a separate grid column from
    # the (still centered) nav links, so layout is unchanged.
    _lsat_brand = (
        '<span class="lsat-brand" aria-hidden="true">'
        '<svg class="lsat-mark" width="15" height="15" viewBox="0 0 24 24"'
        ' fill="none" stroke="currentColor" stroke-width="2"'
        ' stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M8 4 V20 M8 12 H18"/></svg>'
        '<span class="lsat-word">LSAT&nbsp;Prep</span>'
        "</span>"
    )

    _body = (
        """
<div class="header">
  <div class="left-tray">"""
        + _lsat_brand
        + """{left_tray_content}</div>
  <div class="toolbar">{toolbar_content}</div>
  <div class="right-tray">{right_tray_content}</div>
</div>
"""
    )

    # LSAT Prep desktop chrome accent. Injected via stdHtml(head=...) so it lands
    # after the bundled toolbar.css and only layers brand color/hover/sync tints
    # on top of Anki's own theme vars (which flip for light/dark). Purely visual:
    # no link ids, handlers, or structural layout are touched here.
    _lsat_head = """
<style>
:root { --lsat-accent: #4f46e5; --lsat-accent-2: #7c3aed; }
:root.night-mode { --lsat-accent: #7c86ff; --lsat-accent-2: #a78bfa; }

.lsat-brand {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  color: var(--lsat-accent);
  white-space: nowrap;
  -webkit-user-select: none;
  user-select: none;
}
.lsat-brand .lsat-mark { flex: none; display: block; }
.lsat-brand .lsat-word {
  color: var(--fg);
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 0.04em;
  opacity: 0.9;
}
body.fancy .lsat-brand { padding-left: 16px; }

/* indigo accent for the hover / pressed link state */
.hitem:hover,
.hitem:active { color: var(--lsat-accent) !important; }
body.fancy .hitem:hover {
  border-color: color-mix(in srgb, var(--lsat-accent) 45%, transparent) !important;
}
body.fancy .hitem:active {
  background: color-mix(in srgb, var(--lsat-accent) 12%, transparent) !important;
}

/* brand the "changes pending" sync label + tint the spinner indigo */
.normal-sync { color: var(--lsat-accent) !important; }
#sync-spinner.spin {
  filter: brightness(0) saturate(100%) invert(26%) sepia(91%) saturate(2360%)
    hue-rotate(239deg) brightness(95%) contrast(92%);
}
:root.night-mode #sync-spinner.spin {
  filter: brightness(0) saturate(100%) invert(26%) sepia(91%) saturate(2360%)
    hue-rotate(239deg) brightness(125%) contrast(90%);
}
</style>
"""


# Bottom bar
######################################################################


class BottomBar(Toolbar):
    _centerBody = """
<center id=outer><table width=100%% id=header><tr><td align=center>
%s</td></tr></table></center>
"""

    def draw(
        self,
        buf: str = "",
        web_context: Any | None = None,
        link_handler: Callable[[str], Any] | None = None,
    ) -> None:
        # note: some screens may override this
        web_context = web_context or BottomToolbar(self)
        link_handler = link_handler or self._linkHandler
        self.web.set_bridge_command(link_handler, web_context)
        self.web.stdHtml(
            self._centerBody % buf,
            css=["css/toolbar.css", "css/toolbar-bottom.css"],
            context=web_context,
        )
        self.web.adjustHeightToFit()
