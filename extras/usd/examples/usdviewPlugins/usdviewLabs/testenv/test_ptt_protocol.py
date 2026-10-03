#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import json
import unittest

from usdviewLabs.ptt_protocol import (
    decode_event,
    encode_event,
    validate_target,
)


class PttProtocolTest(unittest.TestCase):
    def test_loopback_target_only(self):
        target = validate_target({
            "protocol": 1,
            "host": "127.0.0.1",
            "port": 4321,
            "token": "secret",
        })
        self.assertEqual(target["port"], 4321)

        with self.assertRaises(ValueError):
            validate_target({
                "protocol": 1,
                "host": "0.0.0.0",
                "port": 4321,
                "token": "secret",
            })

    def test_round_trip(self):
        raw = encode_event(
            "secret",
            "start",
            17,
            clientSentUnix=123.0)
        event = decode_event(raw.strip(), "secret")
        self.assertEqual(event["op"], "start")
        self.assertEqual(event["generation"], 17)
        self.assertEqual(event["client_sent_unix"], 123.0)

    def test_invalid_token_rejected(self):
        raw = encode_event(
            "wrong",
            "stop",
            1)
        with self.assertRaises(ValueError):
            decode_event(raw.strip(), "secret")

    def test_invalid_op_rejected(self):
        with self.assertRaises(ValueError):
            encode_event(
                "secret",
                "execute",
                1)


if __name__ == "__main__":
    unittest.main()
