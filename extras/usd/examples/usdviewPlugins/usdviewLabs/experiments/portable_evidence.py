#!/usr/bin/env python3
"""Normalize existing usdview Labs / BuildUSD evidence into z0.evidence.v0."""

import argparse
import json
import re
import sys


_SCHEMA = "z0.evidence.v0"
_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


def _result(value):
    if value in {"success", "passed", "pass"}:
        return "pass"
    if value in {"failure", "failed", "cancelled", "timed_out", "action_required"}:
        return "fail"
    return "unknown"


def normalize(report, revision, ci_jobs=None):
    if not _SHA.match(revision):
        raise ValueError("revision must be a full 40-character Git SHA")

    evidence = []
    invariants = []

    safety = report.get("safety") if isinstance(report, dict) else None
    if isinstance(safety, dict) and isinstance(safety.get("ok"), bool):
        safety_result = "pass" if safety["ok"] else "fail"
    else:
        safety_result = "unknown"
    evidence.append({
        "id": "labs-safety",
        "kind": "usdview-labs-safety-audit",
        "result": safety_result,
        "details": {
            "violations": len(safety.get("violations", []))
            if isinstance(safety, dict) and isinstance(safety.get("violations"), list)
            else None,
        },
    })
    invariants.append({
        "name": "labs-safety-audit",
        "result": safety_result,
        "evidence_refs": ["labs-safety"],
    })

    sessions = report.get("sessions") if isinstance(report, dict) else None
    session_result = "pass" if isinstance(sessions, int) and sessions > 0 else "unknown"
    evidence.append({
        "id": "ux-sessions",
        "kind": "ux-benchmark",
        "result": session_result,
        "details": {"sessions": sessions},
    })

    for index, job in enumerate(ci_jobs or []):
        if not isinstance(job, dict):
            continue
        name = str(job.get("name") or f"job-{index}")
        evidence.append({
            "id": f"buildusd-{index}",
            "kind": "ci-job",
            "result": _result(job.get("conclusion")),
            "details": {"name": name, "conclusion": job.get("conclusion")},
        })

    results = [item["result"] for item in evidence]
    if "fail" in results:
        outcome = "fail"
    elif evidence and all(result == "pass" for result in results):
        outcome = "pass"
    else:
        outcome = "unknown"

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
    args = parser.parse_args()

    with open(args.report, "r", encoding="utf-8") as stream:
        report = json.load(stream)
    jobs = []
    if args.ci_jobs:
        with open(args.ci_jobs, "r", encoding="utf-8") as stream:
            jobs = json.load(stream)
        if not isinstance(jobs, list):
            raise SystemExit("--ci-jobs must contain a JSON array")

    json.dump(normalize(report, args.revision, jobs), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
