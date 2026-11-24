#!/usr/bin/env python3
"""Normalize existing usdview Labs / BuildUSD evidence into z0.evidence.v0."""

import argparse
import json
import re
import sys


_SCHEMA = "z0.evidence.v0"
_SHA = re.compile(r"[0-9a-fA-F]{40}")


def _result(value):
    # A malformed GitHub conclusion is unknown, never a result or exception.
    if not isinstance(value, str):
        return "unknown"
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
    abstentions = {}

    # Workflows need not have a Labs report. An explicit incomplete report
    # still produces unknown evidence instead of being discarded.
    if report is not None:
        safety = report.get("safety") if isinstance(report, dict) else None
        violations = safety.get("violations") if isinstance(safety, dict) else None
        safety_result = "unknown"
        if isinstance(safety, dict):
            if safety.get("ok") is False or (isinstance(violations, list) and violations):
                safety_result = "fail"
            elif safety.get("ok") is True and isinstance(violations, list):
                safety_result = "pass"

            # Native ux_bench.audit_receipts() counters describe blocked or
            # dropped actions. They are safety abstentions, not executions.
            native_evidence = safety.get("evidence")
            if native_evidence is not None:
                if not isinstance(native_evidence, dict):
                    if safety_result == "pass":
                        safety_result = "unknown"
                else:
                    for key in (
                        "stale_accept_blocked",
                        "stale_or_cancelled_final_dropped",
                    ):
                        count = native_evidence.get(key, 0)
                        if type(count) is int and count > 0:
                            abstentions[key] = count
                        elif type(count) is not int or count < 0:
                            if safety_result == "pass":
                                safety_result = "unknown"

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
        if abstentions:
            evidence.append({
                "id": "labs-safety-abstention",
                "kind": "safety-decision",
                "result": "unknown",
                "details": abstentions,
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

    ci_requested = ci_jobs is not None or workflow_conclusion is not None
    if ci_requested:
        evidence.append({
            "id": "buildusd-workflow",
            "kind": "ci-workflow",
            "result": _result(workflow_conclusion),
            "details": {"name": "BuildUSD", "conclusion": workflow_conclusion},
        })

        if not isinstance(ci_jobs, list) or not ci_jobs:
            evidence.append({
                "id": "buildusd-job-list",
                "kind": "ci-job-list",
                "result": "unknown",
                "details": {"reason": "missing-or-invalid-jobs"},
            })
        else:
            required_job_count = 0
            for index, job in enumerate(ci_jobs):
                if not isinstance(job, dict):
                    evidence.append({
                        "id": f"buildusd-{index}",
                        "kind": "ci-job",
                        "result": "unknown",
                        "details": {"reason": "malformed-job", "required": True},
                    })
                    required_job_count += 1
                    continue

                required = job.get("required", True) is not False
                if required:
                    required_job_count += 1
                raw_name = job.get("name")
                name = raw_name if isinstance(raw_name, str) and raw_name else f"job-{index}"
                details = {
                    "name": name,
                    "conclusion": job.get("conclusion"),
                    "required": required,
                }
                if type(job.get("id")) is int:
                    details["job_id"] = job["id"]
                item = {
                    "id": f"buildusd-{index}",
                    "kind": "ci-job",
                    "result": _result(job.get("conclusion")),
                    "details": details,
                }
                if isinstance(job.get("html_url"), str) and job["html_url"]:
                    item["locator"] = job["html_url"]
                evidence.append(item)

            if required_job_count == 0:
                evidence.append({
                    "id": "buildusd-required-jobs",
                    "kind": "ci-job-list",
                    "result": "unknown",
                    "details": {"reason": "no-required-job-evidence"},
                })

    # Failures win over abstentions. Skipped optional jobs remain unknown items
    # but do not override a complete set of passing required observations.
    if any(item["result"] == "fail" for item in evidence):
        outcome = "fail"
    elif abstentions:
        outcome = "abstain"
    else:
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
        "subject": {
            "kind": "workflow" if report is None else "experiment",
            "id": "BuildUSD" if report is None else "usdview-labs-buildusd",
        },
        "outcome": outcome,
        "evidence": evidence,
        "invariants": invariants,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--ci-jobs")
    parser.add_argument("--workflow-conclusion")
    args = parser.parse_args()

    if not (args.report or args.ci_jobs or args.workflow_conclusion):
        parser.error("provide --report or BuildUSD workflow/job evidence")
    report = None
    if args.report:
        with open(args.report, "r", encoding="utf-8") as stream:
            report = json.load(stream)
    jobs = None
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
