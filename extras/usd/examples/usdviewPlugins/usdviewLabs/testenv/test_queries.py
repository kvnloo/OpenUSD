#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import unittest

from usdviewLabs.queries import (
    QUERY_CURRENT_LAYER,
    QUERY_FRAME,
    QUERY_PRIM_TYPE,
    QUERY_SELECTION,
    execute_query,
    route_query_text,
)


class _Prim(object):
    def __init__(self, typeName=None, valid=True):
        self._typeName = typeName
        self._valid = valid

    def IsValid(self):
        return self._valid

    def GetTypeName(self):
        return self._typeName


class _Stage(object):
    def GetPrimAtPath(self, path):
        if path == "/World/Car":
            return _Prim("Xform")
        return _Prim(valid=False)


class _Layer(object):
    identifier = "/tmp/shot.usda"


class _Api(object):
    selectedPaths = ["/World/Car"]
    frame = 24
    stageIdentifier = "/tmp/root.usda"
    layer = _Layer()
    spec = None
    stage = _Stage()

    def GetViewportCurrentRendererId(self):
        return "HdStormRendererPlugin"


class QueriesTest(unittest.TestCase):
    def test_selection_query(self):
        query = route_query_text("what is selected")
        self.assertEqual(query.kind, QUERY_SELECTION)
        result = execute_query(_Api(), query)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, ["/World/Car"])

    def test_frame_query(self):
        query = route_query_text("what frame am i on")
        self.assertEqual(query.kind, QUERY_FRAME)
        self.assertEqual(
            execute_query(_Api(), query).value,
            24.0)

    def test_prim_type_query(self):
        query = route_query_text(
            "what type is /World/Car")
        self.assertEqual(query.kind, QUERY_PRIM_TYPE)
        result = execute_query(_Api(), query)
        self.assertTrue(result.ok)
        self.assertEqual(result.value["type"], "Xform")

    def test_current_layer_query(self):
        query = route_query_text(
            "where is this authored")
        self.assertEqual(query.kind, QUERY_CURRENT_LAYER)
        result = execute_query(_Api(), query)
        self.assertEqual(
            result.value["layer"],
            "/tmp/shot.usda")
        self.assertEqual(
            result.value["source"],
            "current composition layer")

    def test_unknown_question_stays_unknown(self):
        self.assertIsNone(
            route_query_text("why does this look weird"))


if __name__ == "__main__":
    unittest.main()
