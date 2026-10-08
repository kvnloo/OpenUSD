#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Opt-in lightweight context HUD dock."""

from pxr.Usdviewq.qt import QtCore, QtWidgets

from .context_state import capture_hud_state, format_hud_state
from .receipts import record_event


_REFRESH_MS = 250


class ContextHud(QtWidgets.QDockWidget):
    def __init__(self, usdviewApi):
        super(ContextHud, self).__init__(
            "Usdview Context",
            usdviewApi.qMainWindow)
        self._api = usdviewApi
        self._lastState = None

        self.setObjectName("UsdviewLabsContextHud")
        self.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea |
            QtCore.Qt.RightDockWidgetArea |
            QtCore.Qt.BottomDockWidgetArea)

        self._text = QtWidgets.QPlainTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(32)
        self.setWidget(self._text)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_REFRESH_MS)
        self._timer.timeout.connect(self.refresh)

        self.visibilityChanged.connect(
            self._visibility_changed)

    def _visibility_changed(self, visible):
        if visible:
            self._timer.start()
            self.refresh()
        else:
            self._timer.stop()

    def refresh(self):
        state = capture_hud_state(self._api)
        if state == self._lastState:
            return

        self._lastState = state
        self._text.setPlainText(format_hud_state(state))


_hud = None


def showContextHud(usdviewApi):
    global _hud
    if _hud is None:
        _hud = ContextHud(usdviewApi)
        usdviewApi.qMainWindow.addDockWidget(
            QtCore.Qt.RightDockWidgetArea,
            _hud)
        record_event(usdviewApi, "context_hud_construct")

    _hud.show()
    _hud.raise_()
    record_event(usdviewApi, "context_hud_show")
    return True


def hideContextHud(usdviewApi):
    global _hud
    if _hud is None:
        usdviewApi.PrintStatus(
            "Usdview Labs context HUD is not open")
        return False

    _hud.hide()
    record_event(usdviewApi, "context_hud_hide")
    return True
