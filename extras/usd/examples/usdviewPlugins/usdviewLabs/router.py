#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Side-effect-free routing primitives for usdview Labs."""

import hashlib

from .actions import UsdAction


class RouteDecision(object):
    __slots__ = ("action", "reason", "router", "metadata")

    def __init__(self, action, reason="", router="deterministic",
                 metadata=None):
        if action is not None and not isinstance(action, UsdAction):
            raise TypeError("RouteDecision.action must be UsdAction or None")
        self.action = action
        self.reason = str(reason)
        self.router = str(router)
        self.metadata = dict(metadata or {})


def action_signature(action):
    """Return only the executable semantics of an action.

    Source, confidence, and confirmation metadata are intentionally excluded so
    shadow agreement means "same effect", not "identical provenance".
    """
    if action is None:
        return None
    return {
        "kind": action.kind,
        "args": dict(action.args),
    }


def same_action(left, right):
    return action_signature(left) == action_signature(right)


def text_fingerprint(text):
    """Stable short hash for receipts without persisting raw user text."""
    value = str(text).encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:16]


def capture_context(usdviewApi):
    """Capture bounded read-only context before any async/model work."""
    try:
        selected = [str(path) for path in usdviewApi.selectedPaths]
    except Exception:
        selected = []

    try:
        frame = float(usdviewApi.frame)
    except Exception:
        frame = None

    try:
        renderer = usdviewApi.GetViewportCurrentRendererId()
    except Exception:
        renderer = None

    return {
        "stage": getattr(usdviewApi, "stageIdentifier", None),
        "frame": frame,
        "selected_paths": selected,
        "viewer_mode": bool(getattr(usdviewApi, "viewerMode", False)),
        "renderer": renderer,
    }
