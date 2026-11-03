# Wave 09 — a real USD parser does not enforce authored physics semantics

**Evidence:** 2026-10-12, four OpenUSD C++/WASM runs against the original v4 scene and single-field mutations. Outcome: **all four USDA stages opened** and exposed the same prim tree, despite three changes conflicting with the published USD Physics schema.

## Provenance

- Compiler/runtime: published `kvnloo/OpenUSD` BuildUSD success [36633495685](https://github.com/kvnloo/OpenUSD/actions/runs/36633495685), artifact `usd-Wasm64` **11065708454** (zip SHA256 `39f539d0a337a408456c395c6d79a03f646494bb5970559c59a98104bd7c5c26`).
- Parser binary: `wasmFetchResolver.wasm` SHA256 `4c891203705560b4f17b26077e040e6e3220206ffa73eb792c6322763e1cca35`.
- Node.js v22.16.0; the local-only synchronous-XHR shim from Wave 08 supplied fixture bytes. This uses the actual OpenUSD C++ stage parser, **not** a custom USDA parser.
- Fixture baseline `LANE_A_depth_to_USD_fixture_v4.zip/capture.usda` SHA256 `a2e19a191e60bd4b6daea6b88852912af478db21bd959f8f556f677f954c5266`.
- Independently retrieved the published `lib/usd/usdPhysics/resources/usdPhysics/schema.usda` from the **same binary archive**; SHA256 `86e189bb4eeb853394faee3612ceccfae19e6e5327be0f89215f3fdb1a60df90`.

## Actual C++ parser checks

| Fixture | One change from baseline | USD stage opened | Separate targeted schema guard |
| --- | --- | --- | --- |
| `capture.usda` | None | YES | PASS |
| `api_typo.usda` | `PhysicsMeshCollisionAPI` → `PhysicsMeshCollisonAPI` | YES | REJECT |
| `attribute_type.usda` | `bool physics:collisionEnabled` → `float physics:collisionEnabled` | YES | REJECT |
| `enum_typo.usda` | `"convexHull"` → `"convexHul"` | YES | REJECT |

The USD parser accepted each mutated layer; that is a **parser success**, not evidence that the authored collider remains discoverable to a physics engine. The narrow schema preflight derives the expected applied APIs, attribute value types, and permitted approximation tokens from the published schema. Offline exact-source checks: **6 passed, 1 `pxr` skipped** on the fork equivalent; a separate archive-backed consistency test suite passed **7/7**. All three candidate source files were read back with exact blob hashes after being staged in this draft. The strict native `pxr` gate remains unexecuted because the current sandbox has no Python USD bindings.

## Scope/next

The new fork-only guard is specific to the three authored physics prims and does **not** implement a general USD schema validator. The archived schema is independent of our generator, but text-based guarding cannot replace `UsdPhysics` API introspection. Next, run the strict `pxr` test, then import the scene into Newton or Isaac Sim and **measure** actual sphere contact. Existing Gazebo #664 and Newton #4488 blockers are separate.

The runnable replay script, 4 USDA fixtures, raw logs, pinned schema contract, and machine receipt live in the requesting ChatGPT session, **not inside this GitHub PR**. The 195 MiB BuildUSD artifact is referenced by its immutable run/artifact IDs instead of being copied. No upstream writes, default-branch merges, or maintainer notifications.

Credit: OpenUSD and BuildUSD contributors supplied the real parser/schema; AlessioLovato originally reported the Gazebo depth/XYZ issue; linusvwe reported Newton CPU observables, RoboX2020 implemented candidate #4641, and adenzler-nvidia requested a maintainer strategy pause on #4612.
