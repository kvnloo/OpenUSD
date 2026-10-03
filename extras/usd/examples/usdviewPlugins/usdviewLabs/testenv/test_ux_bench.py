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

    def test_build_trial_plan_has_100_paired_trials(self):
        module = _load()
        workflows = [
            {"id": "workflow-{}".format(index)}
            for index in range(10)]
        plan = module.build_trial_plan(
            workflows,
            repeats=5,
            seed=7)

        self.assertEqual(len(plan), 100)
        counts = {}
        for row in plan:
            key = (
                row["workflow"],
                row["mode"])
            counts[key] = counts.get(key, 0) + 1

        for workflow in workflows:
            workflowId = workflow["id"]
            self.assertEqual(
                counts[(workflowId, "stock")],
                5)
            self.assertEqual(
                counts[(workflowId, "palette")],
                5)

        for index in range(0, len(plan), 2):
            pair = plan[index:index + 2]
            self.assertEqual(
                pair[0]["workflow"],
                pair[1]["workflow"])
            self.assertEqual(
                {row["mode"] for row in pair},
                {"stock", "palette"})

    def test_compare_modes_reports_stock_deltas(self):
        module = _load()
        summary = {
            "inspect:stock": {
                "n": 5,
                "success_rate": 0.8,
                "time_to_result_s": {
                    "p50": 2.0,
                    "p95": 3.0,
                    "max": 3.2,
                },
                "steps": {
                    "p50": 6.0,
                    "p95": 7.0,
                    "max": 8,
                },
            },
            "inspect:palette": {
                "n": 5,
                "success_rate": 1.0,
                "time_to_result_s": {
                    "p50": 1.0,
                    "p95": 1.5,
                    "max": 1.7,
                },
                "steps": {
                    "p50": 4.0,
                    "p95": 5.0,
                    "max": 5,
                },
            },
        }

        row = module.compare_modes(summary)[
            "palette_vs_stock"]["inspect"]
        self.assertAlmostEqual(
            row["success_rate"]["delta"],
            0.2)
        self.assertEqual(
            row["time_to_result_s"][
                "p50"]["delta"],
            -1.0)
        self.assertEqual(
            row["time_to_result_s"][
                "p50"]["ratio"],
            0.5)
        self.assertEqual(
            row["steps"]["p50"]["delta"],
            -2.0)

    def test_summarize_probes(self):
        module = _load()
        result = module.summarize_probes([
            {
                "event": "ux_bench_probe",
                "name": "hud-idle-frame-time",
                "value": 0.1,
                "unit": "ms",
                "mode": "palette",
            },
            {
                "event": "ux_bench_probe",
                "name": "hud-idle-frame-time",
                "value": 0.3,
                "unit": "ms",
                "mode": "palette",
            },
        ])

        row = result[
            "hud-idle-frame-time:palette"]
        self.assertEqual(row["n"], 2)
        self.assertEqual(row["unit"], "ms")
        self.assertAlmostEqual(row["p50"], 0.2)
        self.assertEqual(row["p95"], 0.3)

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
