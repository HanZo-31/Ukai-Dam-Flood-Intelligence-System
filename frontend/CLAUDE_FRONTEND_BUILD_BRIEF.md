# Claude work order — build the Ukai Flood Explorer frontend

## Your assignment

Build and finish a polished, working frontend for the existing local Ukai backend. Implement the app, connect real data, inspect it in a browser, fix failures, and perform a second review before reporting completion. Do not stop after a plan, a scaffold, or a static mockup. Make routine design and implementation decisions yourself. Ask only for an actual missing folder, denied permission, or information that cannot be represented honestly as unknown.

This is a frontend task. Backend integration of H01, H02, H03, and reconstructed 2006 is already complete. Do not restart the hydraulic work, run simulations, retrain anything, or change scientific output files.

**Execution mode:** Prefer a local Claude coding session with this project folder open. Ordinary browser-only chat cannot read a Windows folder or verify this laptop's localhost API. If you only have the attached brief/image and no local tools, still provide the complete frontend source files and exact local commands from the supplied contract; explicitly mark real API/browser checks as not performed. Do not pretend folder access, stop with a speculative inspection report, or use unrelated files as substitutes.

**Project root on the combined laptop:**

```text
C:\Users\LENOVO\Documents\Codex\2026-10-07\files-mentioned-by-the-user-start\Ukai_Combined
```

**Write the frontend here:** `<project root>\frontend\`.

**Visual reference:** `frontend\design\UKAI_FRONTEND_CONCEPT.png`.

The frontend folder currently contains this brief and the design reference, not an implemented app. Preserve them. The PNG is a visual concept; its H02 numbers and geographic outline come from supplied project files. It is not a screenshot of a working frontend.

If working on another device, work inside that device's copied `Ukai_Combined\frontend` folder. Return frontend source, lockfile, instructions, and evidence through the SSD as plain files. `127.0.0.1` always refers to the machine running the browser/server; it cannot reach the other laptop. Cross-team acceptance uses the combined laptop. Do not search an unrelated D: drive, substitute an inaccessible backend, or claim real integration based on mock data.

## The product and visual direction

Name: **Ukai Flood Explorer**. A map-first application for inspecting and comparing four stored flood simulations.

Use the visual reference as a strong direction, with these improvements in the working app:

- A compact dark navy left sidebar, a light neutral workspace, rich blue flood layers, crisp typography, restrained amber evidence labels, and generous consistent spacing.
- Three working navigation sections: **Explore**, **Compare**, and **Evidence**. No decorative navigation or buttons without behaviour.
- A top bar with workspace name and actual API connection status. A compact visible **Uncalibrated simulation** label stays present.
- Four selectable scenarios in the sidebar. Show meaningful human names and the supplied peak-release values. Clearly distinguish **2006 · reconstructed historical** from the hypothetical scenarios.
- A compact row of relevant numeric summaries above a large map. Use peak release, flooded area, maximum depth, and arrival resolution. Every value comes from the API; missing values are visibly unavailable.
- A map occupying most of the working area, with layer choices, a readable legend, opacity control, fit-to-scenario, pan/zoom, scale, and a loading/error state.
- A compact right-side evidence inspector; on smaller screens it becomes a drawer or a section below the map.
- Typography: a locally available system font stack including Segoe UI. Main text approximately 14–16 px; clear headings without a giant hero section. Use tabular numerals for measures. Icons must be locally bundled and consistently styled.

Suggested CSS tokens: navy `#12253A`, action blue `#1677EF`, background `#F4F7FB`, main text `#172B42`, secondary text `#6B7C8F`, border `#E4EAF1`, amber background `#FFF1D7`. Maintain readable contrast and visible keyboard focus.

Make it look like a finished geographic analysis application. The real rendered map is the main feature. Avoid a landing page, a wall of cards, neon decoration, arbitrary charts, fabricated telemetry, and oversized promotional copy.

## Local technology and scope

Use **React + TypeScript + Vite**, **OpenLayers** for real GeoJSON/COG maps, and ordinary maintainable CSS. Use a small icon package if needed. Avoid a large component framework or another backend.

Node `24.13.0` and npm `11.6.2` were found on this laptop. Check the current executable and compatible dependencies; install project dependencies inside `frontend`, preserve a package lock, and do not upgrade global tools unnecessarily.

OpenLayers documents [GeoTIFF rendering and numeric styling](https://openlayers.org/en/latest/examples/cog-style.html) and [GeoTIFF reprojection](https://openlayers.org/en/latest/examples/geotiff-reprojection.html). Vite documents its [local development proxy](https://vite.dev/config/server-options#server-proxy). Use compatible installed versions and official examples rather than guessing raster APIs.

Everything runs locally. No Git, CI, hosting, accounts, paid map keys, or output ZIP. Bundle fonts/icons/scripts/styles through the app. No runtime CDN imports or mandatory internet calls. Dependency installation may use the internet; normal app use must work offline.

Read only the relevant source initially: `START_HERE.md`, `services\api\app\api\v1\prototypes.py`, `services\api\app\api_schemas\prototype.py`, and the three manifest/context examples in `part_a`/`receipts` if needed. Do not ingest the entire runtime, database, original datasets, or old audit history into context. Do not read or copy `runtime\database-url.txt`, database passwords, or private configuration into the frontend.

## Actual backend connection

The backend is `http://127.0.0.1:8765`. The user starts it from Windows File Explorer using the project-root `START_UKAI.cmd`, waits for **READY: 4 scenarios verified**, and keeps that server window open. Opening a command file in an AI editor does not execute it.

Run the frontend at `http://127.0.0.1:5173`, bound to `127.0.0.1`, with a strict port. Configure a same-origin `/api` proxy to `http://127.0.0.1:8765`, including the local build-preview configuration. Use relative URLs from the API for data and assets. Forward GET/HEAD and byte-range requests correctly. Avoid backend CORS changes and all database changes.

Available read-only routes:

| Purpose | Route |
| --- | --- |
| Basic service health | `GET /api/v1/health` |
| Scenario list | `GET /api/v1/prototypes/scenarios?limit=20&offset=0` |
| Scenario details | `GET /api/v1/prototypes/scenarios/{scenario_id}` |
| Map layers | `GET /api/v1/prototypes/scenarios/{scenario_id}/layers` |
| Impact summary | `GET /api/v1/prototypes/scenarios/{scenario_id}/impact` |
| Asset bytes | `GET`/`HEAD /api/v1/prototypes/scenarios/{scenario_id}/assets/{asset_type}` |
| Assumptions/context | `GET`/`HEAD /api/v1/prototypes/scenarios/{scenario_id}/assumptions` |
| Quality report | `GET`/`HEAD /api/v1/prototypes/scenarios/{scenario_id}/quality-report` |

Use the **prototype namespace**. Approved-scenario routes correctly hide these four drafts. Do not add a `data_mode` query to prototype routes; these routes accept only their documented query parameters.

The list response contains `items` and `pagination`. Each item has `scenario_id`, `run_id`, `scenario_type`, and prototype/status labels. Detail contains `parameters`, `parameter_units`, `summary`, `engine`, `timing`, `arrival`, `datasets`, `limitations`, `assumptions`, `unavailable_reasons`, coverage, and links. Layer responses contain `layers`, whose items include `asset_type`, `format`, `crs`, `unit`, `nodata`, checksum, coverage, and a relative `url`.

Discover IDs from the API. These current IDs are for verification, not a substitute for discovery:

| Friendly label | Current scenario ID | Peak release |
| --- | --- | --- |
| H01 | `ukai-hyp-h01-release15000-combined-v1` | 15,000 m³/s |
| H02 | `ukai-hyp-h02-release20000-hr-int-v1` | 20,000 m³/s |
| H03 | `ukai-hyp-h03-release30000-combined-v1` | 30,000 m³/s |
| 2006 reconstruction | `ukai-2006-historical-combined-v1` | 25,648 m³/s |

For example, H02 currently reports flooded area `359.7` km² and maximum depth `38.06` m. Those are integration cross-checks, not constants to use instead of API responses.

## Explore: actual rendering requirements

All four core asset roles must work:

| Role | Content | Display unit |
| --- | --- | --- |
| `extent_geojson` | GeoJSON, EPSG:4326 | Flood outline; depth greater than 0.1 m |
| `max_depth_cog` | Single-band COG, EPSG:32643 | m |
| `max_velocity_cog` | Single-band COG, EPSG:32643 | m/s |
| `arrival_time_cog` | Single-band COG, EPSG:32643 | Hours in the UI, converted from stored minutes |

Rendering TIFFs is essential. Download buttons alone do not complete a depth, velocity, or arrival layer. Never turn a TIFF into a decorative picture with arbitrary map bounds.

Prefer a consistent EPSG:32643 map view initially, with the local projection definition registered as needed. Transform GeoJSON coordinates from EPSG:4326 into the actual map view. A suitable local definition is `+proj=utm +zone=43 +datum=WGS84 +units=m +no_defs`. Avoid runtime projection-lookup services. Any different map view must use verified reprojection, not coordinate guessing.

Use OpenLayers GeoTIFF sources and real band values with explicit numerical styling. Make nodata transparent using the supplied metadata/mask. Do not display nodata as zero or as safe land. Arrival is already in **minutes**; do not multiply it by 60 again. Displaying hours means dividing valid stored minutes by 60.

Use distinct, readable sequential palettes and labelled units. Keep the same scale for the same layer across scenarios, especially in comparison. Label clipping/upper-end saturation explicitly. Colour classes are display choices, not validated hazard categories. Keep extent boundaries legible without obscuring the raster.

Use a licensed existing local contextual basemap if actually available and readily usable. Do not invent river paths, settlements, roads, dam locations, or terrain. Do not download a massive map collection or depend on remote tiles. If local context is unavailable, use an honest labelled local raster/extent view with coordinates and scale; the screenshot's background grid is a design reference, not a geographic basemap.

Manage map lifecycle and event cleanup. Retain view appropriately during layer changes; fit on a newly selected scenario or explicit fit action. Abort/ignore stale requests when users switch scenarios quickly. Load the selected raster on demand rather than downloading all twelve rasters immediately.

## Compare and evidence

**Compare:** Show all four API-backed peak-release, flooded-area, and maximum-depth values in a clean comparison table and simple shared-scale bars. Provide a two-scenario map comparison with synchronized views and the same layer/legend. Clearly show which member is reconstructed historical. Describe differences as differences between stored model scenarios; do not infer causation from four cases.

**Evidence:** Make engine/version, source labels, dataset licence text, model-clock convention, calibration/validation state, limitations, unavailable products, run ID, and asset checksums inspectable. Provide working downloads for supplied assets, assumptions, and quality report. Present useful facts in plain language with an expandable technical section for IDs/checksums.

All outputs are uncalibrated, simulated drafts. `run_timestamp` may be null with `run_timestamp_unknown_reason`. Licence evidence is unknown. Coverage timestamps use a declared **nominal model-clock index**, not a verified historical UTC time. Arrival is relative to simulation start. Show these facts accurately; avoid converting nominal coverage into an operational event date.

The plan/result interval is 15 minutes, while map/arrival temporal resolution is 60 minutes. These are different fields. Population/building/road/facility exposure and several products are unavailable. Null means **Not available / Not calculated**, never zero. A successful download, import, or API call does not establish scientific validation. H02's preserved quality file contains earlier strict-contract blockers; treat it as a preparation snapshot, not a new backend outage.

Do not add live monitoring, future forecasts, an ML accuracy badge, evacuation advice, hazard recommendations, a dam-control interface, synthetic victims, or made-up confidence scores. Do not animate the maximum-depth raster as if it were a time series. A static arrival-cutoff view can be a later enhancement and must be labelled as arrival filtering.

## Execution checklist — complete in one sustained implementation

Check an item only after verifying it. Record concise evidence in `FRONTEND_STATUS.md`.

### 1. Inspect and connect

- [ ] Confirm this project root and the design reference exist; preserve existing files.
- [ ] Confirm Node/npm and the backend health/list endpoint; identify all four real scenarios.
- [ ] Record exact commands and an actionable error if the backend is stopped.
- [ ] Set up the frontend, compatible dependencies, package lock, and local proxy without editing backend contracts.

### 2. Build the complete interface

- [ ] Implement the navy sidebar, light workspace, clear typography, summaries, map and evidence inspector.
- [ ] Implement working Explore, Compare and Evidence navigation.
- [ ] Render each scenario's actual extent and fit the correct geographic view.
- [ ] Render actual depth, velocity and arrival COG values, with correct CRS, masks, units and legends.
- [ ] Confirm arrival conversion is minutes-to-hours for presentation only.
- [ ] Make scenario changes update every dependent panel and layer without stale data.
- [ ] Implement opacity, pan/zoom, fit, and practical loading/empty/error states.
- [ ] Implement the four-scenario comparison and two-map synchronized comparison.
- [ ] Implement evidence inspection and working stored-file downloads.
- [ ] Present all missing fields, uncertainty and prototype labels honestly.
- [ ] Make desktop and smaller-window layouts usable without overlap or horizontal overflow.
- [ ] Keep keyboard focus, accessible controls and text labels usable.

### 3. Verify, correct and recheck

- [ ] Run TypeScript checking and a production build; fix real failures.
- [ ] Add focused tests for actual failure risks: unavailable values, units/arrival conversion, stale requests and proxy/API errors. Do not inflate the suite with trivial implementation mirrors.
- [ ] Inspect the running app in a real browser; a build success is not a visual or integration check.
- [ ] Test all four scenarios and all three raster modes plus extent, at least once each.
- [ ] Confirm real raster alignment with extent, colour scales, transparent nodata and layer cleanup.
- [ ] Test comparisons, evidence panels and at least one actual download per asset role.
- [ ] Test backend-offline handling and reconnect/retry without resetting the database.
- [ ] After dependencies are installed, test ordinary use with internet unavailable: no remote scripts/fonts/map tiles are required.
- [ ] Check representative desktop and small-window layouts; fix clipped legends, unreadable text and obstructed map controls.
- [ ] After the last change, repeat the relevant tests/build and the main four-scenario browser journey once more.
- [ ] Mark failed/unperformed checks honestly, with exact reasons; never mark the frontend complete with blank/decorative raster modes.

### 4. Deliver and make it easy to launch

- [ ] Provide project-root `START_FRONTEND.cmd` that launches the local frontend from Windows File Explorer, checks API availability, prints its URL, and leaves an actionable message on failure.
- [ ] Support a local build-preview launch with the same API proxy and no backend changes.
- [ ] Write `FRONTEND_START_HERE.md`: setup once, start backend, start frontend, URLs, stop/restart, troubleshooting and SSD handoff files.
- [ ] Write `FRONTEND_STATUS.md` with completed checkboxes, real test/build/browser evidence, remaining limitations and any exact blockers.
- [ ] Save browser screenshots under `frontend\evidence\`; distinguish screenshots from the supplied design concept.
- [ ] Return the plain source folder and lockfile; no ZIP, deployment or Git operation.

## Work efficiently

Implement API selection and real map rendering first, then the polished shell, comparisons and evidence, then the final review. Reuse components and a small typed API client. Preserve the supplied design and make responsive implementation choices rather than copying fixed screenshot dimensions. Finish all core behaviour before adding cosmetic extras.

If a test fails, fix it and rerun the affected check. Do not repeatedly run the entire existing backend regression suite for frontend-only changes. Do not fill context with huge rasters, runtime internals, or old reports. A real environmental permission denial must be stated plainly; do not search random folders or fabricate a success.

Your final response must name the actual folder, working start command, verified URLs, what was implemented, what was tested, and any unfinished requirement. Produce the working frontend during this run.
