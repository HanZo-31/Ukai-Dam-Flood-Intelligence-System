# Launch, rebuild and recovery

* Rebuild the frontend (bundled Node): double-click `REBUILD_FRONTEND.cmd` in `Ukai_SSD_Ready` (runs `npm run build` = `tsc --noEmit && vite build`, then `npm test`). Read the last lines for pass/fail.
* Run the packaged app: `START_SSD.cmd` → http://127.0.0.1:5174 (API 8766, database 55433). Stop with the package's stop script / closing its window.
* Development frontend with the candidate proxy rule: `DEV_FRONTEND.cmd` → http://127.0.0.1:5175.
* Baseline recovery: the original verified distribution (RAR parts / SSD copy) is untouched; my changed files' originals are in `C:\Ukai\Team1_work\baseline_originals\`. To undo Team 1's edits, copy those originals back over the same paths under `frontend\src` and rebuild.
* Verify a copy: `VERIFY_COPY.cmd`. After edits, seal: `SEAL_WORKING_COPY.cmd`.
* If the candidate service is not running, only the What-if page is affected; press "Try again" after starting it.
