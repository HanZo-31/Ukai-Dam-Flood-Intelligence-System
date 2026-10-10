# Simulation guide — V05

For the current V05 application, run `VERIFY_COPY.cmd`, then `START_SIMULATION.cmd` (http://127.0.0.1:5176), and use `STOP_SIMULATION.cmd` to stop it. The optional computed launcher retains its separate port 5178. See [Simulation polish status](SIMULATION_POLISH_STATUS.md) for the current changes and evidence.

The material below is preserved historical transfer guidance. Its 5174/8766/55433 baseline ports and test counts are not current V05 acceptance results. `CHECK_SIMULATION.cmd` remains the explicitly labelled baseline-only diagnostic; it does not validate the combined profile. Internal profile/database identifiers intentionally retain their old names to preserve existing local data.

---

# Ukai SSD copy — another Windows laptop

Full instructions: [SSD setup and working guide](docs/SIMULATION_SETUP_AND_WORK_GUIDE.md). Next build stage: [20-hour hackathon work order](docs/HACKATHON_20_HOUR_PLAN.md). Actual checks and limits: [final verification](evidence/SSD_FINAL_VERIFICATION.md).

This is the runnable combined application, with frontend/backend source, production frontend, dependencies, all four verified scenario receipts, native PostgreSQL/PostGIS, Python and Node. No ZIP, installer, Git, account or internet connection is needed for ordinary use. Target: Windows x64 with a current browser.

## Copy and run

1. Copy this **entire Ukai_SSD_Ready folder** onto the SSD. Copy it; do not remove the working laptop's original folders.
2. Safely eject, connect the SSD to the other laptop, and open its Ukai_SSD_Ready folder in Windows File Explorer.
3. Double-click **VERIFY_COPY.cmd**. Wait for COPY VERIFIED. This checks contents, not just file count.
4. Double-click **START_SIMULATION.cmd**. The first run verifies files and creates/imports a local database; allow several minutes.
5. Wait for **READY: 4 scenarios verified**. The normal browser opens **http://127.0.0.1:5174** automatically.
6. Keep the server window open. Do not launch three separate windows; the SSD launcher starts frontend, API and database together.

Ports are separate from the working laptop's original app: frontend 5174, API 8766, PostgreSQL 55433. Everything binds to 127.0.0.1. No remote map/font/script service is required.

## What lives where

The SSD holds the app, code, runtimes and checksum-protected scenario deliveries. The receiving laptop keeps its own writable database, imported objects, credentials and logs under `%LOCALAPPDATA%\UkaiSSD\<instance>`. Its exact location is printed at startup. A local NTFS database avoids putting a live database on a removable/exFAT drive.

The receiver recreates the four stored scenarios from verified receipts. It does not execute HEC-RAS, change source rasters, infer missing provenance, or copy this laptop's active database. Numeric database row IDs and import timestamps may be new; scenario/run IDs, output bytes and manifest identities are retained.

The instance is derived from this package and its current path. Another laptop or SSD drive letter gets a separate local database without corrupting the old instance. Keeping the same drive letter avoids a repeated first-run import. The original laptop's database and ports are untouched.

## Recheck after transfer

Close the running SSD server first, then double-click **CHECK_SIMULATION.cmd**. It verifies all four scenarios and downloads through the frontend proxy, records `SSD_SMOKE_RESULT.json` in the printed local state folder, and stops cleanly. Real browser rendering should also be checked on the receiving laptop, especially its WebGL maps.

## Stop and safely eject

Press **Ctrl+C in the SSD server window**, or run **STOP_SIMULATION.cmd**, and wait for **Stopped**. Close the server window, then use Windows safely-remove/eject. Each laptop has its own local database; the SSD may be transferred after shutdown.

## Troubleshooting

- Port in use: stop another copy using these SSD ports. The launcher will not stop unrelated services.
- First-run error: inspect `setup.log`, `api.log`, `frontend.log` in the local-state folder printed at startup. Do not delete the source packages.
- Map/WebGL issue: inspect the receiving browser's hardware acceleration and the map error text. The data and raster renderings still need that device's browser check.
- Editing code: frontend source, lockfile and Windows node_modules are included. Node/npm are bundled under `runtime/node`. Original developer scripts referring to `.venv`/`.quality` should use `runtime/python/python.exe`/`runtime/quality/python.exe` instead; ordinary launch needs only START_SIMULATION.cmd.

## Scope and remaining records

This transfers **Ukai_Combined**, not the large original scientific workspace outside it. For a full scientific archive, separately copy the original `C:\Ukai` folders, including large HEC-RAS result/terrain files and fast-solver work. Those external files are not needed to run the combined app.

The models remain simulated, uncalibrated and not scientifically validated. Missing licences/timezones/exposure data stay explicitly unknown. Original audit history is retained; older launch URLs in those records describe the working laptop. Follow this SSD guide for the portable copy.
# Integration V01 update

For this combined copy, use [START_INTEGRATION.md](START_INTEGRATION.md) and **http://127.0.0.1:5176/**. The original SSD guide below describes the earlier baseline's ports and acceptance results, not the current combined release.
