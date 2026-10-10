# Ukai combined V05 — reference-layout frontend and existing computed candidates

**Latest work:** `POINT_INSPECTION_STATUS.md` documents original-cell map inspection and selected-location reference comparison. Production build plus 326 tests pass, including five read-only real-HTTP tests for the four scenarios and signed same-cell differences. Eight existing candidate/model job tests and the full backend suite were not repeated. No new simulations, imports or approvals were requested. The test instance was stopped; normal launcher ports/profile identity are unchanged. Contours remain absent in this copy.

**Latest UI update:** read `NAVBAR_MAP_STATUS.md` and `navigation_legend_evidence/`. Horizontal layer controls, full-width desktop map and an external page-corner legend are now implemented. The latest build and 294 non-mutating tests pass; eight live-job tests and the full backend suite were not repeated. Previous live/native results below remain historical. The active V05 instance was used for read-only browser checks without restarting it or submitting jobs. No contour background has been added; local terrain inspection is recorded separately. Launcher ports/profile identity are unchanged.

**Current in-place UI cleanup:** see `LAYOUT_CLEANUP_STATUS.md` and `layout_cleanup_evidence/`. The final build and all 296 frontend/live tests passed. The UI now fits available desktop height, with compact layer/card/timeline panels and expandable secondary controls. A fresh native run and subsequent cache regression were verified in an isolated test profile inside V05, not in your existing database. Scientific validation is not implied. The package ID, launcher ports and user-profile ownership rules are unchanged. Earlier V05 UI evidence below is historical relative to this cleanup.

This NEW V05 copy follows the approved reference layout, building on the sealed V04 light interface. The existing map renderer, original stylesheet, colour scales, timeline calculations, solver/backend and scientific inputs are unchanged. Only surrounding layout and control presentation have changed; the map viewport size can differ. See `STUDIO_FRONTEND_STATUS.md` for fresh V05 evidence. The underlying V03 integration combined the verified V02 app, Claude's frontend and BACKEND_DELIVERY_V02. Neither source delivery nor the four original references was modified. All execution is private on this trusted local computer, bound to 127.0.0.1; no application login, cloud or Git is required.

## Run and view the new work

1. Run `VERIFY_COPY.cmd` after receiving/copying this complete plain folder.
2. Run `START_COMPUTED.cmd`. Separate local profile and ports: web 5178, reference API 8786, candidate API 8778, database 55438. It never kills a different instance occupying a port.
3. Open http://127.0.0.1:5178/ -> **What-if** -> **Open the experimental computed run**.
4. Enter **25000** and choose **Run computation**. The first request on a new profile genuinely runs the supplied native solver. Repeating identical computational inputs may reuse checked results, explicitly labelled cache.
5. Read computed identity/products, depth/arrival/difference preview, H02 comparison and coordinate review zones. Explore/Compare/Evidence retain the original four HEC-RAS references.
6. Stop with `STOP_COMPUTED.cmd` or Ctrl+C in the launch window. Wait for `Stopped` before disconnecting the SSD. Legacy `START_COMBINED.cmd` uses earlier default ports; use this folder's matched computed START/STOP pair for V05. Stop any older running copy before starting V05.

No dependency install is needed: the complete portable runtime, original native x64 DLL and verified isolated dependencies are included. Do not copy an old live database, `.env`, passwords or another device's runtime profile.

## Included work and integration fixes

- Real compute-v2, bounded 15,000–30,000 m³/s in the fixed hypothetical forcing family. No nearest-scenario substitution in computed mode.
- Claude's strict capability/job/result/product adapter, abortable polling, checksum verification, canvas preview, comparison and 5 km coordinate-zone analysis.
- Integration fixes: absolute metric grid checks; actual derived-pixel size/native-resolution disclosure; explicit velocity definition; depth comparison without optional arrival; resumable product-download pause; prior result remains visible while a new one downloads.
- Original stored-reference selection and approved-only publication/visibility gates are preserved. Computed results are NOT imported or scientifically approved.

## Scientific limits

Experimental outputs are uncalibrated and not scientifically validated. Native resolution is approximately 100 m; approximately 29 m display pixels are derivatives, not finer hydraulic evidence. Arrival is native seconds converted once with `ceil(seconds/3600)*60` minutes. Velocity is a face-normal component, not velocity-vector magnitude; it is not subtracted from HEC-RAS velocity. H02 comparison changes both engine and release: it does not isolate release effects or demonstrate accuracy. Unknown coverage is not dry. Zones are coordinate review areas, not villages, exposure counts, evacuation orders or an optimal release. ML remains unavailable.

## Evidence

Fresh V05 frontend checks are summarized in `STUDIO_FRONTEND_STATUS.md` and delivered under `reference_layout_evidence/`: production build, 289 passing frontend tests and desktop/mobile browser interaction checks. The unchanged V03 backend's existing isolated test profile was used, not a newly initialized V05 profile. The 25,000 m³/s regression reuses previously checked solver cache: no fresh solver accuracy or native-computation claim follows from this styling change. Physical receiving-device setup and all possible screen sizes remain unverified. `UI_REFRESH_STATUS.md` and `ui_refresh_evidence/` are retained V04 history.

Selected `computed_integration_evidence/` and `COMPUTED_INTEGRATION_STATUS.md` are retained V03 historical acceptance. The companion verification folders contain private runtime/test state; do not exchange those whole folders.

Older `POLISH_STATUS.md`, `INTEGRATION_STATUS.md`, `frontend/FRONTEND_STATUS.md`, `evidence/` and `polish_evidence/` are historical. Backend V02's 119-test/native evidence and V02's 147-frontend/985-backend results are recorded prior results, not proof of the final combined source. Fresh V03 checks are separately identified.

Physical disconnected cold launch, post-copy SSD verification and another-device native compatibility cannot be inferred from same-device localhost tests. Rehearsals/video are excluded. No observed-flood validation is claimed.
# Current Simulation naming / presentation update

See [SIMULATION_POLISH_STATUS.md](SIMULATION_POLISH_STATUS.md). Active SSD-named package files and helper filenames now use **Simulation**, without changing the package identity or stored data. `START_COMPUTED.cmd` still starts its existing 5178 profile, and `STOP_COMPUTED.cmd` still stops it. Alternatively use `START_SIMULATION.cmd` / `STOP_SIMULATION.cmd` for the existing 5176 profile. Do not interchange stop scripts across profiles.

Current fresh evidence: production build/typecheck, 331 frontend tests passed (8 model/job tests skipped), 40 startup/ownership/integrity unit tests passed, and responsive browser checks. No new integrations or model jobs were added or exercised. Earlier evidence below is historical.

---
