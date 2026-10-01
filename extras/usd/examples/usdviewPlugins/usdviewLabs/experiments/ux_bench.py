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
from fractions import Fraction
import json
import math
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


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite JSON number")
    return number


def _reject_json_constant(value):
    raise ValueError("nonstandard JSON constant: " + value)


def read_receipts(configDir, invalidRecords=None):
    records = []
    path = _receipt_path(configDir)
    if not os.path.isfile(path):
        return records
    with open(path, "rb") as stream:
        for lineNumber, line in enumerate(stream, 1):
            try:
                value = json.loads(
                    line, object_pairs_hook=_unique_json_object,
                    parse_float=_finite_json_float,
                    parse_constant=_reject_json_constant)
            except (ValueError, UnicodeError):
                if invalidRecords is not None:
                    invalidRecords.append({
                        "line": lineNumber,
                        "reason": "invalid_json",
                    })
                continue
            if isinstance(value, dict):
                records.append(value)
            elif invalidRecords is not None:
                invalidRecords.append({
                    "line": lineNumber,
                    "reason": "not_an_object",
                })
    return records


def load_workflows(path):
    with open(path, "r") as stream:
        value = json.load(stream)
    if not isinstance(value, list):
        raise ValueError("workflow file must contain a list")
    return value


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def analyze_sessions(records):
    """Pair unique valid endpoints and retain reasons for excluded evidence."""
    grouped = collections.defaultdict(list)
    sessions = []
    evidence = {
        "ok": True,
        "invalid_records": [],
        "invalid_sessions": [],
        "incomplete_sessions": [],
        "duplicate_events": [],
    }
    for index, record in enumerate(records):
        event = record.get("event")
        if event not in (EVENT_START, EVENT_FINISH):
            continue
        sessionId = record.get("session_id")
        if not isinstance(sessionId, str) or not sessionId.strip():
            evidence["invalid_records"].append({
                "record": index + 1,
                "reason": "invalid_session_id",
            })
            continue
        grouped[sessionId].append((index, record))

    for sessionId, entries in sorted(grouped.items()):
        endpoints = {EVENT_START: [], EVENT_FINISH: []}
        seen = {EVENT_START: set(), EVENT_FINISH: set()}
        duplicates = collections.Counter()
        reasons = set()
        for index, record in entries:
            event = record["event"]
            if not _finite_number(record.get("ts_unix")):
                reasons.add("invalid_timestamp")
            if event == EVENT_START:
                workflow = record.get("workflow")
                if not isinstance(workflow, str) or not workflow.strip():
                    reasons.add("invalid_workflow")
                if record.get("mode") not in MODES:
                    reasons.add("invalid_mode")
            else:
                if type(record.get("success")) is not bool:
                    reasons.add("invalid_success")
                steps = record.get("steps")
                if (type(steps) is not int or steps < 0 or
                        not _finite_number(steps)):
                    reasons.add("invalid_steps")
            # Serialized identity distinguishes JSON booleans from numbers.
            # Only exact endpoint copies can be safely de-duplicated here.
            identity = json.dumps(record, sort_keys=True)
            if identity in seen[event]:
                duplicates[event] += 1
            else:
                seen[event].add(identity)
                endpoints[event].append((index, record))

        for event, count in sorted(duplicates.items()):
            evidence["duplicate_events"].append({
                "session_id": sessionId,
                "event": event,
                "count": count,
            })
        starts = endpoints[EVENT_START]
        finishes = endpoints[EVENT_FINISH]
        if not starts:
            reasons.add("missing_start")
        elif len(starts) > 1:
            reasons.add("conflicting_starts")
        if len(finishes) > 1:
            reasons.add("conflicting_finishes")

        if not reasons and finishes:
            startIndex, start = starts[0]
            finishIndex, finish = finishes[0]
            # Preserve mixed integer/float differences before rounding. Casting
            # a large integer first can turn a backwards interval into zero.
            try:
                duration = float(
                    Fraction(finish["ts_unix"]) - Fraction(start["ts_unix"]))
            except OverflowError:
                duration = None
            if finishIndex < startIndex:
                reasons.add("finish_before_start")
            if not _finite_number(duration) or duration < 0:
                reasons.add("invalid_elapsed_time")

        if reasons:
            evidence["invalid_sessions"].append({
                "session_id": sessionId,
                "reasons": sorted(reasons),
            })
            continue
        if not finishes:
            evidence["incomplete_sessions"].append({
                "session_id": sessionId,
                "reason": "missing_finish",
            })
            continue
        sessions.append({
            "session_id": sessionId,
            "workflow": start["workflow"],
            "mode": start["mode"],
            "success": finish["success"],
            "steps": finish["steps"],
            "time_to_result_s": duration,
            "start": start,
            "finish": finish,
        })

    evidence["ok"] = not (
        evidence["invalid_records"] or evidence["invalid_sessions"])
    return sessions, evidence


def pair_sessions(records):
    """Return valid sessions; use analyze_sessions for exclusion diagnostics."""
    return analyze_sessions(records)[0]


def _median_duration(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    lower, upper = ordered[middle - 1:middle + 1]
    # Durations are nonnegative: the difference cannot overflow, unlike a sum.
    return lower + (upper - lower) / 2.0


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
                    "p50": _median_duration(durations),
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
            action = record.get("action")
            if not isinstance(action, dict):
                violations.append({
                    "type": "invalid_action_receipt",
                    "record": record,
                })
                continue
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
    if type(args.success) is not bool:
        raise SystemExit("success must be a boolean")
    if (type(args.steps) is not int or args.steps < 0 or
            not _finite_number(args.steps)):
        raise SystemExit("steps must be a nonnegative integer")
    note = str(args.note or "")[:500]
    invalidRecords = []
    records = read_receipts(args.config_dir, invalidRecords)
    if invalidRecords:
        raise SystemExit("cannot finish a session with malformed receipt records")
    records = [
        record for record in records
        if record.get("session_id") == args.session_id and
        record.get("event") in (EVENT_START, EVENT_FINISH)]
    if not records:
        raise SystemExit("unknown session: {}".format(args.session_id))
    sessions, evidence = analyze_sessions(records)
    if not evidence["ok"]:
        raise SystemExit("cannot finish an invalid or ambiguous session")
    if sessions:
        finish = sessions[0]["finish"]
        if (finish["success"] == args.success and
                finish["steps"] == args.steps and
                finish.get("note", "") == note):
            return 0
        raise SystemExit("session already finished with a different outcome")
    record = {
        "event": EVENT_FINISH,
        "session_id": args.session_id,
        "success": args.success,
        "steps": args.steps,
        "note": note,
        "ts_unix": time.time(),
    }
    _, evidence = analyze_sessions(records + [record])
    if not evidence["ok"]:
        raise SystemExit("finish timestamp does not form a valid elapsed time")
    _append(args.config_dir, record)
    return 0


def command_report(args):
    invalidRecords = []
    records = read_receipts(args.config_dir, invalidRecords)
    sessions, measurement = analyze_sessions(records)
    measurement["invalid_records"].extend(invalidRecords)
    measurement["ok"] = measurement["ok"] and not invalidRecords
    payload = {
        "sessions": len(sessions),
        "summary": summarize_sessions(sessions),
        "safety": audit_receipts(records),
        "measurement": measurement,
    }
    print(json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        allow_nan=False))
    return 0 if payload["safety"]["ok"] and measurement["ok"] else 2


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
