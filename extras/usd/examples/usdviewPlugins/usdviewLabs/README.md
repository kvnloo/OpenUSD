# usdview Labs

Fork-local UX experiment surface for `usdview`.

## P0 — typed command palette

`Ctrl+K` opens a dependency-free command palette that can:

- fuzzy-search commands and prim paths;
- select prims through the public `UsdviewApi`;
- toggle viewer mode;
- clear selection;
- record append-only JSONL action receipts.

All effects pass through a small typed `UsdAction` whitelist. There is no arbitrary Python execution path.

## P1 — measured intent + Jev shadow routing

P1 adds:

- palette construction/open/first-paint/first-result latency metrics;
- a deliberately small deterministic natural-language grammar;
- bounded read-only usdview context capture;
- optional Jev `jev-1.13.0` **shadow-only** routing;
- asynchronous Jev evaluation so provider latency never blocks typing or viewport work;
- realtime-voice text ingress that proposes typed actions but does not execute them;
- hashed text identifiers in receipts instead of persisted raw palette queries/transcripts.

Examples:

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

### Jev shadow mode

Jev is disabled by default. No provider import, credential lookup, or network call occurs during usdview startup.

Opt in explicitly:

```bash
export USDVIEW_LABS_JEV_SHADOW=1
```

The adapter uses `jevkit.client`, `jevkit.keystore`, requested model `jev-1.13.0`, and captures the served model revision. The candidate action is compared with deterministic behavior and **never executed**.

## P2 — local realtime-voice bridge

P2 makes the voice seam usable by an external stage manager without giving that process direct USD access.

Start it from:

```text
Labs -> Start Voice Bridge
```

The bridge:

- binds only to `127.0.0.1`;
- chooses an ephemeral port by default;
- generates a fresh random capability token;
- writes discovery data to `<usdview config>/usdview-labs/voice-endpoint.json`;
- creates that endpoint file with mode `0600` where supported;
- accepts transcript text only — clients cannot submit `UsdAction` objects or Python;
- limits messages to 16 KiB and transcripts to 4096 characters;
- ignores non-final transcript messages;
- uses a bounded queue and drops stale backlog before current intent;
- moves socket work to a daemon thread;
- moves routing/UI work back to the Qt main thread;
- presents every proposed action in an explicit **Accept / Reject** dialog;
- executes nothing until the user presses **Accept**.

Jev remains shadow-only during this flow.

### Protocol

Read `voice-endpoint.json`:

```json
{
  "protocol": 1,
  "host": "127.0.0.1",
  "port": 12345,
  "token": "...",
  "pid": 1234
}
```

Then send one newline-delimited JSON object:

```json
{
  "token": "...",
  "transcript": "select /World/Car",
  "final": true,
  "utterance_id": "optional-id"
}
```

A small standard-library client is included:

```bash
python extras/usd/examples/usdviewPlugins/usdviewLabs/tools/send_voice_transcript.py \
  "select /World/Car"
```

An OMP/Hermes/z0 realtime voice stage manager can implement the same tiny protocol directly.

### Voice trust boundary

```text
microphone / ASR / stage manager
             |
             | transcript only
             v
     localhost token bridge
             |
             v
   deterministic intent router
             |
             +----------> Jev shadow receipt
             |
             v
       Action Preview
        /         \
     Reject      Accept
                   |
                   v
               UsdAction
                   |
                   v
               UsdviewApi
```

The socket thread never receives `UsdviewApi` and cannot mutate USD or Qt state.

## Receipts

Receipts live under:

```text
<usdview config>/usdview-labs/receipts.jsonl
```

They record action latency, palette timing, bounded prim-scan metrics, Jev agreement/provider metadata when enabled, bridge lifecycle, voice proposal acceptance/rejection, and action outcomes.

Raw palette query and voice transcript text is not persisted by these experiment receipts. A short SHA-256 fingerprint plus length is used where correlation is needed.

## Loading

Add the parent `usdviewPlugins` directory to `PYTHONPATH` and this `usdviewLabs` directory to `PXR_PLUGINPATH_NAME`, following `docs/tut_usdview_plugin.rst`.

## Stop conditions

Do not promote or activate a candidate if it:

- adds visible startup cost;
- stalls the UI on large stages;
- binds the voice bridge beyond loopback;
- bypasses token validation or typed actions;
- requires model/provider credentials merely to use usdview;
- makes a model decision observable as a USD mutation.

Provider-specific integrations stay downstream. Only generic UX primitives with measured wins should be considered for upstream OpenUSD.
