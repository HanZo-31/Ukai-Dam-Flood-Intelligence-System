# Team 1 status report: Ukai Flood Intelligence

Date: 8 October 2026, about 22:00 IST (updated in the evening: contract files applied, see the note below)
Working copy: `C:\Ukai\Ukai_SSD_Ready` (baseline package ID `2ccf20b727ac4588a7f3ac39ba68b9ca`)
Delivery folder: `C:\Ukai\Team1_Delivery_v1\` (this file included)

**Bottom line.** The Team 1 pages (Explore timeline, Compare differences, review zones, Evidence methods) are built, rebuilt by the user (111 of 111 tests passed) and checked in the packaged app. They need no new Team 2 backend work and can be merged. The What-if page is built but has never run against a real candidate service. Several robustness and rehearsal checks have not been done (section 5).

How to read this report: *verified* means checked in the packaged app in the in-app browser, or by a rebuild the user ran. *Not performed* means exactly that. Nothing was checked against a real Team 2 service.

**Update (evening):** Team 2's two contract files arrived and were applied (section 5). The source now has 38 overlay files; the user's last real rebuild (111 tests) predates this change, and a new rebuild (expect 121 tests) is pending. Team 2's report also says its proxy already routes candidate calls, which makes Team 1's routing patch unnecessary if that proxy is used (`docs\TEAM2_HANDOFF.md`).

---

## 1. What was built

| Area | What it does |
|---|---|
| Arrival timeline (Explore) | Slider, Play/Pause, Reset and colour-by in elapsed model time (hours since simulation start, no timezone shown). Cells are "reached", "not yet reached" or "not available". |
| Compare differences | Baseline and candidate naming, Swap, flood-extent and arrival-change maps, metric table. Differences are always candidate minus baseline (rule set `compare-v1`). |
| Review zones | 5 km projected squares (`zone-rule-v1`), IDs like `Z-E0270-N2340`. Ranked by newly flooded area, then by how much earlier the candidate arrives. Worded "priority for review", with a note that it is not an evacuation order. |
| Candidate adapter and What-if | One adapter module for contract v1.0.0. Stored lookup only. Explicit lookup button, opt-in "nearest stored" choice, result card, ML shown as unavailable with a reason. |
| Evidence and limits | Methods and limits section on the Evidence page, plus unavailable states for exposure data. |
| Raster reader | A small in-repo reader for the stored float32 Deflate GeoTIFFs, plus a per-URL cache. |

## 2. Numbers and rules (key definitions)

- All four stored references (H01, H02, H03, 2006) share one grid: 3072 x 1024 cells, 28.999 m, EPSG:32643. Arrival is stored in minutes, whole hours.
- A cell is "valid" if finite and above -9000, and "wet" if valid with depth above 0.1 m. Nodata and missing values are never treated as zero.
- Coverage differences (valid in only one scenario) are counted separately from wet/dry differences.
- Arrival-change classes (whole hours): at most -24, at most -6, below 0, 0, below 6, below 24, 24 or more. Velocity is not compared.
- Zone timing is shown only when at least 50 paired cells cover at least 50% of cells with an arrival time in either scenario. Otherwise it reads "Not available".
- Full definitions: `docs\NUMERICAL_DEFINITIONS.md`.

Example result, H01 as baseline and H02 as candidate (matches independent numpy counts): 92,736 newly flooded cells = 77.99 km2; 3 baseline-only cells; 53 of 133 zones flagged for review.

## 3. Completed and verified

- Arrival timeline: logic and tests, including real stored-raster samples. In the browser: slider at 24 h and at the end (114 h), Reset, Play/Pause, and switching scenario during playback (switched cleanly to H03).
- Compare calculation matched independent numpy counts on the real rasters for six pairs. Same scenario gives zero change; swapping reverses the signs.
- Compare UI in the browser: extent and arrival-change maps, metric table (also at about 800 px wide), zone table, same-scenario zero ("No zone is flagged").
- Evidence methods and limits section shown.
- What-if: the service-unavailable state is shown correctly, other pages keep working.
- Display defects found in the browser and fixed:
  1. Indian-style digit grouping (3,35,050) now comma grouping.
  2. Zone coverage showing 101% now capped at 100%.
  3. Doubled full stop in "timing is unavailable" explanations removed.
  4. Metric table clipped at narrow widths now wraps.
  5. Table header "Priority" broke mid-word, and the "Why" cell broke "flooded" mid-word. Both fixed and viewed on the latest build.
- Real rebuilds by the user: 110 tests (20:16), 111 tests (twice, later builds). The latest build is `index-COuIJvaP.js` / `index-B0V8CshZ.css`. `VERIFY_COPY.cmd` was reported run by the user (I did not see its output).
- Pre-merge review (see `WORK_EVIDENCE.md` E24): no internet addresses or fixture imports in app code, no browser storage, no timezone conversion, stylesheet has no external links, all browser requests went to 127.0.0.1, wording rules respected. My separate test runner also gives 111 of 111.
- Delivery folder: 64 files plus this report, no ZIP, no credentials or database state. Every file was staged back from the device and compared with the delivered copy; the checksum list verifies.

## 4. Files changed (Team 1 only)

- Modified (11): `lib/scales.ts`, `map/FloodMap.tsx`, `components/MapControls.tsx`, `components/Legend.tsx`, `components/Sidebar.tsx`, `pages/Explore.tsx`, `pages/Compare.tsx`, `pages/Evidence.tsx`, `App.tsx`, `styles.css`, `vite.config.ts` (dev proxy rule only).
- Added (27): timeline, tiff, compare, zones, rasterCache, candidate and candidateRun libraries; `useCandidate` hook; TimelinePanel, DiffPanel, MethodsPanel components; DiffMap; WhatIf page; test fixtures; eight test files (including the contract test); five data fixtures (including Team 2's two contract files).
- Not touched: Team 2 files, contracts, the shared launcher and production server, backend. The `baseline_originals\` folder holds the original versions for rollback.

## 5. Pending and not done

| Item | Status |
|---|---|
| Offline / disconnected run and clean stop and restart | Not performed. The code and every request seen are local, but it was never run with the connection off. |
| Backend stop and recovery | Not performed. |
| Browser without WebGL | Not performed. |
| Full keyboard-only pass | Partial: Tab moves through the layer toggles with a visible focus ring. The rest not done. |
| Slow-load scenario switch | Not performed (the mid-play switch was). |
| Second-laptop test | Not performed. |
| Two rehearsals and a backup recording | Not performed. |
| Hash check of the extracted copy before the first edit | Skipped at the start. Recorded in the docs. |
| What-if against a real candidate service | Not performed (no service supplied). |
| Align the capabilities reader to the real schema | Done in source (8 Oct, E25): files received, adapter and tests updated (121/121 in my runner, tsc 0 errors). **Needs one more rebuild by the user** to reach the app. |

## 6. Issues and risks to know about

1. **What-if is unproven.** Only mocked-HTTP and labelled-fixture tests exist, which are not integration evidence. The reader of the capabilities response is tolerant and enables nothing it cannot read.
2. **Packaged app shows "Candidate service unavailable"** until Team 2 applies the routing patch and runs the service on port 8770.
3. **Lost file commits.** The link to the computer silently dropped several file writes (for example `styles.css` three times). Each was caught by staging the file back and comparing sizes. Anyone merging by hand should compare file sizes or checksums after copying.
4. **No shell on the user's computer from this session.** Rebuild, seal and verify have to be run by the user; I verify the result in the browser afterwards.
5. **Seal after every rebuild.** The package checks its folder against `SSD_CHECKSUMS.sha256`. After a rebuild, run `SEAL_WORKING_COPY.cmd` then `VERIFY_COPY.cmd`, or startup stops with "Copy file inventory differs from the checksum list".
6. **Scientific limits are unchanged.** Results are simulated, uncalibrated and not scientifically validated. Population, buildings, roads and village names are not available and are not shown.
7. **The delivery is a source overlay and documents, not a standalone package.** It depends on the baseline package named above.

## 7. Team 2 / integration needs

Team 1's own pages need nothing from Team 2. What-if needs:
1. Candidate service on 127.0.0.1:8770 implementing contract v1.0.0 (capabilities, POST job, GET job), stored lookup only.
2. ~~`candidate-openapi-v1.json` and `candidate-examples.json`~~ received and applied (E25).
3. The routing patch applied to `scripts/ssd_web_server.cjs` (`patches\ssd_web_server.candidates.PATCH.md`) and the launcher starting the service.
4. The real-service checks listed in `docs\CANDIDATE_ADAPTER_NOTES.md`.

Merge steps and a browser regression list: `docs\TEAM2_HANDOFF.md`.

## 8. Recommended next steps

1. Offline run: disconnect the internet, restart with `START_SSD.cmd`, click through Explore, Timeline, Compare and Evidence; then stop and restart the backend. (About 30 minutes.)
2. Two rehearsals of the 90-second script (`demo\OPENING_SCRIPT.md`) with a backup screen recording.
3. Merge the Team 1 pages now.
4. When the candidate service is running: run the real-service checks and re-verify What-if (the reader is already aligned to the published schema).

## 9. Where to find things

| Need | File |
|---|---|
| Delivery overview | `DELIVERY.md` |
| Item-by-item status | `WORK_CHECKLIST.md` |
| Evidence E1 to E24 | `WORK_EVIDENCE.md` |
| Formulas and thresholds | `docs\NUMERICAL_DEFINITIONS.md` |
| Candidate adapter notes | `docs\CANDIDATE_ADAPTER_NOTES.md` |
| Rebuild, launch, rollback | `docs\LAUNCH_AND_RECOVERY.md` |
| Acceptance status | `docs\DEVICE_ACCEPTANCE.md` |
| Team 2 handoff | `docs\TEAM2_HANDOFF.md` |
| Claims, script, Q&A, log, screenshots | `demo\` |
| Routing patch (not applied) | `patches\ssd_web_server.candidates.PATCH.md` |
| Checksums and inventory | `CHECKSUMS.sha256`, `FILE_INVENTORY.csv` |
