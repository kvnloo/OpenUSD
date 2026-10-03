# usdview Labs

Fork-local UX experiment surface for `usdview`.

## P0 — typed command palette

`Ctrl+K` opens a dependency-free command palette that fuzzy-searches
commands/prim paths and executes only whitelisted `UsdAction` values.

## P1 — measured intent + Jev shadow routing

Adds palette latency metrics, a small deterministic intent grammar, bounded
read-only context capture, and optional Jev `jev-1.13.0` **shadow-only**
routing.

Jev is disabled by default:

```bash
export USDVIEW_LABS_JEV_SHADOW=1
```

Model output is never executed in these experiments.

## P2 — local realtime-voice bridge

`Labs -> Start Voice Bridge` starts a loopback-only transcript endpoint.

The bridge:

- binds only to `127.0.0.1`;
- uses a fresh capability token;
- writes a private discovery file where supported;
- accepts transcript text only;
- bounds message size and queue depth;
- returns all usdview interaction to the Qt main thread;
- requires explicit **Accept / Reject** before mutable actions execute.

## P3 — interruption safety + read-only Q&A

Voice protocol v2 uses one monotonic generation per utterance:

```text
start -> partial* -> final
   \----------------> cancel
```

A socket-thread `GenerationGate` invalidates stale/cancelled generations.
The Accept button checks that gate again immediately before execution, so a
cancel that arrives after preview paint still blocks the action.

Read-only questions use a separate `UsdQuery` type with no mutation executor.

## P4 — composition inspector + hold-to-talk + dogfood harness

### Rich read-only inspection

P4 expands `UsdQuery` with bounded inspection of:

```text
what property is selected
what is the selected property value
where is this property authored
list properties on /World/Car
show composition for /World/Car
show variants on /World/Car
```

The property stack and prim stack are capped at 50 entries. Large displayed
values are truncated. Query results are displayed but not persisted in
receipts.

`where is this property authored` uses the selected property's
`GetPropertyStack()`. `show composition` uses the selected/path prim's
`GetPrimStack()`. This is deliberately descriptive evidence rather than a
claim that one layer explains every composed value.

### Hold-to-talk hotkey

The hotkey is opt-in:

```text
Labs -> Enable Hold-to-Talk Hotkey
```

Default binding:

```text
Ctrl+Shift+Space
```

Press/release semantics:

```text
key down    -> PTT start(generation)
key up      -> PTT stop(generation)
app loses focus while held -> PTT cancel(generation)
```

usdview still does **not** own microphone capture or ASR.

Instead, the stage manager creates:

```text
<usdview config>/usdview-labs/ptt-target.json
```

with:

```json
{
  "protocol": 1,
  "host": "127.0.0.1",
  "port": 12345,
  "token": "..."
}
```

Only `127.0.0.1` targets are accepted. PTT sends happen on a daemon worker so
the Qt event loop does not wait on the stage manager.

The intended duplex path is:

```text
Ctrl+Shift+Space
       |
       v
usdview PTT start/stop
       |
       v
local stage manager
  [owns mic + ASR]
       |
       | transcript + same generation
       v
usdview voice bridge
       |
       +----> read-only UsdQuery
       |
       +----> typed UsdAction -> explicit preview -> guarded Accept

Jev ------------------------------------------> shadow only
```

### P0–P4 dogfood harness

A stdlib-only harness emulates the external stage manager without owning a
microphone:

```bash
python extras/usd/examples/usdviewPlugins/usdviewLabs/tools/dogfood_usdview_labs.py \
  ptt-loop --transcript "what is selected"
```

Then in usdview:

```text
Labs -> Start Voice Bridge
Labs -> Enable Hold-to-Talk Hotkey
```

Hold and release `Ctrl+Shift+Space`. The harness receives the PTT lifecycle
and injects the canned transcript back through the real voice bridge using the
same generation.

For a mutable-path check:

```bash
python extras/usd/examples/usdviewPlugins/usdviewLabs/tools/dogfood_usdview_labs.py \
  ptt-loop --transcript "select /World/Car"
```

The action must still stop at the explicit preview.

Summarize receipts:

```bash
python extras/usd/examples/usdviewPlugins/usdviewLabs/tools/dogfood_usdview_labs.py \
  report
```

The report surfaces event counts plus p50/p95/max for the available latency
fields and counts stale/cancelled actions that were blocked.

## Receipts

Receipts live under:

```text
<usdview config>/usdview-labs/receipts.jsonl
```

They contain action/query outcomes, palette/voice/PTT latency, bridge lifecycle,
generation cancellation/stale-drop evidence, and Jev shadow metadata when
explicitly enabled.

Raw palette/voice text is not stored in experiment receipts.

## Loading

Add the parent `usdviewPlugins` directory to `PYTHONPATH` and this
`usdviewLabs` directory to `PXR_PLUGINPATH_NAME`, following
`docs/tut_usdview_plugin.rst`.

## Stop conditions

Do not promote or activate a candidate if it:

- adds visible startup cost;
- stalls the UI on large stages;
- binds voice/PTT outside loopback;
- lets an older/cancelled generation execute;
- accepts caller-supplied actions or code;
- owns microphone capture inside usdview;
- requires model/provider credentials merely to use usdview;
- makes model output observable as a USD mutation.

Provider-specific integrations stay downstream. Only generic UX primitives with
measured wins should be considered for upstream OpenUSD.
