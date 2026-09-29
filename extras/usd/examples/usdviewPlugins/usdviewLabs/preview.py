#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Preview/result UI for voice actions and read-only queries."""

import json
import time

from pxr.Usdviewq.qt import QtWidgets

from .receipts import execute_with_receipt, record_event
from .router import action_signature, text_fingerprint


def _latency_ms(started):
    if started is None:
        return None
    return round((time.perf_counter() - started) * 1000.0, 3)


def _client_latency_ms(clientSentUnix):
    if clientSentUnix is None:
        return None
    value = (time.time() - float(clientSentUnix)) * 1000.0
    # Ignore obviously invalid/skewed timestamps.
    if value < -1000.0 or value > 60000.0:
        return None
    return round(value, 3)


class ActionPreviewDialog(QtWidgets.QDialog):
    def __init__(
            self,
            usdviewApi,
            transcript,
            decision,
            generation=0,
            acceptGuard=None,
            receivedPerf=None,
            clientSentUnix=None):
        super(ActionPreviewDialog, self).__init__(usdviewApi.qMainWindow)
        self._api = usdviewApi
        self._transcript = str(transcript)
        self._decision = decision
        self._generation = int(generation)
        self._acceptGuard = acceptGuard or (lambda: True)
        self._receivedPerf = receivedPerf
        self._clientSentUnix = clientSentUnix
        self._shownPerf = None
        self._paintRecorded = False

        self.setWindowTitle("Voice action preview")
        self.setModal(False)
        self.resize(620, 320)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel("Transcript"))
        transcriptView = QtWidgets.QPlainTextEdit(self)
        transcriptView.setReadOnly(True)
        transcriptView.setPlainText(self._transcript)
        transcriptView.setMaximumHeight(90)
        layout.addWidget(transcriptView)

        layout.addWidget(QtWidgets.QLabel("Proposed typed action"))
        actionView = QtWidgets.QPlainTextEdit(self)
        actionView.setReadOnly(True)
        signature = action_signature(decision.action)
        actionView.setPlainText(
            json.dumps(signature, indent=2, sort_keys=True)
            if signature else
            "No supported deterministic action")
        actionView.setMaximumHeight(110)
        layout.addWidget(actionView)

        buttons = QtWidgets.QDialogButtonBox(self)
        self._accept = buttons.addButton(
            "Accept",
            QtWidgets.QDialogButtonBox.AcceptRole)
        self._reject = buttons.addButton(
            "Reject",
            QtWidgets.QDialogButtonBox.RejectRole)

        self._accept.setEnabled(decision.action is not None)
        self._accept.clicked.connect(self._apply)
        self._reject.clicked.connect(self._reject_action)
        layout.addWidget(buttons)

    def showEvent(self, event):
        super(ActionPreviewDialog, self).showEvent(event)
        if self._paintRecorded:
            return
        self._paintRecorded = True
        self._shownPerf = time.perf_counter()

        fields = self._receipt_fields()
        fields.update({
            "bridge_to_preview_ms": _latency_ms(self._receivedPerf),
            "client_to_preview_ms": _client_latency_ms(
                self._clientSentUnix),
        })
        record_event(
            self._api,
            "voice_preview_paint",
            fields)

    def _receipt_fields(self):
        return {
            "generation": self._generation,
            "text_hash": text_fingerprint(self._transcript),
            "text_len": len(self._transcript),
            "proposed_action": action_signature(self._decision.action),
            "router": self._decision.router,
        }

    def _apply(self):
        if self._decision.action is None:
            return

        if not self._acceptGuard():
            fields = self._receipt_fields()
            fields["preview_to_accept_ms"] = _latency_ms(
                self._shownPerf)
            record_event(
                self._api,
                "voice_preview_stale_accept_blocked",
                fields)
            self._api.PrintStatus(
                "Usdview Labs voice: stale/cancelled utterance blocked")
            self.reject()
            return

        result = execute_with_receipt(
            self._api,
            self._decision.action)

        fields = self._receipt_fields()
        fields.update({
            "ok": bool(result.ok),
            "message": result.message,
            "preview_to_accept_ms": _latency_ms(
                self._shownPerf),
        })
        record_event(
            self._api,
            "voice_preview_accept",
            fields)

        self._api.PrintStatus(
            "Usdview Labs voice: {}".format(result.message))

        if result.ok:
            self.accept()

    def _reject_action(self):
        fields = self._receipt_fields()
        fields["preview_to_reject_ms"] = _latency_ms(
            self._shownPerf)
        record_event(
            self._api,
            "voice_preview_reject",
            fields)
        self.reject()

    def cancelFromBridge(self, reason):
        fields = self._receipt_fields()
        fields["reason"] = str(reason)
        fields["preview_to_cancel_ms"] = _latency_ms(
            self._shownPerf)
        record_event(
            self._api,
            "voice_preview_cancel",
            fields)
        self.reject()


class QueryResultDialog(QtWidgets.QDialog):
    def __init__(
            self,
            usdviewApi,
            transcript,
            query,
            result,
            generation=0,
            receivedPerf=None,
            clientSentUnix=None):
        super(QueryResultDialog, self).__init__(usdviewApi.qMainWindow)
        self._api = usdviewApi
        self._transcript = str(transcript)
        self._query = query
        self._result = result
        self._generation = int(generation)
        self._receivedPerf = receivedPerf
        self._clientSentUnix = clientSentUnix
        self._paintRecorded = False

        self.setWindowTitle("Voice scene answer")
        self.setModal(False)
        self.resize(620, 260)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Question"))

        questionView = QtWidgets.QPlainTextEdit(self)
        questionView.setReadOnly(True)
        questionView.setPlainText(self._transcript)
        questionView.setMaximumHeight(75)
        layout.addWidget(questionView)

        layout.addWidget(QtWidgets.QLabel("Answer"))
        answerView = QtWidgets.QPlainTextEdit(self)
        answerView.setReadOnly(True)
        answerView.setPlainText(str(result.message))
        answerView.setMaximumHeight(100)
        layout.addWidget(answerView)

        buttons = QtWidgets.QDialogButtonBox(self)
        closeButton = buttons.addButton(
            "Close",
            QtWidgets.QDialogButtonBox.RejectRole)
        closeButton.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def showEvent(self, event):
        super(QueryResultDialog, self).showEvent(event)
        if self._paintRecorded:
            return
        self._paintRecorded = True

        record_event(self._api, "voice_query_paint", {
            "generation": self._generation,
            "text_hash": text_fingerprint(self._transcript),
            "text_len": len(self._transcript),
            "query": self._query.to_dict(),
            "ok": bool(self._result.ok),
            "bridge_to_result_ms": _latency_ms(
                self._receivedPerf),
            "client_to_result_ms": _client_latency_ms(
                self._clientSentUnix),
        })

    def cancelFromBridge(self, reason):
        record_event(self._api, "voice_query_cancel", {
            "generation": self._generation,
            "query": self._query.to_dict(),
            "reason": str(reason),
        })
        self.reject()
