#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Small deterministic intent grammar for usdview Labs."""

import re

from .actions import (
    ACTION_CLEAR_SELECTION,
    ACTION_SELECT_PATH,
    ACTION_SET_VIEWER_MODE,
    UsdAction,
)
from .router import RouteDecision


_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(/[A-Za-z0-9_./:{}-]+)")


def extract_prim_path(text):
    value = str(text).strip()
    if value.startswith("/") and " " not in value:
        return value
    match = _PATH_RE.search(value)
    return match.group(1) if match else None


def route_text(text, source="intent"):
    """Map only explicit, low-risk phrases to typed actions."""
    raw = str(text).strip()
    normalized = " ".join(raw.lower().split())

    if not normalized:
        return RouteDecision(None, "empty", router="deterministic")

    if normalized in {
            "clear selection", "deselect", "deselect all", "select none"}:
        return RouteDecision(
            UsdAction(ACTION_CLEAR_SELECTION, source=source),
            "clear-selection alias")

    if normalized in {
            "viewer mode on", "enable viewer mode",
            "fullscreen on", "viewer on"}:
        return RouteDecision(
            UsdAction(
                ACTION_SET_VIEWER_MODE,
                {"enabled": True},
                source=source),
            "viewer-on alias")

    if normalized in {
            "viewer mode off", "disable viewer mode",
            "fullscreen off", "viewer off"}:
        return RouteDecision(
            UsdAction(
                ACTION_SET_VIEWER_MODE,
                {"enabled": False},
                source=source),
            "viewer-off alias")

    path = extract_prim_path(raw)
    if path and (
            raw.startswith("/") or
            any(token in normalized
                for token in ("select ", "focus ", "go to ", "goto "))):
        return RouteDecision(
            UsdAction(
                ACTION_SELECT_PATH,
                {"path": path},
                source=source),
            "prim-path intent")

    return RouteDecision(
        None,
        "no deterministic match",
        router="deterministic")
