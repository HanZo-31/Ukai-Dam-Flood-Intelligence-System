# Work / evidence log
## 2026-10-08 session 1
- Read plan, setup guide, final verification, package report. Baseline ID 2ccf20b727ac4588a7f3ac39ba68b9ca.
- Tooling limit: no shell on this computer's link (file list/copy only). Cloud workspace is Linux without npm registry access, so React/OpenLayers code cannot be compiled or run here.
- Read stored rasters with numpy/tifffile: all four scenarios share one 1024×3072 grid (29.0 m, EPSG:32643). Valid arrival 334,244 (H01), 426,586 (H02), 534,249 (H03), 494,437 (2006) cells; minimum 60 min; maximum 6840/6780/6480/8280 min; all values whole hours. Valid-arrival footprint ≠ wet extent (about 800–900 arrival-only and 1,700–2,100 wet-only cells per scenario).
- Implemented the timeline (see TEAM1_CHECKLIST.md). Tests: 55/55 pass in a stand-in runner; real `npm test`/`tsc` not yet run.
- Not performed: hash verification of the extracted copy before editing; any browser check of the new UI.
## 2026-10-08 session 2
- Rebuilt three times by the user (110, 111, 111 tests). Browser checks in the packaged app: timeline, Compare (extent and arrival), swap, same-scenario zero, zones, Evidence, mid-play scenario switch, narrow-width tables, Tab focus ring. Details and limits: WORK_EVIDENCE.md E21–E22.
- Found and fixed four display defects (digit grouping, coverage over 100%, doubled full stop, clipped metric table) and a fifth (a table header broken mid-word; fix on the device, not yet rebuilt).
- Lost device commits happened twice (stale styles.css); caught by staging the file back and comparing.
- Delivery folder assembled; every overlay file was staged back from the device and compared byte for byte with the delivered copy (35 of 35 equal).
