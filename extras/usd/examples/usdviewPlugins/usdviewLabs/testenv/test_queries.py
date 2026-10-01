#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import unittest

from usdviewLabs.queries import (
    QUERY_COMPOSITION,
    QUERY_CURRENT_LAYER,
    QUERY_FRAME,
    QUERY_PRIM_PROPERTIES,
    QUERY_PRIM_TYPE,
    QUERY_PROPERTY_STACK,
    QUERY_PROPERTY_VALUE,
    QUERY_SELECTED_PROPERTY,
    QUERY_SELECTION,
    QUERY_VARIANTS,
    execute_query,
    route_query_text,
)


class _Layer(object):
    def __init__(self, identifier):
        self.identifier = identifier


class _Spec(object):
    def __init__(self, layer, path, specifier="def"):
        self.layer = layer
        self.path = path
        self.specifier = specifier


class _Attribute(object):
    def __init__(self, path="/World/Car.speed", value=42.5):
        self._path = path
        self._value = value

    def GetPath(self):
        return self._path

    def GetName(self):
        return self._path.split(".")[-1]

    def GetTypeName(self):
        return "double"

    def Get(self, *_args):
        return self._value

    def GetPropertyStack(self, *_args):
        return [
            _Spec(_Layer("/tmp/anim.usda"), self._path),
            _Spec(_Layer("/tmp/root.usda"), self._path, "over"),
        ]


class _VariantSet(object):
    def __init__(self, selection):
        self._selection = selection

    def GetVariantSelection(self):
        return self._selection


class _VariantSets(object):
    def GetNames(self):
        return ["lod", "look"]

    def GetVariantSet(self, name):
        return _VariantSet({
            "lod": "high",
            "look": "red",
        }[name])


class _Prim(object):
    def __init__(self, path="/World/Car", typeName="Xform", valid=True):
        self._path = path
        self._typeName = typeName
        self._valid = valid
        self._speed = _Attribute()

    def IsValid(self):
        return self._valid

    def GetTypeName(self):
        return self._typeName

    def GetPath(self):
        return self._path

    def GetProperties(self):
        return [self._speed]

    def GetPrimStack(self):
        return [
            _Spec(_Layer("/tmp/model.usda"), self._path),
            _Spec(_Layer("/tmp/root.usda"), self._path, "over"),
        ]

    def GetVariantSets(self):
        return _VariantSets()

    def GetVariantSet(self, name):
        return self.GetVariantSets().GetVariantSet(name)


class _Stage(object):
    def __init__(self):
        self._prim = _Prim()

    def GetPrimAtPath(self, path):
        if path == "/World/Car":
            return self._prim
        return _Prim(path=path, valid=False)


class _Api(object):
    def __init__(self):
        self.selectedPaths = ["/World/Car"]
        self.frame = 24
        self.stageIdentifier = "/tmp/root.usda"
        self.layer = _Layer("/tmp/shot.usda")
        self.spec = None
        self.stage = _Stage()
        self.prim = self.stage.GetPrimAtPath("/World/Car")
        self.property = _Attribute()

    def GetViewportCurrentRendererId(self):
        return "HdStormRendererPlugin"


class QueriesTest(unittest.TestCase):
    def setUp(self):
        self.api = _Api()

    def test_selection_query(self):
        query = route_query_text("what is selected")
        self.assertEqual(query.kind, QUERY_SELECTION)
        result = execute_query(self.api, query)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, ["/World/Car"])

    def test_frame_query(self):
        query = route_query_text("what frame am i on")
        self.assertEqual(query.kind, QUERY_FRAME)
        self.assertEqual(
            execute_query(self.api, query).value,
            24.0)

    def test_prim_type_query(self):
        query = route_query_text(
            "what type is /World/Car")
        self.assertEqual(query.kind, QUERY_PRIM_TYPE)
        result = execute_query(self.api, query)
        self.assertTrue(result.ok)
        self.assertEqual(result.value["type"], "Xform")

    def test_current_layer_query(self):
        query = route_query_text(
            "where is this authored")
        self.assertEqual(query.kind, QUERY_CURRENT_LAYER)
        result = execute_query(self.api, query)
        self.assertEqual(
            result.value["layer"],
            "/tmp/shot.usda")
        self.assertEqual(
            result.value["source"],
            "current composition layer")

    def test_selected_property_description(self):
        query = route_query_text(
            "what property is selected")
        self.assertEqual(query.kind, QUERY_SELECTED_PROPERTY)
        result = execute_query(self.api, query)
        self.assertTrue(result.ok)
        self.assertEqual(
            result.value["path"],
            "/World/Car.speed")

    def test_selected_property_value(self):
        query = route_query_text(
            "what is the selected property value")
        self.assertEqual(query.kind, QUERY_PROPERTY_VALUE)
        result = execute_query(self.api, query)
        self.assertTrue(result.ok)
        self.assertIn("42.5", result.value["value"])

    def test_property_stack(self):
        query = route_query_text(
            "where is this property authored")
        self.assertEqual(query.kind, QUERY_PROPERTY_STACK)
        result = execute_query(self.api, query)
        self.assertEqual(
            result.value["opinions"][0]["layer"],
            "/tmp/anim.usda")

    def test_prim_properties(self):
        query = route_query_text(
            "list properties on /World/Car")
        self.assertEqual(query.kind, QUERY_PRIM_PROPERTIES)
        result = execute_query(self.api, query)
        self.assertEqual(
            result.value["properties"][0]["name"],
            "speed")

    def test_composition_stack(self):
        query = route_query_text(
            "show composition for /World/Car")
        self.assertEqual(query.kind, QUERY_COMPOSITION)
        result = execute_query(self.api, query)
        self.assertEqual(
            result.value["prim_stack"][0]["layer"],
            "/tmp/model.usda")

    def test_variants(self):
        query = route_query_text(
            "show variants on /World/Car")
        self.assertEqual(query.kind, QUERY_VARIANTS)
        result = execute_query(self.api, query)
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.value["variants"], [
            {"name": "lod", "selection": "high"},
            {"name": "look", "selection": "red"},
        ])

    def test_unknown_question_stays_unknown(self):
        self.assertIsNone(
            route_query_text("why does this look weird"))


if __name__ == "__main__":
    unittest.main()
