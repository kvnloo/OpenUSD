#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Interruption-safe local transcript bridge for usdview Labs."""

from __future__ import print_function

import json
import os
import queue
import secrets
import socket
import threading
import time

from pxr.Usdviewq.qt import QtCore

from .preview import ActionPreviewDialog, QueryResultDialog
from .queries import execute_query, route_query_text
from .receipts import record_event
from .router import text_fingerprint
from .voice import ingest_transcript
from .voice_lifecycle import GenerationGate
from .voice_protocol import (
    MAX_MESSAGE_BYTES,
    decode_message,
    encode_response,
)


_HOST = "127.0.0.1"
_QUEUE_SIZE = 8
_POLL_MS = 30


class _VoiceServer(threading.Thread):
    def __init__(self, port, token, outputQueue, gate):
        super(_VoiceServer, self).__init__(
            name="usdview-labs-voice-server")
        self.daemon = True

        self.port = int(port)
        self.token = str(token)
        self.outputQueue = outputQueue
        self.gate = gate

        self.ready = threading.Event()
        self.stopEvent = threading.Event()
        self.error = None
        self.boundPort = None

    def _offer_latest(self, message):
        try:
            self.outputQueue.put_nowait(message)
            return
        except queue.Full:
            pass

        try:
            self.outputQueue.get_nowait()
        except queue.Empty:
            pass

        try:
            self.outputQueue.put_nowait(message)
        except queue.Full:
            pass

    def run(self):
        server = None

        try:
            server = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM)
            server.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1)
            server.bind((_HOST, self.port))
            self.boundPort = server.getsockname()[1]
            server.listen(4)
            server.settimeout(0.25)
            self.ready.set()

            while not self.stopEvent.is_set():
                try:
                    conn, _addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self.stopEvent.is_set():
                        break
                    raise

                with conn:
                    conn.settimeout(0.5)
                    data = b""

                    try:
                        while (
                                b"\n" not in data and
                                len(data) <= MAX_MESSAGE_BYTES):
                            chunk = conn.recv(4096)
                            if not chunk:
                                break
                            data += chunk

                        raw = data.split(b"\n", 1)[0]
                        message = decode_message(
                            raw,
                            self.token)
                        message["_received_perf"] = time.perf_counter()
                        message["_received_unix"] = time.time()

                        accepted = self.gate.observe(message)
                        if not accepted:
                            conn.sendall(encode_response(
                                True,
                                queued=False,
                                stale=True,
                                latest_generation=self.gate.latest()))
                            continue

                        queued = False
                        if message["op"] in {
                                "start", "final", "cancel"}:
                            self._offer_latest(message)
                            queued = True

                        conn.sendall(encode_response(
                            True,
                            queued=queued,
                            stale=False,
                            latest_generation=self.gate.latest()))

                    except Exception as exc:
                        try:
                            conn.sendall(encode_response(
                                False,
                                error=str(exc)))
                        except Exception:
                            pass

        except Exception as exc:
            self.error = exc
            self.ready.set()

        finally:
            if server is not None:
                try:
                    server.close()
                except Exception:
                    pass

    def stop(self):
        self.stopEvent.set()


class VoiceBridgeController(QtCore.QObject):
    def __init__(self, usdviewApi):
        super(VoiceBridgeController, self).__init__(
            usdviewApi.qMainWindow)

        self._api = usdviewApi
        self._queue = queue.Queue(maxsize=_QUEUE_SIZE)
        self._server = None
        self._gate = None
        self._token = None
        self._endpointPath = None
        self._preview = None
        self._previewGeneration = None

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_POLL_MS)
        self._timer.timeout.connect(self._poll)

        try:
            usdviewApi.qMainWindow.destroyed.connect(self.stop)
        except Exception:
            pass

    def _requested_port(self):
        value = os.environ.get(
            "USDVIEW_LABS_VOICE_PORT",
            "0").strip()

        try:
            port = int(value)
        except ValueError:
            raise ValueError(
                "USDVIEW_LABS_VOICE_PORT must be an integer")

        if port < 0 or port > 65535:
            raise ValueError("voice port out of range")

        return port

    def _endpoint_dir(self):
        base = os.path.join(
            str(self._api.configDir),
            "usdview-labs")

        if not os.path.isdir(base):
            try:
                os.makedirs(base)
            except OSError:
                if not os.path.isdir(base):
                    raise

        return base

    def _write_endpoint(self):
        path = os.path.join(
            self._endpoint_dir(),
            "voice-endpoint.json")
        tempPath = path + ".tmp"

        payload = {
            "protocol": 2,
            "host": _HOST,
            "port": self._server.boundPort,
            "token": self._token,
            "pid": os.getpid(),
            "created_unix": time.time(),
        }

        fd = os.open(
            tempPath,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600)

        with os.fdopen(fd, "w") as stream:
            json.dump(
                payload,
                stream,
                sort_keys=True)

        os.replace(tempPath, path)

        try:
            os.chmod(path, 0o600)
        except Exception:
            pass

        self._endpointPath = path
        return path

    def start(self):
        if (
                self._server is not None and
                self._server.is_alive()):
            self._safe_status(
                "Usdview Labs voice bridge already running on "
                "127.0.0.1:{}".format(
                    self._server.boundPort))
            return True

        self._token = secrets.token_urlsafe(24)
        self._gate = GenerationGate()

        try:
            port = self._requested_port()
        except Exception as exc:
            self._safe_status(
                "Usdview Labs voice bridge: {}".format(exc))
            return False

        server = _VoiceServer(
            port,
            self._token,
            self._queue,
            self._gate)
        self._server = server
        server.start()

        if not server.ready.wait(0.5):
            self._safe_status(
                "Usdview Labs voice bridge did not become ready")
            self.stop()
            return False

        if server.error is not None:
            self._safe_status(
                "Usdview Labs voice bridge failed: {}".format(
                    server.error))
            self.stop()
            return False

        try:
            endpointPath = self._write_endpoint()
        except Exception as exc:
            self._safe_status(
                "Usdview Labs voice bridge endpoint failed: {}".format(
                    exc))
            self.stop()
            return False

        self._timer.start()

        record_event(self._api, "voice_bridge_start", {
            "host": _HOST,
            "port": server.boundPort,
            "protocol": 2,
        })

        self._safe_status(
            "Usdview Labs voice bridge: 127.0.0.1:{} ({})".format(
                server.boundPort,
                endpointPath))
        return True

    def stop(self, *_args):
        self._timer.stop()

        self._cancel_preview(
            "voice bridge stopped")

        oldServer = self._server
        self._server = None
        if oldServer is not None:
            oldServer.stop()

        if self._endpointPath:
            try:
                os.remove(self._endpointPath)
            except OSError:
                pass
            self._endpointPath = None

        self._token = None
        self._gate = None

        try:
            record_event(
                self._api,
                "voice_bridge_stop")
        except Exception:
            pass

        self._safe_status(
            "Usdview Labs voice bridge stopped")

    def _safe_status(self, message):
        try:
            self._api.PrintStatus(message)
        except Exception:
            pass

    def _poll(self):
        latest = None

        while True:
            try:
                latest = self._queue.get_nowait()
            except queue.Empty:
                break

        if latest is not None:
            self._handle(latest)

    def _handle(self, message):
        op = message["op"]
        generation = int(message["generation"])

        if op == "start":
            self._cancel_preview(
                "superseded by generation {}".format(generation))
            record_event(self._api, "voice_generation_start", {
                "generation": generation,
            })
            return

        if op == "cancel":
            self._cancel_preview(
                "generation {} cancelled".format(generation))
            record_event(self._api, "voice_generation_cancel", {
                "generation": generation,
            })
            return

        if op != "final":
            return

        if (
                self._gate is None or
                not self._gate.can_execute(generation)):
            record_event(self._api, "voice_final_dropped", {
                "generation": generation,
                "reason": "stale-or-cancelled",
            })
            return

        self._cancel_preview(
            "superseded by newer final")

        transcript = message["transcript"]
        query = route_query_text(
            transcript,
            source="voice-query")

        if query is not None:
            result = execute_query(
                self._api,
                query)
            record_event(self._api, "voice_query", {
                "generation": generation,
                "text_hash": text_fingerprint(transcript),
                "text_len": len(transcript),
                "query": query.to_dict(),
                "ok": bool(result.ok),
            })
            self._show_query(
                message,
                query,
                result)
            return

        decision = ingest_transcript(
            self._api,
            transcript,
            shadow=True)
        self._show_action(
            message,
            decision)

    def _show_action(self, message, decision):
        generation = int(message["generation"])

        dialog = ActionPreviewDialog(
            self._api,
            message["transcript"],
            decision,
            generation=generation,
            acceptGuard=lambda g=generation: (
                self._gate is not None and
                self._gate.can_execute(g)),
            receivedPerf=message.get("_received_perf"),
            clientSentUnix=message.get("client_sent_unix"))

        self._attach_preview(
            dialog,
            generation)

    def _show_query(self, message, query, result):
        generation = int(message["generation"])

        dialog = QueryResultDialog(
            self._api,
            message["transcript"],
            query,
            result,
            generation=generation,
            receivedPerf=message.get("_received_perf"),
            clientSentUnix=message.get("client_sent_unix"))

        self._attach_preview(
            dialog,
            generation)

    def _attach_preview(self, dialog, generation):
        self._preview = dialog
        self._previewGeneration = int(generation)

        dialog.finished.connect(
            lambda _code, d=dialog: self._preview_finished(d))
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _preview_finished(self, dialog):
        if self._preview is dialog:
            self._preview = None
            self._previewGeneration = None

    def _cancel_preview(self, reason):
        dialog = self._preview
        self._preview = None
        self._previewGeneration = None

        if dialog is not None:
            try:
                dialog.cancelFromBridge(reason)
            except Exception:
                try:
                    dialog.reject()
                except Exception:
                    pass


_controller = None


def _get_controller(usdviewApi):
    global _controller

    if _controller is None:
        _controller = VoiceBridgeController(
            usdviewApi)

    return _controller


def startVoiceBridge(usdviewApi):
    return _get_controller(usdviewApi).start()


def stopVoiceBridge(usdviewApi):
    global _controller

    if _controller is None:
        usdviewApi.PrintStatus(
            "Usdview Labs voice bridge is not running")
        return False

    _controller.stop()
    return True
