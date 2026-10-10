# Team 1 work evidence

Every statement says who ran the check and where. "Stand-in runner" = a small substitute for vitest I wrote in the cloud workspace (it has no npm registry), so it is **not** the real `npm test`.

**E1 Documents.** Read `docs/HACKATHON_20_HOUR_PLAN.md`, `docs/SSD_SETUP_AND_WORK_GUIDE.md`, `evidence/SSD_FINAL_VERIFICATION.md`, `SSD_PACKAGE_REPORT.json`. Reported baseline (quoted, not repeated by me): 902 backend tests passed, 4 skipped; 21 frontend tests passed; 24 downloads checked. Reported as not performed: automated browser checks, second-laptop test, disconnected-internet test, complete fast-solver environment.

**E2 Working-copy hash check: not done before editing.** `VERIFY_COPY.cmd` will now list my changed files as differences; `SEAL_WORKING_COPY.cmd` is needed at the end. Originals: `Team1_work\baseline_originals\`.

**E3 Journey on the device: not performed.**

**E4 Evidence files:** this file, `WORK_CHECKLIST.md`, `demo_evidence\CLAIMS.md`, `demo_evidence\OPENING_SCRIPT.md`.

**E5 Contract.** `TEAM1_CANDIDATE_CONTRACT.md` v1.0.0 read. Its OpenAPI export and examples are not yet in `Team1_work\contract\`. The contract does not define the capabilities response, so the adapter reads several plausible shapes and enables nothing it cannot read (see `CANDIDATE_ADAPTER_NOTES.md`).

**E6 Timeline logic.** Rasters read with numpy/tifffile (all four share one 3072×1024 grid, 28.999 m cells, EPSG:32643). Valid arrival cells: H01 334,244; H02 426,586; H03 534,249; 2006 494,437. Whole-hour values, minimum 60 min. Fixture `lib/fixtures/arrival_samples.json` holds per-scenario histograms, per-hour reached counts and sampled nodata/valid cells. Stand-in runner: timeline tests pass, including monotonic reveal and final reveal = valid footprint.

**E7 Timeline UI** compiled in the user's rebuilds (E19) and viewed in the packaged app (E21).

**E8 Comparison numbers.** `compare.ts` was run on the real stored rasters for six pairs and matched independent numpy (float64) on counts, km², depth mean, arrival mean/median and zone results. Examples: H02→H03 new flooded 90.612 km² (54 flagged zones); H02→2006 new flooded 57.116 km²; H01→H03 new flooded 168.595 km²; H02→H01 new 3 cells and baseline-only 92,736 cells. Same scenario → zero change. Swapping H02/H03 swapped new and baseline-only and reversed signs.

**E9 TIFF reader.** `tiff.test.ts` builds small TIFFs: multi-tile read, georeference, nodata, rejection of 16-bit, wrong compression, predictor, BigTIFF, short tile; cache fetch-once and failure-not-cached. Stand-in runner: pass. Real-file reads reproduce numpy counts (E8).

**E10 Compare UI** (`DiffPanel`, `DiffMap`) compiled in the user's rebuilds and viewed in the packaged app (E21, E22, E23).

**E11 Candidate adapter tests.** `candidate.test.ts` (mocked fetch + labelled fixtures): ID and range checks, request body, nearest-peak tie rule, three capability shapes plus unreadable ones, nine result-identity rejections, unavailable vs request errors (server text never shown), queued→running→completed, failed job, mismatched identity, poll limit. Stand-in runner. This is **not** a test against the real service.

**E12 What-if UI** compiled in the user's rebuilds; viewed only in its service-unavailable state (E21). Never viewed with a working service.

**E13 Routing.** Dev proxy rule added before `/api`. Production-server change is only a written patch.

**E14 Zones.** Synthetic partition test (totals reconcile with whole-grid compare, order, determinism, same-scenario, unavailable timing) and real-raster test against numpy for six pairs (`compare.real.test.ts`; skipped with a message if the rasters are not found). Stand-in runner: synthetic tests pass; real tests were run through the separate harness and matched.

**E15 Evidence panel** `MethodsPanel` committed; not viewed.

**E16 Real TypeScript check (added later).** I staged the real `@types/react`, `csstype` and the `ol` type files from your `node_modules` and ran the real `tsc` (6.0.3, strict, `noUnusedLocals`, `noUnusedParameters`, same options as `tsconfig.json`) over all of `src` including React, OpenLayers and test files. Result: **0 errors**. Limits: `lucide-react` and `vitest` were replaced by small type stubs; about 40 deep `ol` type files were not staged, so a few OpenLayers types resolved loosely. This is not `npm run build` and not a browser run.

**E17 Arrival-change classes.** Whole-hour classes (steps at 6 h and 24 h) tested on synthetic grids and on four real pairs against independent numpy counts (all equal). `demo_evidence\preview_H02_to_H03_difference_NOT_A_SCREENSHOT.png` is an image I drew from the same class arrays (top: flood extent difference, bottom: arrival change); it is **not** a screenshot of the app.

**E18 Source guards.** `hygiene.test.ts` fails if an application file imports `testing/` fixtures or names an internet address; mutation-checked (it failed when I injected both).

**Test totals (superseded by E19/E22/E23).** Latest real run by the user: 13 files, 111 tests passed. My stand-in runner on the same tree also gives 111/111 (re-run 8 Oct ~21:30); it is a separate harness, not vitest. The type check is E16.

**E19 Real rebuild (user ran `REBUILD_FRONTEND.cmd`, 8 Oct 2026 20:16, output pasted to me).** `tsc --noEmit` and `vite build` (vite 7.3.7, 1988 modules, built in 30 s) succeeded; real `vitest run` v3.2.7: **13 files, 110 tests passed**, including the real-raster tests (timeline 25, compare/zones/arrival classes 11) and the source guards. This is the user's run, not mine. The printed message was "Build and frontend tests passed."

**E20 Startup gate.** `START_SSD.cmd` then stopped with "Copy file inventory differs from the checksum list". Cause: the package verifies the folder against `SSD_CHECKSUMS.sha256`, and my edits plus the new `dist` change that inventory (this is the pre-edit hash check I skipped, E2). Remedy: `SEAL_WORKING_COPY.cmd` then `VERIFY_COPY.cmd`.

**E21 Browser checks I performed (built-in browser, packaged app on 127.0.0.1:5174, build of 8 Oct 20:16, 20:35–20:45).**
* Explore → Timeline (H01): slider 24 h shows a coloured reached area along the river and pale grey for valid-but-not-yet-reached; 114 h of 114 h (6840 min) shows everything reached; Reset returns to 0 h; Play advanced to 8 h in about 4 s; Pause stops it. Screenshots: `demo_evidence\screenshots\timeline_H01_24h.jpg`, `timeline_H01_114h_end.jpg`.
* Compare H01→H02: difference map, metric table, 53 of 133 zones flagged; numbers equal the independent counts (new flooded 92,736 cells = 77.99 km²; baseline-only 3 cells). Arrival-time layer: class counts 2,018 / 92,290 / 221,433 / 18,489 / 11 / 0 / 2 equal the numpy counts. Screenshot `compare_arrival_difference_H01_to_H02.jpg`.
* Swap: baseline H02, candidate H01: new and baseline-only exchanged, depth and arrival signs reversed.
* Same scenario H02 vs H02: 0 new, 0 baseline-only, "No zone is flagged".
* Evidence page shows the methods and limits section. Console: no errors.
* What-if with no candidate service (user's screenshot and my page read): "Candidate service unavailable … Explore, Compare and Evidence still work"; Look-up button disabled; ML shows unavailable.
**Defects found and fixed after this run (need rebuild + reseal to appear):** thousands grouping used the Indian style (3,35,050) → now en-US; zone coverage showed 101% → capped at 100%; doubled full stop in "timing is unavailable" explanations; the metric table was cut off at ≤1180 px width → layout switches to one column and cells wrap.
**Still not performed:** What-if against a real service; scenario switch during a slow load; backend stop/recovery; no-WebGL; keyboard-only pass; narrow-width visual check; offline/disconnected test; second laptop.

**E22 Further browser checks (built-in browser, build `index-BPPPnV7F.js` / `index-Dxn9PNAq.css`, 8 Oct ~20:50).**
* Compare H01→H02 on the new build: comma grouping (92,736 cells), no zone coverage above 100% (values 100% and 38%), no doubled full stops, metric table and zone table wrap instead of clipping at ~800 px width.
* Found: at narrow widths the "Priority" column header broke mid-word. Fix written to `styles.css` (header cells no longer break inside words) and verified present on the device (11,766 bytes) **but not rebuilt or viewed**.
* Scenario switch during timeline play (H01 playing → H03 selected): page showed H03 values (30,000 m3/s, 450.4 km², 39.28 m), no stuck playback, no new error.
* Keyboard: Tab moves through the layer toggles with a visible focus ring. The page-reader listing showed the four scenario buttons without a name. Source review (`Sidebar.tsx`): each is a `<button>` containing visible text (short name and type label) with `aria-pressed`, so it has an accessible name; the empty entries were a reader limitation, not a defect found.
* Console errors seen: connection-refused entries from the server restarts and one 503 (candidate service absent). No application script errors.
**Rebuild history:** run 1 (20:16) 110 tests; run 2 111 tests (`index-k9b0vVEP.js`; its CSS did not change because `styles.css` on the device was an older copy: a commit had been lost); run 3 (20:46) 111 tests, CSS `index-Dxn9PNAq.css` containing the wrap fixes. Lost commits are caught by staging the file back and comparing sizes.

**E23 Build of 8 Oct ~21:10 (`index-DQnhuywT.js`, `index-D59VpBXZ.css`, user's rebuild).** Zone-table header no longer breaks inside words (checked in the browser). New finding on the same build: in the body, the "Why" cell broke "flooded" as "floode / d area" because body cells used a break-anywhere rule. Fix: body cells now break only when a word cannot fit (`overflow-wrap:break-word`) and the Zone and Why columns have minimum widths. `styles.css` is 11,879 bytes on the device (verified by staging it back). **Rebuilt by the user and viewed (build `index-COuIJvaP.js` / `index-B0V8CshZ.css`):** the Priority header and the Why column wrap at spaces, no mid-word breaks, tables not clipped; console shows only the earlier connection-refused and 503 entries. One more commit to the device was lost before it landed; the staging check caught it.

**E24 Pre-merge review (8 Oct ~21:30).** (1) Source scan of application files: no internet addresses, no import of `testing/` fixtures, no localStorage, no console/TODO, no timezone conversions; stylesheet has no `@import`, `url()` or external links. (2) All network requests seen in the browser during E21–E23 went to 127.0.0.1:5174. (3) Wording scan: "simulated / uncalibrated / not scientifically validated" present on Sidebar, Compare, Methods; "priority for review" with an explicit "not an evacuation order" note; unavailable values shown as "Not available", not zero. (4) Stand-in tests 111/111. (5) Stale lines in these documents corrected. This is a review by reading and scanning plus the checks above; it is not a substitute for the checks still listed as not performed.

**E25 Contract alignment (8 Oct, evening).** Received Team 2's `candidate-openapi-v1.json` and `candidate-examples.json`; kept unchanged under `lib/fixtures`. Gaps found by reading them against `candidate.ts`: `completed_at` and `timing_scope` were not required; the request-ID pattern allowed a leading underscore or hyphen the service rejects; the five reference-resource keys were not all required; `selection_range_m3s` and `experimental_ml_enabled` were not read; test fixtures used invented scenario IDs. All fixed (see `docs\CANDIDATE_ADAPTER_NOTES.md`); What-if also shows the service's timing scope next to the lookup time. New `candidate.contract.test.ts` (10 tests). Checks I ran: my stand-in runner 121/121 (111 before + 10 new); two mutations (dropping the two required fields, loosening the ID pattern) made 2 of the new tests fail, then restored to 121/121; real `tsc` 6.0.3 with the same staged type files and stubs as E16: 0 errors. **Not yet run:** the user's real `REBUILD_FRONTEND.cmd` (expect 14 test files, 121 tests) and a browser look at What-if on the new build. Still **not** tested against a running candidate service.
