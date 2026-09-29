#!/usr/bin/env python3
#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Deterministic 144-case routing evaluation for usdview Labs."""

from __future__ import print_function

import argparse
import json
import os
import statistics
import time

from usdviewLabs.intents import route_text
from usdviewLabs.queries import route_query_text
from usdviewLabs.router import action_signature
from usdviewLabs.jev_shadow import JevShadowAdapter


_PATHS = [
    "/World/Car",
    "/World/Hero",
    "/World/Camera",
    "/World/Props/Table",
    "/World/Props/Chair",
    "/World/Lights/Key",
    "/World/Lights/Fill",
    "/World/Set/Building",
    "/World/Set/Road",
    "/World/Characters/Alice",
    "/World/Characters/Bob",
    "/World/FX/Smoke",
    "/World/FX/Fire",
    "/World/Geo/Ground",
    "/World/Geo/Tree",
    "/World/Looks/CarPaint",
    "/World/Rig/Root",
    "/World/Environment/Sky",
    "/World/Vehicles/Truck",
    "/World/Vehicles/Bike",
    "/World/Cameras/Main",
    "/World/Cameras/ShotCam",
    "/World/Asset/Body",
    "/World/Asset/Wheels",
]

_QUERY_PHRASES = [
    "what is selected",
    "what's selected",
    "what frame am i on",
    "current frame",
    "what renderer",
    "current renderer",
    "what file is this",
    "current stage",
    "what property is selected",
    "selected property",
    "what is the selected property value",
    "show property value",
    "where is this property authored",
    "show property stack",
    "list properties on /World/Car",
    "show properties on /World/Hero",
    "show composition for /World/Car",
    "show composition for /World/Set/Building",
    "show variants on /World/Car",
    "show variants on /World/Asset/Body",
]

_UNSUPPORTED = [
    "make it cinematic",
    "fix the scene",
    "make this better",
    "optimize everything",
    "delete the bad stuff",
    "change the material",
    "make the car blue",
    "move it left",
    "rotate this 90 degrees",
    "save over the source",
    "flatten everything",
    "publish this asset",
    "repair composition",
    "why does this look weird",
    "what should I do next",
    "make it faster",
    "clean this up",
    "rename the selected prim",
    "author a new variant",
    "remove all overrides",
    "mute the broken layer",
    "reload and fix it",
    "use the best renderer",
    "do whatever is safest",
]


def _action(kind, args=None):
    return {
        "kind": kind,
        "args": dict(args or {}),
    }


def build_cases():
    cases = []

    for path in _PATHS:
        cases.append({
            "family": "select_explicit",
            "text": "select {}".format(path),
            "expected_action": _action(
                "select_path",
                {"path": path}),
            "expected_query": None,
        })

    for path in _PATHS:
        cases.append({
            "family": "focus_path",
            "text": "focus {}".format(path),
            "expected_action": _action(
                "select_path",
                {"path": path}),
            "expected_query": None,
        })

    for path in _PATHS[:16]:
        cases.append({
            "family": "raw_path",
            "text": path,
            "expected_action": _action(
                "select_path",
                {"path": path}),
            "expected_query": None,
        })

    clear = [
        "clear selection",
        "deselect",
        "deselect all",
        "select none",
    ] * 3
    for text in clear:
        cases.append({
            "family": "clear_selection",
            "text": text,
            "expected_action": _action(
                "clear_selection"),
            "expected_query": None,
        })

    viewer_on = [
        "viewer mode on",
        "enable viewer mode",
        "fullscreen on",
        "viewer on",
    ] * 3
    for text in viewer_on:
        cases.append({
            "family": "viewer_on",
            "text": text,
            "expected_action": _action(
                "set_viewer_mode",
                {"enabled": True}),
            "expected_query": None,
        })

    viewer_off = [
        "viewer mode off",
        "disable viewer mode",
        "fullscreen off",
        "viewer off",
    ] * 3
    for text in viewer_off:
        cases.append({
            "family": "viewer_off",
            "text": text,
            "expected_action": _action(
                "set_viewer_mode",
                {"enabled": False}),
            "expected_query": None,
        })

    for text in _QUERY_PHRASES:
        query = route_query_text(
            text,
            source="eval")
        cases.append({
            "family": "read_only_query",
            "text": text,
            "expected_action": None,
            "expected_query": (
                query.kind if query is not None else None),
        })

    for text in _UNSUPPORTED:
        cases.append({
            "family": "unsupported",
            "text": text,
            "expected_action": None,
            "expected_query": None,
        })

    if len(cases) != 144:
        raise AssertionError(
            "expected 144 cases, got {}".format(len(cases)))
    return cases


def _correct(actual, expected):
    return actual == expected


def _p(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = int(round(
        (len(ordered) - 1) * fraction))
    return ordered[index]


def run_case(case, useJev=False, adapter=None):
    started = time.perf_counter()
    deterministic = route_text(
        case["text"],
        source="eval")
    query = route_query_text(
        case["text"],
        source="eval")
    deterministicMs = (
        time.perf_counter() - started) * 1000.0

    action = action_signature(
        deterministic.action)
    queryKind = query.kind if query is not None else None

    row = {
        **case,
        "deterministic_action": action,
        "deterministic_query": queryKind,
        "deterministic_action_correct": _correct(
            action,
            case["expected_action"]),
        "deterministic_query_correct": _correct(
            queryKind,
            case["expected_query"]),
        "deterministic_latency_ms": round(
            deterministicMs,
            4),
    }

    if useJev:
        adapter = adapter or JevShadowAdapter()
        decision = adapter.route(
            case["text"],
            {
                "stage": "eval.usda",
                "frame": 24.0,
                "selected_paths": ["/World/Car"],
                "viewer_mode": False,
                "renderer": "HdStormRendererPlugin",
            })
        candidate = action_signature(
            decision.action)
        row.update({
            "jev_action": candidate,
            "jev_correct": _correct(
                candidate,
                case["expected_action"]),
            "jev_agrees_deterministic": (
                candidate == action),
            "jev_reason": decision.reason,
            "jev_metadata": decision.metadata,
        })

    return row


def summarize(rows):
    summary = {
        "n": len(rows),
        "deterministic_action_accuracy": (
            sum(r["deterministic_action_correct"] for r in rows)
            / len(rows)),
        "deterministic_query_accuracy": (
            sum(r["deterministic_query_correct"] for r in rows)
            / len(rows)),
        "families": {},
    }

    for family in sorted(set(
            row["family"] for row in rows)):
        group = [
            row for row in rows
            if row["family"] == family]
        item = {
            "n": len(group),
            "deterministic_action_accuracy": (
                sum(r["deterministic_action_correct"] for r in group)
                / len(group)),
            "deterministic_query_accuracy": (
                sum(r["deterministic_query_correct"] for r in group)
                / len(group)),
        }

        if "jev_correct" in group[0]:
            item.update({
                "jev_accuracy": (
                    sum(r["jev_correct"] for r in group)
                    / len(group)),
                "jev_agreement": (
                    sum(r["jev_agrees_deterministic"] for r in group)
                    / len(group)),
            })

        summary["families"][family] = item

    if rows and "jev_correct" in rows[0]:
        latencies = []
        for row in rows:
            value = (
                row.get("jev_metadata") or {}
            ).get("route_latency_ms")
            if isinstance(value, (int, float)):
                latencies.append(float(value))

        summary.update({
            "jev_accuracy": (
                sum(r["jev_correct"] for r in rows)
                / len(rows)),
            "jev_agreement": (
                sum(r["jev_agrees_deterministic"] for r in rows)
                / len(rows)),
            "jev_latency_ms": {
                "n": len(latencies),
                "p50": statistics.median(latencies)
                if latencies else None,
                "p95": _p(latencies, 0.95),
                "max": max(latencies)
                if latencies else None,
            },
        })

    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--jev",
        action="store_true",
        help="enable live Jev shadow scoring")
    parser.add_argument(
        "--jsonl",
        default=None,
        help="optional per-case JSONL output path")
    args = parser.parse_args()

    if args.jev:
        os.environ[
            "USDVIEW_LABS_JEV_SHADOW"] = "1"

    adapter = (
        JevShadowAdapter()
        if args.jev else None)

    rows = [
        run_case(
            case,
            useJev=args.jev,
            adapter=adapter)
        for case in build_cases()
    ]

    if args.jsonl:
        with open(args.jsonl, "w") as stream:
            for row in rows:
                stream.write(
                    json.dumps(
                        row,
                        sort_keys=True) + "\n")

    print(json.dumps(
        summarize(rows),
        indent=2,
        sort_keys=True))

    deterministicOk = all(
        row["deterministic_action_correct"] and
        row["deterministic_query_correct"]
        for row in rows)

    return 0 if deterministicOk else 1


if __name__ == "__main__":
    raise SystemExit(main())
