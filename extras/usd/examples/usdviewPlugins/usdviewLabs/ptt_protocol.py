#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Pure-stdlib PTT control protocol.

The stage manager owns the target endpoint. usdview emits lifecycle signals
only; it never owns microphone capture or ASR.
"""

from __future__ import print_function

import hmac
import json
import os
import time


HOST = "127.0.0.1"
MAX_CONTROL_BYTES = 4096
MAX_TOKEN_CHARS = 512
OPS = frozenset({"start", "stop", "cancel"})


def target_path(configDir):
    return os.path.join(
        str(configDir),
        "usdview-labs",
        "ptt-target.json")


def validate_target(payload):
    if not isinstance(payload, dict):
        raise ValueError("PTT target must be an object")

    if int(payload.get("protocol", 0)) != 1:
        raise ValueError("unsupported PTT target protocol")

    host = str(payload.get("host", ""))
    if host != HOST:
        raise ValueError("PTT target must bind to 127.0.0.1")

    try:
        port = int(payload["port"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("PTT target port is invalid")
    if port < 1 or port > 65535:
        raise ValueError("PTT target port out of range")

    token = str(payload.get("token", ""))
    if not token or len(token) > MAX_TOKEN_CHARS:
        raise ValueError("PTT target token is invalid")

    return {
        "protocol": 1,
        "host": host,
        "port": port,
        "token": token,
    }


def load_target(configDir):
    with open(target_path(configDir), "r") as stream:
        return validate_target(json.load(stream))


def encode_event(token, op, generation, clientSentUnix=None):
    op = str(op).lower()
    if op not in OPS:
        raise ValueError("invalid PTT op")

    generation = int(generation)
    if generation < 0:
        raise ValueError("generation out of range")

    payload = {
        "token": str(token),
        "op": op,
        "generation": generation,
        "client_sent_unix": (
            float(clientSentUnix)
            if clientSentUnix is not None
            else time.time()),
    }
    raw = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    if len(raw) > MAX_CONTROL_BYTES:
        raise ValueError("PTT event too large")
    return raw


def decode_event(raw, expectedToken):
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("PTT event must be bytes")
    if len(raw) > MAX_CONTROL_BYTES:
        raise ValueError("PTT event too large")

    try:
        payload = json.loads(bytes(raw).decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid PTT JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("PTT event must be an object")

    token = str(payload.get("token", ""))
    if not hmac.compare_digest(token, str(expectedToken)):
        raise ValueError("invalid PTT token")

    op = str(payload.get("op", "")).lower()
    if op not in OPS:
        raise ValueError("invalid PTT op")

    try:
        generation = int(payload["generation"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("generation must be an integer")
    if generation < 0:
        raise ValueError("generation out of range")

    return {
        "op": op,
        "generation": generation,
        "client_sent_unix": payload.get("client_sent_unix"),
    }
