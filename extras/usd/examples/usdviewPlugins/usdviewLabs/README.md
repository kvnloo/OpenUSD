# usdview Labs

Fork-local UX experiment surface for `usdview`.

## P0 experiment

`Ctrl+K` opens a dependency-free command palette. The initial build can:

- fuzzy-search commands;
- fuzzy-search prim paths without indexing the entire stage;
- select a prim through the public `UsdviewApi`;
- toggle viewer mode;
- clear selection;
- record append-only JSONL action receipts under `~/.usdview/usdview-labs/` (or the configured usdview directory).

All effects pass through a small typed `UsdAction` whitelist. There is no arbitrary Python execution path.

## Why the action layer exists

Future inputs such as Jev routing and realtime voice should **propose typed actions**, not emit Python or call Qt directly:

```text
Ctrl+K / transcript / agent intent
              |
              v
          UsdAction
              |
      deterministic executor
              |
          UsdviewApi
              |
            USD
              |
           receipt
```

`router.py` contains a side-effect-free shadow-router seam so a Jev adapter can be evaluated against deterministic routing before it is allowed to execute anything.

## Loading the experiment

Add the parent `usdviewPlugins` directory to `PYTHONPATH` and this `usdviewLabs` directory to `PXR_PLUGINPATH_NAME`, following `docs/tut_usdview_plugin.rst`.

## P0 acceptance criteria

- no external Python dependencies;
- palette implementation is deferred until the command is first invoked;
- `Ctrl+K` opens the palette;
- command filtering is immediate;
- prim search is debounced and bounded (5000 inspected / 40 matches);
- model/voice paths cannot execute arbitrary Python;
- every executed action produces a receipt, but receipt failures never break the action.

## Next experiments

1. Add latency markers for palette-open, first-result, execution, and viewport-update.
2. Add deterministic natural-language aliases and a Jev shadow adapter.
3. Record router agreement and suggestion acceptance before activating model routing.
4. Feed realtime voice transcripts into the exact same typed action interface.
5. Promote only generic, measured UX improvements upstream; keep model/provider integrations downstream.
