#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Typed read-only scene queries for usdview Labs.

UsdQuery is deliberately separate from UsdAction: query execution exposes no
mutation methods and returns plain data for display/receipts.
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

SUPPORTED_QUERIES = frozenset({
    QUERY_SELECTION,
    QUERY_FRAME,
    QUERY_RENDERER,
    QUERY_STAGE,
    QUERY_PRIM_TYPE,
    QUERY_CURRENT_LAYER,
})

_PATH_RE = re.compile(r"(/[A-Za-z0-9_./:{}-]+)")


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


def route_query_text(text, source="voice-query"):
    raw = str(text).strip()
    normalized = " ".join(raw.lower().split())

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
            "where is this authored",
            "what layer is this from",
            "current layer",
            "which layer"}:
        return UsdQuery(QUERY_CURRENT_LAYER, source=source)

    if normalized.startswith("what type is "):
        match = _PATH_RE.search(raw)
        if match:
            return UsdQuery(
                QUERY_PRIM_TYPE,
                {"path": match.group(1)},
                source=source)

    return None


def _identifier(value):
    if value is None:
        return None
    return getattr(value, "identifier", None) or str(value)


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

    if query.kind == QUERY_PRIM_TYPE:
        path = str(query.args.get("path", ""))
        try:
            prim = usdviewApi.stage.GetPrimAtPath(path)
        except Exception:
            prim = None

        if not prim or not prim.IsValid():
            return QueryResult(
                False,
                None,
                "Prim not found: {}".format(path))

        typeName = prim.GetTypeName() or "untyped"
        return QueryResult(
            True,
            {
                "path": path,
                "type": typeName,
            },
            "{} is {}".format(path, typeName))

    raise AssertionError("Unhandled supported query: {}".format(query.kind))
