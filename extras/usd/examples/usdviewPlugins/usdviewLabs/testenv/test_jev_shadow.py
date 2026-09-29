#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import os
import unittest

from usdviewLabs.actions import ACTION_SET_VIEWER_MODE
from usdviewLabs.jev_shadow import (
    JevShadowAdapter,
    decision_from_choice,
)


class JevShadowTest(unittest.TestCase):
    def test_select_choice_requires_explicit_path(self):
        decision = decision_from_choice("select_path", "focus the car")
        self.assertIsNone(decision.action)

    def test_viewer_choice_maps_to_typed_action(self):
        decision = decision_from_choice("viewer_on", "go big")
        self.assertEqual(decision.action.kind, ACTION_SET_VIEWER_MODE)
        self.assertTrue(decision.action.args["enabled"])

    def test_shadow_is_disabled_by_default(self):
        previous = os.environ.pop("USDVIEW_LABS_JEV_SHADOW", None)
        try:
            self.assertFalse(JevShadowAdapter.enabled())
        finally:
            if previous is not None:
                os.environ["USDVIEW_LABS_JEV_SHADOW"] = previous


if __name__ == "__main__":
    unittest.main()
