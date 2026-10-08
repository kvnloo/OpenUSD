#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import unittest

from usdviewLabs.actions import (
    ACTION_CLEAR_SELECTION,
    ACTION_SELECT_PATH,
    ACTION_SET_VIEWER_MODE,
)
from usdviewLabs.intents import extract_prim_path, route_text


class IntentsTest(unittest.TestCase):
    def test_raw_prim_path(self):
        decision = route_text("/World/Car")
        self.assertEqual(decision.action.kind, ACTION_SELECT_PATH)
        self.assertEqual(decision.action.args["path"], "/World/Car")

    def test_focus_prim_path(self):
        decision = route_text("focus /World/Car")
        self.assertEqual(decision.action.kind, ACTION_SELECT_PATH)
        self.assertEqual(decision.action.args["path"], "/World/Car")

    def test_clear_selection_alias(self):
        decision = route_text("deselect all")
        self.assertEqual(decision.action.kind, ACTION_CLEAR_SELECTION)

    def test_viewer_mode_aliases(self):
        enabled = route_text("viewer mode on")
        disabled = route_text("fullscreen off")
        self.assertEqual(enabled.action.kind, ACTION_SET_VIEWER_MODE)
        self.assertTrue(enabled.action.args["enabled"])
        self.assertFalse(disabled.action.args["enabled"])

    def test_unknown_text_does_not_guess(self):
        self.assertIsNone(route_text("make it cinematic").action)

    def test_extract_path_from_phrase(self):
        self.assertEqual(
            extract_prim_path("please focus /World/Hero.material"),
            "/World/Hero.material")


if __name__ == "__main__":
    unittest.main()
