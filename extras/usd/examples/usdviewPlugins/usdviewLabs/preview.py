#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Explicit accept/reject UI for voice-proposed typed actions."""

import json

from pxr.Usdviewq.qt import QtWidgets

from .receipts import execute_with_receipt, record_event
from .router import action_signature, text_fingerprint


class ActionPreviewDialog(QtWidgets.QDialog):
    def __init__(self, usdviewApi, transcript, decision):
        super(ActionPreviewDialog, self).__init__(usdviewApi.qMainWindow)
        self._api = usdviewApi
        self._transcript = str(transcript)
        self._decision = decision

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

    def _receipt_fields(self):
        return {
            "text_hash": text_fingerprint(self._transcript),
            "text_len": len(self._transcript),
            "proposed_action": action_signature(self._decision.action),
            "router": self._decision.router,
        }

    def _apply(self):
        if self._decision.action is None:
            return

        result = execute_with_receipt(
            self._api,
            self._decision.action)

        fields = self._receipt_fields()
        fields.update({
            "ok": bool(result.ok),
            "message": result.message,
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
        record_event(
            self._api,
            "voice_preview_reject",
            self._receipt_fields())
        self.reject()
