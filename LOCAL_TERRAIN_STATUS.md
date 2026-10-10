# Offline light terrain background — V05

Implemented 2026-10-10 (Asia/Kolkata). All project changes are inside this V05 folder.

## What changed

- Explore and both Compare maps now have a light local terrain backdrop beneath their existing flood layers.
- Subtle unlabelled source-derived contour-like isolines and relative terrain shading; no online tiles, API key, new dependencies, models or integrations.
- `Light terrain` checkbox returns to the original plain grid. The small `Local terrain · display only` disclosure explains limitations.
- Optional image-loading failure hides only the background; flood-layer state and retry handling remain separate.
- Original flood raster sources, scales, arrival expressions, timing, opacity, point inspection, selection marker and fit behavior are preserved.
- The coordinate footer now describes projected coordinates without the outdated “no basemap” claim.

## Source and limitations

Read-only input: `part_a/inputs/terrain.tif`, SHA-256 `c439396123c0414c41be4f4abb73fbb630cb24dfaf5b0a37d9471f8694fb7687`.

The supplied HEC-RAS-tagged terrain uses EPSG:32643 and covers only the local lower-Tapi footprint. Its nodata holes and outside coverage remain transparent over the original grid; blue background outside the terrain is not newly classified water. No roads, coastline, settlements or missing terrain have been invented.

Elevation units, vertical datum and source licence are not verified in the existing metadata. Therefore there are no labelled metre-elevation contours or terrain elevation readouts. The contour-like display edges use 10 source-value intervals on a smoothed half-resolution display derivative. Relative relief is normalized image-gradient shading, not scientifically scaled hillshade. It is contextual decoration, not flood depth, water elevation, calibration, approval or a validated topographic survey. Verify the source licence before distributing the derived terrain beyond the existing private/local project.

## Files

| File | Purpose |
| --- | --- |
| `scripts/build_local_terrain.py` | Reproducible local derivative builder with source-hash gate; reads input only |
| `frontend/src/map/terrain/light-terrain.png` | 1783 × 595 RGBA backdrop, about 306 kB; transparent nodata |
| `frontend/src/map/terrain/provenance.json` | Source/output hashes, coverage, CRS, processing and limitations |
| `frontend/src/map/terrain/extent.ts` | Generated exact projected extent used to position the image |
| `frontend/src/map/localTerrain.ts` | Independent background layer below flood data |
| `frontend/src/map/local-terrain.css` | Compact toggle/disclosure styles |
| `frontend/src/map/FloodMap.tsx` | Background setup, visibility and disclosure only; original flood implementation retained |
| `frontend/src/pages/Explore.tsx` | Coordinate-footer text correction only |
| `frontend/src/map/localTerrain.test.ts` | Three layer/projection/failure/metadata tests |
| `tests/test_local_terrain.py` | Five generation, PNG, original-file and flood-code preservation tests |
| `simulation_polish_evidence/tools/verify_terrain.py` | Pre-change package comparison with narrow permitted edits |
| `simulation_polish_evidence/tools/terrain_checks.py` | Unit/lint evidence recorder |

Production `frontend/dist`, `FILE_INVENTORY.csv` and `SIMULATION_CHECKSUMS.sha256` are rebuilt/refreshed. Existing data, solver, API, database configuration and historical evidence are not edited.

## Fresh verification

- Build and TypeScript checks passed.
- **334 frontend tests passed; 8 existing candidate/model-job live checks skipped.** Includes read-only HTTP point inspection of all four stored scenarios and signed comparison values. Evidence: `simulation_polish_evidence/terrain-http/`.
- **Five terrain unit/regression checks passed**, including real source hash/extent, PNG alpha mask and pixel encoding, and byte-identical original flood swap/timing/opacity/marker/fit code. Evidence: `simulation_polish_evidence/terrain-checks/`.
- Correctness lint passed on new Python files using the already bundled quality runtime; no tools installed.
- Browser: all four scenario selections, depth/arrival/velocity controls, original H01 0–114-hour slider/end/reset, historical model window, fit control, terrain off/on, visible terrain and both Compare maps verified. Narrow Explore/disclosure and Compare checked at 320 × 720; desktop checked at 1280 × 720. No horizontal document overflow observed; both narrow Compare maps reached ready.
- Optional background failure callback is unit-tested; an actual failed-image browser/network fault was not injected.
- Preserved-file hashes and startup integrity checks are recorded in `simulation_polish_evidence/TERRAIN_PRESERVATION.json`; final package is resealed without bypassing verification.
- Browser evidence: `simulation_polish_evidence/TERRAIN_BROWSER_CHECKS.json` and `terrain-desktop.png`.

Initial build problems were test-harness issues, not a relaxed gate: a direct Node filesystem test import needed unavailable type declarations and was replaced with Vite's raw metadata import; sandboxed Vite could not resolve the source path, so the same bundled build was rerun with scoped filesystem access. Logs retained in `terrain-initial/` and `terrain-build/`. A direct lint attempt used the wrong Python runtime; successful lint uses the existing `runtime/quality/python.exe`.

No full backend suite, new model run, import, approval, scientific validation, external network/offline-browser emulation, physical SSD or receiving-device rehearsal was performed in this display-only task. No public deployment or external map service was added.

## Run / reproduce

Normal startup remains `VERIFY_COPY.cmd` then `START_SIMULATION.cmd`; use `STOP_SIMULATION.cmd` to stop this profile. The verification runtime was stopped after testing.

To regenerate deliberately inside V05: `runtime\python\python.exe -B scripts\build_local_terrain.py`, rebuild/test the frontend, run the preservation check, then use `SEAL_WORKING_COPY.cmd`. Rebuilding or writing new evidence invalidates the previous seal until resealed. The source-hash gate must not be bypassed if a different terrain arrives; inspect it first.

Earlier completion reports describe their historical source states and counts. This document and the terrain-specific evidence describe the new background; previous “no contours/no basemap” reports are not retroactive proof for this release.
