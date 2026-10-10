# Final SSD verification - 8 October 2026

Distribution: `E:\Ukai\Ukai_SSD_Ready`. Prepared laptop copy: `C:\Users\LENOVO\Documents\Codex\2026-10-07\files-mentioned-by-the-user-start\Ukai_SSD_Ready`.

Package lineage ID: `2ccf20b727ac4588a7f3ac39ba68b9ca`. The final `SSD_CHECKSUMS.sha256` describes the actual final bytes; the ID alone does not certify an edited copy. Read `SSD_PACKAGE_REPORT.json` for the final recorded scope and status.

## Performed checks

- [x] Native Python 3.12.4, Node 24.13.0 and PostgreSQL 17.11 execute from the prepared folder. Backend/GIS modules import from bundled packages.
- [x] Independent dependency audit examined 696 native files. Core Python/GIS, quality tools, Node and PostgreSQL/PostGIS dependencies are present. PostgreSQL's Microsoft runtime DLLs were added locally. Optional PL/Perl, PL/Tcl, PL/Python and extra GUI modules are outside the app's used startup path and are not certified by this audit.
- [x] Fresh isolated database initialized using bundled PostgreSQL; schema migrations and PostGIS creation completed.
- [x] H02, H01, H03 and reconstructed 2006 receipts imported. Scenario/run identities and manifest identities agree with the delivered reference library.
- [x] All four references served through the portable frontend proxy on 5174 and API on 8766.
- [x] All 24 download resources: complete GET SHA-256 matches; HEAD body/length; prototype/scientific-warning headers; one-byte range contents and exact Content-Range/length; matching If-Range; stale If-Range fallback; unsatisfiable-range response/header.
- [x] Draft scenarios remain isolated from approved/publication routes. Original receipt inventories match after HTTP checks.
- [x] Built frontend HTML, JavaScript and stylesheet resources served successfully through the portable web server.
- [x] Full backend suite run from the packed folder and bundled Python: **902 passed, 4 skipped**, with one upstream Starlette/httpx deprecation warning. No library upgrade was needed for migration.
- [x] Final frontend production build and typecheck pass using bundled Node. **21/21 real Vitest tests pass**, across six files.
- [x] Ten focused launcher checks pass within the backend suite: invalid/truncated/modified/duplicate/traversal checksum inventories; offline verification; active-check refusal; cross-process instance lock; shutdown error propagation; relative state-directory resolution.
- [x] Normal startup confirms the four exact references. Duplicate startup reuses the instance; CHECK refuses a running instance instead of silently skipping.
- [x] Normal stop and warm restart pass. Warm restart performs the full four-scenario HTTP recheck and does not create another import. Database process marker is absent after shutdown.
- [x] Actual relocated SSD execution: Python/GIS modules import from `E:\Ukai\Ukai_SSD_Ready`; its launcher starts the API/frontend and passes all four scenario/resource checks, using the already created isolated local database. `SSD_SMOKE_RESULT.json` records that SSD source root and successful clean stop. This is a relocation check on the current laptop, not a second-laptop test.
- [x] Frontend development configuration uses the portable API on 8766 and development port 5175; the final build/typecheck and 21 tests pass. The working-folder sealing helper targets an explicit test folder and leaves the baseline manifest unchanged; its own digests verify.
- [x] Receiving state is separate from the distribution. No live database directory or machine credentials are shipped. Large original scientific files and the full fast-solver environment remain separate.
- [x] SSD is NTFS and the initial full-folder transfer completed successfully. Final checksum/relocation outcome is recorded by `SSD_PACKAGE_REPORT.json` and the separate transfer-verification result after final sealing.

Evidence: `ssd-full-backend-tests.log`, `ssd-final-frontend-build.log`, `ssd-final-frontend-tests.log`, `ssd-warm-recheck.log`, `SSD_SMOKE_RESULT.json`, `SSD_WORKFLOW_RESULT.json`, and the transfer records in this evidence folder.

## Exact limits

- [ ] New automated visual/browser screenshots. Chrome and Edge in the restricted execution environment terminate in crash-handler setup before loading an app page. The browser report contains **zero performed UI checks and zero screenshots**. This is recorded as not performed, not a pass. The workflow aggregate therefore correctly reports false when it includes that browser step, even though backend/HTTP/start-stop steps passed.
- [ ] Receiving-laptop WebGL/layout acceptance. Earlier working-laptop visual checks of 16 combinations were reported by the user; they are not a new independent test of this portable copy on a different device.
- [ ] Physical network-disconnection check. App code and assets use local services; no test in this session disconnected the laptop's adapter.
- [ ] Fresh fast-solver operation on another machine. Its solver/compiler/dependencies/large inputs are outside this app distribution. The 20-hour plan makes this an explicit gate.

These limits do not alter the recorded API/resource results. Complete the short receiving-device checklist in `docs/SSD_SETUP_AND_WORK_GUIDE.md` before a live judging demo on that device. The product remains simulated, uncalibrated and not scientifically validated.

## Documents and continuation

`docs/SSD_SETUP_AND_WORK_GUIDE.md` gives setup, start/stop, offline development, rebuild, sealing and versioned SSD exchanges. `docs/HACKATHON_20_HOUR_PLAN.md` starts from the current integrated four-reference frontend and adds arrival reveal, comparison differences, a bounded rapid-model path and explained zone priorities with preparation throughout.

There is no remaining B-01/H02 first-import dependency. The rapid solver remains under evaluation. Recorded older run times support minutes; fresh results must be timed before using a "seconds" claim.
