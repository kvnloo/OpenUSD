#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Typed, deterministic action contracts for usdview Labs.

The module intentionally has no Qt, model, or network dependencies. Inputs from
command palettes, voice systems, or model routers must become a UsdAction
before they can affect usdview.
"""

from __future__ import print_function

import json
from collections import namedtuple


ACTION_CLEAR_SELECTION = "clear_selection"
ACTION_SELECT_PATH = "select_path"
ACTION_SET_FRAME = "set_frame"
ACTION_SET_VIEWER_MODE = "set_viewer_mode"
ACTION_SET_RENDERER = "set_renderer"
ACTION_STATUS = "status"

SUPPORTED_ACTIONS = frozenset({
    ACTION_CLEAR_SELECTION,
    ACTION_SELECT_PATH,
    ACTION_SET_FRAME,
    ACTION_SET_VIEWER_MODE,
    ACTION_SET_RENDERER,
    ACTION_STATUS,
})


class UsdAction(object):
    """A small serializable command envelope."""

    __slots__ = ("kind", "args", "source", "confidence",
                 "requires_confirmation")

    def __init__(self, kind, args=None, source="unknown", confidence=1.0,
                 requires_confirmation=False):
        if kind not in SUPPORTED_ACTIONS:
            raise ValueError("Unsupported usdview action: {}".format(kind))
        self.kind = kind
        self.args = dict(args or {})
        self.source = str(source)
        self.confidence = float(confidence)
        self.requires_confirmation = bool(requires_confirmation)

    def to_dict(self):
        return {
            "kind": self.kind,
            "args": self.args,
            "source": self.source,
            "confidence": self.confidence,
            "requires_confirmation": self.requires_confirmation,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True)

    def __repr__(self):
        return "UsdAction({})".format(self.to_json())


ActionResult = namedtuple("ActionResult", "ok message")


def _require_arg(action, name):
    if name not in action.args:
        raise ValueError("Action '{}' requires argument '{}'".format(
            action.kind, name))
    return action.args[name]


def execute_action(usdviewApi, action):
    """Execute one whitelisted action through UsdviewApi only.

    There is deliberately no arbitrary Python execution path here. Future Jev
    or voice integrations should produce UsdAction values and use this
    function instead of emitting source code.
    """

    if not isinstance(action, UsdAction):
        raise TypeError("execute_action expects UsdAction")

    if action.requires_confirmation:
        return ActionResult(False, "Action requires confirmation")

    if action.kind == ACTION_CLEAR_SELECTION:
        usdviewApi.ClearPrimSelection()
        usdviewApi.UpdateGUI()
        return ActionResult(True, "Selection cleared")

    if action.kind == ACTION_SELECT_PATH:
        path = str(_require_arg(action, "path"))
        prim = usdviewApi.stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            return ActionResult(False, "Prim not found: {}".format(path))
        usdviewApi.ClearPrimSelection()
        usdviewApi.AddPrimToSelection(prim)
        usdviewApi.UpdateGUI()
        return ActionResult(True, "Selected {}".format(path))

    if action.kind == ACTION_SET_FRAME:
        frame = float(_require_arg(action, "frame"))
        usdviewApi.dataModel.currentFrame = frame
        usdviewApi.UpdateViewport()
        return ActionResult(True, "Frame {}".format(frame))

    if action.kind == ACTION_SET_VIEWER_MODE:
        value = bool(_require_arg(action, "enabled"))
        usdviewApi.viewerMode = value
        return ActionResult(True, "Viewer mode {}".format(
            "enabled" if value else "disabled"))

    if action.kind == ACTION_SET_RENDERER:
        renderer = str(_require_arg(action, "renderer"))
        if renderer not in usdviewApi.GetViewportRendererNames():
            return ActionResult(False, "Renderer not available: {}".format(
                renderer))
        usdviewApi.SetViewportRenderer(renderer)
        return ActionResult(True, "Renderer {}".format(renderer))

    if action.kind == ACTION_STATUS:
        message = str(_require_arg(action, "message"))
        usdviewApi.PrintStatus(message)
        return ActionResult(True, message)

    raise AssertionError("Unhandled supported action: {}".format(action.kind))
