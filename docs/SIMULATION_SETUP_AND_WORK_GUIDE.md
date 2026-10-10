# Simulation guide — V05

For the current V05 application, run `VERIFY_COPY.cmd`, then `START_SIMULATION.cmd` (http://127.0.0.1:5176), and use `STOP_SIMULATION.cmd` to stop it. The optional computed launcher retains its separate port 5178. See [Simulation polish status](../SIMULATION_POLISH_STATUS.md) for the current changes and evidence.

The material below is preserved historical transfer guidance. Its 5174/8766/55433 baseline ports and test counts are not current V05 acceptance results. `CHECK_SIMULATION.cmd` remains the explicitly labelled baseline-only diagnostic; it does not validate the combined profile. Internal profile/database identifiers intentionally retain their old names to preserve existing local data.

---

# Ukai SSD setup and working guide

Prepared 8 October 2026. This guide applies to the combined application and its four stored reference scenarios. Read `evidence/SSD_FINAL_VERIFICATION.md` for the current verification results. The 20-hour work order is `docs/HACKATHON_20_HOUR_PLAN.md`.

## 1. Folders and what they contain

| Location | Purpose |
| --- | --- |
| `E:\Ukai\Ukai_SSD_Ready` | Prepared app on this SSD: frontend and backend source, built frontend, Windows runtimes/dependencies, four scenario receipts, launchers, guides and evidence. |
| `C:\Users\LENOVO\Documents\Codex\2026-10-07\files-mentioned-by-the-user-start\Ukai_SSD_Ready` | Matching prepared laptop copy. |
| `C:\Users\LENOVO\Documents\Codex\2026-10-07\files-mentioned-by-the-user-start\Ukai_Combined` | Original combined working project. Its original launch method uses different ports. |
| `C:\Ukai\Ukai\part_a_handoff\fast_solver` | Separate existing fast-solver source/results on Team A's laptop. This app distribution does not include a complete solver environment or the large original scientific workspace. Inventory and deliver those essentials in the 20-hour plan. |
| `%LOCALAPPDATA%\UkaiSSD\<instance>` | A laptop's own writable database, imported objects, credentials, logs and recheck result. Startup prints the exact folder. |

Another laptop may assign the SSD a letter other than `E:`. Open the actual SSD folder; the launchers find their own location. Keep the prepared distribution as the recovery baseline. No ZIP or Git operation is needed.

The former B-01/H02 contract exchange and first genuine import are already complete. All four reference scenarios are integrated. Do not restart that old handoff sequence.

## 2. First run on another Windows laptop

Requirements: Windows x64, a current browser with WebGL for the raster maps, and free local disk space for the database and scenario objects. Allow at least 2 GiB free local disk space in addition to the app folder. Bundled runtimes cover ordinary app startup; the experimental fast solver has separate requirements.

- [ ] Stop the app before disconnecting the SSD: use `STOP_SIMULATION.cmd`, and wait for **Stopped** in its server window.
- [ ] Safely eject the SSD, connect it to the other laptop, and open `Ukai_SSD_Ready` in File Explorer.
- [ ] Double-click **VERIFY_COPY.cmd**. Wait for **COPY VERIFIED**. If it fails, read the named missing/changed file and recopy the matching prepared folder. Do not reseal a damaged transfer just to suppress the failure.
- [ ] Double-click **START_SIMULATION.cmd**. The first run creates that laptop's database and imports the four receipts. Allow several minutes; leave the window open.
- [ ] Wait for **READY: 4 scenarios verified**. The browser should open `http://127.0.0.1:5174`. If it does not, open that address yourself.
- [ ] Confirm H01, H02, H03 and reconstructed 2006 appear. Inspect Explore, Compare and Evidence.
- [ ] Perform the receiving-device map check in section 4, then stop cleanly and restart once.

Do not run `npm install`, install a database server, use Docker, or launch separate frontend/backend windows for ordinary use. The single launcher starts the built frontend, API and database. `START_UKAI.cmd`, `START_FRONTEND.cmd` and `START_FRONTEND_PREVIEW.cmd` in this distribution are aliases to that same launcher.

| Service | Address/port |
| --- | --- |
| Built application | `http://127.0.0.1:5174` |
| Local API | `127.0.0.1:8766` |
| Local PostgreSQL | `127.0.0.1:55433` |
| Optional frontend development server | `http://127.0.0.1:5175` |

All app services bind to loopback. Another device cannot use this laptop's `127.0.0.1` address. Each laptop runs its own copy and local state.

## 3. Daily start, stop, transfer and backup

Start with `START_SIMULATION.cmd`; keep its window open. A second launch reuses the running instance. Run only one portable copy on a laptop at a time because the portable ports are fixed.

To stop, press Ctrl+C in that server window or double-click `STOP_SIMULATION.cmd`. Wait for **Stopped** before removing the SSD. Closing a browser tab does not stop the services. A stop command from a different copy/path targets a different local instance; use the launcher from the folder you started.

The SSD stores immutable scenario deliveries and the app. The live database and imported objects live on the laptop. Moving to another laptop recreates them from the same receipts; this is expected. Changing the app's path/SSD letter can create another local instance and repeat first-run import. This does not transfer another laptop's run history. Copy any new candidate result folders and demo evidence explicitly.

After intentional code changes, retain a previous passing plain-folder delivery, rebuild/recheck the new working copy, and create a new delivery ID. Do not copy a running database directory or machine credentials to another laptop. To preserve a local database history, use its supported stopped/database-export workflow as a separate task; reference replay only needs the shipped receipts.

## 4. Recheck and receiving-device visual acceptance

Close the running portable app and run **CHECK_SIMULATION.cmd**. It starts its own services, verifies four scenario/run identities and all 24 resources through the frontend proxy, checks full hashes, HEAD and byte-range behavior, writes `SSD_SMOKE_RESULT.json` into the printed local state folder, and stops. **RUN_FULL_RECHECK.cmd** is an alias to this portable smoke check; it does not run the 902-test developer suite.

Then start the app and complete this checklist on the actual receiving laptop:

- [ ] For each of the four scenarios, select **Extent, Depth, Velocity and Arrival**: all 16 combinations render without an error message. Nodata remains unavailable; raster layers use the shared legends.
- [ ] Compare two different scenarios: the table and both maps load, pan/zoom stay linked, and layer changes apply to both.
- [ ] Evidence shows engine, simulation/uncalibrated labels, limitations, units, model-clock context and the stored JSON previews.
- [ ] Open at least one raster and one JSON download. The automated smoke checks cover all 24 complete resources and their hashes.
- [ ] At a narrow window/mobile-sized width, the sections remain accessible without sideways page scrolling.
- [ ] Stop the app: its page reports that the API is unavailable. Restart it and confirm recovery.
- [ ] When convenient, test normal use with internet disconnected. Save locally required packages/data first; do not interrupt a call/download merely to perform this check.
- [ ] Save the receiving device, date, browser, package ID and pass/fail notes in a separate `DEVICE_ACCEPTANCE.md` outside the sealed distribution.

The automated browser launcher in this restricted execution environment cannot reliably start Chrome/Edge: both terminate in their crash-handler setup before an app page is loaded. This is recorded as **not performed**, not a successful screenshot test. Earlier working-laptop visual checks were reported in the project conversation; they do not establish rendering on a different GPU/browser. The receiving-device check above is still required.

## 5. Work on code without losing the baseline

For the 20-hour work, use each machine's local disk. Recommended working locations are:

```text
Machine A: C:\Ukai_Work\team_a\Ukai_SSD_Ready\
Machine B: C:\Ukai_Work\team_b\Ukai_SSD_Ready\
SSD exchanges: <SSD>\Ukai\hackathon_work\exchanges\team_a\<delivery_id>\
               <SSD>\Ukai\hackathon_work\exchanges\team_b\<delivery_id>\
```

- [ ] Copy the entire prepared folder into the relevant local working location. Keep the folder name `Ukai_SSD_Ready`; keep the SSD baseline intact.
- [ ] Verify the new local copy **before editing it**, then start it once. Its local runtime state is separate because the path differs.
- [ ] Assign owners: Team A handles scientific inputs, solver/candidate packaging and comparison evidence; Team B handles frontend/API consumption and interface changes. Agree contracts together. Do not have two assistants edit the same file at once.
- [ ] Give an assistant the exact local working root, relevant files, current request/result contract and the narrowly scoped task from the 20-hour plan. Tell it to preserve references and report actual tests.
- [ ] Record edits, limitations and the result of the affected checks. Do not re-run every old check after a prose-only edit.

### Frontend development and rebuilding offline

1. Run `START_SIMULATION.cmd` in the local working copy and wait for readiness.
2. Run **DEV_FRONTEND.cmd**. Open `http://127.0.0.1:5175`. This development frontend proxies to the portable API on 8766; no original-project port change is needed.
3. Edit `frontend\src\`. Existing Windows dependencies are included. Do not install or upgrade packages during offline use unless you already have a complete local replacement.
4. Stop the development window with Ctrl+C. Run **REBUILD_FRONTEND.cmd**: it builds/types-checks and runs the frontend tests using bundled Node.
5. Stop/restart `START_SIMULATION.cmd`; verify the built app on 5174. Only rebuilt `frontend\dist\` is served by the ordinary launcher.

If a build/test fails, keep the previous passing delivery and fix the named error. A source edit alone does not update the ordinary built app.

### Backend and new result work

Use bundled `runtime\python\python.exe` for app scripts, and `runtime\quality\python.exe` for the separate quality tools. The app uses Python 3.12.4; its packed backend has been regression-tested. A conventional `.venv` is not shipped. The old source/handoff scripts remain available but their historic commands are not portable startup instructions.

The current four receipts and preview admission are a fixed reference set. A new fast-solver/surrogate result does not automatically appear by copying a TIFF beside them. Agree its manifest/context units and engine identity, preserve native results, validate/import a new candidate delivery into an isolated target, then update candidate admission through the supported integration path. Follow the 20-hour candidate-interface gate; do not edit the reference receipt manifests, change their hashes to fit new assets, or simply set scientific validation to true.

Native fast-solver build/runtime dependencies, input terrain/geometry/hydrographs and tuned arrays are separate from this app bundle. Team A must inventory and transfer them with their compatible environment before promising fresh calculations on another device. The older `-march=native` DLL build is not proof of CPU portability.

### Sealing an intentional new working delivery

- [ ] Stop the app and finish the relevant build/tests and acceptance notes.
- [ ] Write `DELIVERY.md` with a new delivery ID, owner, base package ID, changed files, commands, test results and limitations. Retain the unchanged base package ID as lineage; the new delivery's checksum manifest identifies its actual bytes.
- [ ] Run **SEAL_WORKING_COPY.cmd** in that edited working folder. It explicitly seals that folder only. This records bytes; it does not validate the software.
- [ ] Run **VERIFY_COPY.cmd** and confirm success against the new checksum inventory.
- [ ] Copy a new plain versioned delivery to the SSD exchange folder. Never overwrite an acknowledged delivery or the prepared baseline.
- [ ] The receiver verifies the delivery and acknowledges its ID before integrating the agreed changed files. Keep its database state local.

## 6. Troubleshooting

| Symptom | Action |
| --- | --- |
| Browser cannot connect | Keep the correct server window open; wait for READY; use 5174 for the built portable app. Inspect printed local `setup.log`, `api.log`, `frontend.log` if readiness fails. |
| Port already used | Stop the other portable copy on that laptop using its own STOP launcher. Do not kill an unrelated service or the original combined app. |
| COPY VERIFICATION FAILED | Compare the exact named files with the passing distribution. For a damaged transfer, recopy. For intentional edits, test and seal a new working delivery; keep the baseline evidence separate. |
| CHECK says to stop the app | Stop the portable server first. The checker refuses to silently skip its work while an instance is running. |
| Database creation error | Read `setup.log`. An incomplete database directory is preserved for diagnosis. Do not delete scientific/source folders or suppress the error by pretending imports ran. |
| Map error, table works | Check browser WebGL/hardware acceleration and the displayed error. Preserve the device acceptance failure; use the verified table/evidence until rendering is corrected. |
| API connected while data fail | The health badge is a process health check; a database/query failure can still appear in the page banner. Use the actual data error and logs, not the badge alone. |
| Edited frontend does not appear | Build it with REBUILD_FRONTEND, then restart the ordinary app. The 5174 app serves the stored build. |

The model labels remain: HEC-RAS reference simulations; fast solver under evaluation for speed; optional surrogate only after its held-out gate; decision layer for comparisons and priorities for review. The system does not claim calibrated forecasts or operational emergency advice.
