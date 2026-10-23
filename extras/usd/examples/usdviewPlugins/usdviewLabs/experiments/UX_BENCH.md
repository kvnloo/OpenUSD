# usdview Labs UX benchmark

This is the evidence layer for deciding whether a UX primitive is worth
upstreaming.

The benchmark compares the same named task in three modes:

- `stock`: existing usdview panels/interpreter;
- `palette`: Ctrl+K deterministic command/query UX;
- `voice`: transcript/PTT path.

## 100-trial stock/palette pass

Generate a deterministic interleaved plan:

```bash
python experiments/ux_bench.py plan \
  --modes stock palette \
  --repeats 5 \
  --seed 0 \
  --output /tmp/usdview-ux-plan.json
```

With the ten checked-in workflows this produces exactly 100 trials. Each
workflow is paired across stock/palette within a repetition, while workflow and
mode order are shuffled to reduce order bias.

For each planned trial, mark a start and finish:

```bash
SESSION=$(python experiments/ux_bench.py start \
  --workflow composition-stack --mode stock)

# perform the task

python experiments/ux_bench.py finish \
  --session-id "$SESSION" --success --steps 6
```

Voice can be measured separately with the same start/finish protocol.

## Auxiliary probes

Record measurements that are not task sessions through the same receipt stream:

```bash
python experiments/ux_bench.py probe \
  --name hud-idle-frame-time \
  --value 0.12 --unit ms --mode palette

python experiments/ux_bench.py probe \
  --name search-5k-first-results \
  --value 1.8 --unit ms --mode palette \
  --workflow select-prim
```

Use repeated probes rather than one-off values. The report emits p50/p95/max for
each probe group.

## Report

```bash
python experiments/ux_bench.py report
```

The report includes:

- success rate and time-to-result p50/p95/max per workflow/mode;
- interaction-step p50/p95/max;
- per-workflow candidate-vs-stock deltas and ratios;
- auxiliary probe p50/p95/max;
- safety-audit results from the same receipt stream.

The safety audit includes these invariants:

- Jev shadow output must never appear as an executed action;
- read-only query sources must never enter the action executor;
- voice bridge starts must remain loopback-only.

Use these results—not preference—to decide whether command palette, context HUD,
or inspection primitives are candidates for upstream discussion.
