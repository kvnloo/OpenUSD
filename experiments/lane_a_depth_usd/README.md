# Lane A — synthetic USD physics interchange gate

**Downstream-only experiment.** This is not an OpenUSD upstream fix or a real capture. Related evidence: [kvnloo/OpenUSD#49](https://github.com/kvnloo/OpenUSD/issues/49).

Runs three checks without touching production code:

1. Generate an 8×6 synthetic depth plane, 5 cm closed collider, authored camera, 1 kg sphere and Y-up gravity scene. Check structural invariants in Python.
2. Independently check the generated closed collider's manifold edges, outward winding, SI volume, and first-contact analytical distance; mutation controls separately reject a flipped triangle and incorrect slab thickness.
3. With **actual** `usd-core==26.8` Python bindings, parse the generated USDA; check `defaultPrim`, world transforms, camera aperture, USD Physics APIs, and composing the entire stage as an external reference. No simulated collision is asserted.

```bash
python -m pip install 'pytest==9.0.2' 'usd-core==26.8'
LANE_A_REQUIRE_PXR=1 python -m pytest -q experiments/lane_a_depth_usd/test_schema_gate.py
```

The gate is deliberately **strict** with `LANE_A_REQUIRE_PXR=1`: `pxr` import failure must fail, not skip. In a CPU-only offline sandbox without `pxr`, local results were `2 passed, 1 skipped`; strict mode was `2 passed, 1 failed` as intended. Do not report those as a parser pass.

The generated collider's 96 vertices match those in the separately verified v4 archive within 2e-12 m; both meshes are watertight with consistent winding and ~0.145833 m³ volume, though triangle connectivity differs. These checks are *independent geometry evidence*, not a parser pass.


This self-contained generator is a *source-level derivative*, not a byte-for-byte copy of the previously shared `LANE_A_depth_to_USD_fixture_v4.zip`. The earlier fixture's own `13 passed / 1 skipped` numerical tests were run separately. Their geometry and analytical contact target (0.428353 s) **do not** establish physics-engine fidelity.

No OpenUSD runtime, renderer, Newton, Isaac Sim, or Gazebo behavior is verified by this PR until a real CI job runs and returns concrete evidence. A green parse would establish scene-schema/reference composition only. Follow-up: import a parsed stage into an actual physics engine and measure first contact.

**Credit:** The depth-image versus XYZ reconstruction discrepancy was originally reported by AlessioLovato in [gazebosim/gz-sensors#614](https://github.com/gazebosim/gz-sensors/issues/614). The corresponding [gz-sensors#664](https://github.com/gazebosim/gz-sensors/pull/664) remains a separate review/CI question. The original Newton CPU observables report [#4612](https://github.com/newton-physics/newton/issues/4612) is by linusvwe, with RoboX2020 volunteering to implement it. This synthetic scene/parser gate is not attributed to either reporter.

## Physics metadata guard (Wave 09)

A real OpenUSD C++/WASM parser accepted all three **syntactically valid but semantically invalid** v4 scene mutations: a misspelled `PhysicsMeshCollisionAPI`, a `float` in place of `bool physics:collisionEnabled`, and an unsupported `physics:approximation = "convexHul"`. Stage parsing is therefore **not proof** that a physics engine will recognize the intended collider.

`physics_schema_preflight.py` narrowly validates this fixture's `CollisionSlab`, `DropSphere` and `PhysicsWorld` against `usd_physics_contract.json`, generated from the **actual** `lib/usd/usdPhysics/resources/usdPhysics/schema.usda` in BuildUSD run 36633495685, artifact 11065708454 (schema SHA256 `86e189bb4eeb853394faee3612ceccfae19e6e5327be0f89215f3fdb1a60df90`).

Local fork-equivalent test results: **6 passed, 1 skipped**, the skip being the required native Python `pxr` parser. Strict mode remains red on hosts without `pxr`; that is intentional, not evidence of parser success. A separate 7/7 verification included re-deriving the pinned contract from the actual archived BuildUSD schema. The guard is **not** a general USD validator, UsdPhysics API-introspection substitute, or physical contact result. The native `pxr` test and Newton/Isaac Sim import remain outstanding.
