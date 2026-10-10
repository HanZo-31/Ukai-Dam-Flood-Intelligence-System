# V05 — in-place layout cleanup

## Completed changes

All edits and verification outputs for this task were confined to `UKAI_COMBINED_V05`. No V06, other project edits, installations, new scenarios or hydraulic changes were made.

| Area | Change |
| --- | --- |
| Workspace | Removed the fixed minimum page/map heights that forced nested scrolling on shorter or zoomed desktop screens. Explore uses available height; other pages retain their normal scrolling. |
| Sidebar/header | Smaller spacing, navigation/scenario cards and heading without losing scenario selection or API connection status. |
| Map layers | Three primary choices remain visible. Reveal, extent and opacity are under a closed-by-default **More controls** disclosure. Fit/zoom remain available. |
| Scenario card | Compact facts/evidence link; all metrics, metadata and uncertainty remain accessible. Duplicate clock context is visually condensed but remains available to assistive technology and in the timeline explanations. |
| Legend | Smaller footprint with the original colours, values, ticks and no-data semantics. |
| Timeline | Slimmer dock. Clock/play/pause/reset are visible; redundant colour-by/explanation are under **Timeline details**. Depth/velocity maximum-over-run warnings stay visible, not inside the closed disclosure. |
| Responsive layout | Short desktop, tablet and mobile layouts checked for panel collisions and overflow. Mobile keeps natural vertical scrolling. |

The reference image's decorative terrain, cyan palette, river geometry and example duration were not substituted for real simulation data. The original map background, raster colours and simulation behavior are preserved; changed viewport dimensions mean pixel-identical screenshots are not claimed.

## Actual code files

- Changed `frontend/src/studio.css` — presentation, spacing and responsive sizing.
- Changed `frontend/src/components/ExploreLayers.tsx` — groups existing secondary controls in a disclosure; existing callbacks/values remain.
- Changed `frontend/src/components/ExploreTimeline.tsx` — requests the compact presentation.
- Changed `frontend/src/components/TimelinePanel.tsx` — optional compact markup only. The original 600 ms clock, effects/state, model-hour/minute handling, availability logic and control handlers are preserved. Other consumers keep the default presentation.
- Added `frontend/src/components/layout-cleanup.test.tsx` — seven additional presentation tests.
- Rebuilt `frontend/dist/`; refreshed startup/status documentation, release identifier, inventory and checksums. The **SSD package ID and existing user-profile identity were not changed**.
- Added `layout_cleanup_evidence/` reports/logs and real browser screenshots. Private verification snapshots, database, objects, solver outputs and caches were temporary and are not part of the deliverable.

`Explore.tsx`, the map renderer, raster/colour/timeline libraries, original styles, Legend, Compare, What-if, Evidence, backend, native solver, routes/contracts, dependency locks and launcher scripts are unchanged.

## Fresh checks of final source

- [x] Production TypeScript/Vite build passed.
- [x] **296 frontend tests passed**, zero failures/skips, across 31 test files. Final logs and source hashes: `layout_cleanup_evidence/final/`.
- [x] Real reference rasters, timeline reveals, extent and comparison tests passed.
- [x] Existing live candidate lookup and compute-v2 producer/consumer checks passed. The first live regression produced a real 25,000 m³/s native run in the new isolated test profile (`live/COMPUTE_REGRESSION.json`: first request cache-hit false); subsequent runs verified checked-cache reuse, products, H02 comparison and zones. This is functional verification, not calibration or scientific accuracy evidence.
- [x] Browser checks: three primary layers, secondary disclosure, opacity 0.1–1, extent/fit, synchronized colour-by controls, play/pause/reset, H03 reset to depth/full-run, metadata and Evidence navigation.
- [x] Browser Compare rendered both real reference maps. What-if 20,000 m³/s returned stored H02, explicitly not computed. Evidence retained six download links.
- [x] Final 1280×592 short-screen layout: no main/sidebar/default-card overflow beyond rounding tolerance, primary layer and legend panels do not overlap; controls fit. Depth/velocity warnings remain visible.
- [x] 375×812 mobile: zero horizontal document overflow; expanded secondary controls fit and do not overlap the legend. 1024×720 tablet and 1672×941 desktop layouts also checked.
- [x] No captured browser warning/error messages; temporary viewport override reset and verification tab closed.
- [x] Preservation check: **25,422 protected original V05 files unchanged**, no protected mismatches; original timeline clock/handlers are identical and final source matches passing tests.

The final source-bound test report takes precedence over preliminary/refined checks. Early verification helpers encountered Windows long-path normalization and console encoding issues; those were corrected without changing simulation/backend code. Browser assertions were corrected to read the existing `.map-host` readiness marker and native radio `checked` property; these were test-inspection issues, not simulation defects.

## Evidence and startup

- `layout_cleanup_evidence/desktop-clean.jpg` — actual desktop frontend.
- `layout_cleanup_evidence/short-screen-clean.jpg` — actual short-screen frontend.
- `layout_cleanup_evidence/mobile-clean.jpg` — actual mobile frontend.
- `BEFORE_CHANGE.json`, `PRESERVATION.json`, `BROWSER_CHECKS.json` and responsive geometry reports distinguish actual checks from claims not made.
- Earlier `reference_layout_evidence/`, `ui_refresh_evidence/` and backend/handoff reports retain history; they are not new acceptance of this cleanup.

Start this same V05 folder with `VERIFY_COPY.cmd` then `START_COMPUTED.cmd`; open **http://127.0.0.1:5178/**. Restart an existing instance normally and refresh the browser to load the rebuilt frontend. The existing legacy launcher may use 5176; the temporary check port 5191 is not a normal startup port. Stop with the matched stop script before disconnecting an SSD.

The full backend test suite was not repeated because backend code is unchanged. Another-device/physical SSD startup, every possible screen/browser/camera state and scientific flood validation are not claimed. The isolated verification profile was not the user's normal live database.
