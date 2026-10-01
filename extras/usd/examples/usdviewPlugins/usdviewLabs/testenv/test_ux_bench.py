#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import types
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


class UxMeasurementEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.module = _load()
        self.start = {
            "event": self.module.EVENT_START,
            "session_id": "session-a",
            "workflow": "select-prim",
            "mode": "palette",
            "ts_unix": 10.0,
        }
        self.finish = {
            "event": self.module.EVENT_FINISH,
            "session_id": "session-a",
            "success": True,
            "steps": 2,
            "note": "",
            "ts_unix": 11.0,
        }

    def _report(self, records, extraLine=""):
        with tempfile.TemporaryDirectory() as configDir:
            path = self.module._receipt_path(configDir)
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as stream:
                for record in records:
                    stream.write(json.dumps(record) + "\n")
                stream.write(extraLine)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = self.module.command_report(
                    types.SimpleNamespace(config_dir=configDir))
            def rejectConstant(value):
                raise ValueError("non-finite JSON: " + value)
            return status, json.loads(
                output.getvalue(), parse_constant=rejectConstant)

    def test_duplicate_endpoints_are_idempotent_and_visible(self):
        status, report = self._report([
            self.start, dict(self.start), self.finish, dict(self.finish)])
        self.assertEqual(status, 0)
        self.assertEqual(report["sessions"], 1)
        self.assertEqual(report["summary"]["select-prim:palette"]["n"], 1)
        self.assertEqual(len(report["measurement"]["duplicate_events"]), 2)

    def test_ambiguous_sessions_are_excluded_with_reasons(self):
        cases = {
            "conflicting start": [
                self.start, dict(self.start, workflow="variants"), self.finish],
            "conflicting finish": [
                self.start, self.finish, dict(self.finish, success=False)],
            "session id reused": [
                self.start, self.finish, dict(self.start, ts_unix=20.0),
                dict(self.finish, ts_unix=21.0)],
            "finish before start": [self.finish, self.start],
            "missing start": [self.finish],
        }
        for name, records in cases.items():
            with self.subTest(name=name):
                status, report = self._report(records)
                self.assertEqual(status, 2)
                self.assertEqual(report["sessions"], 0)
                self.assertEqual(report["summary"], {})
                self.assertFalse(report["measurement"]["ok"])
                self.assertTrue(report["measurement"]["invalid_sessions"])

    def test_invalid_values_cannot_become_measurements(self):
        cases = {
            "string false": {"success": "false"},
            "integer success": {"success": 1},
            "negative steps": {"steps": -1},
            "fractional steps": {"steps": 1.5},
            "boolean steps": {"steps": True},
            "backwards clock": {"ts_unix": 9.0},
            "infinite clock": {"ts_unix": float("inf")},
            "nan clock": {"ts_unix": float("nan")},
            "string clock": {"ts_unix": "11.0"},
            "boolean clock": {"ts_unix": True},
            "missing clock": {"ts_unix": None},
        }
        for name, updates in cases.items():
            with self.subTest(name=name):
                status, report = self._report([
                    self.start, dict(self.finish, **updates)])
                self.assertEqual(status, 2)
                self.assertEqual(report["sessions"], 0)
                self.assertTrue(
                    report["measurement"]["invalid_sessions"] or
                    report["measurement"]["invalid_records"])

    def test_finite_timestamps_cannot_overflow_elapsed_time(self):
        status, report = self._report([
            dict(self.start, ts_unix=-1e308),
            dict(self.finish, ts_unix=1e308)])
        self.assertEqual(status, 2)
        self.assertEqual(report["sessions"], 0)

    def test_integer_timestamps_keep_small_elapsed_differences(self):
        status, report = self._report([
            dict(self.start, ts_unix=2 ** 53),
            dict(self.finish, ts_unix=2 ** 53 + 1)])
        self.assertEqual(status, 0)
        timing = report["summary"]["select-prim:palette"]["time_to_result_s"]
        self.assertEqual(timing["p50"], 1.0)

    def test_mixed_timestamps_preserve_order_and_elapsed_time(self):
        cases = (
            (10 ** 20 + 1, 1e20, 2, None),
            (10 ** 20 - 1, 1e20, 0, 1.0),
            (2 ** 53 + 1, float(2 ** 53 + 2), 0, 1.0),
        )
        for start, finish, expectedStatus, expectedDuration in cases:
            with self.subTest(start=start, finish=finish):
                status, report = self._report([
                    dict(self.start, ts_unix=start),
                    dict(self.finish, ts_unix=finish)])
                self.assertEqual(status, expectedStatus)
                if expectedDuration is None:
                    self.assertEqual(report["sessions"], 0)
                else:
                    timing = report["summary"]["select-prim:palette"]["time_to_result_s"]
                    self.assertEqual(timing["p50"], expectedDuration)

    def test_median_of_finite_durations_stays_finite(self):
        status, report = self._report([
            dict(self.start, ts_unix=0.0),
            dict(self.finish, ts_unix=1e308),
            dict(self.start, session_id="b", ts_unix=0.0),
            dict(self.finish, session_id="b", ts_unix=1e308)])
        self.assertEqual(status, 0)
        timing = report["summary"]["select-prim:palette"]["time_to_result_s"]
        self.assertEqual(timing["p50"], 1e308)

    def test_incomplete_session_is_distinct_from_invalid_evidence(self):
        status, report = self._report([self.start])
        self.assertEqual(status, 0)
        self.assertEqual(report["sessions"], 0)
        self.assertTrue(report["measurement"]["incomplete_sessions"])
        self.assertFalse(report["measurement"]["invalid_sessions"])

    def test_valid_sessions_survive_invalid_neighbors(self):
        status, report = self._report([
            self.start, dict(self.finish, success=False),
            dict(self.start, session_id="bad"),
            dict(self.finish, session_id="bad", steps=-1)])
        self.assertEqual(status, 2)
        self.assertEqual(report["sessions"], 1)
        self.assertEqual(report["summary"]["select-prim:palette"]["success_rate"], 0.0)
        self.assertEqual(len(report["measurement"]["invalid_sessions"]), 1)

    def test_malformed_jsonl_is_visible(self):
        for line in ('{broken json\n', '[]\n'):
            with self.subTest(line=line):
                status, report = self._report([self.start, self.finish], line)
                self.assertEqual(status, 2)
                self.assertEqual(report["sessions"], 1)
                self.assertTrue(report["measurement"]["invalid_records"])

    def test_duplicate_json_fields_are_not_silently_reinterpreted(self):
        for fields in (
                '"success": true, "success": false',
                '"success": false, "success": true',
                '"success": true, "note": {"x": 1, "x": 2}'):
            with self.subTest(fields=fields):
                line = ('{"event": "ux_bench_finish", '
                        '"session_id": "session-a", '
                        '"steps": 2, "ts_unix": 11, ' + fields + '}\n')
                status, report = self._report([self.start], line)
                self.assertEqual(status, 2)
                self.assertEqual(report["sessions"], 0)
                self.assertTrue(report["measurement"]["invalid_records"])

    def test_malformed_audit_record_returns_a_report(self):
        status, report = self._report([
            self.start, self.finish, {"event": "action", "action": "bad"}])
        self.assertEqual(status, 2)
        self.assertEqual(report["sessions"], 1)
        self.assertFalse(report["safety"]["ok"])

    def test_nonfinite_audit_values_are_reported_as_invalid_json(self):
        for number in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(number=number):
                line = ('{"event": "voice_bridge_start", '
                        '"host": "unexpected", "ts_unix": ' + number + '}\n')
                status, report = self._report([self.start, self.finish], line)
                self.assertEqual(status, 2)
                self.assertEqual(report["sessions"], 1)
                self.assertTrue(report["measurement"]["invalid_records"])

    def test_invalid_session_metadata_is_reported(self):
        for updates in ({"session_id": []}, {"workflow": []}, {"mode": "unknown"}):
            with self.subTest(updates=updates):
                status, report = self._report([
                    dict(self.start, **updates), self.finish])
                self.assertEqual(status, 2)
                self.assertEqual(report["sessions"], 0)

    def test_finish_retry_does_not_append_another_observation(self):
        with tempfile.TemporaryDirectory() as configDir:
            self.module._append(configDir, self.start)
            args = types.SimpleNamespace(
                config_dir=configDir, session_id="session-a",
                success=True, steps=2, note="")
            self.assertEqual(self.module.command_finish(args), 0)
            path = self.module._receipt_path(configDir)
            with open(path, "rb") as stream:
                original = stream.read()
            self.assertEqual(self.module.command_finish(args), 0)
            with open(path, "rb") as stream:
                self.assertEqual(stream.read(), original)
            args.success = False
            with self.assertRaises(SystemExit):
                self.module.command_finish(args)
            with open(path, "rb") as stream:
                self.assertEqual(stream.read(), original)

    def test_finish_rejects_unknown_session_and_negative_steps(self):
        with tempfile.TemporaryDirectory() as configDir:
            args = types.SimpleNamespace(
                config_dir=configDir, session_id="unknown",
                success=True, steps=1, note="")
            with self.assertRaises(SystemExit):
                self.module.command_finish(args)
            self.module._append(configDir, self.start)
            args.session_id = "session-a"
            args.steps = -1
            with self.assertRaises(SystemExit):
                self.module.command_finish(args)
            records = self.module.read_receipts(configDir)
            self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
