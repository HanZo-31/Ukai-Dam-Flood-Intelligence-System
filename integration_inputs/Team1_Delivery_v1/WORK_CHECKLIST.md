# Team 1 work checklist

Working copy: `C:\Ukai\Ukai_SSD_Ready` (extracted from the RAR parts). Package lineage ID `2ccf20b727ac4588a7f3ac39ba68b9ca`.
Legend: **[x]** done with evidence · **[~]** written and checked here, still needs your real rebuild / browser check · **[ ]** not done.
Evidence for each line is in `WORK_EVIDENCE.md` (same numbering).

## 0–2 h Baseline and preparation
- [x] B1 Read plan, setup guide, final verification, package report; package ID recorded. (E1)
- [ ] B2 Hash-verify the extracted working copy before edits. **Not done** (no shell on the link; I did not ask you to run `VERIFY_COPY.cmd` first). Originals of every file changed are in `Team1_work\baseline_originals\`. (E2)
- [ ] B3 Journey H02 → Compare H01/H03 → Evidence on this copy. **Not done**; needs `START_SSD.cmd` and a browser. (E3)
- [x] B4 WORK_CHECKLIST.md, WORK_EVIDENCE.md, demo_evidence/CLAIMS.md, demo_evidence/OPENING_SCRIPT.md created. (E4)
- [x] B5 Candidate contract v1.0.0 read; `candidate-openapi-v1.json` and `candidate-examples.json` received later on 8 Oct (A4, E25). (E5)
- [x] B6 File ownership and changed paths recorded (below).

## 2–5 h Arrival timeline (Explore)
- [x] T1 Logic: single hours→minutes conversion, window from metadata, reached / not yet reached / unavailable. (E6)
- [x] T2 Numeric tests incl. real stored-raster samples; 180-minute cell hidden at 2 h, visible at 3 h. (E6)
- [x] T3 UI (viewed, E21): slider, label, Reset, play/pause, colour-by, legend, scenario-switch reset. (E7)
- [x] T4 Browser checks of the timeline: slider, end state, Reset, Play/Pause (E21). Scenario switch mid-play not yet checked.

## 5–8 h Comparisons
- [x] C1 Pure calculation `compare-v1` (wet > 0.1 m, new / common / baseline-only, coverage separate, paired depth and arrival, candidate − baseline). (E8)
- [x] C2 Same-scenario = zero; swap reverses; counts × pixel area = km²; nodata excluded; checked on the real rasters for 6 pairs against independent numpy. (E8)
- [x] C3 In-repo COG reader with unit tests (identity compression) and raster cache. (E9)
- [x] C4 UI (viewed, E21–E23): baseline/candidate naming, swap, metric table, extent-difference and arrival-difference maps, unavailable states. (E10, E17)
- [x] C5 Browser check of Compare: maps, table, swap, same-scenario zero, zones (E21). Fixes for four display defects are committed and need a rebuild.

## 8–14 h Candidate adapter and What-if
- [x] A1 Single adapter `lib/candidate.ts` for contract 1.0.0; capability reader; request/result checks; stale-response guard; last good result kept. (E11)
- [x] A2 Fixture and mocked-HTTP tests: unavailable service, request errors, loading, failed job, mismatched IDs, requested vs actual peak, reserved queued/running states. Fixtures are labelled and not imported by the app. (E11)
- [~] A3 (viewed only in service-unavailable state) What-if page: deliberate Run, explicit nearest opt-in, stored-lookup labels, ML-unavailable reason from capabilities. (E12)
- [x] A4 Capabilities and result checks aligned to Team 2's `candidate-openapi-v1.json` and `candidate-examples.json` (received 8 Oct); `candidate.contract.test.ts` added (E25). Needs one more user rebuild to be in the app.
- [ ] A5 Test against the real service on 127.0.0.1:8770. **Not performed** (service not supplied/running).
- [x] A6 Dev proxy rule for `/api/v1/candidates` → 8770 in `vite.config.ts`; production-server patch written, **not applied** (`patches\ssd_web_server.candidates.PATCH.md`). (E13)

## 14–16 h Review zones
- [x] Z1 `zone-rule-v1`: 5 km projected squares, complete partition, new-flooded-area rank then median paired arrival advance, deterministic ties, minimum paired coverage. (E14)
- [x] Z2 Partition reconciles with whole-grid areas; same scenario → no priority; repeat runs identical; real-raster totals match numpy. (E14)
- [x] Z3 (viewed, E21–E23) Zone table, explanations, unavailable reasons, map highlight. (E10)
- [x] Z4 No administrative polygons were supplied, so zones are labelled as coordinate zones.

## 16–18 h Polish and assembly
- [x] P1 (viewed, E21) Evidence page: methods and limits panel. (E15)
- [x] P2 Real `REBUILD_FRONTEND.cmd`: tsc + vite build + vitest passed. Latest run (user, 8 Oct 20:46): 13 files, **111/111 tests passed**, bundle `index-BPPPnV7F.js`, CSS `index-Dxn9PNAq.css` (E19, E22).
- [x] P2b Copy sealed and started (user). Re-seal needed after each rebuild.
- [~] P3 (scenario buttons have accessible names: source review, E22) Done in the browser (E22): scenario switch during timeline play (clean switch, playback stops); metric and zone tables at ~800 px width; Tab moves focus through the layer toggles with a visible focus ring. **Not done:** slow-load switch, backend stop/recovery, no-WebGL, a full keyboard-only pass.
- [ ] P4 Offline launch and clean stop/restart. **Not performed.**
- [ ] P5 Actual integration with Team 2's service. **Pending.**

## 18–20 h Rehearsal and handoff
- [ ] H1 Two rehearsals, screenshots, backup recording. **Not performed.**
- [x] H2 Versioned delivery folder `C:\Ukai\Team1_Delivery_v1\` with DELIVERY.md, FILE_INVENTORY.csv, CHECKSUMS.sha256 written (no ZIP). It is a **source overlay + documents**, not a standalone package; it depends on baseline package `2ccf20b727ac4588a7f3ac39ba68b9ca`.
- [x] H3 Latest CSS tweak (zone-table wrapping, E23) rebuilt and viewed. The user reports `VERIFY_COPY.cmd` was run on this build and completed (8 Oct ~21:24); I did not see its output, so this is the user's report, not my check.

## Changed paths (Team 1 only; Team 2 files untouched)
Modified: `frontend/src/lib/scales.ts`, `map/FloodMap.tsx`, `components/MapControls.tsx`, `components/Legend.tsx`, `components/Sidebar.tsx`, `pages/Explore.tsx`, `pages/Compare.tsx`, `pages/Evidence.tsx`, `App.tsx`, `styles.css`, `frontend/vite.config.ts` (dev proxy rule only).
Also added: `lib/hygiene.test.ts`, `lib/fixtures/arrival_bins_expected.json`.
Added under `frontend/src/`: `lib/timeline.ts`, `lib/tiff.ts`, `lib/compare.ts`, `lib/zones.ts`, `lib/rasterCache.ts`, `lib/candidate.ts`, `lib/candidateRun.ts`, `hooks/useCandidate.ts`, `components/TimelinePanel.tsx`, `components/DiffPanel.tsx`, `components/MethodsPanel.tsx`, `map/DiffMap.tsx`, `pages/WhatIf.tsx`, `testing/candidateFixtures.ts`, tests `lib/{timeline,timeline.real,tiff,compare,compare.real,candidate}.test.ts`, fixtures `lib/fixtures/{arrival_samples,compare_expected}.json`.
Not changed: `scripts/ssd_web_server.cjs`, launchers, backend, Team 2 files, contracts.
