#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Pure-stdlib protocol validation for the local voice bridge."""

from __future__ import print_function

import hmac
import json


MAX_MESSAGE_BYTES = 16384
MAX_TRANSCRIPT_CHARS = 4096
MAX_GENERATION = (1 << 63) - 1
OPS = frozenset({"start", "partial", "final", "cancel"})


def _parse_generation(payload):
    generation = payload.get("generation", 0)
    try:
        generation = int(generation)
    except (TypeError, ValueError):
        raise ValueError("generation must be an integer")
    if generation < 0 or generation > MAX_GENERATION:
        raise ValueError("generation out of range")
    return generation


def decode_message(raw, expectedToken):
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("voice message must be bytes")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("voice message too large")

    try:
        payload = json.loads(bytes(raw).decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("voice message must be an object")

    token = str(payload.get("token", ""))
    if not hmac.compare_digest(token, str(expectedToken)):
        raise ValueError("invalid token")

    # Protocol-1 compatibility: messages without op map final=true to "final"
    # and final=false to "partial".
    op = payload.get("op")
    if op is None:
        op = "final" if bool(payload.get("final", True)) else "partial"
    op = str(op).lower()
    if op not in OPS:
        raise ValueError("invalid voice op")

    transcript = str(payload.get("transcript", "")).strip()
    if op in {"partial", "final"} and not transcript:
        raise ValueError("empty transcript")
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        raise ValueError("transcript too long")

    utteranceId = payload.get("utterance_id")
    if utteranceId is not None:
        utteranceId = str(utteranceId)[:128]

    clientSentUnix = payload.get("client_sent_unix")
    if clientSentUnix is not None:
        try:
            clientSentUnix = float(clientSentUnix)
        except (TypeError, ValueError):
            raise ValueError("client_sent_unix must be numeric")

    return {
        "op": op,
        "generation": _parse_generation(payload),
        "transcript": transcript,
        "final": op == "final",
        "utterance_id": utteranceId,
        "client_sent_unix": clientSentUnix,
    }


def encode_response(ok, **fields):
    payload = {"ok": bool(ok)}
    payload.update(fields)
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
