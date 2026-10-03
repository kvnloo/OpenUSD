#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Opt-in hold-to-talk hotkey signaling.

Ctrl+Shift+Space emits start/stop/cancel to a loopback stage-manager target.
This module never captures audio and never receives transcripts.
"""

from __future__ import print_function

import json
import os
import queue
import socket
import threading
import time

from pxr.Usdviewq.qt import QtCore, QtWidgets

from .ptt_protocol import (
    MAX_CONTROL_BYTES,
    encode_event,
    load_target,
    target_path,
)
from .receipts import append_record, record_event


_QUEUE_SIZE = 16
_TIMEOUT_S = 0.25
_MAX_GENERATION = (1 << 63) - 1


def _next_generation(previous):
    current = time.monotonic_ns() & _MAX_GENERATION
    if current <= previous:
        current = previous + 1
    return current


class _PttSender(threading.Thread):
    def __init__(self, configDir):
        super(_PttSender, self).__init__(
            name="usdview-labs-ptt-sender")
        self.daemon = True
        self.configDir = str(configDir)
        self.events = queue.Queue(maxsize=_QUEUE_SIZE)
        self.stopEvent = threading.Event()

    def enqueue(self, op, generation):
        try:
            self.events.put_nowait({
                "op": str(op),
                "generation": int(generation),
                "queued_perf": time.perf_counter(),
            })
            return True
        except queue.Full:
            append_record(self.configDir, {
                "event": "ptt_signal_drop",
                "op": str(op),
                "generation": int(generation),
                "reason": "queue-full",
            })
            return False

    def run(self):
        while True:
            if self.stopEvent.is_set() and self.events.empty():
                break

            try:
                event = self.events.get(timeout=0.1)
            except queue.Empty:
                continue

            started = time.perf_counter()
            ok = False
            errorType = None
            targetPort = None

            try:
                target = load_target(self.configDir)
                targetPort = target["port"]
                raw = encode_event(
                    target["token"],
                    event["op"],
                    event["generation"])

                with socket.create_connection(
                        (target["host"], target["port"]),
                        timeout=_TIMEOUT_S) as conn:
                    conn.settimeout(_TIMEOUT_S)
                    conn.sendall(raw)
                    response = conn.makefile("rb").readline(
                        MAX_CONTROL_BYTES)

                payload = json.loads(response.decode("utf-8"))
                ok = bool(payload.get("ok"))
                if not ok:
                    errorType = "target-rejected"

            except Exception as exc:
                errorType = type(exc).__name__

            append_record(self.configDir, {
                "event": "ptt_signal",
                "op": event["op"],
                "generation": event["generation"],
                "ok": ok,
                "error_type": errorType,
                "target_port": targetPort,
                "queue_to_send_ms": round(
                    (started - event["queued_perf"]) * 1000.0, 3),
                "send_latency_ms": round(
                    (time.perf_counter() - started) * 1000.0, 3),
            })

    def stop(self):
        self.stopEvent.set()


class PttHotkeyController(QtCore.QObject):
    """Application event filter for Ctrl+Shift+Space press/release."""

    def __init__(self, usdviewApi):
        super(PttHotkeyController, self).__init__(
            usdviewApi.qMainWindow)
        self._api = usdviewApi
        self._enabled = False
        self._held = False
        self._generation = 0
        self._sender = None

        try:
            usdviewApi.qMainWindow.destroyed.connect(self.disable)
        except Exception:
            pass

    def enable(self):
        if self._enabled:
            self._status(
                "Usdview Labs PTT hotkey already enabled")
            return True

        if not os.path.isfile(target_path(self._api.configDir)):
            self._status(
                "Usdview Labs PTT target missing: {}".format(
                    target_path(self._api.configDir)))
            return False

        app = QtWidgets.QApplication.instance()
        if app is None:
            self._status(
                "Usdview Labs PTT: QApplication unavailable")
            return False

        self._sender = _PttSender(self._api.configDir)
        self._sender.start()
        app.installEventFilter(self)
        self._enabled = True

        record_event(self._api, "ptt_hotkey_enable", {
            "hotkey": "Ctrl+Shift+Space",
        })
        self._status(
            "Usdview Labs PTT enabled: hold Ctrl+Shift+Space")
        return True

    def disable(self, *_args):
        if not self._enabled:
            return False

        if self._held:
            self._emit("cancel")
            self._held = False

        app = QtWidgets.QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass

        sender = self._sender
        self._sender = None
        if sender is not None:
            sender.stop()

        self._enabled = False
        record_event(self._api, "ptt_hotkey_disable")
        self._status("Usdview Labs PTT hotkey disabled")
        return True

    def _status(self, message):
        try:
            self._api.PrintStatus(message)
        except Exception:
            pass

    def _emit(self, op):
        sender = self._sender
        if sender is None:
            return False
        return sender.enqueue(op, self._generation)

    def _matches_press(self, event):
        if event.key() != QtCore.Qt.Key_Space:
            return False

        modifiers = event.modifiers()
        return (
            bool(modifiers & QtCore.Qt.ControlModifier) and
            bool(modifiers & QtCore.Qt.ShiftModifier))

    def eventFilter(self, watched, event):
        if not self._enabled:
            return False

        eventType = event.type()

        if eventType == QtCore.QEvent.KeyPress:
            if (
                    not event.isAutoRepeat() and
                    not self._held and
                    self._matches_press(event)):
                self._generation = _next_generation(
                    self._generation)
                self._held = True
                self._emit("start")
                record_event(self._api, "ptt_hotkey_down", {
                    "generation": self._generation,
                })
            return False

        if eventType == QtCore.QEvent.KeyRelease:
            if (
                    self._held and
                    event.key() == QtCore.Qt.Key_Space and
                    not event.isAutoRepeat()):
                self._emit("stop")
                record_event(self._api, "ptt_hotkey_up", {
                    "generation": self._generation,
                })
                self._held = False
            return False

        deactivateTypes = {
            QtCore.QEvent.ApplicationDeactivate,
            QtCore.QEvent.WindowDeactivate,
        }
        if eventType in deactivateTypes and self._held:
            self._emit("cancel")
            record_event(self._api, "ptt_hotkey_cancel", {
                "generation": self._generation,
                "reason": "deactivate",
            })
            self._held = False

        return False


_controller = None


def _get_controller(usdviewApi):
    global _controller
    if _controller is None:
        _controller = PttHotkeyController(usdviewApi)
    return _controller


def enablePttHotkey(usdviewApi):
    return _get_controller(usdviewApi).enable()


def disablePttHotkey(usdviewApi):
    global _controller
    if _controller is None:
        usdviewApi.PrintStatus(
            "Usdview Labs PTT hotkey is not enabled")
        return False
    return _controller.disable()
