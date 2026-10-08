import unittest

from usdviewLabs.actions import (
    ACTION_CLEAR_SELECTION,
    ACTION_SELECT_PATH,
    ACTION_SET_VIEWER_MODE,
    UsdAction,
    execute_action,
)


class _Prim(object):
    def __init__(self, path, valid=True):
        self.path = path
        self.valid = valid

    def IsValid(self):
        return self.valid


class _Stage(object):
    def __init__(self):
        self.prims = {"/World": _Prim("/World")}

    def GetPrimAtPath(self, path):
        return self.prims.get(path, _Prim(path, False))


class _Api(object):
    def __init__(self):
        self.stage = _Stage()
        self.viewerMode = False
        self.selected = []
        self.updated = 0

    def ClearPrimSelection(self):
        self.selected = []

    def AddPrimToSelection(self, prim):
        self.selected.append(prim.path)

    def UpdateGUI(self):
        self.updated += 1


class ActionsTest(unittest.TestCase):
    def test_select_path(self):
        api = _Api()
        result = execute_action(api, UsdAction(
            ACTION_SELECT_PATH, {"path": "/World"}, source="test"))
        self.assertTrue(result.ok)
        self.assertEqual(api.selected, ["/World"])
        self.assertEqual(api.updated, 1)

    def test_missing_path_does_not_change_selection(self):
        api = _Api()
        api.selected = ["old"]
        result = execute_action(api, UsdAction(
            ACTION_SELECT_PATH, {"path": "/Missing"}))
        self.assertFalse(result.ok)
        self.assertEqual(api.selected, ["old"])

    def test_clear_selection(self):
        api = _Api()
        api.selected = ["/World"]
        result = execute_action(api, UsdAction(ACTION_CLEAR_SELECTION))
        self.assertTrue(result.ok)
        self.assertEqual(api.selected, [])

    def test_confirmation_gate(self):
        api = _Api()
        result = execute_action(api, UsdAction(
            ACTION_SET_VIEWER_MODE, {"enabled": True},
            requires_confirmation=True))
        self.assertFalse(result.ok)
        self.assertFalse(api.viewerMode)


if __name__ == "__main__":
    unittest.main()
