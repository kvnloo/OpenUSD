# Independent OpenUSD C++/WASM scene verification — 2026-10-12

**Evidence status:** parser/reference-composition PASS (6/6), physics **NOT RUN**. Fork-only experiment; not upstream promotion.

## Exact provenance

- Existing fork BuildUSD run: [36633495685](https://github.com/kvnloo/OpenUSD/actions/runs/36633495685), associated with fork #15 at `52546b361dd0d70ef8dda386138f026bd6ff8e5d`.
- Binary: `usd-Wasm64` GitHub Actions artifact **11065708454**, archive SHA256 `39f539d0a337a408456c395c6d79a03f646494bb5970559c59a98104bd7c5c26`.
- OpenUSD C++ `wasmFetchResolver.wasm`: SHA256 `4c891203705560b4f17b26077e040e6e3220206ffa73eb792c6322763e1cca35`.
- Harness: Node **v22.16.0**, Emscripten WebAssembly build, local-only synchronous XHR shim exposing an explicit USDA fixture directory, no remote HTTP.
- Original input: `LANE_A_depth_to_USD_fixture_v4.zip`'s `capture.usda` (not included in this GitHub change).
- Derived input: generator from the initial PR #50 source; later #50 commits add tests but do not modify `make_usda()`.
- Repro bundle (scripts + fixtures + logs + machine receipt, *without* binary): `LANE_A_wave_08_OpenUSD_WASM_validation.zip`; SHA256 `a193ac91bd017020a1f76ca7109aae155d4a40da16b8661e92faad2a99067b28`. Stored in the requesting ChatGPT session, **not uploaded to GitHub**.

## Six independently executed checks

| Fixture | Expected | Observed |
| --- | --- | --- |
| v4 original | USDA opens; `/World` owns camera, visual mesh, collision slab, sphere and physics scene | PASS |
| PR #50 derived | Same prim families load under `/World` | PASS |
| v4 reference | Referencing `defaultPrim=World` composes `Capture`, `DropSphere`, `PhysicsWorld` under `/Scene` | PASS |
| Derived reference | Same default-prim composition | PASS |
| Corrupt USDA | Actual C++ parser rejects malformed `def Sphere` syntax | PASS (negative control) |
| Reference without defaultPrim | Actual OpenUSD emits a composition warning; `/Scene` has no expected children | PASS (negative control) |

Parser output includes `Sensor`, `Reconstruction`, `CollisionSlab`, `DropSphere`, `PhysicsWorld`, and their authored properties. Failed-stage checks test the returned content, **not process exit code alone**, because the example can exit zero after printing `Unable to open url`.

## Reproduce without depending on fork CI admission

With access to the archived GitHub Actions binary:

```sh
gh api repos/kvnloo/OpenUSD/actions/artifacts/11065708454/zip > usd-Wasm64.zip
python validate_wasm_stage.py --artifact ./usd-Wasm64.zip --scenes ./scenes --out ./evidence-replay
```

Those Python/JS harness files and six control stages are in the ChatGPT bundle above, not this PR. The downloaded artifact supplies the *actual C++ USD parser*. No new production dependencies or parser source code.

## Deliberate limits and next gate

**This does not validate:** CPython `pxr` bindings for `usd-core==26.8`, semantics of `UsdPhysics` applied APIs, actual gravity/contact behavior, Gazebo Ogre/Ogre2 depth/XYZ equivalence, or real-world geometry. No `Newton` or `Isaac Sim` simulation executed.

Next: run the strict `pxr` test already present in PR #50; inspect staged `CollisionAPI`/`MeshCollisionAPI` and the resolved physics scene using the native Python API; then run one controlled sphere drop. Keep schema/physics result **LIMITED** until measured.

**Credit:** AlessioLovato reported Gazebo #614 depth/XYZ mismatch; linusvwe reported Newton #4612; RoboX2020 volunteered the CPU observables fix; OpenUSD contributors and BuildUSD maintainers produced the official parser binary. This verification did not modify or supersede their work.
