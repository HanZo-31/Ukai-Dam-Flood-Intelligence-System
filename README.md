Ukai Dam Flood Intelligence System — V05

A locally runnable flood-scenario explorer for Ukai Dam. Explore four stored reference simulations, inspect locations, compare scenarios and access supporting evidence. A separate experimental computed-run workflow uses the supplied fast solver when its capability checks pass.

**Scientific status:** experimental and uncalibrated. This is not a validated real-time forecast, public warning service, evacuation advisor or dam-control system. Missing data is not zero flooding or confirmed safety. ML prediction remains unavailable under the current acceptance requirements.

## Features

- **Explore:** H01, H02, H03 and reconstructed 2006, with depth, arrival-time and velocity layers.
- **Model time:** arrival-based reveal relative to simulation start. Maximum-depth layers are maxima over the run, not instantaneous depth snapshots.
- **Point inspection:** click the map or enter coordinates to inspect available original-cell values.
- **Compare:** paired views and eligible differences, with explicit unknown-coverage handling.
- **What-if:** separate experimental computed runs, not automatic replacement or approval of references.
- **Evidence:** provenance, limitations and available downloads.
- **Light terrain:** optional local display background; unknown units, datum and licensing remain explicit. 

## Quick start — complete Windows package

### Requirements

- Windows x64 and a browser with WebGL support.
- Complete matching V05 package, including `runtime/`, `frontend/dist/`, installed dependencies and scenario assets.
- At least 2 GiB free local space beyond the package for stored-reference setup; computations can require more.
- A trusted local computer. Services bind to `127.0.0.1`; no application login or public hosting is required.

Ordinary portable startup does **not** require Docker, a separately installed database, `npm install` or a new Python virtual environment.

### 1. Open the project folder

Open your complete `UKAI_COMBINED_V05` in File Explorer. You should see:

text
VERIFY_COPY.cmd
START_SIMULATION.cmd
STOP_SIMULATION.cmd
runtime/
frontend/
receipts/


The parent folder and drive letter can differ between computers. Launchers find their own location.

### 2. Verify the received package

Double-click **VERIFY_COPY.cmd** and wait for **COPY VERIFIED**.

If verification fails, stop and inspect the named missing or changed file. Restore a matching verified delivery. Do not reseal an unexplained damaged copy just to hide the error.

**Intentional edits:** this README update changes sealed bytes. A maintainer must refresh the full non-Git delivery inventory/checksums before verification can pass for the new documentation. See the integrity section below.

### 3. Start

Double-click **START_SIMULATION.cmd**. Keep its window open.

The first run prepares machine-local state and imports the shipped references. Allow several minutes and wait for readiness. A candidate-unavailable readiness message means experimental computation is unavailable; it does not authorize fabricated results.

### 4. Open the website

Open **http://127.0.0.1:5176/** if the browser does not open automatically.

| Default profile service | Loopback port |
|---|---|
| Built frontend | 5176 |
| Reference API | 8767 |
| Candidate service | 8770 |
| PostgreSQL | 55434 |

`START_COMBINED.cmd` is another entry point to this default profile.

### 5. Check basic operation

1. Confirm all four reference scenarios appear.
2. Select a scenario and try Depth, Arrival time and Velocity.
3. Move the model-time slider and inspect a location.
4. Open Compare and select different scenarios.
5. Open Evidence and check available downloads and limitations.

An API-connected indicator shows connectivity, not scientific validation or successful rendering of every asset.

### 6. Stop safely

Double-click **STOP_SIMULATION.cmd** from the same project folder, or press **Ctrl+C** in its launch window. Wait for shutdown before disconnecting an SSD.

Closing the browser does not stop services. Do not kill unrelated processes to free a port.

## Optional separate computed profile

1. Start **START_COMPUTED.cmd** and wait for readiness.
2. Open **http://127.0.0.1:5178/**.
3. Open What-if, then the experimental computed-run page.
4. Use inputs permitted by the reported capabilities. The documented peak-release range is 15,000–30,000 m³/s within the supplied hypothetical forcing family.
5. A request may execute the native solver; identical inputs may reuse explicitly labelled checked cache.
6. Stop with **STOP_COMPUTED.cmd** from the same folder.

| Computed profile service | Loopback port |
|---|---|
| Built frontend | 5178 |
| Reference API | 8786 |
| Candidate service | 8778 |
| PostgreSQL | 55438 |

Do not interchange the profiles' stop scripts. For beginners, run one profile at a time.

Computed outputs are not automatically imported or scientifically approved. HEC-RAS references and fast-solver outputs are different engine products; their comparison does not establish accuracy or isolate release effects.

See [computed workflow and limits](START_COMPUTED_HERE.md). Older UI-status entries in that document are historical.

Project structure


frontend/             React, TypeScript, OpenLayers, Vite; UI and map tests
services/api/         FastAPI service, schemas, repositories and endpoint tests
database/             PostgreSQL/PostGIS initialization and migrations
scripts/              Validation, registration, packaging and local utilities
rapid_engine/         Experimental provider and solver integration
computed_contract/    Computed-run contract and examples
team2_work/           Candidate service and combined runtime orchestration
native_received_v01/  Native fast-solver source and artifacts
part_a/               Scientific source inputs and supporting deliveries
receipts/             Stored reference deliveries and assets
solver_inputs_v01/    Supplied solver inputs
solver_env/           Native dependencies and isolated environment identity
runtime/              Bundled Windows runtimes; excluded from Git upload
docs/                 Contracts, runbooks and historical handoff reports
tests/                Shared/backend tests
*_evidence/           Recorded integration, verification and interface evidence


The portable application uses bundled Python. Earlier B1/B2 instructions mentioning Python 3.13, Docker, `.venv` or different ports are historical development workflows, not this quick start
