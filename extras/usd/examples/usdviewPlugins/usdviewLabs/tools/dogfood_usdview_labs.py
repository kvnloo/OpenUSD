#!/usr/bin/env python3
#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Dogfood harness for the usdview Labs P0-P4 stack.

The ptt-loop subcommand emulates a stage manager without microphone capture:
PTT start/cancel are forwarded immediately into the voice bridge so generation
invalidation is exercised, and PTT stop injects a canned final transcript with
the same generation.
"""

import argparse
import collections
import hmac
import json
import os
import secrets
import socket
import statistics
import sys
import time


HOST = "127.0.0.1"
MAX_BYTES = 16384


def _labs_dir(config_dir):
    return os.path.join(
        os.path.expanduser(config_dir),
        "usdview-labs")


def _private_write(path, payload):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    tmp = path + ".tmp"
    fd = os.open(
        tmp,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(payload, stream, sort_keys=True)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_json(path):
    with open(path, "r") as stream:
        return json.load(stream)


def _recv_line(conn, limit=MAX_BYTES):
    data = b""
    while b"\n" not in data and len(data) <= limit:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
    if len(data) > limit:
        raise ValueError("message too large")
    return data.split(b"\n", 1)[0]


def _reply(conn, ok, **fields):
    payload = {"ok": bool(ok)}
    payload.update(fields)
    conn.sendall(
        (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"))


def _voice_endpoint(config_dir):
    endpoint = _read_json(os.path.join(
        _labs_dir(config_dir),
        "voice-endpoint.json"))
    if endpoint.get("host") != HOST:
        raise ValueError("voice bridge is not loopback-only")
    return endpoint


def _send_voice(config_dir, op, generation, transcript=""):
    endpoint = _voice_endpoint(config_dir)
    payload = {
        "token": endpoint["token"],
        "op": op,
        "generation": int(generation),
        "transcript": transcript,
        "client_sent_unix": time.time(),
    }
    raw = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")

    with socket.create_connection(
            (endpoint["host"], int(endpoint["port"])),
            timeout=1.0) as conn:
        conn.sendall(raw)
        response = _recv_line(conn)
    return json.loads(response.decode("utf-8"))


def run_ptt_loop(args):
    token = secrets.token_urlsafe(24)
    target_path = os.path.join(
        _labs_dir(args.config_dir),
        "ptt-target.json")

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM)
    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1)
    server.bind((HOST, 0))
    server.listen(4)
    server.settimeout(0.5)
    port = server.getsockname()[1]

    _private_write(target_path, {
        "protocol": 1,
        "host": HOST,
        "port": port,
        "token": token,
        "pid": os.getpid(),
        "created_unix": time.time(),
    })

    print("PTT dogfood target:", target_path)
    print("Listening on {}:{}".format(HOST, port))
    print("In usdview: Labs -> Start Voice Bridge")
    print("Then: Labs -> Enable Hold-to-Talk Hotkey")
    print("Hold Ctrl+Shift+Space, then release.")
    print("Release injects transcript:", repr(args.transcript))

    completed = 0
    try:
        while True:
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                continue

            with conn:
                conn.settimeout(0.5)
                try:
                    payload = json.loads(
                        _recv_line(conn).decode("utf-8"))

                    supplied = str(payload.get("token", ""))
                    if not hmac.compare_digest(supplied, token):
                        _reply(conn, False, error="invalid token")
                        continue

                    op = str(payload.get("op"))
                    generation = int(payload.get("generation"))
                    if op not in {"start", "stop", "cancel"}:
                        _reply(conn, False, error="invalid op")
                        continue

                    print("PTT", op, "generation", generation)
                    _reply(conn, True)

                    if op == "start":
                        result = _send_voice(
                            args.config_dir,
                            "start",
                            generation)
                        print("voice start ->", json.dumps(
                            result, sort_keys=True))

                    elif op == "stop":
                        result = _send_voice(
                            args.config_dir,
                            "final",
                            generation,
                            args.transcript)
                        print("voice final ->", json.dumps(
                            result, sort_keys=True))
                        completed += 1

                    elif op == "cancel":
                        result = _send_voice(
                            args.config_dir,
                            "cancel",
                            generation)
                        print("voice cancel ->", json.dumps(
                            result, sort_keys=True))
                        completed += 1

                    if args.once and completed:
                        return 0

                except Exception as exc:
                    try:
                        _reply(
                            conn,
                            False,
                            error=type(exc).__name__)
                    except Exception:
                        pass
                    print(
                        "dogfood error:",
                        type(exc).__name__,
                        str(exc),
                        file=sys.stderr)

    except KeyboardInterrupt:
        return 0
    finally:
        server.close()
        try:
            current = _read_json(target_path)
            if hmac.compare_digest(
                    str(current.get("token", "")),
                    token):
                os.remove(target_path)
        except Exception:
            pass


def _latencies(records, key):
    values = []
    for record in records:
        value = record.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = int(round(
        (len(ordered) - 1) * fraction))
    return ordered[index]


def run_report(args):
    path = os.path.join(
        _labs_dir(args.config_dir),
        "receipts.jsonl")

    records = []
    with open(path, "r") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    if args.last:
        records = records[-args.last:]

    counts = collections.Counter(
        record.get("event", "<missing>")
        for record in records)

    print("receipts:", len(records))
    for event, count in sorted(counts.items()):
        print("{:34s} {}".format(event, count))

    print("\nlatency summaries (ms)")
    keys = [
        "duration_ms",
        "bridge_to_preview_ms",
        "client_to_preview_ms",
        "bridge_to_result_ms",
        "client_to_result_ms",
        "preview_to_accept_ms",
        "queue_to_send_ms",
        "send_latency_ms",
    ]
    for key in keys:
        values = _latencies(records, key)
        if not values:
            continue
        print(
            "{:28s} n={:<4d} p50={:8.3f} p95={:8.3f} max={:8.3f}".format(
                key,
                len(values),
                statistics.median(values),
                _percentile(values, 0.95),
                max(values)))

    print("\nsafety evidence")
    print(
        "stale accepts blocked:",
        counts.get("voice_preview_stale_accept_blocked", 0))
    print(
        "stale/cancelled finals dropped:",
        counts.get("voice_final_dropped", 0))
    print(
        "PTT signal drops:",
        counts.get("ptt_signal_drop", 0))
    return 0


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        default="~/.usdview",
        help="usdview config directory; default: ~/.usdview")

    sub = parser.add_subparsers(
        dest="command",
        required=True)

    ptt = sub.add_parser(
        "ptt-loop",
        help="emulate a local ASR stage manager")
    ptt.add_argument(
        "--transcript",
        default="what is selected",
        help="canned final transcript injected on PTT release")
    ptt.add_argument(
        "--once",
        action="store_true",
        help="exit after one stop/cancel round trip")
    ptt.set_defaults(func=run_ptt_loop)

    report = sub.add_parser(
        "report",
        help="summarize usdview Labs receipts")
    report.add_argument(
        "--last",
        type=int,
        default=0,
        help="only inspect the last N receipts")
    report.set_defaults(func=run_report)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
