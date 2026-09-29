#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Ctrl+K command palette experiment for usdview."""

from __future__ import print_function

from pxr.Usdviewq.qt import QtCore, QtWidgets

from .actions import (
    ACTION_CLEAR_SELECTION,
    ACTION_SELECT_PATH,
    ACTION_SET_VIEWER_MODE,
    UsdAction,
)
from .fuzzy import ranked, score
from .receipts import execute_with_receipt


_MAX_RESULTS = 50
_MAX_PRIM_MATCHES = 40
_MAX_PRIMS_SCANNED = 5000
_PRIM_DEBOUNCE_MS = 75


class _Entry(object):
    __slots__ = ("label", "detail", "action")

    def __init__(self, label, detail, action):
        self.label = label
        self.detail = detail
        self.action = action

    @property
    def search_text(self):
        return "{} {}".format(self.label, self.detail)


class CommandPalette(QtWidgets.QDialog):
    def __init__(self, usdviewApi):
        super(CommandPalette, self).__init__(usdviewApi.qMainWindow)
        self._api = usdviewApi
        self._entries = self._command_entries()
        self._pendingQuery = ""

        self.setWindowTitle("Usdview Labs")
        self.setModal(False)
        self.resize(680, 420)

        self._query = QtWidgets.QLineEdit(self)
        self._query.setPlaceholderText(
            "Search commands or prim paths (for example: /World/Car)")
        self._results = QtWidgets.QListWidget(self)
        self._hint = QtWidgets.QLabel(
            "Enter: run/select    Esc: close    Prim scan is bounded",
            self)

        self._primTimer = QtCore.QTimer(self)
        self._primTimer.setSingleShot(True)
        self._primTimer.timeout.connect(self._refresh_with_prims)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._query)
        layout.addWidget(self._results)
        layout.addWidget(self._hint)

        self._query.textChanged.connect(self._query_changed)
        self._query.returnPressed.connect(self._run_current)
        self._results.itemActivated.connect(lambda _: self._run_current())
        self._refresh("", includePrims=False)

    def showEvent(self, event):
        super(CommandPalette, self).showEvent(event)
        self._query.setFocus()
        self._query.selectAll()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
            return
        super(CommandPalette, self).keyPressEvent(event)

    def _command_entries(self):
        return [
            _Entry(
                "Clear selection",
                "selection",
                UsdAction(ACTION_CLEAR_SELECTION, source="palette")),
            _Entry(
                "Enable viewer mode",
                "viewport viewer fullscreen",
                UsdAction(ACTION_SET_VIEWER_MODE, {"enabled": True},
                          source="palette")),
            _Entry(
                "Disable viewer mode",
                "viewport panels restore",
                UsdAction(ACTION_SET_VIEWER_MODE, {"enabled": False},
                          source="palette")),
        ]

    def _iter_matching_prims(self, query):
        if len(query.strip()) < 2:
            return

        count = 0
        emitted = 0
        for prim in self._api.stage.Traverse():
            count += 1
            path = str(prim.GetPath())
            if score(query, path) is not None:
                yield _Entry(
                    path,
                    prim.GetTypeName() or "Prim",
                    UsdAction(ACTION_SELECT_PATH, {"path": path},
                              source="palette"))
                emitted += 1
                if emitted >= _MAX_PRIM_MATCHES:
                    return
            if count >= _MAX_PRIMS_SCANNED:
                return

    def _query_changed(self, text):
        self._pendingQuery = str(text)
        self._refresh(self._pendingQuery, includePrims=False)
        self._primTimer.start(_PRIM_DEBOUNCE_MS)

    def _refresh_with_prims(self):
        self._refresh(self._pendingQuery, includePrims=True)

    def _refresh(self, text, includePrims):
        entries = ranked(
            text, self._entries,
            key=lambda entry: entry.search_text,
            limit=_MAX_RESULTS)

        if includePrims and text.strip():
            entries.extend(self._iter_matching_prims(text) or [])
            entries = ranked(
                text, entries,
                key=lambda entry: entry.search_text,
                limit=_MAX_RESULTS)

        self._results.clear()
        for entry in entries:
            item = QtWidgets.QListWidgetItem(
                "{}    {}".format(entry.label, entry.detail))
            item.setData(QtCore.Qt.UserRole, entry)
            self._results.addItem(item)

        if self._results.count():
            self._results.setCurrentRow(0)

    def _run_current(self):
        item = self._results.currentItem()
        if item is None:
            return
        entry = item.data(QtCore.Qt.UserRole)
        result = execute_with_receipt(self._api, entry.action)
        self._api.PrintStatus("Usdview Labs: {}".format(result.message))
        if result.ok:
            self.close()


_palette = None


def showPalette(usdviewApi):
    global _palette
    if _palette is None:
        _palette = CommandPalette(usdviewApi)
    _palette.show()
    _palette.raise_()
    _palette.activateWindow()
