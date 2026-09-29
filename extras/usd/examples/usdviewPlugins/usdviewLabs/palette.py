#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Ctrl+K command palette experiment for usdview."""

from __future__ import print_function

import time

from pxr.Usdviewq.qt import QtCore, QtWidgets

from .actions import (
    ACTION_CLEAR_SELECTION,
    ACTION_SELECT_PATH,
    ACTION_SET_VIEWER_MODE,
    UsdAction,
)
from .fuzzy import ranked, score
from .intents import route_text
from .receipts import execute_with_receipt, record_event
from .router import RouteDecision
from .shadow import schedule_shadow


_MAX_RESULTS = 50
_MAX_PRIM_MATCHES = 40
_MAX_PRIMS_SCANNED = 5000
_PRIM_DEBOUNCE_MS = 75


class _Entry(object):
    __slots__ = ("label", "detail", "action", "decision")

    def __init__(self, label, detail, action, decision=None):
        self.label = label
        self.detail = detail
        self.action = action
        self.decision = decision

    @property
    def search_text(self):
        return "{} {}".format(self.label, self.detail)


class CommandPalette(QtWidgets.QDialog):
    def __init__(self, usdviewApi):
        super(CommandPalette, self).__init__(usdviewApi.qMainWindow)
        self._api = usdviewApi
        self._entries = self._command_entries()
        self._pendingQuery = ""
        self._sessionMetrics = []
        self._pendingOpenMetric = None

        self.setWindowTitle("Usdview Labs")
        self.setModal(False)
        self.resize(680, 420)

        self._query = QtWidgets.QLineEdit(self)
        self._query.setPlaceholderText(
            "Search commands, intents, or prim paths")
        self._results = QtWidgets.QListWidget(self)
        self._hint = QtWidgets.QLabel(
            "Enter: run/select    Esc: close    Jev: shadow-only",
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

    def prepareOpen(self, constructed, invokeMs):
        self._pendingOpenMetric = {
            "phase": "open",
            "constructed": bool(constructed),
            "invoke_to_show_ms": round(float(invokeMs), 3),
        }

    def showEvent(self, event):
        super(CommandPalette, self).showEvent(event)
        self._sessionMetrics = []
        if self._pendingOpenMetric is not None:
            self._sessionMetrics.append(self._pendingOpenMetric)
            self._pendingOpenMetric = None

        self._showStarted = time.perf_counter()
        self._query.setFocus()
        self._query.selectAll()
        QtCore.QTimer.singleShot(0, self._record_first_paint)

    def closeEvent(self, event):
        if self._sessionMetrics:
            record_event(self._api, "palette_session", {
                "metrics": self._sessionMetrics,
                "last_query_len": len(self._pendingQuery),
            })
            self._sessionMetrics = []
        super(CommandPalette, self).closeEvent(event)

    def _record_first_paint(self):
        self._sessionMetrics.append({
            "phase": "first_paint",
            "duration_ms": round(
                (time.perf_counter() - self._showStarted) * 1000.0, 3),
        })

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
                UsdAction(
                    ACTION_SET_VIEWER_MODE,
                    {"enabled": True},
                    source="palette")),
            _Entry(
                "Disable viewer mode",
                "viewport panels restore",
                UsdAction(
                    ACTION_SET_VIEWER_MODE,
                    {"enabled": False},
                    source="palette")),
        ]

    def _scan_matching_prims(self, query):
        if len(query.strip()) < 2:
            return [], 0

        entries = []
        scanned = 0

        for prim in self._api.stage.Traverse():
            scanned += 1
            path = str(prim.GetPath())

            if score(query, path) is not None:
                entries.append(_Entry(
                    path,
                    prim.GetTypeName() or "Prim",
                    UsdAction(
                        ACTION_SELECT_PATH,
                        {"path": path},
                        source="palette")))

                if len(entries) >= _MAX_PRIM_MATCHES:
                    break

            if scanned >= _MAX_PRIMS_SCANNED:
                break

        return entries, scanned

    def _query_changed(self, text):
        self._pendingQuery = str(text)

        metric = self._refresh(
            self._pendingQuery,
            includePrims=False)
        metric["phase"] = "first_results"
        self._sessionMetrics.append(metric)

        self._primTimer.start(_PRIM_DEBOUNCE_MS)

    def _refresh_with_prims(self):
        metric = self._refresh(
            self._pendingQuery,
            includePrims=True)
        metric["phase"] = "prim_results"
        self._sessionMetrics.append(metric)

    def _refresh(self, text, includePrims):
        started = time.perf_counter()
        primsScanned = 0

        entries = ranked(
            text,
            self._entries,
            key=lambda entry: entry.search_text,
            limit=_MAX_RESULTS)

        decision = route_text(text, source="palette-intent")
        if decision.action is not None:
            entries.insert(0, _Entry(
                "Intent: {}".format(decision.action.kind),
                decision.reason,
                decision.action,
                decision))

        if includePrims and text.strip():
            primEntries, primsScanned = self._scan_matching_prims(text)
            entries.extend(primEntries)

            intentEntries = [
                entry for entry in entries if entry.decision is not None]
            normalEntries = [
                entry for entry in entries if entry.decision is None]
            normalEntries = ranked(
                text,
                normalEntries,
                key=lambda entry: entry.search_text,
                limit=_MAX_RESULTS - len(intentEntries))
            entries = intentEntries + normalEntries

        self._results.clear()

        for entry in entries[:_MAX_RESULTS]:
            item = QtWidgets.QListWidgetItem(
                "{}    {}".format(entry.label, entry.detail))
            item.setData(QtCore.Qt.UserRole, entry)
            self._results.addItem(item)

        if self._results.count():
            self._results.setCurrentRow(0)

        return {
            "query_len": len(text),
            "include_prims": bool(includePrims),
            "result_count": self._results.count(),
            "prims_scanned": primsScanned,
            "duration_ms": round(
                (time.perf_counter() - started) * 1000.0, 3),
        }

    def _run_current(self):
        item = self._results.currentItem()
        if item is None:
            return

        entry = item.data(QtCore.Qt.UserRole)
        deterministic = entry.decision or RouteDecision(
            entry.action,
            "palette selection",
            "palette")

        result = execute_with_receipt(self._api, entry.action)

        if self._pendingQuery.strip():
            schedule_shadow(
                self._api,
                self._pendingQuery,
                deterministic)

        self._api.PrintStatus(
            "Usdview Labs: {}".format(result.message))

        if result.ok:
            self.close()


_palette = None


def showPalette(usdviewApi):
    global _palette

    started = time.perf_counter()
    constructed = _palette is None

    if constructed:
        _palette = CommandPalette(usdviewApi)

    _palette.prepareOpen(
        constructed,
        (time.perf_counter() - started) * 1000.0)
    _palette.show()
    _palette.raise_()
    _palette.activateWindow()
