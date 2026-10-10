# Polished integration V02 — status and evidence

Date: 2026-10-09 (Asia/Calcutta). Release: `ukai-combined-20261009-v02-polished`.

This version develops the preserved V01 in a new plain folder. V01, original team deliveries, hydraulic input files and original assets are not edited. This computer is the final demo laptop, as confirmed by the user; a separate receiving-laptop check is not required for this demo. Universal portability is not claimed.

## Implemented

- [x] Remove the proposed Review guide from the product, as requested. Navigation contains only Explore, Compare, What-if and Evidence. Operator instructions stay in separate Markdown documentation.
- [x] Correct a real extent-map projection bug: EPSG:4326 longitude/latitude GeoJSON is transformed into the EPSG:32643 map, not reinterpreted as metres. Already-projected outlines retain their coordinates; unknown CRS is refused.
- [x] Add comparison briefings using current scenario/run IDs, asset checksums, coverage, paired denominators and uncertainty. The locally downloaded Markdown is a derived review note, not a new model result or approval.
- [x] Add keyboard skip-to-content, page heading, section focus management and focusable map surfaces.
- [x] Improve muted-text/action contrast and visible keyboard focus. Fix document overflow found during keyboard navigation.
- [x] Add explicit map retry, extent-outline fallback and comparison retry; report graphics-context loss and raster tile errors.
- [x] Add What-if input help/error associations. Keep actual returned release, stored-only timing and last-successful-result behaviour.
- [x] Replace remaining misleading zone labels with candidate-only recorded wet footprint wording; mathematical comparison/ranking rules remain unchanged.
- [x] Prepare launch/recovery card, claims register, demo script/Q&A and a static screenshot backup. The gallery is not a video or rehearsal.

## Fresh checks on V02

- [x] Production build/typecheck and **147 frontend tests passed, zero failed/skipped**, including 16 added polish/projection checks and seven live HTTP checks (`frontend-final-v07`).
- [x] Bundled dependency consistency, correctness lint, gradual backend type checks, proxy syntax and frozen OpenAPI validation passed (`quality-v01`). No packages were installed.
- [x] All **24 actual reference downloads** passed checksum, HEAD/ETag, exact range and If-Range checks through V02; no reimports (`resources-v01`).
- [x] Browser checks of the final no-guide build: 16 scenario/layer ready states; keyboard skip/navigation and 3 h / 180 min timeline; actual briefing download; exact and opted-in nearest What-if; out-of-range disable; failed request retains its previous result.
- [x] Deliberately disabled raster rendering: explicit diagnostic message, correctly projected extent fallback, comparison tables/briefing usable. Unit tests cover true null/throwing WebGL context probes. This is not a claim that the demo laptop lacks WebGL.
- [x] Identity-verified candidate interruption: previous result remains identifiable and reference maps still work. Owned full shutdown produces the API-unreachable state.
- [x] Final combined backend regression: **985 passed, four skipped, one existing Starlette/HTTPX deprecation warning**, 117.34 seconds. Owned shutdown was clean and checked backend sources stayed unchanged (`backend-regression-v01`). Windows-specific skips are not counted as passes.
- [ ] Final restart/recovery and release seal: being closed; see the companion verification reports for actual outcomes. Do not treat this unchecked line as complete until the final record is updated.

Fresh public logs/screenshots are delivered under `polish_evidence/`. The companion `UKAI_COMBINED_V02_VERIFICATION` holds execution evidence and private test/runtime scratch outside the sealed delivery; do not exchange that whole directory. V01 reports under `integration_evidence/` are historical.

Earlier failed attempts remain recorded: sandbox realpath restriction; live tests pointed at V01 after its planned shutdown; initial unresealed startup refusal; TypeScript-only errors in the new test; wrong H02 test fixture folder before using `part_a`. These were not counted as successful checks. Any earlier screenshots/checks containing Review guide predate its requested removal.

## Remaining human/device checks

- [ ] Physically disconnect network and perform a cold launch/judge journey on this final laptop. Local source/resource checks do not prove physical disconnection.
- [ ] Perform two actual operator-led 3–5 minute rehearsals, one from stopped offline state, with a planned recovery.
- [ ] Save and play a normal-speed backup video; retain a separate local and SSD copy.
- [ ] Complete operator accessibility acceptance, including actual assistive technology if required. Focused keyboard/label/contrast checks are not a formal accessibility certification.
- [ ] Verify the final plain folder and demo materials after copying onto the SSD. No mounted `E:\Ukai` destination was available during inspection.

Use [the launch/recovery card](demo_evidence/LAUNCH_AND_RECOVERY_CARD.md) and [script/Q&A](demo_evidence/DEMO_SCRIPT_AND_QA.md) for these actions. Record outcomes in a new evidence folder rather than changing a sealed delivery.

No fresh solver runs, additional scenarios, enabled ML predictor, calibration, observational validation or operational safety recommendations have been added. Approved-only publication controls are unchanged. Stored scenarios remain first.
