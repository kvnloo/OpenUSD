# usdview Labs UX benchmark

This is the evidence layer for deciding whether a UX primitive is worth
upstreaming.

The benchmark compares the same named task in three modes:

- `stock`: existing usdview panels/interpreter;
- `palette`: Ctrl+K deterministic command/query UX;
- `voice`: transcript/PTT path.

For each run, mark a start and finish:

```bash
SESSION=$(python experiments/ux_bench.py start \
  --workflow composition-stack --mode stock)

# perform the task

python experiments/ux_bench.py finish \
  --session-id "$SESSION" --success --steps 6
```

Repeat for palette and voice.

Then:

```bash
python experiments/ux_bench.py report
```

The report groups by workflow/mode and calculates success rate, time-to-result
p50/p95/max, and interaction-step p50/p95/max.

It also audits the same receipt stream for safety invariants including:

- Jev shadow output must never appear as an executed action;
- read-only query sources must never enter the action executor;
- voice bridge starts must remain loopback-only.

Use these results—not preference—to decide whether command palette, context HUD,
or inspection primitives are candidates for upstream discussion.

## Receipt validity and retries

The existing `sessions`, `summary`, and `safety` report fields remain. The
additional `measurement` field identifies excluded evidence, incomplete sessions,
and exact duplicate endpoints. A report exits with status 2 when either the
measurement validation or safety audit fails; valid independent sessions still
appear in the summary alongside the diagnostics.

Each measured session needs one unambiguous start and finish, in that order.
Exact copies of an endpoint are counted once and listed in `duplicate_events`.
Conflicting endpoints and reused session IDs are excluded with a reason in
`invalid_sessions`. A valid start without a finish is listed separately in
`incomplete_sessions`; it is not an observed success or failure. Malformed JSONL
records (including duplicate fields and non-finite numbers) and invalid session IDs appear in `invalid_records`.

`success` must be a JSON boolean. Steps must be a nonnegative integer. Both
wall-clock timestamps and their difference must be finite, and the finish cannot
precede the start. Invalid values are not coerced into successful, zero-step, or
zero-duration observations. These wall-clock measurements do not guarantee a
monotonic clock or account for clock adjustments; the report rejects backwards
intervals rather than claiming they took zero seconds.

Retrying the `finish` command sequentially with the same session, outcome, steps,
and note leaves the receipt file unchanged. Changing an already-finished outcome
is rejected. Concurrent finish commands are not an atomic transaction: if they
produce conflicting endpoints, the report exposes the ambiguity and excludes the
session. This validation uses CPU-only synthetic receipts; it establishes no
usdview/Qt/GPU timing or UX improvement.

Run the focused regression tests without importing USD or Qt:

```bash
python -m unittest discover -s testenv -p test_ux_bench.py -v
```
