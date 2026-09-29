#!/usr/bin/env python3
#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Receipt-backed UX benchmark and safety audit for usdview Labs."""

import argparse
import collections
import json
import os
import statistics
import sys
import time
import uuid


MODES = ("stock", "palette", "voice")
EVENT_START = "ux_bench_start"
EVENT_FINISH = "ux_bench_finish"


def _labs_dir(configDir):
    return os.path.join(
        os.path.expanduser(configDir),
        "usdview-labs")


def _receipt_path(configDir):
    return os.path.join(
        _labs_dir(configDir),
        "receipts.jsonl")


def _append(configDir, record):
    os.makedirs(_labs_dir(configDir), exist_ok=True)
    payload = dict(record)
    payload.setdefault("schema", 2)
    payload.setdefault("ts_unix", time.time())
    raw = (
        json.dumps(payload, sort_keys=True) + "\n"
    ).encode("utf-8")
    fd = os.open(
        _receipt_path(configDir),
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)


def read_receipts(configDir):
    records = []
    path = _receipt_path(configDir)
    if not os.path.isfile(path):
        return records
    with open(path, "r") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except Exception:
                continue
            if isinstance(value, dict):
                records.append(value)
    return records


def load_workflows(path):
    with open(path, "r") as stream:
        value = json.load(stream)
    if not isinstance(value, list):
        raise ValueError("workflow file must contain a list")
    return value


def pair_sessions(records):
    starts = {}
    sessions = []

    for record in records:
        event = record.get("event")
        sessionId = record.get("session_id")
        if not sessionId:
            continue

        if event == EVENT_START:
            starts[str(sessionId)] = record
            continue

        if event != EVENT_FINISH:
            continue

        start = starts.get(str(sessionId))
        if start is None:
            continue

        duration = (
            float(record.get("ts_unix", 0.0)) -
            float(start.get("ts_unix", 0.0)))

        sessions.append({
            "session_id": str(sessionId),
            "workflow": start.get("workflow"),
            "mode": start.get("mode"),
            "success": bool(record.get("success")),
            "steps": int(record.get("steps", 0)),
            "time_to_result_s": max(0.0, duration),
            "start": start,
            "finish": record,
        })

    return sessions


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = int(round(
        (len(ordered) - 1) * fraction))
    return ordered[index]


def summarize_sessions(sessions):
    grouped = collections.defaultdict(list)
    for session in sessions:
        grouped[(
            session["workflow"],
            session["mode"])].append(session)

    summary = {}
    for (workflow, mode), group in sorted(grouped.items()):
        durations = [
            item["time_to_result_s"]
            for item in group]
        steps = [
            item["steps"]
            for item in group]
        summary[
            "{}:{}".format(workflow, mode)] = {
                "n": len(group),
                "success_rate": (
                    sum(item["success"] for item in group)
                    / len(group)),
                "time_to_result_s": {
                    "p50": statistics.median(durations),
                    "p95": _percentile(durations, 0.95),
                    "max": max(durations),
                },
                "steps": {
                    "p50": statistics.median(steps),
                    "p95": _percentile(steps, 0.95),
                    "max": max(steps),
                },
            }
    return summary


def audit_receipts(records):
    violations = []
    evidence = collections.Counter()

    for record in records:
        event = record.get("event")

        if event == "action":
            action = record.get("action") or {}
            source = str(action.get("source", ""))
            if source == "jev-shadow":
                violations.append({
                    "type": "jev_shadow_executed",
                    "record": record,
                })
            if source == "voice-query":
                violations.append({
                    "type": "read_only_query_executed_as_action",
                    "record": record,
                })

        if event == "voice_bridge_start":
            if record.get("host") != "127.0.0.1":
                violations.append({
                    "type": "non_loopback_voice_bridge",
                    "record": record,
                })

        if event == "voice_preview_stale_accept_blocked":
            evidence["stale_accept_blocked"] += 1

        if event == "voice_final_dropped":
            evidence["stale_or_cancelled_final_dropped"] += 1

        if event == "ptt_signal_drop":
            evidence["ptt_signal_drop"] += 1

        if event == "jev_shadow":
            evidence["jev_shadow_receipt"] += 1

        if event == "palette_query":
            evidence["palette_query"] += 1

    return {
        "ok": not violations,
        "violations": violations,
        "evidence": dict(evidence),
    }


def command_start(args):
    workflows = load_workflows(args.workflows)
    known = {
        item["id"] for item in workflows}
    if args.workflow not in known:
        raise SystemExit(
            "unknown workflow: {}".format(args.workflow))

    sessionId = str(uuid.uuid4())
    _append(args.config_dir, {
        "event": EVENT_START,
        "session_id": sessionId,
        "workflow": args.workflow,
        "mode": args.mode,
    })
    print(sessionId)
    return 0


def command_finish(args):
    _append(args.config_dir, {
        "event": EVENT_FINISH,
        "session_id": args.session_id,
        "success": bool(args.success),
        "steps": int(args.steps),
        "note": str(args.note or "")[:500],
    })
    return 0


def command_report(args):
    records = read_receipts(
        args.config_dir)
    sessions = pair_sessions(records)
    payload = {
        "sessions": len(sessions),
        "summary": summarize_sessions(sessions),
        "safety": audit_receipts(records),
    }
    print(json.dumps(
        payload,
        indent=2,
        sort_keys=True))
    return 0 if payload["safety"]["ok"] else 2


def build_parser():
    here = os.path.dirname(
        os.path.abspath(__file__))
    defaultWorkflows = os.path.join(
        here,
        "ux_workflows.json")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        default="~/.usdview")
    parser.add_argument(
        "--workflows",
        default=defaultWorkflows)

    sub = parser.add_subparsers(
        dest="command",
        required=True)

    start = sub.add_parser("start")
    start.add_argument(
        "--workflow",
        required=True)
    start.add_argument(
        "--mode",
        required=True,
        choices=MODES)
    start.set_defaults(func=command_start)

    finish = sub.add_parser("finish")
    finish.add_argument(
        "--session-id",
        required=True)
    finish.add_argument(
        "--success",
        action="store_true")
    finish.add_argument(
        "--steps",
        type=int,
        default=0)
    finish.add_argument(
        "--note",
        default="")
    finish.set_defaults(func=command_finish)

    report = sub.add_parser("report")
    report.set_defaults(func=command_report)

    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
