#!/usr/bin/env python3
"""Normalize existing usdview Labs / BuildUSD evidence into z0.evidence.v0."""

import argparse
import json
import re
import sys


_SCHEMA = "z0.evidence.v0"
_SHA = re.compile(r"[0-9a-fA-F]{40}")


def _result(value):
    if value in {"success", "passed", "pass"}:
        return "pass"
    if value in {"failure", "failed", "cancelled", "timed_out", "action_required"}:
        return "fail"
    return "unknown"


def _measurement_complete(report):
    # Legacy P6 reports have no measurement diagnostics. When present, preserve
    # incomplete or invalid observations as unknown, even if some sessions ran.
    if not isinstance(report, dict) or "measurement" not in report:
        return True
    measurement = report["measurement"]
    if not isinstance(measurement, dict) or measurement.get("ok") is not True:
        return False
    invalid_fields = ("invalid_records", "invalid_sessions", "incomplete_sessions")
    for field in invalid_fields + ("duplicate_events",):
        if not isinstance(measurement.get(field), list):
            return False
    # Exact duplicate events are idempotent diagnostics, not invalid sessions.
    return not any(measurement[field] for field in invalid_fields)


def normalize(report, revision, ci_jobs=None, workflow_conclusion=None):
    if not isinstance(revision, str) or not _SHA.fullmatch(revision):
        raise ValueError("revision must be a full 40-character Git SHA")

    evidence = []
    invariants = []

    safety = report.get("safety") if isinstance(report, dict) else None
    violations = safety.get("violations") if isinstance(safety, dict) else None
    safety_result = "unknown"
    if isinstance(safety, dict):
        if safety.get("ok") is False or (isinstance(violations, list) and violations):
            safety_result = "fail"
        elif safety.get("ok") is True and isinstance(violations, list):
            safety_result = "pass"
    evidence.append({
        "id": "labs-safety",
        "kind": "usdview-labs-safety-audit",
        "result": safety_result,
        "details": {
            "violations": len(violations) if isinstance(violations, list) else None,
        },
    })
    invariants.append({
        "name": "labs-safety-audit",
        "result": safety_result,
        "evidence_refs": ["labs-safety"],
    })

    sessions = report.get("sessions") if isinstance(report, dict) else None
    session_result = (
        "pass"
        if (
            isinstance(sessions, int)
            and not isinstance(sessions, bool)
            and sessions > 0
            and _measurement_complete(report)
        )
        else "unknown"
    )
    evidence.append({
        "id": "ux-sessions",
        "kind": "ux-benchmark",
        "result": session_result,
        "details": {"sessions": sessions},
    })

    workflow_result = None
    if workflow_conclusion is not None:
        workflow_result = _result(workflow_conclusion)
        evidence.append({
            "id": "buildusd-workflow",
            "kind": "ci-workflow",
            "result": workflow_result,
            "details": {"name": "BuildUSD", "conclusion": workflow_conclusion},
        })

    for index, job in enumerate(ci_jobs or []):
        if not isinstance(job, dict):
            # Missing job details are required unknown evidence, not an absent job.
            job = {}
        name = str(job.get("name") or f"job-{index}")
        evidence.append({
            "id": f"buildusd-{index}",
            "kind": "ci-job",
            "result": _result(job.get("conclusion")),
            "details": {
                "name": name,
                "conclusion": job.get("conclusion"),
                "required": job.get("required", True) is not False,
            },
        })

    if any(item["result"] == "fail" for item in evidence):
        outcome = "fail"
    elif workflow_result == "fail":
        outcome = "fail"
    else:
        # Optional skipped jobs retain their unknown evidence items. Required
        # jobs must be complete even when the workflow summary claims success.
        required_results = [
            item["result"]
            for item in evidence
            if item["kind"] != "ci-job"
            or item.get("details", {}).get("required", True)
        ]
        outcome = (
            "pass"
            if required_results and all(result == "pass" for result in required_results)
            else "unknown"
        )

    return {
        "schema": _SCHEMA,
        "producer": {
            "name": "openusd",
            "repository": "kvnloo/OpenUSD",
            "revision": revision,
        },
        "subject": {"kind": "experiment", "id": "usdview-labs-buildusd"},
        "outcome": outcome,
        "evidence": evidence,
        "invariants": invariants,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--ci-jobs")
    parser.add_argument("--workflow-conclusion")
    args = parser.parse_args()

    with open(args.report, "r", encoding="utf-8") as stream:
        report = json.load(stream)
    jobs = []
    if args.ci_jobs:
        with open(args.ci_jobs, "r", encoding="utf-8") as stream:
            jobs = json.load(stream)
        if not isinstance(jobs, list):
            raise SystemExit("--ci-jobs must contain a JSON array")

    json.dump(
        normalize(
            report,
            args.revision,
            jobs,
            workflow_conclusion=args.workflow_conclusion,
        ),
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
