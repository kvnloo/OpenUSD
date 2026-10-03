#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Append-only execution receipts for usdview Labs experiments."""

from __future__ import print_function

import json
import os
import time

from .actions import execute_action


def _selection_paths(usdviewApi):
    try:
        return [str(path) for path in usdviewApi.selectedPaths]
    except Exception:
        return []


def _receipt_path(usdviewApi):
    base = os.path.join(usdviewApi.configDir, "usdview-labs")
    if not os.path.isdir(base):
        os.makedirs(base)
    return os.path.join(base, "receipts.jsonl")


def execute_with_receipt(usdviewApi, action):
    """Execute an action and append evidence for replay/UX analysis."""

    before = _selection_paths(usdviewApi)
    started = time.perf_counter()
    result = execute_action(usdviewApi, action)
    duration_ms = (time.perf_counter() - started) * 1000.0
    after = _selection_paths(usdviewApi)

    record = {
        "schema": 1,
        "ts_unix": time.time(),
        "stage": getattr(usdviewApi, "stageIdentifier", None),
        "action": action.to_dict(),
        "ok": bool(result.ok),
        "message": result.message,
        "duration_ms": round(duration_ms, 3),
        "selection_before": before,
        "selection_after": after,
    }

    try:
        with open(_receipt_path(usdviewApi), "a") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception as exc:
        usdviewApi.PrintStatus(
            "Usdview Labs receipt write failed: {}".format(exc))

    return result
