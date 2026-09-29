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

    transcript = str(payload.get("transcript", "")).strip()
    if not transcript:
        raise ValueError("empty transcript")
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        raise ValueError("transcript too long")

    utteranceId = payload.get("utterance_id")
    if utteranceId is not None:
        utteranceId = str(utteranceId)[:128]

    return {
        "transcript": transcript,
        "final": bool(payload.get("final", True)),
        "utterance_id": utteranceId,
    }


def encode_response(ok, **fields):
    payload = {"ok": bool(ok)}
    payload.update(fields)
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
