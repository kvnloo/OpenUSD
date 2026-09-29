#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Append-only receipts for usdview Labs experiments."""

from __future__ import print_function

import json
import os
import threading
import time

from .actions import execute_action


_WRITE_LOCK = threading.Lock()


def _selection_paths(usdviewApi):
    try:
        return [str(path) for path in usdviewApi.selectedPaths]
    except Exception:
        return []


def _receipt_path_from_dir(configDir):
    base = os.path.join(str(configDir), "usdview-labs")
    if not os.path.isdir(base):
        try:
            os.makedirs(base)
        except OSError:
            if not os.path.isdir(base):
                raise
    return os.path.join(base, "receipts.jsonl")


def append_record(configDir, record):
    """Append one JSONL record. Return an exception instead of raising."""
    payload = dict(record)
    payload.setdefault("schema", 2)
    payload.setdefault("ts_unix", time.time())

    try:
        path = _receipt_path_from_dir(configDir)
        with _WRITE_LOCK:
            with open(path, "a") as stream:
                stream.write(json.dumps(payload, sort_keys=True) + "\n")
        return None
    except Exception as exc:
        return exc


def _report_error(usdviewApi, exc):
    if exc is None:
        return
    try:
        usdviewApi.PrintStatus(
            "Usdview Labs receipt write failed: {}".format(exc))
    except Exception:
        pass


def record_event(usdviewApi, event, fields=None):
    record = {
        "event": str(event),
        "stage": getattr(usdviewApi, "stageIdentifier", None),
    }
    record.update(dict(fields or {}))
    _report_error(
        usdviewApi,
        append_record(usdviewApi.configDir, record))


def execute_with_receipt(usdviewApi, action):
    """Execute one typed action and append before/after evidence."""
    before = _selection_paths(usdviewApi)
    started = time.perf_counter()
    result = execute_action(usdviewApi, action)
    duration_ms = (time.perf_counter() - started) * 1000.0

    record = {
        "event": "action",
        "stage": getattr(usdviewApi, "stageIdentifier", None),
        "action": action.to_dict(),
        "ok": bool(result.ok),
        "message": result.message,
        "duration_ms": round(duration_ms, 3),
        "selection_before": before,
        "selection_after": _selection_paths(usdviewApi),
    }

    _report_error(
        usdviewApi,
        append_record(usdviewApi.configDir, record))
    return result
