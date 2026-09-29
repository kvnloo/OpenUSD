# usdview Labs

Fork-local UX experiment surface for `usdview`.

## P0 — typed command palette

`Ctrl+K` opens a dependency-free command palette that can fuzzy-search
commands/prim paths, select prims through `UsdviewApi`, toggle viewer mode,
clear selection, and emit append-only experiment receipts.

All effects pass through a small typed `UsdAction` whitelist. There is no
arbitrary Python execution path.

## P1 — measured intent + Jev shadow routing

P1 adds palette latency metrics, a deliberately small deterministic intent
grammar, bounded read-only context capture, and optional Jev
`jev-1.13.0` **shadow-only** routing.

Jev is disabled by default:

```bash
export USDVIEW_LABS_JEV_SHADOW=1
```

The adapter uses `jevkit.client` + `jevkit.keystore`, captures the served
model revision, runs off the UI thread, and never executes its proposed action.

## P2 — local realtime-voice bridge

Start from:

```text
Labs -> Start Voice Bridge
```

The bridge binds only to `127.0.0.1`, chooses an ephemeral port by default,
generates a fresh capability token, writes a mode-`0600` discovery file where
supported, accepts transcript text only, bounds message/queue size, and returns
all routing/UI work to the Qt main thread.

Every mutable action still requires an explicit **Accept / Reject** preview.

## P3 — push-to-talk lifecycle, interruption, and read-only Q&A

P3 upgrades the endpoint protocol to generation-aware lifecycle events:

```text
start -> partial* -> final
   \----------------> cancel
```

Each utterance carries a monotonically increasing `generation`.

The socket thread updates a thread-safe generation gate immediately on message
arrival. A preview's Accept button checks that gate again immediately before
execution. This means:

- a newer utterance invalidates every older preview;
- `cancel` wins over a later/replayed `start` or `final` from the same generation;
- stale generations are rejected before they reach Qt;
- a cancel arriving after preview paint but before Accept still blocks execution.

### Protocol v2

Read:

```text
<usdview config>/usdview-labs/voice-endpoint.json
```

Example lifecycle messages:

```json
{"token":"...","op":"start","generation":42}
{"token":"...","op":"partial","generation":42,"transcript":"select /World"}
{"token":"...","op":"final","generation":42,"transcript":"select /World/Car"}
```

Cancellation:

```json
{"token":"...","op":"cancel","generation":42}
```

Protocol-1 `final: true/false` transcript messages remain accepted for
compatibility, mapped to generation `0`.

The bundled client supports all four operations:

```bash
python extras/usd/examples/usdviewPlugins/usdviewLabs/tools/send_voice_transcript.py \
  --op final --generation 42 "select /World/Car"
```

An OMP/Hermes/z0 push-to-talk stage manager should allocate one generation when
PTT begins, reuse it for partial/final/cancel, then allocate a larger generation
for the next utterance.

### Read-only scene questions

Questions use a distinct `UsdQuery` type rather than `UsdAction`. The query
executor has no mutation path.

Current deterministic examples:

```text
what is selected
what frame am I on
what renderer
what file is this
what type is /World/Car
where is this authored
```

For `where is this authored`, P3 reports the selected Composition-tab
`Sdf.Spec` layer when available, otherwise the current composition layer. It
does **not** claim that a generic layer selection proves full value provenance.

Read-only answers display immediately. Mutable requests continue through the
explicit action-preview gate.

### Voice latency telemetry

P3 records:

- client-send -> preview/result paint when timestamps are sane;
- bridge-receive -> preview/result paint;
- preview paint -> Accept / Reject / Cancel;
- action execution latency (from prior slices);
- generation start/cancel/stale-drop events.

Raw query/transcript text is still not persisted in experiment receipts;
correlation uses a short SHA-256 fingerprint plus length.

## Trust boundary

```text
microphone / ASR / stage manager
             |
        transcript only
             |
     127.0.0.1 + token
             |
       GenerationGate
             |
       +-----+------+
       |            |
   UsdQuery     deterministic
  read-only       UsdAction
       |            |
    answer       Preview
                   / \
              Reject Accept
                       |
                    guard()
                       |
                   UsdviewApi

Jev ----------------> shadow comparison only
```

The socket thread never receives `UsdviewApi`.

## Receipts

Receipts live under:

```text
<usdview config>/usdview-labs/receipts.jsonl
```

They contain action/query outcomes, palette/voice latency, bridge lifecycle,
generation cancellation/stale-drop evidence, and Jev shadow metadata when
explicitly enabled.

## Loading

Add the parent `usdviewPlugins` directory to `PYTHONPATH` and this
`usdviewLabs` directory to `PXR_PLUGINPATH_NAME`, following
`docs/tut_usdview_plugin.rst`.

## Stop conditions

Do not promote or activate a candidate if it:

- adds visible startup cost;
- stalls the UI on large stages;
- binds the voice bridge beyond loopback;
- lets an older/cancelled generation execute;
- accepts caller-supplied actions/code;
- requires model/provider credentials merely to use usdview;
- makes a model decision observable as a USD mutation.

Provider-specific integrations stay downstream. Only generic UX primitives with
measured wins should be considered for upstream OpenUSD.
