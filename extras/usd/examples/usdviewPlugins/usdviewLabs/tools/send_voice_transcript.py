#!/usr/bin/env python3
#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Send voice lifecycle events to a running usdview Labs bridge."""

import argparse
import json
import os
import socket
import sys
import time
import uuid


MAX_GENERATION = (1 << 63) - 1


def _endpoint_path(configDir):
    return os.path.join(
        os.path.expanduser(configDir),
        "usdview-labs",
        "voice-endpoint.json")


def new_generation():
    return time.time_ns() & MAX_GENERATION


def send_event(
        configDir,
        op,
        generation,
        transcript="",
        utteranceId=None,
        timeout=1.0):
    with open(_endpoint_path(configDir), "r") as stream:
        endpoint = json.load(stream)

    payload = {
        "token": endpoint["token"],
        "op": str(op),
        "generation": int(generation),
        "transcript": str(transcript),
        "utterance_id": utteranceId or str(uuid.uuid4()),
        "client_sent_unix": time.time(),
    }

    raw = (
        json.dumps(payload, sort_keys=True) + "\n"
    ).encode("utf-8")

    with socket.create_connection(
            (endpoint["host"], int(endpoint["port"])),
            timeout=timeout) as conn:
        conn.sendall(raw)
        response = conn.makefile("rb").readline(16384)

    return json.loads(response.decode("utf-8"))


def send(configDir, transcript, timeout=1.0):
    """Backward-compatible helper: one generated final utterance."""
    return send_event(
        configDir,
        "final",
        new_generation(),
        transcript=transcript,
        timeout=timeout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "transcript",
        nargs="?",
        default="",
        help="Transcript text; required for partial/final")
    parser.add_argument(
        "--op",
        choices=("start", "partial", "final", "cancel"),
        default="final")
    parser.add_argument(
        "--generation",
        type=int,
        default=None,
        help="Monotonic utterance generation; generated if omitted")
    parser.add_argument(
        "--config-dir",
        default="~/.usdview",
        help="usdview config directory; default: ~/.usdview")
    args = parser.parse_args()

    generation = (
        args.generation
        if args.generation is not None
        else new_generation())

    result = send_event(
        args.config_dir,
        args.op,
        generation,
        transcript=args.transcript)

    result["generation"] = generation
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
