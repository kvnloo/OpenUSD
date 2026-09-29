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
