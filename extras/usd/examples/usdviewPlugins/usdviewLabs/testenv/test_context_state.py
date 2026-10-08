#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import unittest

from usdviewLabs.context_state import (
    capture_hud_state,
    format_hud_state,
)


class _PathObj(object):
    def __init__(self, path):
        self._path = path

    def GetPath(self):
        return self._path


class _Layer(object):
    identifier = "/tmp/layer.usda"


class _Spec(object):
    layer = _Layer()


class _TimeCode(object):
    def GetValue(self):
        return 12.5


class _Api(object):
    selectedPaths = ["/World/Car", "/World/Light"]
    prim = _PathObj("/World/Car")
    property = _PathObj("/World/Car.speed")
    layer = _Layer()
    spec = _Spec()
    viewportSize = (1280, 720)
    validationErrors = [1, 2]
    frame = _TimeCode()
    stageIdentifier = "/tmp/root.usda"
    viewerMode = False

    def GetViewportCurrentRendererId(self):
        return "HdStormRendererPlugin"


class ContextStateTest(unittest.TestCase):
    def test_capture_is_bounded_and_read_only(self):
        state = capture_hud_state(_Api())
        self.assertEqual(state["selected_count"], 2)
        self.assertEqual(state["focus_prim"], "/World/Car")
        self.assertEqual(
            state["focus_property"],
            "/World/Car.speed")
        self.assertEqual(
            state["composition_spec_layer"],
            "/tmp/layer.usda")
        self.assertEqual(
            state["validation_error_count"],
            2)
        self.assertEqual(
            state["frame"],
            12.5)

    def test_format_contains_core_context(self):
        text = format_hud_state(
            capture_hud_state(_Api()))
        self.assertIn("HdStormRendererPlugin", text)
        self.assertIn("/World/Car.speed", text)
        self.assertIn("Validation errors", text)


if __name__ == "__main__":
    unittest.main()
