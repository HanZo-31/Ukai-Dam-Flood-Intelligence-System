# Team 1 → Team 2 / integration: what is needed before merging

## Short answer
Team 1's features (arrival timeline, Compare differences, review zones, Evidence methods) need **no new backend work**. They read the existing stored rasters through the existing reference API (port 8766) and compute in the browser.

**Only the What-if page depends on Team 2**, and it cannot be called integrated until the items below are done.

## Needed from Team 2 (backend / integration)
1. **Candidate service running on 127.0.0.1:8770** implementing contract v1.0.0: `GET /api/v1/candidates/capabilities`, `POST /api/v1/candidates/jobs`, `GET /api/v1/candidates/jobs/{job_id}`. Stored lookup only (`computed:false`, `scientifically_validated:false`, `calibration_status:"uncalibrated"`, ML disabled).
2. ~~Schema files~~ **Received 8 Oct** and applied on Team 1's side (E25). Nothing further needed unless the contract version changes.
3. **Production routing** (shared file, not edited by Team 1): apply `patches/ssd_web_server.candidates.PATCH.md` to `scripts/ssd_web_server.cjs` so `/api/v1/candidates` goes to 8770 while everything else stays on 8766. Have the supervisor/launcher start the candidate service on 8770 (or set `UKAI_CANDIDATE_PORT`).
4. **Real-service checks** (listed in `CANDIDATE_ADAPTER_NOTES.md`): capabilities; POST 20000 exact; POST 26000 without and with `allow_nearest_stored`; repeated request ID (same content = same job, different content = 409); unknown job (404); stop the service mid-session and recover. Results must only reference `/api/v1/prototypes/scenarios/<source_scenario_id>` resources.

## Merge steps (integration owner)
1. Take `source_overlay\frontend\` into the frontend (already in `C:\Ukai\Ukai_SSD_Ready` for this working copy).
2. Apply the routing patch and add the service start (items 1 and 3).
3. `REBUILD_FRONTEND.cmd` (expect 14 test files, 121 tests after the contract-alignment change; 111 before it), then `SEAL_WORKING_COPY.cmd`, `VERIFY_COPY.cmd`, `START_SSD.cmd`.
4. Browser regression: Explore timeline, Compare H01→H02 (new flooded 92,736 cells = 77.99 km²; 53 of 133 zones), same-scenario zero, Evidence methods, What-if with the service stopped and then running.
5. Rollback: copy `baseline_originals\frontend\…` over the same paths and rebuild.

## Not Team 2's work
Population, buildings, roads and village names remain "not available"; nothing for them was requested from the backend.

## Update 8 Oct evening: Team 2's own proxy
Team 2's status report says its combined runtime already routes `/api/v1/candidates` to port 8770 in its own proxy (`assembly\ssd_web_server.cjs`, combined app on 5176, reference API on 8767). If that proxy is the one used for the merge, item 3 above (Team 1's routing patch) is not needed; use Team 2's proxy and serve Team 1's rebuilt `dist`. Team 1 has not seen or tested that proxy.
