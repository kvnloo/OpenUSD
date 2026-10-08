#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Typed read-only scene queries for usdview Labs.

UsdQuery is deliberately separate from UsdAction: query execution exposes no
mutation methods and returns bounded plain data for display/receipts.
"""

from __future__ import print_function

import json
import re
from collections import namedtuple


QUERY_SELECTION = "selection"
QUERY_FRAME = "frame"
QUERY_RENDERER = "renderer"
QUERY_STAGE = "stage"
QUERY_PRIM_TYPE = "prim_type"
QUERY_CURRENT_LAYER = "current_layer"
QUERY_SELECTED_PROPERTY = "selected_property"
QUERY_PROPERTY_VALUE = "property_value"
QUERY_PROPERTY_STACK = "property_stack"
QUERY_PRIM_PROPERTIES = "prim_properties"
QUERY_COMPOSITION = "composition"
QUERY_VARIANTS = "variants"

SUPPORTED_QUERIES = frozenset({
    QUERY_SELECTION,
    QUERY_FRAME,
    QUERY_RENDERER,
    QUERY_STAGE,
    QUERY_PRIM_TYPE,
    QUERY_CURRENT_LAYER,
    QUERY_SELECTED_PROPERTY,
    QUERY_PROPERTY_VALUE,
    QUERY_PROPERTY_STACK,
    QUERY_PRIM_PROPERTIES,
    QUERY_COMPOSITION,
    QUERY_VARIANTS,
})

_PATH_RE = re.compile(r"(/[A-Za-z0-9_./:{}-]+)")
_MAX_ITEMS = 50
_MAX_VALUE_CHARS = 1200


class UsdQuery(object):
    __slots__ = ("kind", "args", "source")

    def __init__(self, kind, args=None, source="unknown"):
        if kind not in SUPPORTED_QUERIES:
            raise ValueError("Unsupported usdview query: {}".format(kind))
        self.kind = str(kind)
        self.args = dict(args or {})
        self.source = str(source)

    def to_dict(self):
        return {
            "kind": self.kind,
            "args": dict(self.args),
            "source": self.source,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True)


QueryResult = namedtuple("QueryResult", "ok value message")


def _path_from_text(text):
    match = _PATH_RE.search(str(text))
    return match.group(1) if match else None


def route_query_text(text, source="voice-query"):
    raw = str(text).strip()
    normalized = " ".join(raw.lower().split())
    path = _path_from_text(raw)

    if normalized in {
            "what is selected",
            "what's selected",
            "what do i have selected",
            "show selection",
            "current selection"}:
        return UsdQuery(QUERY_SELECTION, source=source)

    if normalized in {
            "what frame",
            "what frame am i on",
            "current frame",
            "show current frame"}:
        return UsdQuery(QUERY_FRAME, source=source)

    if normalized in {
            "what renderer",
            "which renderer",
            "current renderer"}:
        return UsdQuery(QUERY_RENDERER, source=source)

    if normalized in {
            "what stage",
            "which stage",
            "current stage",
            "what file is this"}:
        return UsdQuery(QUERY_STAGE, source=source)

    if normalized in {
            "what property is selected",
            "what's the selected property",
            "selected property",
            "show selected property"}:
        return UsdQuery(QUERY_SELECTED_PROPERTY, source=source)

    if normalized in {
            "what is the selected property value",
            "what's the selected property value",
            "what is its value",
            "show property value",
            "selected property value"}:
        return UsdQuery(QUERY_PROPERTY_VALUE, source=source)

    if normalized in {
            "where is this property authored",
            "where does this property come from",
            "show property stack",
            "property stack"}:
        return UsdQuery(QUERY_PROPERTY_STACK, source=source)

    if "properties" in normalized and (
            path or "selected" in normalized or
            normalized in {"list properties", "show properties"}):
        return UsdQuery(
            QUERY_PRIM_PROPERTIES,
            {"path": path} if path else {},
            source=source)

    if (
            "composition" in normalized or
            (path and (
                normalized.startswith("where does ") or
                normalized.startswith("where is ")))):
        return UsdQuery(
            QUERY_COMPOSITION,
            {"path": path} if path else {},
            source=source)

    if "variant" in normalized and (
            path or "selected" in normalized or
            normalized in {"show variants", "list variants"}):
        return UsdQuery(
            QUERY_VARIANTS,
            {"path": path} if path else {},
            source=source)

    if normalized in {
            "where is this authored",
            "what layer is this from",
            "current layer",
            "which layer"}:
        return UsdQuery(QUERY_CURRENT_LAYER, source=source)

    if normalized.startswith("what type is ") and path:
        return UsdQuery(
            QUERY_PRIM_TYPE,
            {"path": path},
            source=source)

    return None


def _identifier(value):
    if value is None:
        return None
    return getattr(value, "identifier", None) or str(value)


def _bounded(value, maxChars=_MAX_VALUE_CHARS):
    try:
        text = repr(value)
    except Exception:
        text = "<unrepresentable>"
    if len(text) > maxChars:
        return text[:maxChars] + "...<truncated>"
    return text


def _current_prim(usdviewApi):
    try:
        prim = usdviewApi.prim
        if prim and prim.IsValid():
            return prim
    except Exception:
        pass
    return None


def _prim_for_query(usdviewApi, query):
    path = str(query.args.get("path") or "")
    if path:
        try:
            prim = usdviewApi.stage.GetPrimAtPath(path)
        except Exception:
            prim = None
        if prim and prim.IsValid():
            return prim
        return None
    return _current_prim(usdviewApi)


def _prim_path(prim):
    try:
        return str(prim.GetPath())
    except Exception:
        return "<unknown>"


def _selected_property(usdviewApi):
    try:
        prop = usdviewApi.property
        if prop:
            return prop
    except Exception:
        pass
    return None


def _property_description(prop):
    if prop is None:
        return None

    try:
        path = str(prop.GetPath())
    except Exception:
        path = None

    try:
        name = str(prop.GetName())
    except Exception:
        name = None

    try:
        typeName = str(prop.GetTypeName())
    except Exception:
        typeName = None

    kind = (
        "relationship"
        if hasattr(prop, "GetTargets")
        else "attribute"
        if hasattr(prop, "Get")
        else "property")

    return {
        "path": path,
        "name": name,
        "type": typeName,
        "kind": kind,
    }


def _spec_rows(specs):
    rows = []
    for spec in list(specs)[:_MAX_ITEMS]:
        layer = getattr(spec, "layer", None)
        try:
            path = str(spec.path)
        except Exception:
            path = None
        try:
            specifier = str(spec.specifier)
        except Exception:
            specifier = None
        rows.append({
            "layer": _identifier(layer),
            "path": path,
            "specifier": specifier,
        })
    return rows


def execute_query(usdviewApi, query):
    if not isinstance(query, UsdQuery):
        raise TypeError("execute_query expects UsdQuery")

    if query.kind == QUERY_SELECTION:
        try:
            paths = [str(path) for path in usdviewApi.selectedPaths]
        except Exception:
            paths = []
        return QueryResult(
            True,
            paths,
            "Selected: {}".format(
                ", ".join(paths) if paths else "nothing"))

    if query.kind == QUERY_FRAME:
        try:
            frame = float(usdviewApi.frame)
        except Exception:
            frame = None
        return QueryResult(
            frame is not None,
            frame,
            "Current frame: {}".format(frame)
            if frame is not None else
            "Current frame unavailable")

    if query.kind == QUERY_RENDERER:
        try:
            renderer = usdviewApi.GetViewportCurrentRendererId()
        except Exception:
            renderer = None
        return QueryResult(
            renderer is not None,
            renderer,
            "Current renderer: {}".format(renderer)
            if renderer is not None else
            "Renderer unavailable")

    if query.kind == QUERY_STAGE:
        stage = getattr(usdviewApi, "stageIdentifier", None)
        return QueryResult(
            stage is not None,
            stage,
            "Current stage: {}".format(stage)
            if stage is not None else
            "Stage unavailable")

    if query.kind == QUERY_CURRENT_LAYER:
        spec = getattr(usdviewApi, "spec", None)
        layer = getattr(spec, "layer", None) if spec is not None else None
        source = "selected composition spec"

        if layer is None:
            layer = getattr(usdviewApi, "layer", None)
            source = "current composition layer"

        identifier = _identifier(layer)
        return QueryResult(
            identifier is not None,
            {
                "layer": identifier,
                "source": source,
            } if identifier is not None else None,
            "{}: {}".format(source.capitalize(), identifier)
            if identifier is not None else
            "No composition layer/spec is selected")

    if query.kind == QUERY_SELECTED_PROPERTY:
        prop = _selected_property(usdviewApi)
        value = _property_description(prop)
        return QueryResult(
            value is not None,
            value,
            json.dumps(value, indent=2, sort_keys=True)
            if value is not None else
            "No property is selected")

    if query.kind == QUERY_PROPERTY_VALUE:
        prop = _selected_property(usdviewApi)
        if prop is None:
            return QueryResult(False, None, "No property is selected")

        description = _property_description(prop) or {}
        if hasattr(prop, "GetTargets"):
            try:
                value = [str(path) for path in prop.GetTargets()][:_MAX_ITEMS]
            except Exception as exc:
                return QueryResult(
                    False, None,
                    "Could not read relationship targets: {}".format(exc))
        elif hasattr(prop, "Get"):
            try:
                value = prop.Get(getattr(usdviewApi, "frame", None))
            except Exception:
                try:
                    value = prop.Get()
                except Exception as exc:
                    return QueryResult(
                        False, None,
                        "Could not read property value: {}".format(exc))
        else:
            return QueryResult(
                False, None,
                "Selected property has no readable value")

        rendered = _bounded(value)
        result = {
            "property": description,
            "value": rendered,
        }
        return QueryResult(
            True,
            result,
            "{} = {}".format(
                description.get("path") or "property",
                rendered))

    if query.kind == QUERY_PROPERTY_STACK:
        prop = _selected_property(usdviewApi)
        if prop is None or not hasattr(prop, "GetPropertyStack"):
            return QueryResult(
                False, None,
                "No stack-capable property is selected")

        try:
            stack = prop.GetPropertyStack(
                getattr(usdviewApi, "frame", None))
        except Exception:
            try:
                stack = prop.GetPropertyStack()
            except Exception as exc:
                return QueryResult(
                    False, None,
                    "Could not inspect property stack: {}".format(exc))

        rows = _spec_rows(stack)
        result = {
            "property": _property_description(prop),
            "opinions": rows,
            "truncated": len(stack) > _MAX_ITEMS,
        }
        return QueryResult(
            True,
            result,
            json.dumps(result, indent=2, sort_keys=True))

    if query.kind in {
            QUERY_PRIM_TYPE,
            QUERY_PRIM_PROPERTIES,
            QUERY_COMPOSITION,
            QUERY_VARIANTS}:
        prim = _prim_for_query(usdviewApi, query)
        if prim is None:
            requested = query.args.get("path") or "current selection"
            return QueryResult(
                False, None,
                "Prim not found: {}".format(requested))

        path = _prim_path(prim)

        if query.kind == QUERY_PRIM_TYPE:
            typeName = prim.GetTypeName() or "untyped"
            return QueryResult(
                True,
                {
                    "path": path,
                    "type": typeName,
                },
                "{} is {}".format(path, typeName))

        if query.kind == QUERY_PRIM_PROPERTIES:
            try:
                properties = list(prim.GetProperties())
            except Exception as exc:
                return QueryResult(
                    False, None,
                    "Could not list properties: {}".format(exc))

            rows = []
            for prop in properties[:_MAX_ITEMS]:
                rows.append(_property_description(prop))
            result = {
                "path": path,
                "properties": rows,
                "truncated": len(properties) > _MAX_ITEMS,
            }
            return QueryResult(
                True,
                result,
                json.dumps(result, indent=2, sort_keys=True))

        if query.kind == QUERY_COMPOSITION:
            try:
                stack = list(prim.GetPrimStack())
            except Exception as exc:
                return QueryResult(
                    False, None,
                    "Could not inspect composition: {}".format(exc))
            result = {
                "path": path,
                "prim_stack": _spec_rows(stack),
                "truncated": len(stack) > _MAX_ITEMS,
            }
            return QueryResult(
                True,
                result,
                json.dumps(result, indent=2, sort_keys=True))

        if query.kind == QUERY_VARIANTS:
            try:
                variantSets = prim.GetVariantSets()
                names = list(variantSets.GetNames())
                rows = []
                for name in names[:_MAX_ITEMS]:
                    variantSet = prim.GetVariantSet(name)
                    rows.append({
                        "name": str(name),
                        "selection": str(
                            variantSet.GetVariantSelection() or ""),
                    })
            except Exception as exc:
                return QueryResult(
                    False, None,
                    "Could not inspect variants: {}".format(exc))

            result = {
                "path": path,
                "variants": rows,
                "truncated": len(names) > _MAX_ITEMS,
            }
            return QueryResult(
                True,
                result,
                json.dumps(result, indent=2, sort_keys=True))

    raise AssertionError("Unhandled supported query: {}".format(query.kind))
