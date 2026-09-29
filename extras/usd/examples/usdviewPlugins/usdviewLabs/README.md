# usdview Labs

Fork-local UX experiment surface for `usdview`.

## P0 — typed command palette

`Ctrl+K` opens a dependency-free command palette that can:

- fuzzy-search commands;
- fuzzy-search prim paths without indexing the entire stage;
- select a prim through the public `UsdviewApi`;
- toggle viewer mode;
- clear selection;
- record append-only JSONL action receipts.

All effects pass through a small typed `UsdAction` whitelist. There is no arbitrary Python execution path.

## P1 — measured intent routing

P1 adds:

- palette-open, first-paint, first-result, and bounded prim-search latency metrics;
- a deliberately small deterministic natural-language grammar;
- read-only bounded context capture;
- a Jev `jev-1.13.0` **shadow-only** adapter;
- asynchronous Jev evaluation so provider latency never blocks typing or viewport work;
- realtime-voice **text ingress** that proposes typed actions but does not execute them;
- hashed text identifiers in receipts instead of raw palette queries/transcripts.

Current deterministic aliases include:

```text
/World/Car
select /World/Car
focus /World/Car
clear selection
deselect all
viewer mode on
viewer mode off
```

Unknown language intentionally returns no action.

## Jev shadow mode

Jev is optional and disabled by default. No provider import, credential lookup, or network call occurs during usdview startup.

To opt in:

```bash
export USDVIEW_LABS_JEV_SHADOW=1
```

The adapter uses the same canonical pieces already used by `z0intelligence`:

- `jevkit.client`;
- `jevkit.keystore`;
- requested model `jev-1.13.0`;
- capture of the served revision.

Shadow output is **never executed**. It is compared with the deterministic/selected action and written as an experiment receipt containing agreement, latency, model/revision, probabilities, and usage metadata.

## Voice ingress

An external realtime voice system should supply an already-transcribed utterance:

```python
from usdviewLabs.voice import ingest_transcript

decision = ingest_transcript(usdviewApi, transcript)
```

`decision.action` is only a proposal. The voice module does not call the executor or mutate usdview.

This keeps the eventual architecture:

```text
Ctrl+K / voice transcript / agent intent
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

Jev ------------------------> shadow comparison only
```

## Receipts

Receipts live under `<usdview config>/usdview-labs/receipts.jsonl`.

P1 records:

- action execution latency;
- palette construction/open/first-paint time;
- query-to-first-results latency;
- bounded prim scan count and latency;
- Jev agreement/provider latency when explicitly enabled;
- voice ingress match/no-match.

Raw palette query and voice transcript text is not persisted by these P1 receipts. A short SHA-256 fingerprint plus length is used where correlation is needed.

## Loading

Add the parent `usdviewPlugins` directory to `PYTHONPATH` and this `usdviewLabs` directory to `PXR_PLUGINPATH_NAME`, following `docs/tut_usdview_plugin.rst`.

## Stop conditions

Do not promote a candidate if it:

- adds visible startup cost;
- stalls the UI on large stages;
- bypasses the typed action executor;
- requires model/provider credentials merely to use usdview;
- makes a model decision observable as a USD mutation.

Provider-specific integrations stay downstream. Only generic UX primitives with measured wins should be considered for upstream OpenUSD.
