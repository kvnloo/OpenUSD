#!/usr/bin/env python3
#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Send one final transcript to a running usdview Labs voice bridge."""

import argparse
import json
import os
import socket
import sys
import uuid


def _endpoint_path(configDir):
    return os.path.join(
        os.path.expanduser(configDir),
        "usdview-labs",
        "voice-endpoint.json")


def send(configDir, transcript, timeout=1.0):
    with open(_endpoint_path(configDir), "r") as stream:
        endpoint = json.load(stream)

    payload = {
        "token": endpoint["token"],
        "transcript": transcript,
        "final": True,
        "utterance_id": str(uuid.uuid4()),
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "transcript",
        help="Final transcript text to preview in usdview")
    parser.add_argument(
        "--config-dir",
        default="~/.usdview",
        help="usdview config directory; default: ~/.usdview")
    args = parser.parse_args()

    result = send(
        args.config_dir,
        args.transcript)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
