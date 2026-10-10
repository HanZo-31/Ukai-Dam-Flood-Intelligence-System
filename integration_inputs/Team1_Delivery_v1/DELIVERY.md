# Team 1 delivery — version 1, complete copy for Team 2 (8 Oct 2026)

**Delivery name:** `Team1_Delivery_v1_for_Team2` (a copy of `Team1_Delivery_v1` plus rebuilt dist, test results and overlap review; the original folder is unchanged).
**Base package ID:** `2ccf20b727ac4588a7f3ac39ba68b9ca` (`Ukai_SSD_Ready`, from `SSD_PACKAGE_ID.txt`).
**Delivery ID:** SHA-256 of `CHECKSUMS.sha256`, stored in `DELIVERY_ID.txt` (that file is outside the checksum list).
**Built bundle:** `rebuilt_frontend/dist/assets/index-DwdKibgl.js`, `index-B0V8CshZ.css`. Built on the user's machine; this copy's `dist` was taken from `C:\Ukai\Ukai_SSD_Ready\frontend\dist` with no maps, env files or credentials.

**What this is:** the Team 1 changes to the Ukai Flood Explorer frontend, as a *source overlay* plus documents, demo material and evidence. It is **not** a standalone package. It depends on the baseline package `Ukai_SSD_Ready` (lineage ID `2ccf20b727ac4588a7f3ac39ba68b9ca`); the overlay files are the same ones already in place in `C:\Ukai\Ukai_SSD_Ready\frontend`.

## Contents
| Path | What |
|---|---|
| `source_overlay\frontend\` | 38 Team 1 files (11 modified, 27 added: code, tests, fixtures including Team 2's two contract files), laid out as under `frontend\` |
| `baseline_originals\frontend\` | the original versions of the modified files, for rollback |
| `docs\TEAM2_HANDOFF.md` | what Team 2 / integration must do before merging (backend, routing, schema files, real-service checks) |
| `docs\` | numerical definitions (compare-v1, zone-rule-v1, arrival classes), candidate adapter notes, launch/rebuild/recovery, device acceptance status |
| `demo\` | claims sheet, 90-second opening script, Q&A, work log, three real screenshots, one drawn preview (named `…NOT_A_SCREENSHOT`) |
| `patches\ssd_web_server.candidates.PATCH.md` | written patch for the shared production server; **not applied** (shared file) |
| `rebuilt_frontend\dist\` | the rebuilt production frontend (13 files) |
| `tests_and_results\TEST_RESULTS.md` | which test runs are real, which unconfirmed |
| `OVERLAP_REVIEW.md` | the 11 shared files with baseline vs Team 1 hashes |
| `TEAM1_STATUS_REPORT.md` | one-page-per-topic status: done, pending, issues, next steps |
| `WORK_CHECKLIST.md`, `WORK_EVIDENCE.md` | status per item with evidence E1–E22 and what was not done |
| `FILE_INVENTORY.csv`, `CHECKSUMS.sha256` | every file here with size and SHA-256 |

## What was delivered
1. Arrival timeline in Explore (elapsed model time, hourly steps, reached / not yet reached, play, reset, colour-by).
2. Compare: baseline/candidate naming, swap, extent-difference and arrival-change maps, metric table (compare-v1).
3. Coordinate review zones (5 km squares, zone-rule-v1), "priority for review" wording, unavailable reasons shown.
4. Candidate adapter for contract 1.0.0 and a What-if page (stored lookup only; ML shown unavailable).
5. Methods and limits on the Evidence page; unavailable states for exposure data.
6. 111 automated tests in the user's last real run (121 in my stand-in runner after the contract-alignment change; the user's real rebuild of that change is pending), including real-raster tests matched to independent numpy counts.

## Applying / re-checking
The overlay is already in the working copy. To rebuild: `REBUILD_FRONTEND.cmd`, then `SEAL_WORKING_COPY.cmd`, `VERIFY_COPY.cmd`, `START_SSD.cmd`. To roll back: copy `baseline_originals\frontend\…` over the same paths and rebuild.

## Known gaps — read before relying on this
* **What-if was never run against a real candidate service** (none supplied). Only mocked-HTTP and labelled-fixture tests, which are not integration evidence. The capabilities reader now follows Team 2's published schema and examples (received 8 Oct, E25); that is agreement with the files, not a run against the service.
* The production routing patch is not applied; until it is, the packaged app (port 5174) shows "Candidate service unavailable". The dev server (`DEV_FRONTEND.cmd`, 5175) has the proxy rule.
* Zone-table wrapping fixes are built and viewed (E23). The user reports `VERIFY_COPY.cmd` was run on this build and completed; I did not see its output.
* Not performed: pre-edit hash verification, offline/disconnected test, backend stop/recovery, no-WebGL, full keyboard-only pass, second-laptop test, two rehearsals and backup recording.
* Population, roads, buildings and village names are not available and are not shown. Results are simulated, uncalibrated and not scientifically validated.

No ZIP, no credentials, no database state, no scratch files. Fixtures are used by tests only.
