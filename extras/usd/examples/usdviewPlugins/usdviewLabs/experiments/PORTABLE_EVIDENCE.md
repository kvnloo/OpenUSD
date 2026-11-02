# Portable OpenUSD evidence producer

Issue: https://github.com/kvnloo/OpenUSD/issues/17

The pure-stdlib adapter normalizes a P6 report and/or completed BuildUSD jobs into a
`z0.evidence.v0` receipt, without modifying native `receipts.jsonl`, execution,
plugins or CI. Contract: https://github.com/kvnloo/ace-digital-twin/pull/116.
Pass the exact 40-character Git revision. The adapter cannot independently
attest source provenance; retain the original run URL with the receipt.

## Verified historical BuildUSD fixture

`testenv/fixtures/buildusd-pr15-jobs.json` records the seven job conclusions
from https://github.com/kvnloo/OpenUSD/actions/runs/36633495685
at head `52546b361dd0d70ef8dda386138f026bd6ff8e5d` (PR #15).
Validation, Linux, macOS, Windows, and both Wasm jobs succeeded. GPUTests
was skipped and is optional on pull requests (push-only in buildusd.yml).
This is historical evidence, not a current-branch result.

From `extras/usd/examples/usdviewPlugins/usdviewLabs`:

```sh
python3 experiments/portable_evidence.py \
  --revision 52546b361dd0d70ef8dda386138f026bd6ff8e5d \
  --ci-jobs testenv/fixtures/buildusd-pr15-jobs.json \
  --workflow-conclusion success > /tmp/openusd-pr15.evidence.json
```

Add `--report /path/to/p6-report.json` when normalizing existing P6 output.
Native `stale_accept_blocked` or `stale_or_cancelled_final_dropped` counters
produce `abstain`, unless a concrete failure requires `fail`. Missing
required job results and unverified workflow status remain `unknown`.
Never combine report and CI results from different source revisions.

CTest registers `testUsdviewLabsPortableEvidence` when PXR_BUILD_TESTS and
PXR_ENABLE_PYTHON_SUPPORT are on. GitHub Actions: `BuildUSD`, whose
Linux/macOS/Windows jobs execute the project's headless CTest suites.
