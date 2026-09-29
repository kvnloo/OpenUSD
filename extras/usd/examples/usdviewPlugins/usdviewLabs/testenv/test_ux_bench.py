#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import importlib.util
import os
import unittest


_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "experiments",
    "ux_bench.py")


def _load():
    spec = importlib.util.spec_from_file_location(
        "usdview_labs_ux_bench",
        os.path.abspath(_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UxBenchTest(unittest.TestCase):
    def test_pair_sessions(self):
        module = _load()
        rows = module.pair_sessions([
            {
                "event": "ux_bench_start",
                "session_id": "a",
                "workflow": "select-prim",
                "mode": "palette",
                "ts_unix": 10.0,
            },
            {
                "event": "ux_bench_finish",
                "session_id": "a",
                "success": True,
                "steps": 2,
                "ts_unix": 11.25,
            },
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["time_to_result_s"],
            1.25)

    def test_audit_rejects_jev_execution(self):
        module = _load()
        result = module.audit_receipts([
            {
                "event": "action",
                "action": {
                    "source": "jev-shadow",
                },
            },
        ])
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["violations"][0]["type"],
            "jev_shadow_executed")

    def test_audit_accepts_shadow_receipt(self):
        module = _load()
        result = module.audit_receipts([
            {
                "event": "jev_shadow",
            },
            {
                "event": "voice_bridge_start",
                "host": "127.0.0.1",
            },
        ])
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["evidence"]["jev_shadow_receipt"],
            1)


if __name__ == "__main__":
    unittest.main()
