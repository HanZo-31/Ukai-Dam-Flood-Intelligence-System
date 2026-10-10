# Device, browser and offline acceptance

Quoted from the package report (not repeated by Team 1): automated browser/screenshot checks, second-laptop test and internet-disconnection test were **not performed**.

Team 1 checks still to be performed on the laptop (none done yet):
1. `REBUILD_FRONTEND.cmd` passes (tsc, vitest, vite build).
2. `START_SSD.cmd`; Explore H02 → Timeline: slider 0→end, Reset, play/pause, colour-by; switch scenario mid-play.
3. Compare H02 vs H03: difference map, swap, zone table, row click highlights a zone; same scenario both sides → zero and "no zone flagged".
4. What-if with the service stopped (message, other pages still work); then with the service running (once supplied).
5. Evidence page shows the methods and limits section.
6. Disconnect the internet and repeat 2–3; stop and restart cleanly.
7. Browser without WebGL: tables, Evidence and downloads still usable.

## Status at delivery (8 Oct 2026)
Done: 1 (rebuild passes, 111 tests); 2 partly (timeline slider/Reset/Play/Pause, mid-play scenario switch); 3 (Compare, swap, same-scenario zero, zones); 4 first half (service stopped: message shown, other pages work); 5.
Not done: 4 second half (needs the real service), 6 (internet disconnection and restart cycle), 7 (no-WebGL), second laptop, two rehearsals with backup recording.
