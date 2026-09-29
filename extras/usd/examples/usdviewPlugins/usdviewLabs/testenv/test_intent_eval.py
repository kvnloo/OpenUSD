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
    "intent_eval.py")


def _load():
    spec = importlib.util.spec_from_file_location(
        "usdview_labs_intent_eval",
        os.path.abspath(_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntentEvalTest(unittest.TestCase):
    def test_corpus_has_144_cases(self):
        module = _load()
        self.assertEqual(
            len(module.build_cases()),
            144)

    def test_deterministic_baseline_is_exact(self):
        module = _load()
        rows = [
            module.run_case(case)
            for case in module.build_cases()]
        self.assertTrue(all(
            row["deterministic_action_correct"] and
            row["deterministic_query_correct"]
            for row in rows))

    def test_negative_families_expect_no_action(self):
        module = _load()
        negatives = [
            case for case in module.build_cases()
            if case["family"] in {
                "read_only_query",
                "unsupported"}]
        self.assertTrue(negatives)
        self.assertTrue(all(
            case["expected_action"] is None
            for case in negatives))


if __name__ == "__main__":
    unittest.main()
