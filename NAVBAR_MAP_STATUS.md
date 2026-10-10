# V05 — layer navbar, larger desktop map and external legend

## Completed

- [x] Horizontal **Depth (m) / Arrival time (h) / Velocity (m/s)** selection bar, outside the map canvas. Native keyboard-accessible radios still drive the same callbacks/state.
- [x] Full-width desktop map: the former fixed inspector column is no longer reserved. At the checked 1672×941 viewport the map is **1452 px wide**, versus the earlier 1182 px. The toolbar/footer remain outside the canvas; map height still responds to screen height and visible scientific explanations.
- [x] Moved the existing dynamic legend/range into the bottom-right **page corner**, beside the timeline. No legend remains inside the Explore map element. Depth, arrival, velocity, extent, reached/unknown values and all original colours/ticks/notes are retained.
- [x] Scenario facts/metrics/metadata/Evidence remain in an expandable **Scenario details** panel; More controls retains reveal, extent and opacity. These two toolbar panels are mutually exclusive to prevent mobile overlap.
- [x] Fit remains in the toolbar; native map zoom/pan, time reveal/play/reset, original 114-hour H02 model window and minute conversion remain unchanged.
- [x] Responsive desktop/short-screen/tablet/mobile arrangement verified.
- [x] Read-only inspection of the two existing local terrain rasters; originals untouched.

All changes were made inside V05. No other project folder, data-access/publication rule, simulation output, database schema, solver, dependency or launch script was changed. No new scenarios, model jobs, imports, approvals, cloud services or authentication were introduced.

## Actual changes

| File | Work |
| --- | --- |
| `frontend/src/components/ExploreLayers.tsx` | Horizontal control presentation, toolbar Fit and mutually exclusive secondary disclosure. Same layer/reveal/extent/opacity/fit handlers. |
| `frontend/src/pages/Explore.tsx` | Moves controls outside the map, moves the scenario card into a toolbar disclosure and the original Legend into the page footer. Existing state, clock conversion and FloodMap props remain. |
| `frontend/src/studio.css` | Full-width map grid, navbar, drawer, external page-corner scale and responsive layout. |
| `frontend/src/components/layer-navigation.test.tsx` | Six new presentation/legend tests. |
| `frontend/dist/` | Rebuilt production frontend. |
| Startup/status docs, release ID, inventory/checksums | Current evidence and history distinguished. SSD package ID and existing profile identity retained. |
| `navigation_legend_evidence/` | Logs, source hashes, screenshots, preservation receipt and terrain inspection. |

The original `Legend.tsx`, `TimelinePanel.tsx`, map renderer, palette/timeline libraries, scientific data, backend/solver code and other pages' implementation are unchanged. The larger viewport can change the visible map framing; pixel-identical screenshots are not claimed.

## Fresh verification and limits

- Final TypeScript/Vite production build passed.
- **294 tests passed; 8 live-job tests intentionally not run** (302 total). Final source-bound report/logs: `navigation_legend_evidence/final/`. Tests cover original real-raster timeline/extent/comparison calculations, existing frontend/contract behavior and the new controls/legend presentation.
- The eight tests submit candidate/model jobs. They were not repeated against the user's active profile. Earlier 296-test fresh/native integration evidence in `layout_cleanup_evidence/` is recorded history, not fresh acceptance of this update. The backend/solver are unchanged; their full suite was not rerun.
- Browser checks used the user's already-running V05 instance on `127.0.0.1:5176`, without stopping/restarting it, initializing a profile or submitting jobs. Layer controls, opacity, extent/fit, actual clock values, playback stopping at the declared end, Reset, scenario/evidence disclosure and six download links were checked. Both Compare maps rendered; What-if and computed-run entry remain available. No captured console errors/warnings.
- Layout checked at 1672×941, 1280×592, 1024×720, 900×720 and 375×812. The colour scale is outside the map. Mobile uses natural vertical scrolling; no horizontal overflow was observed.
- Preservation receipt: **25,461 protected prior V05 files unchanged**, no protected mismatches; final frontend source hashes match passing tests. Original terrain/flood assets and simulation/clock/solver code remain identical.
- Physical SSD/another-device launch, every browser/screen/camera state and scientific accuracy are not claimed.

Actual screenshots: `navigation_legend_evidence/desktop-depth-navbar.jpg`, `desktop-navbar.jpg`, `short-navbar.jpg` and `mobile-navbar.jpg`. These are the working application, not the illustrative topographic reference.

## Terrain inspection — candidate for a separate contour-background step

Inspected files:

1. `part_a/inputs/terrain.tif`
2. `solver_inputs_v01/terrain/Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif`

They are **identical copies of one raster**, not two independent terrain datasets: SHA-256 `c439396123c0414c41be4f4abb73fbb630cb24dfaf5b0a37d9471f8694fb7687`.

- Single-band float32 GeoTIFF, 3565×1189 pixels.
- Georeferenced in **EPSG:32643**, matching H02; horizontal pixels approximately **29 m**. This does not change or improve the hydraulic mesh resolution.
- Raster bounds enclose H02's grid. The small read-only sample includes nodata, so bounding-box coverage must not be mistaken for valid terrain at every location.
- Nodata is -9999. GeoTIFF band elevation units are not tagged. Source licence/provenance and vertical datum remain unverified in inherited evidence; no scientific approval is inferred.
- Sample elevations were inspected only as a diagnostic; their extrema are not full-grid extrema or validated heights. See `TERRAIN_INSPECTION.json` for the exact metadata/sample counts.

The raster is a **technical candidate** for a local offline contour background. This request's terrain action was inspection only: **no contours were generated and the current map background was not changed**. A contour implementation should use a separate derived asset, confirm elevation-unit interpretation, respect nodata/coverage, retain uncertainty/source attribution and leave simulation outputs and the approved API untouched. The uploaded image cannot provide accurate georeferenced contour geometry and was not used as terrain data.

## View the changes

Refresh the already-running V05 page at **http://127.0.0.1:5176/**. A hard refresh may be needed for an older open tab. No restart is required to serve the rebuilt static frontend. Your matched launcher/stop scripts and profile ownership are unchanged; `START_COMPUTED.cmd` continues to use port 5178 if that launch mode is selected.

Earlier `LAYOUT_CLEANUP_STATUS.md`, `STUDIO_FRONTEND_STATUS.md` and their evidence folders remain history. Use this status file and `navigation_legend_evidence/final/` for the latest work.
