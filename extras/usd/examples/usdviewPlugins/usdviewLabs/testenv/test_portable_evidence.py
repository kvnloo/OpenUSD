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

    def test_requires_exact_revision(self):
        with self.assertRaises(ValueError):
            self.module.normalize({"sessions": 1}, "dev")


if __name__ == "__main__":
    unittest.main()
