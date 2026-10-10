# Integration V01 — working acceptance record

Status: both deliveries integrated; local engineering acceptance passed. Final operator/device sign-off is not complete. This is the stored-reference fallback, not the optional fresh-solver or ML path.

Team 1 ID `c346de1f86fa1d4bc657128d02c6ed1dfab0338a072ab6307eb30e4ad7e121cd`: 82 hashes, 11 baseline originals and both frozen contract files matched. Inventory is not checksum-listed; rows independently matched and received digest recorded.

Team 2 V05 ID `cc656f9987a43a545d90f8c7dd0691a71d48d58da7bb1f414002c4bcaa097fa8`: 74 hashes and source-bound recorded evidence verified. Baseline `2ccf20b727ac4588a7f3ac39ba68b9ca`: all 22,382 hashes matched before copying.

## Integration corrections

- Retain tested combined proxy/supervisor, not the proposed old-server patch.
- Root launch/stop scripts now use combined ports 5176/8767/8770/55434; dev reference proxy uses 8767.
- Add live HTTP adapter tests, explicitly skipped without a configured target.
- Enforce exact reference-resource URLs, valid job IDs, boolean cache flags and string warnings before rendering or following a response.
- Missing/corrupt real rasters now fail instead of silently passing tests.
- Clarify extent/zone wording: candidate-only wet footprint includes unmatched coverage, not proof that baseline nodata is dry. Numeric compare-v1/zone-rule-v1 counts retained.

## Fresh acceptance

- [x] Fresh bundled frontend typecheck and production build: passed (`frontend-v03`).
- [x] Full frontend test run with actual HTTP target: **131 passed, zero skipped/failed** (`frontend-live-v02`). Includes original 121 tests, three adapter-hardening guards and seven live-service tests. Frozen schema files, real raster counts and identity checks pass.
- [x] Combined backend regression: **985 passed, four skipped, one existing Starlette/HTTPX deprecation warning**, 107.92 seconds (`backend-regression-v01`). Skips are Windows-specific lock/descriptor checks, not silently counted as passes. Original approved-only publication/admission controls remain covered.
- [x] Separate owned cold initialization: four unchanged references imported; duplicate launch reuses children; candidate failure records explicit degradation while reference API stays usable; warm restart reuses imports and recovers saved jobs; all owned listeners close cleanly (`lifecycle-v01`).
- [x] All **24 real download resources**: full-file checksum, HEAD/ETag, exact Range, If-Range and invalid-range handling through the merged proxy pass (`resources-v01`); no reimports.
- [x] Real browser: all 16 scenario × map-layer combinations reached ready states with screenshots; sampled depth/arrival images visually inspected; no warnings/errors before the deliberate outage. Timeline 3-hour/180-minute keyboard scrub, final hour, play/pause/reset, maxima labels and scenario-switch reset checked.
- [x] Browser comparison: H01→H02 92,736 candidate-only wet-footprint cells / 77.99 km², 53/133 review zones; swapped signs/areas, same-scenario zero, arrival classes and zone unavailable reasons verified. Counts are independently covered by the raster tests.
- [x] Actual What-if browser: 20000 exact, 26000 rejected without nearest opt-in (last successful result retained), 26000→30000 with opt-in, 25000→20000 lower tie; open returned real scenario; out-of-range submission disabled; ML unavailable.
- [x] Browser candidate interruption: last result retained, Explore remains available, unavailable capability disables input. Full owned shutdown yields visible API-not-reachable and layer failure, not a misleading ready page (`browser-v01`).

Three click-to-observed stored lookup interactions were approximately 286 / 285 / 276 ms including browser-automation overhead; displayed service-only lookup time 0.021 / 0.023 / 0.020 s. These are not hydraulic runtime, browser-ready map latency, robust performance percentiles or an SLA.

Failed historical checks retained: `frontend-v01` wrapper console encoding failure after a successful build; `frontend-live-v01` had one test-only content-type assumption failure (download files were incorrectly required to be JSON metadata). The test was corrected; all 131 then passed. Backend scientific gates were not relaxed to make tests pass.

The final manifest is `SIMULATION_CHECKSUMS.sha256`; it covers the new source/build, input inventories and public evidence. `INTEGRATION_FILE_INVENTORY.csv` lists relative paths, sizes and SHA-256 values. Final sealing and warm-start receiver checks are recorded outside the immutable manifest in the companion verification report; do not edit files afterward without resealing and repeating affected checks.

## Operator/device gates

Physical network-disconnected run, receiving laptop, full keyboard/no-WebGL acceptance, two timed rehearsals and backup recording remain unverified until performed. No fresh solver results, extra scenarios, scientifically validated output or enabled ML are claimed.

- [ ] Physically disconnect networking and confirm a cold launch/judge journey on the actual demonstration device.
- [ ] Verify the receiving laptop (including its rendering/native runtime), if different from this computer.
- [ ] Complete a full keyboard-only/accessibility review and an actual no-WebGL fallback test. The checked keyboard slider is only partial accessibility evidence.
- [ ] Perform two operator-led 3–5 minute rehearsals, one from stopped state, and save a local backup video plus SSD copy. Browser smoke is not a rehearsal or recording.

These device/operator gates do not block the completed code merge, but they block claiming the entire 20-hour demonstration plan is signed off. Only four original scenarios exist. Optional solver generation / independently gated ML remain unavailable rather than invented or enabled.

Baseline and original deliveries were not edited. Private database state is not distributed. Historical reports remain as history; fresh evidence for this version is under `integration_evidence`.
