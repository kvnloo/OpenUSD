#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import json
import unittest

from usdviewLabs.voice_protocol import (
    MAX_TRANSCRIPT_CHARS,
    decode_message,
    encode_response,
)


class VoiceProtocolTest(unittest.TestCase):
    def test_valid_final_transcript(self):
        raw = json.dumps({
            "token": "secret",
            "transcript": "select /World/Car",
            "final": True,
            "utterance_id": "u1",
        }).encode("utf-8")

        message = decode_message(raw, "secret")
        self.assertEqual(
            message["transcript"],
            "select /World/Car")
        self.assertTrue(message["final"])
        self.assertEqual(
            message["utterance_id"],
            "u1")

    def test_invalid_token_rejected(self):
        raw = json.dumps({
            "token": "wrong",
            "transcript": "clear selection",
        }).encode("utf-8")

        with self.assertRaises(ValueError):
            decode_message(raw, "secret")

    def test_partial_transcript_is_preserved_as_partial(self):
        raw = json.dumps({
            "token": "secret",
            "transcript": "select",
            "final": False,
        }).encode("utf-8")

        self.assertFalse(
            decode_message(raw, "secret")["final"])

    def test_empty_transcript_rejected(self):
        raw = json.dumps({
            "token": "secret",
            "transcript": "   ",
        }).encode("utf-8")

        with self.assertRaises(ValueError):
            decode_message(raw, "secret")

    def test_oversized_transcript_rejected(self):
        raw = json.dumps({
            "token": "secret",
            "transcript": "x" * (
                MAX_TRANSCRIPT_CHARS + 1),
        }).encode("utf-8")

        with self.assertRaises(ValueError):
            decode_message(raw, "secret")

    def test_response_is_newline_delimited_json(self):
        raw = encode_response(
            True,
            queued=True)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertTrue(
            json.loads(raw.decode("utf-8"))["queued"])


if __name__ == "__main__":
    unittest.main()
