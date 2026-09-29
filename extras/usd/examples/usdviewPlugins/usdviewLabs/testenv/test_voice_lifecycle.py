#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import unittest

from usdviewLabs.voice_lifecycle import GenerationGate


class GenerationGateTest(unittest.TestCase):
    def test_newer_generation_supersedes_old(self):
        gate = GenerationGate()
        self.assertTrue(gate.observe({
            "generation": 10,
            "op": "start",
        }))
        self.assertTrue(gate.can_execute(10))

        self.assertTrue(gate.observe({
            "generation": 11,
            "op": "start",
        }))
        self.assertFalse(gate.can_execute(10))
        self.assertTrue(gate.can_execute(11))

    def test_cancel_blocks_execution(self):
        gate = GenerationGate()
        gate.observe({
            "generation": 3,
            "op": "start",
        })
        gate.observe({
            "generation": 3,
            "op": "cancel",
        })
        self.assertTrue(gate.is_cancelled(3))
        self.assertFalse(gate.can_execute(3))

    def test_same_generation_cannot_resurrect_after_cancel(self):
        gate = GenerationGate()
        gate.observe({
            "generation": 4,
            "op": "cancel",
        })
        gate.observe({
            "generation": 4,
            "op": "start",
        })
        gate.observe({
            "generation": 4,
            "op": "final",
        })
        self.assertFalse(gate.can_execute(4))

    def test_stale_message_rejected(self):
        gate = GenerationGate()
        gate.observe({
            "generation": 9,
            "op": "start",
        })
        self.assertFalse(gate.observe({
            "generation": 8,
            "op": "final",
        }))
        self.assertEqual(gate.latest(), 9)


if __name__ == "__main__":
    unittest.main()
