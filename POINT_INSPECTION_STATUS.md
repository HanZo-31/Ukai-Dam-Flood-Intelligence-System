# V05 — map-point inspection and comparison

## Completed scope

- [x] Explore: click a location, or focus the map and press Enter to inspect its centre.
- [x] Alternative coordinate entry in EPSG:32643 metres, with validation.
- [x] Original-resolution depth, arrival and stored maximum velocity values; no interpolation or overview sampling.
- [x] Explicit valid zero, **No data**, outside coverage, unavailable asset and error states. Unknown is never zero/dry/safe.
- [x] Projected coordinates and derived longitude/latitude, plus a separate selected-point vector marker.
- [x] Retry/clear controls; scenario remount clears the selection; canceled/stale requests cannot display as the current selection.
- [x] Timeline arrival state is derived from stored arrival minutes and elapsed hours. Depth/velocity stay full-run maxima, not animated time-varying levels.
- [x] Compare: select a location on either synchronized map or enter coordinates. Both scenarios read their own original cells at the same projected location.
- [x] Candidate-minus-baseline depth and relative-arrival differences only for valid, aligned original cells with compatible engine/arrival metadata. Swapping scenarios reverses the signed difference.
- [x] Velocity values are shown side by side; no velocity delta is invented without a harmonized definition. Missing/misaligned/incompatible inputs suppress differences.
- [x] Desktop, short laptop and 320-pixel mobile layouts checked. The comparison table scrolls internally, not the document.
- [x] Preservation checks, source-bound tests, read-only HTTP tests, browser evidence, documentation and final inventory/checksums.

All project edits are inside V05. No original flood/terrain file, raster palette, solver, database schema, API route/publication gate or launcher was changed. No new simulations, imports, approvals, ML training or external services were requested. The existing localhost profile was used for GET-only data checks; no private profile/database/credentials were copied into the deliverable.

## Where the code is

| Path | Implementation |
| --- | --- |
| `frontend/src/lib/pointInspection.ts` | Strict unit/CRS/grid validation; bounded range transport; first-image one-cell reads; no-data and compatible-difference semantics. |
| `frontend/src/hooks/usePointInspection.ts` | Cancellation, per-selection/scenario identity and stale-result suppression. |
| `frontend/src/components/PointInspector.tsx` | Accessible form/readout and shared comparison table, timing/uncertainty explanations, retry/clear. |
| `frontend/src/map/FloodMap.tsx` | Optional selection events, Enter-to-inspect and an isolated vector marker. Original raster/style/opacity/clock/fit blocks are unchanged. |
| `frontend/src/pages/Explore.tsx` | Optional inspection drawer; scenario-keyed selection; no change to existing clock/mode handlers. |
| `frontend/src/pages/Compare.tsx` | Shared selected coordinate and both readouts alongside the existing synchronized maps/difference tools. |
| `frontend/src/point-inspection.css`, `main.tsx` | Optional panel styling and responsive table/drawer layout. |
| `frontend/package.json`, `package-lock.json` | Declares the already-installed GeoTIFF version directly. **No package was installed and no installed version changed.** |
| `point_inspection_evidence/` | Before-change receipt, original-code snapshots, logs, range-transfer records, guards and actual screenshots. |

## Storage/resource safeguards

- Reads the first TIFF image at its original resolution with a one-pixel window. It never samples a displayed colour or resampled overview.
- Only existing local stored-raster API paths are allowed; external absolute URLs are reduced to the permitted same-origin path. Redirects, arbitrary schemes/paths and mismatched roles are rejected.
- Requires HTTP **206** and consistent Content-Range/body length. Whole-file fallback is disabled; unsupported range servers show a retryable error instead of downloading large assets.
- Each requested range is at most 1 MiB, total requested bytes at most 4 MiB per asset/selection, compressed/decompressed tile size is bounded, and reads have a 15-second cancellation deadline.
- Missing/nonfinite/nodata values and invalid negative metrics do not become zeros. Unsupported CRS, rotation/tiepoint/pixel interpretation, unit, band or nodata metadata is rejected rather than guessed.
- The original asset API controls visibility/integrity. The inspector does not claim to hash an entire file from a partial range read.
- Slider changes only update the displayed arrival state; they do not re-fetch selected-point data. The marker does not change raster opacity or the map view.

## Fresh verification

- Final TypeScript/Vite production build passed.
- **326 tests passed; 8 existing model/job tests skipped** (334 total, 34 test files passed). The eight were not rerun because this work does not change model execution and should not generate jobs in the current profile.
- Four real-raster tests compare all three metrics and nodata cells against small independent Rasterio 1×1-window expectations from each original scenario. Unit tests also cover zero, edges, outside coverage, invalid metadata/units, incompatible grids/origins, reversed signs and malformed/truncated/oversized HTTP responses.
- Five live **read-only** HTTP tests cover all four scenario assets and signed same-cell differences. Range request counts/transferred bytes are recorded under `final/range-http/`; no job/administrative requests are made. For example, H02's three inspected points transferred 1,597,104 bytes total across 18 bounded range requests, not whole raster downloads.
- Actual browser H02 cell: depth **11.34 m**, arrival **180 min / 3 h**, stored velocity **2.14 m/s**. H01/H02 comparison gives **+0.63 m** depth difference; swapping gives **−0.63 m**. Both have 3 h arrival at this cell; relative difference is 0 h.
- Browser map clicks/keyboard entry, real nodata, invalid/outside coordinates, rapid reselection, clear/retry, scenario reset and timeline semantics verified. At 0 elapsed h the inspected arrival is unreached; at 114 h it is reached; full-run depth remains 11.34 m.
- No captured browser console warnings/errors. Desktop/1280×592 and 320-pixel mobile checks pass; internal table/drawer scrolling remains available.
- The preservation guard compares against the pre-work V05 checksum receipt. It verifies unchanged protected assets/backend/solver and byte-identical original raster swap/style/opacity/timeline/fit and Explore clock/mode-handler blocks. Optional new selection/marker code is isolated.
- The startup guard initially rejected newly added unsealed files, as designed. Inventory/checksums were refreshed, **not bypassed**; the normal launcher subsequently verified the sealed copy and reached all four references. The verification instance was stopped afterward.

Final evidence: `point_inspection_evidence/final/report.json`, logs, `PRESERVATION.json`, `BROWSER_CHECKS.json`, `range-http/` records and screenshots `explore-point.jpg`, `compare-point.jpg`, `laptop-point.jpg`. Intermediate reports are diagnostic history, not final-source acceptance. Earlier frontend/native/backend reports elsewhere are recorded history.

## Current limitations / remaining project work

- **Contour background is not implemented in this V05 copy.** Its two local terrain files are identical technical candidates inspected earlier; unit/datum/provenance review and a separate derived contour implementation remain separate work. Completion in a different folder/device has not been verified here.
- The existing flood outputs remain simulated, uncalibrated and scientifically unvalidated. A precise cursor coordinate or original export cell does not establish survey accuracy or independent hydraulic resolution.
- Relative-arrival differences are elapsed-from-start differences, not synchronized calendar timing, live predictions, risk/exposure counts, evacuation guidance or an optimal release.
- No fresh full backend suite, physical SSD/another-device launch or every possible browser/screen/camera state is claimed. Existing backend/solver implementation is unchanged.
- ML readiness, actual calibration/observation validation, terrain licensing/datum resolution and other historically unresolved scientific work are not completed by this UI feature.

## Run / use

Run V05's `VERIFY_COPY.cmd`, then your matched launcher. `START_COMPUTED.cmd` uses **http://127.0.0.1:5178/**; the legacy combined launcher uses **5176**. In Explore choose **Inspect location** or click the map. In Compare click either map or enter a coordinate to read both scenarios. Stop with the matched stop script before disconnecting an SSD. Package/profile identity and localhost-only behavior are preserved.
