#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Small bounded read-only context snapshot for usdview Labs."""


def _safe(callable_, default=None):
    try:
        return callable_()
    except Exception:
        return default


def _path(value):
    if value is None:
        return None
    try:
        return str(value.GetPath())
    except Exception:
        return str(value)


def _identifier(value):
    if value is None:
        return None
    return getattr(value, "identifier", None) or str(value)


def capture_hud_state(usdviewApi):
    selected = _safe(
        lambda: [str(path) for path in usdviewApi.selectedPaths],
        []) or []

    prim = _safe(lambda: usdviewApi.prim)
    prop = _safe(lambda: usdviewApi.property)
    layer = _safe(lambda: usdviewApi.layer)
    spec = _safe(lambda: usdviewApi.spec)

    specLayer = getattr(spec, "layer", None) if spec is not None else None

    viewport = _safe(lambda: tuple(usdviewApi.viewportSize), (0, 0))
    renderer = _safe(lambda: usdviewApi.GetViewportCurrentRendererId())
    validations = _safe(lambda: len(usdviewApi.validationErrors), 0)

    try:
        frame = usdviewApi.frame
        if hasattr(frame, "GetValue"):
            frame = frame.GetValue()
        frame = float(frame)
    except Exception:
        frame = None

    return {
        "stage": _safe(lambda: usdviewApi.stageIdentifier),
        "frame": frame,
        "renderer": renderer,
        "viewer_mode": bool(_safe(lambda: usdviewApi.viewerMode, False)),
        "viewport": viewport,
        "selected_count": len(selected),
        "selected_paths": selected[:8],
        "selection_truncated": len(selected) > 8,
        "focus_prim": _path(prim),
        "focus_property": _path(prop),
        "composition_layer": _identifier(layer),
        "composition_spec_layer": _identifier(specLayer),
        "validation_error_count": int(validations or 0),
    }


def format_hud_state(state):
    selected = list(state.get("selected_paths") or [])
    if state.get("selection_truncated"):
        selected.append("...")

    rows = [
        ("Stage", state.get("stage")),
        ("Frame", state.get("frame")),
        ("Renderer", state.get("renderer")),
        ("Viewer mode", state.get("viewer_mode")),
        ("Viewport", state.get("viewport")),
        ("Selected", ", ".join(selected) if selected else "nothing"),
        ("Focus prim", state.get("focus_prim")),
        ("Focus property", state.get("focus_property")),
        ("Composition layer", state.get("composition_layer")),
        ("Spec layer", state.get("composition_spec_layer")),
        ("Validation errors", state.get("validation_error_count")),
    ]

    return "\n".join(
        "{:<18} {}".format(label + ":", value)
        for label, value in rows)
