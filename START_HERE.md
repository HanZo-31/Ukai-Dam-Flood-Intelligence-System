# Ukai Simulation V05 — start here

## Current: Simulation naming and website polish

Use `VERIFY_COPY.cmd` → **`START_SIMULATION.cmd`** → http://127.0.0.1:5176/. Stop this profile with **`STOP_SIMULATION.cmd`**. These replace the former SSD-named launchers without changing the running profile, scenario IDs or ports. `START_COMPUTED.cmd` remains the optional separate 5178 profile; stop it with `STOP_COMPUTED.cmd`.

See [SIMULATION_POLISH_STATUS.md](SIMULATION_POLISH_STATUS.md) for the rename table, presentation changes and fresh evidence. Build/typecheck and **331 frontend tests passed**, including read-only HTTP checks against the four existing scenarios; **8 model/job tests were intentionally skipped**. **40 startup/ownership/integrity unit tests passed**. Desktop, narrow-mobile and short-laptop browser checks passed. No new integration, lookup/model jobs, simulations, imports or approval actions were submitted.

Only V05 was edited. The existing 2D rendering, colours, scientific data, timeline logic and API/solver implementation remain unchanged. Historical reports and private database/profile identifiers retain their original names/values for reproducibility and compatibility. The following sections are earlier records, not newer test results.

---

## Current: map-point inspection and selected-location comparison

See [POINT_INSPECTION_STATUS.md](POINT_INSPECTION_STATUS.md). In **Explore**, click the map, press Enter on the focused map, or use **Inspect location** to enter coordinates. Read original-cell depth, arrival and stored velocity, with explicit no-data/outside/error states. In **Compare**, select a point on either map to see both scenarios and eligible candidate-minus-baseline depth/relative-arrival differences. Velocity is displayed, not numerically subtracted without a harmonized definition.

Latest evidence: `point_inspection_evidence/final/` — production build and **326 passing tests**, including read-only HTTP checks against all four scenarios. Eight existing model/job tests were not repeated; their earlier results remain historical. No new simulations/imports/approvals were submitted. All source edits are inside V05; data/backend/solver/publication gates and installed dependency versions remain unchanged.

The verification instance has been stopped. Run `VERIFY_COPY.cmd`, then the existing V05 launcher: `START_COMPUTED.cmd` uses 5178; the legacy combined launcher uses 5176. Use the matched stop script when finished. The earlier sections below retain history.

The contour background is **not implemented in this V05 copy**. Terrain inspection remains available in `navigation_legend_evidence/TERRAIN_INSPECTION.json`; a claim that it was completed elsewhere is not verified here.

---

## Earlier navbar/legend record

## Current: horizontal layer bar, larger map and external page legend

See [NAVBAR_MAP_STATUS.md](NAVBAR_MAP_STATUS.md) for the latest in-place V05 update. Depth / Arrival time / Velocity now form a horizontal bar outside the map. The desktop map spans the full workspace width, with scenario details in an expandable toolbar panel. The unchanged layer legend/range is in the bottom-right **page** corner, not over the canvas.

Fresh evidence is `navigation_legend_evidence/`: final production build, **294 passing tests and 8 intentionally unrun live-job tests**, browser checks and read-only terrain inspection. Previous 296-test live integration results below are historical, not fresh results for this UI update. The active V05 services/database were not restarted or modified; refresh the existing browser to load the rebuilt UI. Your current legacy launcher uses http://127.0.0.1:5176/; `START_COMPUTED.cmd` still uses 5178. Package/profile identity and launch scripts remain unchanged.

Local georeferenced terrain was found, but no contour background was generated or added. Read the terrain section in `NAVBAR_MAP_STATUS.md` for technical readiness and unknowns.

---

## Earlier cleanup record

## Current: in-place layout cleanup (2026-10-10)

V05 has been updated in place with smaller panels, secondary layer/timeline disclosures and a screen-height-aware map workspace. No other project folder was changed. Read [LAYOUT_CLEANUP_STATUS.md](LAYOUT_CLEANUP_STATUS.md) for the current changes, **296 passing frontend/live tests** and actual desktop/mobile screenshots in `layout_cleanup_evidence/`. The renderer, scientific rasters/palettes, timeline calculations and integrations remain unchanged. The existing package ID/startup profile is preserved.

Run **this folder's** `VERIFY_COPY.cmd`, then `START_COMPUTED.cmd`, and open http://127.0.0.1:5178/. If an existing instance is running, stop it normally with its matched stop script before restarting, then refresh the browser. Port 5191 was temporary verification only. Temporary private test databases/copies are not delivered.

The sections below and `reference_layout_evidence/` record the first V05 implementation, before this cleanup. Use `layout_cleanup_evidence/final/` for the latest source-bound test results.

---

## Original V05 implementation record

This is the complete V05 project copy. The light sidebar, floating layer controls, compact scenario card and bottom timeline follow the supplied visual reference. The existing 2D renderer, raster data, colour scales, scientific inputs, timeline calculations, backend and solver remain unchanged. The viewport layout has changed with permission; pixel-identical screenshots are not claimed. The header's simulation badge remains removed, while scientific uncertainty remains in scenario details and Evidence.

Read [STUDIO_FRONTEND_STATUS.md](STUDIO_FRONTEND_STATUS.md) for the exact changes, fresh checks and limits. Run `VERIFY_COPY.cmd`, then **this folder's** `START_COMPUTED.cmd`; open http://127.0.0.1:5178/. Stop using **this folder's** `STOP_COMPUTED.cmd`. Stop any older instance first: the launcher refuses occupied ports rather than killing another copy. The temporary browser-check port 5180 is not the normal launch port. No dependency installation is needed.

Fresh V05 frontend evidence and actual screenshots are under `reference_layout_evidence/`. The final production build and all 289 frontend tests passed. These checks used the unchanged backend's existing isolated test profile, not a freshly initialized V05 profile. Receiving-device/physical SSD startup has not been repeated for V05. Read [START_COMPUTED_HERE.md](START_COMPUTED_HERE.md) for the underlying computed-run behavior and scientific limits.

All older reports below are retained history, not new V05 acceptance. In particular, `ui_refresh_evidence/` and `UI_REFRESH_STATUS.md` describe V04; `computed_integration_evidence/` describes V03.

---

## Historical V04 instructions

This is the new light frontend, based on concepts 1 and 3. The existing 2D simulation, assets, layer controls, legend, timeline and backend remain unchanged. Only the badge beside API status was removed; scientific uncertainty is still visible in scenario details and Evidence.

Read [UI_REFRESH_STATUS.md](UI_REFRESH_STATUS.md) for changes and verification. Run `VERIFY_COPY.cmd`, then **this folder's** `START_COMPUTED.cmd`; open http://127.0.0.1:5178/. Stop using **this folder's** `STOP_COMPUTED.cmd`. Stop any older instance first: the launcher refuses occupied ports rather than killing another copy. The temporary UI-check port 5180 is not the normal launch port. No dependency installation is needed.

Read [START_COMPUTED_HERE.md](START_COMPUTED_HERE.md) for existing computed-run behavior and scientific limits. Evidence in `ui_refresh_evidence/` is fresh V04 frontend verification. `COMPUTED_INTEGRATION_STATUS.md` and other older reports below are historical V03/V02 evidence, not new V04 hydraulic validation.

---

## Historical V02 instructions

This copy includes both deliveries plus V02 polish and the corrected extent projection. Read [POLISH_STATUS.md](POLISH_STATUS.md) and [START_INTEGRATION.md](START_INTEGRATION.md). Run `START_COMBINED.cmd` / `START_SIMULATION.cmd` and open **http://127.0.0.1:5176/**; stop using `STOP_COMBINED.cmd`. `INTEGRATION_STATUS.md` and the notes below retain earlier history, not V02 acceptance.

# Historical portable SSD copy

Use [START_HERE_SIMULATION.md](START_HERE_SIMULATION.md). Start with START_SIMULATION.cmd; this copy uses http://127.0.0.1:5174. The notes below are retained as original development history.

---

# Ukai combined project — actual status

**Backend integration: complete and rechecked.**

Working folder: `C:\Users\LENOVO\Documents\Codex\2026-10-07\files-mentioned-by-the-user-start\Ukai_Combined`

## Start it

1. Open this working folder in **Windows File Explorer** and double-click `START_UKAI.cmd`. Clicking its Codex file link only opens the script for viewing.
2. Wait for `READY: 4 scenarios verified`, then keep the server window open.
3. Your normal browser opens http://127.0.0.1:8765/docs automatically after the API responds. The in-app browser can be retried after the normal Windows launch.
4. Use `/api/v1/prototypes/scenarios` to list the four existing simulations.
5. Close the API window to stop the API. Use `STOP_DATABASE.cmd` to shut down its dedicated database.

The database and assets belong to this combined workspace. The Team A and Team B master folders were used as sources.

## Checked results

- [x] H01, H02, H03 and reconstructed 2006 imported into the actual PostgreSQL/PostGIS backend.
- [x] Details, layers, impact, assumptions, quality reports and downloads verified through HTTP for all four.
- [x] Drafts hidden from approved routes; removing local admission hides the preview resources.
- [x] Rasters pass COG, grid, unit, coverage-tag, finite-value and checksum checks.
- [x] Arrival rasters retain original valid cells, use the coordinate window and convert hours to minutes.
- [x] Outlines rebuilt at full precision from pixel edges and independently compared with depth greater than 0.1 m.
- [x] Final receipt hashes independently rechecked.
- [x] Copied original scenario files still match Team A master files.
- [x] Final regression: 887 passed, 4 skipped, 1 warning in 224.67s (0:03:44).
- [x] Team B correctness lint and gradual typing gate pass; 48 source files checked.

## What changed to connect the teams

- Local draft contract `1.1.0-local-draft` preserves an unknown producing-run timestamp with an explicit reason. It cannot be approved. The original strict V1 publication requirements remain enforced.
- Input licence text says UNKNOWN and asserts no permission. Dataset versions identify actual file bytes by checksum.
- Model-clock coverage uses a declared nominal UTC index. This does not establish an actual historical timezone or producing-run UTC time.
- The reconstructed 2006 draft carries no fabricated observed-event catalog entry. Its context explains the unverified source and interpolation.
- Windows file publication uses an atomic fallback when hard links are denied; concurrent creation and immutable-file checks are covered.
- The dedicated database returns aware timestamps in UTC to match the API contract. This preserves instants.
- Python 3.12/3.13 compatibility is supported for the local launch and quality checks. Runtime dependency versions remain pinned.
- Backup/restore supports the explicit portable PostgreSQL tools as well as the existing Docker adapter.

## Remaining project work

- [ ] Build and connect the frontend. This source drop has the backend and API explorer, with no finished frontend.
- [ ] Add observation-based calibration/validation if scientifically validated prediction is required.
- [ ] Resolve terrain/licence/vertical-datum and historical-time provenance for strict scientific publication.
- [ ] Add exposure inputs and calculations if population/building/road impacts are required. Missing values stay null.

Existing fast-solver evaluation remains separate. Integration did not run a simulation, train an ML model or establish forecast accuracy.

## Evidence and repeat check

Current evidence index: `evidence/latest-run.json`; checked completion record: `evidence/COMPLETION.json`.
Individual failed earlier attempts remain as audit history. Use the current index to select the final evidence.
H02’s preserved preparation report records the earlier strict-contract blockers. The final import/HTTP reports establish current local draft integration; scientific approval remains pending.
Close the running API before double-clicking `RUN_FULL_RECHECK.cmd`. It rechecks the receipts, verifies existing IDs without overwriting them, probes all routes and reruns tests.

## SSD sharing

The `part_a` and `receipts` folders are portable, self-contained file deliveries. Keep the combined runtime/database at its current path on this laptop.
For another device, use the source and receipts with a new local Python environment and database import. Copying a live database directory or this laptop’s Python environment is not a verified migration.

No Git, CI, hosted service, authentication UI or output ZIP was used.
