#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import importlib.util
import json
import os
import unittest


_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "experiments",
    "portable_evidence.py",
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "usdview_labs_portable_evidence", os.path.abspath(_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PortableEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.module = _load()
        self.sha = "0123456789abcdef0123456789abcdef01234567"

    def test_all_green_is_pass(self):
        receipt = self.module.normalize(
            {"sessions": 4, "safety": {"ok": True, "violations": []}},
            self.sha,
            [
                {"name": "Linux", "conclusion": "success"},
                {"name": "Windows", "conclusion": "success"},
            ],
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "pass")

    def test_successful_workflow_allows_optional_skipped_job(self):
        receipt = self.module.normalize(
            {"sessions": 4, "safety": {"ok": True, "violations": []}},
            self.sha,
            [
                {"name": "Linux", "conclusion": "success"},
                {"name": "GPUTests", "conclusion": "skipped", "required": False},
            ],
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "pass")
        self.assertEqual(receipt["evidence"][-1]["result"], "unknown")

    def test_failed_job_is_fail_even_if_workflow_claims_success(self):
        receipt = self.module.normalize(
            {"sessions": 4, "safety": {"ok": True, "violations": []}},
            self.sha,
            [{"name": "Windows", "conclusion": "failure"}],
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "fail")
        self.assertEqual(receipt["evidence"][-1]["details"]["name"], "Windows")

    def test_missing_evidence_stays_unknown(self):
        receipt = self.module.normalize({}, self.sha)
        self.assertEqual(receipt["outcome"], "unknown")
        self.assertTrue(any(item["result"] == "unknown" for item in receipt["evidence"]))

    def test_safety_violation_cannot_pass(self):
        receipt = self.module.normalize(
            {"sessions": 1, "safety": {"ok": False, "violations": [{"type": "x"}]}},
            self.sha,
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "fail")

    def test_successful_workflow_requires_completed_required_jobs(self):
        for conclusion in (None, "skipped", "neutral", "in_progress", "unknown"):
            for required in (None, True):
                with self.subTest(conclusion=conclusion, required=required):
                    job = {"name": "Linux", "conclusion": conclusion}
                    if required is not None:
                        job["required"] = required
                    receipt = self.module.normalize(
                        {"sessions": 4, "safety": {"ok": True, "violations": []}},
                        self.sha,
                        [job],
                        workflow_conclusion="success",
                    )
                    self.assertEqual(receipt["outcome"], "unknown")
                    self.assertEqual(receipt["evidence"][-1]["result"], "unknown")
                    self.assertTrue(receipt["evidence"][-1]["details"]["required"])

    def test_missing_required_job_conclusion_is_unknown(self):
        receipt = self.module.normalize(
            {"sessions": 4, "safety": {"ok": True, "violations": []}},
            self.sha,
            [{"name": "Linux"}],
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "unknown")
        self.assertEqual(receipt["evidence"][-1]["details"]["name"], "Linux")

    def test_only_boolean_false_marks_a_job_optional(self):
        for required in (None, 0, "", "false", [], {}):
            with self.subTest(required=required):
                receipt = self.module.normalize(
                    {"sessions": 4, "safety": {"ok": True, "violations": []}},
                    self.sha,
                    [{"name": "Linux", "conclusion": "skipped", "required": required}],
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "unknown")
                self.assertTrue(receipt["evidence"][-1]["details"]["required"])

    def test_optional_failed_job_still_fails_workflow(self):
        receipt = self.module.normalize(
            {"sessions": 4, "safety": {"ok": True, "violations": []}},
            self.sha,
            [{"name": "GPUTests", "conclusion": "failure", "required": False}],
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "fail")

    def test_unknown_workflow_cannot_be_replaced_by_successful_jobs(self):
        receipt = self.module.normalize(
            {"sessions": 4, "safety": {"ok": True, "violations": []}},
            self.sha,
            [{"name": "Linux", "conclusion": "success"}],
            workflow_conclusion="in_progress",
        )
        self.assertEqual(receipt["outcome"], "unknown")

    def test_revision_must_contain_exactly_forty_hex_characters(self):
        for revision in (self.sha + "\n", self.sha + " ", None, 1):
            with self.subTest(revision=revision):
                with self.assertRaises(ValueError):
                    self.module.normalize({}, revision)

    def test_boolean_is_not_a_completed_session_count(self):
        for sessions in (True, False):
            with self.subTest(sessions=sessions):
                receipt = self.module.normalize(
                    {"sessions": sessions, "safety": {"ok": True, "violations": []}},
                    self.sha,
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "unknown")
                self.assertEqual(receipt["evidence"][1]["result"], "unknown")

    def test_violation_evidence_overrides_a_successful_safety_summary(self):
        receipt = self.module.normalize(
            {"sessions": 1, "safety": {"ok": True, "violations": [{"type": "x"}]}},
            self.sha,
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "fail")
        self.assertEqual(receipt["evidence"][0]["result"], "fail")
        self.assertEqual(receipt["evidence"][0]["details"]["violations"], 1)
        self.assertEqual(receipt["invariants"][0]["result"], "fail")

    def test_incomplete_violation_list_cannot_establish_safety_pass(self):
        for safety in (
            {"ok": True},
            {"ok": True, "violations": None},
            {"ok": True, "violations": {}},
            {"ok": True, "violations": 0},
            {"ok": True, "violations": ""},
        ):
            with self.subTest(safety=safety):
                receipt = self.module.normalize(
                    {"sessions": 1, "safety": safety},
                    self.sha,
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "unknown")
                self.assertEqual(receipt["invariants"][0]["result"], "unknown")

    def test_invalid_counts_remain_unknown(self):
        for sessions in (0, -1, None, 1.0, "1", [], {}):
            with self.subTest(sessions=sessions):
                receipt = self.module.normalize(
                    {"sessions": sessions, "safety": {"ok": True, "violations": []}},
                    self.sha,
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "unknown")

    def test_explicit_safety_failure_survives_incomplete_details(self):
        for safety in ({"ok": False}, {"ok": False, "violations": []}):
            with self.subTest(safety=safety):
                receipt = self.module.normalize(
                    {"sessions": 1, "safety": safety},
                    self.sha,
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "fail")

    def test_violations_without_a_success_flag_still_fail(self):
        receipt = self.module.normalize(
            {"sessions": 1, "safety": {"violations": [{"type": "x"}]}},
            self.sha,
            workflow_conclusion="success",
        )
        self.assertEqual(receipt["outcome"], "fail")

    def test_generated_p6_report_preserves_invalid_measurements(self):
        # Generated by P6 bd52324e0e64ba78dc5b05e9b4819cc7ea183143,
        # with one valid and one backwards-clock session.
        path = os.path.join(
            os.path.dirname(__file__), "fixtures", "p6-mixed-invalid-report.json"
        )
        with open(path, encoding="utf-8") as stream:
            report = json.load(stream)
        self.assertEqual(report["sessions"], 1)
        self.assertTrue(report["safety"]["ok"])
        self.assertFalse(report["measurement"]["ok"])
        receipt = self.module.normalize(
            report, self.sha, workflow_conclusion="success"
        )
        self.assertEqual(receipt["outcome"], "unknown")
        self.assertEqual(receipt["evidence"][1]["result"], "unknown")
        self.assertEqual(receipt["evidence"][1]["details"]["sessions"], 1)

    def _measurement(self, **changes):
        measurement = {
            "ok": True,
            "invalid_records": [],
            "invalid_sessions": [],
            "incomplete_sessions": [],
            "duplicate_events": [],
        }
        measurement.update(changes)
        return measurement

    def _normalize_measurement(self, measurement, **kwargs):
        report = {
            "sessions": 1,
            "safety": {"ok": True, "violations": []},
            "measurement": measurement,
        }
        return self.module.normalize(report, self.sha, **kwargs)

    def test_complete_measurement_with_benign_duplicates_can_pass(self):
        for duplicates in ([], [{"session_id": "a", "event": "ux_bench_finish"}]):
            with self.subTest(duplicates=duplicates):
                receipt = self._normalize_measurement(
                    self._measurement(duplicate_events=duplicates),
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "pass")

    def test_ambiguous_measurement_stays_unknown(self):
        for measurement in (None, True, [], {}, {"ok": True}):
            with self.subTest(measurement=measurement):
                receipt = self._normalize_measurement(
                    measurement, workflow_conclusion="success"
                )
                self.assertEqual(receipt["outcome"], "unknown")

    def test_measurement_success_flag_must_be_true(self):
        for ok in (False, None, 1, "true"):
            with self.subTest(ok=ok):
                receipt = self._normalize_measurement(
                    self._measurement(ok=ok), workflow_conclusion="success"
                )
                self.assertEqual(receipt["outcome"], "unknown")

    def test_measurement_diagnostics_must_be_complete_lists(self):
        for field in (
            "invalid_records", "invalid_sessions", "incomplete_sessions",
            "duplicate_events",
        ):
            for value in (None, {}, "", 0):
                with self.subTest(field=field, value=value):
                    receipt = self._normalize_measurement(
                        self._measurement(**{field: value}),
                        workflow_conclusion="success",
                    )
                    self.assertEqual(receipt["outcome"], "unknown")
            with self.subTest(field=field, missing=True):
                measurement = self._measurement()
                del measurement[field]
                self.assertEqual(
                    self._normalize_measurement(measurement)["outcome"], "unknown"
                )

    def test_invalid_measurement_evidence_overrides_ok_true(self):
        for field in ("invalid_records", "invalid_sessions", "incomplete_sessions"):
            with self.subTest(field=field):
                receipt = self._normalize_measurement(
                    self._measurement(**{field: [{"reason": "fixture"}]}),
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "unknown")

    def test_measurement_unknown_cannot_hide_real_failures(self):
        measurement = self._measurement(ok=False)
        receipt = self._normalize_measurement(
            measurement, ci_jobs=[{"name": "Linux", "conclusion": "failure"}]
        )
        self.assertEqual(receipt["outcome"], "fail")
        receipt = self.module.normalize(
            {"sessions": 1, "measurement": measurement, "safety": {"ok": False}},
            self.sha,
        )
        self.assertEqual(receipt["outcome"], "fail")

    def test_requires_exact_revision(self):
        with self.assertRaises(ValueError):
            self.module.normalize({"sessions": 1}, "dev")


if __name__ == "__main__":
    unittest.main()
