# Reference-layout frontend V05 — implementation and verification

**Historical first-V05 report.** The subsequent in-place cleanup is documented in [LAYOUT_CLEANUP_STATUS.md](LAYOUT_CLEANUP_STATUS.md). Latest acceptance is `layout_cleanup_evidence/final/` (296 passing tests). Unlike this original report, TimelinePanel now has an optional compact *presentation*; its original clock, availability logic and event handlers remain identical. No other project folder was modified during cleanup.

## Scope and result

Implemented the light visual layout requested from the supplied reference image. The user authorized moving/restyling layer controls, the legend and timeline while preserving actual flood data, palettes and rendering/solver logic. V05 is a new complete plain folder; the sealed V04 baseline and original deliveries were not overwritten.

- White sidebar with blue active navigation/scenario styling.
- Light header with actual local API status; the adjacent simulation badge remains removed.
- Floating Depth / Arrival / Velocity controls, arrival-time reveal toggle, extent, opacity and fit controls.
- Existing legend in the lower-left map area, retaining its actual colours/ticks/data semantics.
- Compact scenario card with actual peak release, model-time state, scenario identity, exposure availability and an Evidence link.
- Original metrics, metadata and scientific limitations remain accessible through the scenario disclosure and Evidence page.
- Bottom timeline dock reuses the original timeline component, play/pause/reset and clock conversions. Full-run and arrival-reveal states remain distinct. The disabled/full-run dock does not pretend to animate.
- Responsive desktop and mobile layout, including short laptop screens.

The illustrated map background, flood geometry, colouring and sample 138-hour duration were NOT substituted for real project data. For the verified H02 reference the actual window is 114 hours; 48 hours is 2,880 elapsed model minutes. Missing exposure remains unavailable rather than becoming an invented measurement. Uncalibrated/not-validated status is still visible in scenario metadata and Evidence.

## Files created or changed

| Repository-relative file | Change |
| --- | --- |
| `frontend/src/studio.css` | New presentation-only layout stylesheet, loaded after the preserved original/light styles. |
| `frontend/src/components/ExploreLayers.tsx` | New accessible wrapper for existing layer, reveal, extent, opacity and fit operations. |
| `frontend/src/components/ExploreScenario.tsx` | New actual-data scenario card; retains original metric/metadata components in its disclosure. |
| `frontend/src/components/ExploreTimeline.tsx` | New dock wrapping the unchanged timeline component, with truthful full-run/unavailable states. |
| `frontend/src/components/studio.test.tsx` | Twelve new component tests; fixtures are synthetic test inputs, not scientific evidence. |
| `frontend/src/pages/Explore.tsx` | Reassembles the layout and wires existing controls; original state/clock/clamping and map-prop block are preserved. |
| `frontend/src/components/TopBar.tsx` | Optional heading subtitle; truthful API status retained. |
| `frontend/src/App.tsx` | Explore heading/subtitle; routing and scenario lifecycle retained. |
| `frontend/src/main.tsx` | Loads the new stylesheet. |
| `frontend/dist/` | Rebuilt production frontend. |
| Root startup guides, release/package IDs, inventory/checksums | Identify this new copy and distinguish current from historical evidence. |
| `reference_layout_evidence/` | Fresh public reports, logs and actual browser screenshots. |

No dependency, backend, database schema, scientific asset, publication policy, solver, map renderer, palette library, original stylesheet, original Legend or original TimelinePanel changes were made. Compare, What-if and Evidence functionality was not redesigned.

## Fresh verification of final source

- [x] Production TypeScript/Vite build passed.
- [x] All **289 frontend tests passed**, with zero failed or skipped tests; final logs/report are in `reference_layout_evidence/frontend-release/`.
- [x] Final tested frontend source hashes match the delivered source.
- [x] Browser checks exercised all three raster modes, reveal/full-run distinctions, play/pause/reset, actual clock values, scenario reset, opacity, extent/fit, scenario disclosures and evidence navigation/download links.
- [x] Existing Compare and What-if navigation checked, with no captured browser console errors.
- [x] Layout inspected at 1672×941, 1280×720 and 375-pixel mobile width; mobile horizontal overflow was zero. The laptop Evidence button and timeline are visible.
- [x] Cached compute-v2 frontend regression passed against the existing isolated profile. This is reuse of previously checked solver results, not a new native computation or accuracy result.
- [x] SHA-256 preservation guard verified **25,402 protected baseline files unchanged**. The existing renderer, palettes, timeline logic/component, scientific data, backend and solver remain identical. Changed viewport geometry is authorized; pixel-identical UI is not claimed.
- [x] Temporary verification services stopped; no private runtime profile/database/credentials are included in the public evidence folder.

Intermediate local checks initially exposed four attribute-order-sensitive new assertions and a short-screen spacing problem. Both were corrected before the final build/test/browser checks. Intermediate attempts are not acceptance evidence; the final release report is authoritative.

Actual UI screenshots: `reference_layout_evidence/explore-reference-layout-full.jpg`, `laptop-1280.jpg` and `mobile-375.jpg`. They show the project itself, not the illustrative source image.

## Evidence limits and remaining acceptance

- [ ] Freshly initialize/run the V05 profile on the receiving computer after copying the complete folder and passing `VERIFY_COPY.cmd`.
- [ ] Visually verify maps and controls on that receiving computer; physical SSD/disconnected cold launch and native compatibility were not repeated in this UI-only task.
- The full backend suite was not rerun: backend/solver files are unchanged. Earlier backend/native results retained in V03 reports are recorded history, not fresh V05 hydraulic validation.
- No new flood observations, calibration, scientific approval, ML model, exposure measurements, basemap dependency or additional scenarios were introduced.
- No claim is made for every screen size, browser, camera state or production/public hosting. Execution remains localhost-only.

## Start the correct copy

Run this V05 folder's `VERIFY_COPY.cmd`, then `START_COMPUTED.cmd`, and open **http://127.0.0.1:5178/**. Stop an older instance first if its ports are occupied. Stop this copy with `STOP_COMPUTED.cmd`; do not unplug an SSD while services are running. Port 5180 was temporary verification only. Do not exchange companion verification folders containing private runtime state.

`UI_REFRESH_STATUS.md` / `ui_refresh_evidence/` are V04 history. `COMPUTED_INTEGRATION_STATUS.md` / `computed_integration_evidence/` are V03 history. Other inherited completion reports retain older context and must not override this V05 status.
