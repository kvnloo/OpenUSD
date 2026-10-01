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

    def test_requires_exact_revision(self):
        with self.assertRaises(ValueError):
            self.module.normalize({"sessions": 1}, "dev")


if __name__ == "__main__":
    unittest.main()
