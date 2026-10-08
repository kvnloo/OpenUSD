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
    def test_v2_final_with_generation(self):
        raw = json.dumps({
            "token": "secret",
            "op": "final",
            "generation": 7,
            "transcript": "select /World/Car",
            "utterance_id": "u1",
            "client_sent_unix": 123.5,
        }).encode("utf-8")

        message = decode_message(raw, "secret")
        self.assertEqual(message["op"], "final")
        self.assertEqual(message["generation"], 7)
        self.assertTrue(message["final"])
        self.assertEqual(message["utterance_id"], "u1")
        self.assertEqual(message["client_sent_unix"], 123.5)

    def test_start_and_cancel_need_no_transcript(self):
        for op in ("start", "cancel"):
            raw = json.dumps({
                "token": "secret",
                "op": op,
                "generation": 8,
            }).encode("utf-8")
            self.assertEqual(
                decode_message(raw, "secret")["op"],
                op)

    def test_partial_and_final_require_transcript(self):
        for op in ("partial", "final"):
            raw = json.dumps({
                "token": "secret",
                "op": op,
                "generation": 8,
            }).encode("utf-8")
            with self.assertRaises(ValueError):
                decode_message(raw, "secret")

    def test_protocol1_final_boolean_still_works(self):
        raw = json.dumps({
            "token": "secret",
            "transcript": "clear selection",
            "final": False,
        }).encode("utf-8")
        message = decode_message(raw, "secret")
        self.assertEqual(message["op"], "partial")
        self.assertEqual(message["generation"], 0)
        self.assertFalse(message["final"])

    def test_invalid_token_rejected(self):
        raw = json.dumps({
            "token": "wrong",
            "op": "final",
            "transcript": "clear selection",
        }).encode("utf-8")
        with self.assertRaises(ValueError):
            decode_message(raw, "secret")

    def test_invalid_generation_rejected(self):
        raw = json.dumps({
            "token": "secret",
            "op": "start",
            "generation": -1,
        }).encode("utf-8")
        with self.assertRaises(ValueError):
            decode_message(raw, "secret")

    def test_oversized_transcript_rejected(self):
        raw = json.dumps({
            "token": "secret",
            "op": "final",
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
