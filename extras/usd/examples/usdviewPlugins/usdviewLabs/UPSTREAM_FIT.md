# usdview Labs — upstream-fit decision record

Date: 2026-09-29

This is a fork-local decision record. It is not an upstream proposal.

## Current experiment stack

- P0 — typed command palette
- P1 — measured deterministic intent + Jev shadow
- P2 — authenticated loopback voice bridge + explicit preview
- P3 — generation cancellation + read-only queries
- P4 — richer composition/property inspection + PTT + dogfood
- P5 — Ctrl+K read-only query palette + context HUD
- P6 — receipt-backed stock/palette/voice benchmark
- Jev eval — 144 labeled routing cases

## Upstream-fit matrix

### 1. Composition/property provenance inspection — strongest fit

Existing OpenUSD issues repeatedly require users to understand where composed
behavior comes from:

- #2818 — request for layer-tree/dependency traversal
  https://github.com/PixarAnimationStudios/OpenUSD/issues/2818
- #2971 — nested specialize/reference composition behavior
  https://github.com/PixarAnimationStudios/OpenUSD/issues/2971
- #3072 — flattening mixed-TCPS arcs changes composed timing
  https://github.com/PixarAnimationStudios/OpenUSD/issues/3072
- #3201 — non-deterministic composition with nested instancing/inherits/specializes
  https://github.com/PixarAnimationStudios/OpenUSD/issues/3201

Labs P4/P5 already provide bounded read-only views of:

- selected property stack;
- prim stack;
- current composition/spec layer;
- variants;
- property values.

Potential upstream shape should be ordinary usdview inspection UX, not an agent
or natural-language feature.

Evidence gate before proposing:
- dogfood on real stages;
- compare time-to-answer against Composition/property panels and interpreter;
- confirm large stacks remain responsive;
- align with existing usdview panel conventions.

### 2. Performance diagnostics — relevant, but do not upstream HUD yet

Current issues show expensive update paths where interactive diagnosis matters:

- #3912 — hierarchical-reference transform updates; reporter also observed an
  usdview-specific "update vis column" taking over 2 seconds
  https://github.com/PixarAnimationStudios/OpenUSD/issues/3912
- #1607 — poor update performance for many instanceable prim edits
  https://github.com/PixarAnimationStudios/OpenUSD/issues/1607
- #1957 — nested variant-set selection becomes dramatically slower with scale
  https://github.com/PixarAnimationStudios/OpenUSD/issues/1957

The Labs HUD/receipts are useful for experiments, but there is not yet evidence
that the HUD itself belongs upstream.

Use P6 to ensure:
- idle HUD polling is negligible;
- palette/query instrumentation is not causing UI stalls;
- benchmarks can reproduce stock-vs-Labs differences.

A future upstream contribution should target a measured bottleneck or generic
diagnostic primitive, not a z0-specific telemetry layer.

### 3. Command palette / fuzzy prim discovery — keep downstream pending evidence

Search on 2026-09-29 found no clear open OpenUSD issue explicitly requesting a
usdview command palette, prim-tree fuzzy search, or prim-tree filter.

That does not mean the feature is bad; it means there is not enough upstream
demand evidence yet.

Do not post an RFC solely because Labs has an implementation.

Promotion gate:
- P6 shows meaningful reduction in time-to-result / steps for representative
  tasks;
- real usdview users prefer it during dogfood;
- implementation can be reduced to generic local command/search mechanics.

### 4. Context HUD — downstream until idle-cost + demand are demonstrated

The P5 HUD is intentionally bounded and model-free, but no direct upstream issue
was found requesting it.

Keep fork-local unless:
- idle cost is effectively zero in real runtime traces;
- recurring user workflows benefit beyond information already visible in
  usdview;
- the UI can fit existing usdview conventions without persistent clutter.

### 5. Attribute inspector UX — separate low-risk lane

#334 reports confusing numeric formatting in the usdview attribute inspector:
https://github.com/PixarAnimationStudios/OpenUSD/issues/334

This is more focused than the Labs architecture and could be investigated as an
independent low-risk contribution. Do not bundle it with palette/voice/Jev.

### 6. Voice / PTT / Jev — downstream experiments only

No upstream OpenUSD dependency should be introduced for:

- microphone capture;
- ASR;
- stage-manager transport;
- Jev / model providers;
- credentials;
- model-based mutation.

The useful architectural seam is the typed read-only/action boundary. Provider
integrations remain downstream.

## #3072 status

Issue:
https://github.com/PixarAnimationStudios/OpenUSD/issues/3072

Validated fork candidate:
https://github.com/kvnloo/OpenUSD/pull/2

Current candidate:
`ff98ef2e658dcdc51df045865d1b9b2042cf39f5`

It is based on the current upstream dev SHA used during validation and already
has executed regression evidence for references + payloads, nested TCPS,
authored offsets/scales, and cancellation-scale coverage.

The connected GitHub integration returned HTTP 403 when attempting to create
the upstream PR. That is a tooling permission boundary, not a known code issue.

Avoid another issue comment unless there is new evidence or a maintainer reply.

## Promotion order

1. Finish P0-P5 CI/runtime dogfood.
2. Fill P6 stock-vs-palette measurements.
3. Run the 144-case Jev eval; keep Jev shadow-only.
4. If provenance inspection wins measurably, extract the smallest generic
   composition/property UX primitive.
5. Discuss that primitive in the most relevant existing issue before opening a
   broad UX RFC.
6. Keep palette/HUD downstream unless their benchmark results independently
   justify upstream discussion.
7. Promote #3072 through a normal upstream PR when account/tool permissions
   permit it.
