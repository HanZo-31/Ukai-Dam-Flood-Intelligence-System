# Fresh integration evidence

All reports here describe this local combined copy, unlike retained baseline reports. Time stamps include UTC/offset where applicable. No live database, private configuration, credentials or test scratch is included.

Reading order:

1. `RECEIVING_VERIFICATION.json`: immutable inputs, delivery IDs, baseline hashes, original-file overlap and contract comparison. It intentionally says integration was not yet accepted at receipt time.
2. `frontend-v03/`: final production build/typecheck and unit tests (124 pass + seven explicit live skips without a configured target).
3. `frontend-live-v02/`: full 131-pass frontend suite including real HTTP adapter calls.
4. `backend-regression-v01/`: 985 backend passes, four Windows skips, one existing warning; owned target, unchanged catalog/source, clean shutdown.
5. `lifecycle-v01/report.json`: isolated cold-start, duplicate use, candidate interruption and restart proof. Private state and role/setup logs are deliberately omitted.
6. `resources-v01/report.json`: four real receipts and all 24 download checks through the new proxy.
7. `browser-v01/`: actual merged UI screenshots and scope/timing record. No physically disconnected network, forced no-WebGL, second device, full keyboard audit or rehearsal video is claimed.
8. `attempts/`: retained test-wrapper / content-type-assumption failures and their correction history; not passing evidence.
9. `tools/`: receiving/build/resource verification helpers. These never install dependencies or run hydraulic simulations.

Recorded baseline and input-team evidence remains under `evidence/`, `team2_work/evidence/` and `integration_inputs/`; its old paths/counts and unavailable-delivery statements are historical snapshots, not current integration blockers.

## Reproduce affected checks

From the complete application folder, while `START_COMBINED.cmd` is ready:

```powershell
& .\runtime\node\node.exe .\runtime\node\node_modules\npm\bin\npm-cli.js run build --prefix frontend
$env:UKAI_CANDIDATE_TEST_BASE = 'http://127.0.0.1:5176'
& .\runtime\node\node.exe .\runtime\node\node_modules\npm\bin\npm-cli.js run test --prefix frontend -- --maxWorkers=2 --minWorkers=1
Remove-Item Env:\UKAI_CANDIDATE_TEST_BASE
```

For builds, add the bundled `runtime/node` directory to that terminal's PATH as `REBUILD_FRONTEND.cmd` does. Build output changes require resealing. `REBUILD_FRONTEND.cmd` runs ordinary unit-only mode; live tests are explicitly skipped unless the target variable is set.

Backend regression reproduction is an intentional separate-state operation: use `team2_work/probe_combined_runtime.py --source <this-folder> --output <new-external-evidence-folder>` first, then `team2_work/run_final_regression.py --source <this-folder> --state <that-output>/local-runtime-state --output <another-fresh-external-folder>`. Do not use the baseline database, a live transferred database, or output folders inside the app. Helpers preserve logs and stop their own profiles. Do not repeatedly run a full suite just to refresh unchanged evidence.

After a deliberate source change: repeat affected checks, `SEAL_WORKING_COPY.cmd`, then `VERIFY_COPY.cmd`. Neither sealing nor hash verification proves scientific correctness or a successful operator rehearsal.
