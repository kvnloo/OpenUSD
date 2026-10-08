#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Asynchronous Jev shadow scheduling.

The worker receives only captured read-only context and never receives a
UsdviewApi object, so it cannot mutate USD or Qt state.
"""

from __future__ import print_function

import threading

from .jev_shadow import JevShadowAdapter
from .receipts import append_record
from .router import (
    action_signature,
    capture_context,
    text_fingerprint,
)


def schedule_shadow(usdviewApi, text, deterministicDecision, adapter=None):
    adapter = adapter or JevShadowAdapter()
    if not adapter.enabled():
        return False

    request = str(text)
    context = capture_context(usdviewApi)
    configDir = usdviewApi.configDir
    deterministic = action_signature(deterministicDecision.action)

    def _work():
        candidate = adapter.route(request, context)
        candidateAction = action_signature(candidate.action)
        append_record(configDir, {
            "event": "jev_shadow",
            "text_hash": text_fingerprint(request),
            "text_len": len(request),
            "deterministic": deterministic,
            "candidate": candidateAction,
            "agree": deterministic == candidateAction,
            "candidate_reason": candidate.reason,
            "metadata": candidate.metadata,
        })

    worker = threading.Thread(
        target=_work,
        name="usdview-labs-jev-shadow")
    worker.daemon = True
    worker.start()
    return True
