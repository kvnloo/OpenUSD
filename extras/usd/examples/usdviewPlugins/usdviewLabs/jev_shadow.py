#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Optional Jev shadow router.

This mirrors z0intelligence's canonical Jev transport shape: jevkit.client,
jevkit.keystore, a pinned model revision, and capture of the served revision.
It is disabled by default and never executes the action it proposes.
"""

from __future__ import print_function

import json
import os
import time

from .actions import (
    ACTION_CLEAR_SELECTION,
    ACTION_SELECT_PATH,
    ACTION_SET_VIEWER_MODE,
    UsdAction,
)
from .intents import extract_prim_path
from .router import RouteDecision


EXPECTED_JEV_MODEL = "jev-1.13.0"

_ROUTE_CHOICES = {
    "select_path": "Select the referenced USD prim path",
    "clear_selection": "Clear current prim selection",
    "viewer_on": "Enable viewer mode",
    "viewer_off": "Disable viewer mode",
    "none": "No allowed action matches",
}


def decision_from_choice(choice, text, probability=None, metadata=None):
    confidence = (
        float(probability) if probability is not None else 1.0)
    meta = dict(metadata or {})

    if choice == "select_path":
        path = extract_prim_path(text)
        if not path:
            return RouteDecision(
                None,
                "Jev selected path action without a path",
                "jev-shadow",
                meta)
        action = UsdAction(
            ACTION_SELECT_PATH,
            {"path": path},
            source="jev-shadow",
            confidence=confidence)
    elif choice == "clear_selection":
        action = UsdAction(
            ACTION_CLEAR_SELECTION,
            source="jev-shadow",
            confidence=confidence)
    elif choice == "viewer_on":
        action = UsdAction(
            ACTION_SET_VIEWER_MODE,
            {"enabled": True},
            source="jev-shadow",
            confidence=confidence)
    elif choice == "viewer_off":
        action = UsdAction(
            ACTION_SET_VIEWER_MODE,
            {"enabled": False},
            source="jev-shadow",
            confidence=confidence)
    else:
        action = None

    return RouteDecision(
        action,
        "Jev choice: {}".format(choice),
        "jev-shadow",
        meta)


class _Capture(object):
    """Use jevkit's own transport while recording the served model."""

    def __init__(self):
        self.model = None

    def __call__(self, body, headers, timeout, *args, **kwargs):
        from jevkit import client as jevClient

        raw = jevClient._http_transport(body, headers, timeout)
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict) and payload.get("model"):
                self.model = str(payload["model"])
        except Exception:
            pass
        return raw


class JevShadowAdapter(object):
    def __init__(self, timeout=1.0, model=EXPECTED_JEV_MODEL):
        self.timeout = float(timeout)
        self.model = str(model)

    @staticmethod
    def enabled():
        return os.environ.get(
            "USDVIEW_LABS_JEV_SHADOW", "").strip().lower() in {
                "1", "true", "yes", "on"}

    def route(self, text, context):
        """Return a proposal only. The caller must never execute it."""
        if not self.enabled():
            return RouteDecision(
                None,
                "disabled",
                "jev-shadow",
                {"enabled": False})

        started = time.perf_counter()

        try:
            from jevkit import client as jevClient
            from jevkit import keystore

            key = keystore.resolve()
            if not key:
                return RouteDecision(
                    None,
                    "credential unavailable",
                    "jev-shadow",
                    {"enabled": True, "available": False})

            capture = _Capture()
            state = json.dumps({
                "request": str(text),
                "context": dict(context or {}),
                "extracted_path": extract_prim_path(text),
            }, sort_keys=True)

            reply = jevClient.ask(
                state,
                {"route": jevClient.choice(
                    "Which allowed usdview action best matches the request?",
                    _ROUTE_CHOICES)},
                timeout=self.timeout,
                retries=0,
                model=self.model,
                api_key=key,
                transport=capture)

            answer = reply["answers"]["route"]
            choice = answer["choice"]
            probabilities = answer.get("probabilities") or {}
            served = capture.model or self.model

            try:
                credentialSource = "jevkit:{}".format(keystore.source())
            except Exception:
                credentialSource = "jevkit"

            metadata = {
                "enabled": True,
                "available": True,
                "model": served,
                "revision": served,
                "requested_model": self.model,
                "model_matches_requested": served == self.model,
                "credential_source": credentialSource,
                "provider_latency_ms": reply.get("latency_ms"),
                "usage": reply.get("usage") or {},
                "route_latency_ms": round(
                    (time.perf_counter() - started) * 1000.0, 3),
                "probabilities": probabilities,
            }

            return decision_from_choice(
                choice,
                text,
                probabilities.get(choice),
                metadata)

        except Exception as exc:
            return RouteDecision(
                None,
                "Jev unavailable: {}".format(type(exc).__name__),
                "jev-shadow",
                {
                    "enabled": True,
                    "available": False,
                    "route_latency_ms": round(
                        (time.perf_counter() - started) * 1000.0, 3),
                })
