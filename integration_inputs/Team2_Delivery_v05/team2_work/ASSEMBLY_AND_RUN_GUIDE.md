# Team 2 — combined runtime and final assembly

## Required local inputs

Use the complete verified `Ukai_SSD_Ready` distribution: package ID `2ccf20b727ac4588a7f3ac39ba68b9ca`, bundled Python 3.12.4, Node and PostgreSQL, existing backend/dependencies, built frontend and all four receipts. The Team 2 overlay contains no copied runtime, database, mutable jobs or credentials. Windows x64 and sufficient writable local disk space are required; allow at least 2 GiB beyond the immutable app files as the baseline guide recommends.

On another computer, copy and verify the complete baseline and this plain overlay. Retain both originals as recovery inputs. Do not install dependencies or move a live database.

## One-command combined start/stop

Run from the delivered `team2_work` folder:

```powershell
.\START_TEAM2.cmd "D:\Window C2\Projects Works\Ukai_SSD_Ready"
```

The argument is the actual complete baseline folder; substitute the receiver's path. Alternatively set `UKAI_REFERENCE_ROOT` before running the CMD launchers. If the overlay is installed as `<baseline>\team2_work` in a **new assembly copy**, the launchers can locate the adjacent bundled runtime; do not insert it into the preserved baseline.

| Role | Default loopback port |
| --- | --- |
| Built frontend and same-origin proxy | 5176 |
| Actual reference API | 8767 |
| Candidate fallback service | 8770 |
| Separately owned PostgreSQL | 55434 |

Wait for READY; open `http://127.0.0.1:5176`. Keep the launcher window open. CMD pauses after the process exits so errors remain visible. Stop with Ctrl+C or:

```powershell
.\STOP_TEAM2.cmd "D:\Window C2\Projects Works\Ukai_SSD_Ready"
```

Stop requests are asynchronous: wait for **Stopped** in the server terminal. Removing an SSD or closing the browser is not a stop operation.

Default state is `%LOCALAPPDATA%\UkaiTeam2\<hash-of-absolute-baseline-path>`. It contains ownership/status, database, imported objects, credentials, role logs and candidate jobs and must stay local/private. Relocating the baseline path creates a new local profile and first-run import. Repeated launch at the same owned profile reuses the live instance; warm restart reuses imports and saved jobs. Changing port profiles requires a separate state root.

The sealed baseline is verified before first owned initialization. Its verification cache is an initialization optimization, not a new full hash audit on every start. Run the baseline VERIFY_COPY command and overlay receiver verification after transfer or suspected corruption.

## Explicit CLI profile

From the delivered folder:

```powershell
$ukaiSource = 'D:\Window C2\Projects Works\Ukai_SSD_Ready'
$ukaiState = Join-Path $env:LOCALAPPDATA 'UkaiTeam2\demo-custom'
& "$ukaiSource\runtime\python\python.exe" -B .\combined_runtime.py --source $ukaiSource --state $ukaiState --db-port 55434 --api-port 8767 --web-port 5176 --candidate-port 8770 --no-browser
```

In another terminal use exactly the same source/state/ports plus `--stop`. CMD launchers use the defaults; they do not stop custom profiles. `--no-browser` avoids browser launch but still starts services. All services bind 127.0.0.1. Occupied ports are reported, never cleared by killing unrelated processes.

Startup scrubs inherited database/profile variables and initializes only its owned target using existing baseline helpers. A nonempty unowned state folder or changed ownership/profile is refused. Do not edit owner markers or delete private state to suppress a failure.

## Candidate adapter

Use same-origin `/api/v1/candidates/...` through port 5176. Direct development can use `http://127.0.0.1:8770`; permitted development CORS origins remain the contract's 5174/5175. Return URLs under `/api/v1/prototypes/...` are reference resources; resolve them through the reference API adapter, not directly against 8770.

The baseline frontend remains unchanged and does not acquire a candidate UI just because the endpoint exists. Team 1 must deliver its adapter/build. Capabilities disables experimental ML; current jobs are immediate stored selections, not queued simulations. Unknown intermediate releases reject unless nearest reference is explicitly enabled; show both requested and actual peak.

For isolated candidate development only:

```powershell
& "$ukaiSource\runtime\python\python.exe" -B .\run_candidate_service.py --source $ukaiSource --state (Join-Path $env:LOCALAPPDATA 'UkaiTeam2\candidate-only') --port 8770
```

Use Ctrl+C to stop. This path does not start the reference API; do not run it simultaneously on the same candidate port as the combined supervisor.

## Recovery

Correction release v04 rechecks owned status, the actual four-reference catalog and candidate capability before duplicate reuse. A matching proxy with stale/failed status or unreachable API is not reported as ready; no unrelated process is stopped. Investigate the matching local status/logs and use a clean owned restart. Do not edit ownership markers to force reuse.

Candidate documentation is now a self-contained offline reference at http://127.0.0.1:8770/docs with no external assets, and raw schema at /openapi.json. Interactive CDN Swagger/ReDoc is deliberately not provided. The contract/schema1.0.0 remains unchanged. New and cached lookups now rehash all manifest-bound input files as well as artifacts/evidence.

If candidate exits after readiness, the supervisor records `ready_candidate_unavailable`; reference API/frontend stay usable and candidate proxy requests return an explicit 503. Stop the owned combined instance, wait for Stopped and restart to restore candidate service and saved jobs. API/frontend exit triggers owned cleanup, not a misleading ready status.

Inspect printed state-folder `combined-status.json`, `setup.log`, `api.log`, `candidate.log`, `frontend.log` locally. Do not distribute database URLs/password files. Shutdown failures remain failures and require investigation before ejecting. No blanket process kill or recursive state deletion is authorized.

Rollback: stop Team 2 cleanly and launch the retained baseline with its original START_SSD.cmd (5174/8766/55433). Baseline bytes and working state were not rewritten. Candidate job history stays in the separate Team 2 profile.

## Final Team 1 assembly, currently blocked

1. Receive Team 1's exact plain-folder delivery ID/source/build/inventory/checksums and verify it before copying.
2. Compare both inventories; Team 1 owns frontend source/build, Team 2 owns candidate service/supervisor. Deliberately reconcile any proxy/launcher overlap; do not replace a newer folder blindly.
3. Create a new complete assembly copy outside the preserved baseline. Apply declared Team 1 source and rebuilt artifacts there; add this overlay as `team2_work`.
4. Start against the new assembly copy; the supervisor serves that copy's `frontend/dist` and initializes separately owned reference state. Current configurable bridge already routes the candidate namespace; keep reference routing intact.
5. Verify real user journey, units, IDs, returned resources, requested/actual peaks, loading/error/unavailable labels and ML disabled state.
6. Run affected frontend checks and final assembled regression, then seal a new version. The current baseline-build evidence is not that final acceptance.

Fresh backend/source results are in WORK_EVIDENCE.md. Device/browser/offline/recording requirements are in DEMO_AND_ACCEPTANCE.md. No scientific/publication gate is relaxed.
