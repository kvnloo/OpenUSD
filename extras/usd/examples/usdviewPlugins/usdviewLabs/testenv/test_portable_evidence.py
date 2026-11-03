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

    def test_native_safety_abstentions_are_not_passes(self):
        for key in ("stale_accept_blocked", "stale_or_cancelled_final_dropped"):
            with self.subTest(key=key):
                receipt = self.module.normalize(
                    {
                        "sessions": 2,
                        "safety": {
                            "ok": True,
                            "violations": [],
                            "evidence": {key: 1},
                        },
                    },
                    self.sha,
                    [{"name": "Linux", "conclusion": "success"}],
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "abstain")
                self.assertEqual(receipt["invariants"][0]["result"], "pass")
                decisions = [
                    item for item in receipt["evidence"]
                    if item["id"] == "labs-safety-abstention"
                ]
                self.assertEqual(decisions[0]["result"], "unknown")
                self.assertEqual(decisions[0]["details"][key], 1)

    def test_real_safety_failure_dominates_abstention(self):
        receipt = self.module.normalize(
            {
                "sessions": 1,
                "safety": {
                    "ok": False,
                    "violations": [{"type": "jev_shadow_executed"}],
                    "evidence": {"stale_accept_blocked": 1},
                },
            },
            self.sha,
        )
        self.assertEqual(receipt["outcome"], "fail")

    def test_malformed_safety_counters_do_not_pass(self):
        for count in (True, -1, "2", [], None):
            with self.subTest(count=count):
                receipt = self.module.normalize(
                    {
                        "sessions": 1,
                        "safety": {
                            "ok": True,
                            "violations": [],
                            "evidence": {"stale_accept_blocked": count},
                        },
                    },
                    self.sha,
                )
                self.assertEqual(receipt["outcome"], "unknown")

    def test_missing_buildusd_job_list_is_unknown(self):
        report = {"sessions": 1, "safety": {"ok": True, "violations": []}}
        for jobs in (None, [], {"Linux": "success"}, "success"):
            with self.subTest(jobs=jobs):
                receipt = self.module.normalize(
                    report, self.sha, jobs, workflow_conclusion="success"
                )
                self.assertEqual(receipt["outcome"], "unknown")
                self.assertTrue(any(
                    item["id"] == "buildusd-job-list"
                    and item["result"] == "unknown"
                    for item in receipt["evidence"]
                ))

    def test_malformed_job_does_not_disappear(self):
        for malformed in (None, 1, "Linux", ["list"]):
            with self.subTest(malformed=malformed):
                receipt = self.module.normalize(
                    None, self.sha,
                    [{"name": "Windows", "conclusion": "success"}, malformed],
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "unknown")
                self.assertEqual(receipt["evidence"][-1]["result"], "unknown")

    def test_workflow_only_requires_conclusion_and_required_jobs(self):
        jobs = [
            {"name": "Linux", "conclusion": "success"},
            {"name": "GPUTests", "conclusion": "skipped", "required": False},
        ]
        successful = self.module.normalize(
            None, self.sha, jobs, workflow_conclusion="success"
        )
        self.assertEqual(successful["outcome"], "pass")
        self.assertEqual(successful["subject"], {"kind": "workflow", "id": "BuildUSD"})
        self.assertEqual(successful["evidence"][-1]["result"], "unknown")
        self.assertEqual(
            self.module.normalize(None, self.sha, jobs)["outcome"], "unknown"
        )
        optional_only = self.module.normalize(
            None, self.sha, [jobs[-1]], workflow_conclusion="success"
        )
        self.assertEqual(optional_only["outcome"], "unknown")

    def test_non_string_conclusion_is_unknown_not_exception(self):
        for value in ([], {}, 1, True):
            with self.subTest(value=value):
                receipt = self.module.normalize(
                    None, self.sha,
                    [{"name": "Linux", "conclusion": value}],
                    workflow_conclusion="success",
                )
                self.assertEqual(receipt["outcome"], "unknown")
                self.assertEqual(receipt["evidence"][-1]["result"], "unknown")

    def test_real_pr15_buildusd_jobs_normalize_without_labs(self):
        # Actual run: https://github.com/kvnloo/OpenUSD/actions/runs/36633495685
        path = os.path.join(
            os.path.dirname(__file__), "fixtures", "buildusd-pr15-jobs.json"
        )
        with open(path, encoding="utf-8") as stream:
            jobs = json.load(stream)
        revision = "52546b361dd0d70ef8dda386138f026bd6ff8e5d"
        receipt = self.module.normalize(
            None, revision, jobs, workflow_conclusion="success"
        )
        self.assertEqual(receipt["outcome"], "pass")
        self.assertEqual(receipt["producer"]["revision"], revision)
        self.assertEqual(len([
            item for item in receipt["evidence"] if item["kind"] == "ci-job"
        ]), 7)
        self.assertEqual(receipt["evidence"][-1]["result"], "unknown")
        self.assertEqual(receipt["evidence"][-1]["details"]["required"], False)
        self.assertEqual(receipt["evidence"][1]["details"]["job_id"], 109628280217)
        jobs[5]["conclusion"] = None
        self.assertEqual(
            self.module.normalize(
                None, revision, jobs, workflow_conclusion="success"
            )["outcome"], "unknown"
        )

    def test_workflow_only_cli_normalizes_real_fixture(self):
        import subprocess
        import sys
        path = os.path.join(
            os.path.dirname(__file__), "fixtures", "buildusd-pr15-jobs.json"
        )
        command = [
            sys.executable, os.path.abspath(_PATH),
            "--revision", "52546b361dd0d70ef8dda386138f026bd6ff8e5d",
            "--ci-jobs", path,
            "--workflow-conclusion", "success",
        ]
        process = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        self.assertEqual(json.loads(process.stdout)["outcome"], "pass")

    def test_requires_exact_revision(self):
        with self.assertRaises(ValueError):
            self.module.normalize({"sessions": 1}, "dev")


if __name__ == "__main__":
    unittest.main()
