#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import unittest

from usdviewLabs.actions import ACTION_SELECT_PATH
from usdviewLabs.voice import propose_transcript


class VoiceIngressTest(unittest.TestCase):
    def test_transcript_returns_proposal_only(self):
        decision = propose_transcript("select /World/Car")
        self.assertEqual(decision.action.kind, ACTION_SELECT_PATH)
        self.assertEqual(decision.action.source, "voice")
        self.assertEqual(decision.action.args["path"], "/World/Car")

    def test_receipt_metadata_does_not_store_raw_text(self):
        text = "select /World/SecretCar"
        decision = propose_transcript(text)
        self.assertEqual(decision.metadata["text_len"], len(text))
        self.assertIn("text_hash", decision.metadata)
        self.assertNotIn(text, decision.metadata.values())


if __name__ == "__main__":
    unittest.main()
