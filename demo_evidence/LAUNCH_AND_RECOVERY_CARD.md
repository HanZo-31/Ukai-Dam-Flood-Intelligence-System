# Ukai local demo: launch and recovery card

Release: `ukai-combined-20261009-v02-polished`.

## Start

1. Open this complete plain project folder on the final demo laptop.
2. Run `VERIFY_COPY.cmd` after a transfer or if corruption is suspected.
3. Run `START_COMBINED.cmd`. Keep the launcher window open and wait for READY.
4. Open http://127.0.0.1:5176/ and confirm API connected and four scenarios.
5. Start with **Explore** and follow the separate demo script. Use the demonstrated stored-reference path, not a new solver run or ML prediction.

Loopback-only ports: web 5176, reference API 8767, candidate service 8770, PostgreSQL 55434. The launcher refuses collisions; never kill an unknown process just to free a port.

## Recover

- A layer fails: use **Retry map layer**. If raster graphics are unsupported, choose **Use extent outline**. Compare tables and original downloads remain usable without WebGL.
- A comparison fails: use **Retry comparison**; check that the backend is running.
- Candidate service unavailable: Explore, Compare and Evidence remain the fallback. Stop and restart the combined launcher, then use Try again in What-if. Do not present an old successful result as a newly computed one.
- API unavailable: run the combined launcher, wait for READY, then retry. A disconnected badge is not a ready result.
- Whole application cannot start: retain the failure and use the labelled screenshot backup, or stop V02 cleanly and launch the preserved V01 copy. Do not run two copies on the same ports.

The optional URL http://127.0.0.1:5176/?raster=off deliberately disables raster rendering to exercise recovery. It does not establish that the laptop actually lacks WebGL. Return to the normal URL to restore raster mode.

## Stop

Run `STOP_COMBINED.cmd` or press Ctrl+C in the launcher. Wait for “Stopped” before closing the launcher or removing an SSD. Private database state and credentials remain outside the delivered project folder.

## Physical offline acceptance — operator action required

AI/browser verification is not evidence that Wi-Fi/Ethernet was physically disconnected. After preparation, on this final demo laptop:

- [ ] Stop the combined application and wait for Stopped.
- [ ] Disconnect Wi-Fi/Ethernet manually without changing security settings.
- [ ] Start the application cold; note the timezone-aware date/time.
- [ ] Complete Explore → Timeline → Compare/zones → What-if → Evidence.
- [ ] Confirm no required asset, font, basemap or API needs the internet.
- [ ] Open `DEMO_BACKUP.html` directly and confirm its screenshots load locally.
- [ ] Stop and restart once; record the result and any error.

Record the actual outcome in a new evidence file outside the sealed delivery. Do not tick these boxes merely because static source checks or online localhost tests passed.
