# Frontend status (honest record)

## Current portable-copy verification - 8 October 2026

The source, production frontend build and typecheck pass with bundled Node. Real Vitest reports **21/21 passed**, across six files. The portable API and all 24 download resources pass independent HTTP/hash/header/range checks; the backend reports **902 passed, 4 skipped**. Portable development uses `DEV_FRONTEND.cmd` on 5175, proxied to API 8766. Ordinary use starts the built app on 5174 with `START_SSD.cmd`.

**New automated browser screenshots are not performed:** the restricted environment terminates Chrome/Edge in crash-handler setup before loading a page. Earlier visual results were reported for the working laptop; a receiving laptop still needs its own WebGL/layout acceptance. Read `../evidence/SSD_FINAL_VERIFICATION.md` and `../docs/SSD_SETUP_AND_WORK_GUIDE.md` for the current scope and evidence.

The following original scaffold record is retained as history. Its “not yet built / real Vitest not yet run” statements have been superseded by the results above.

---

Date: 2026-10-08. Label: draft prototype UI, uncalibrated simulation, not validated.

Legend: DONE = performed with evidence · WRITTEN = code exists, not yet run · NOT YET = not performed.

| # | Checklist item | State | Evidence / note |
|---|---|---|---|
| 1 | Inspect brief, design, API shapes; connect | DONE (shapes) / NOT YET (live) | Types in `src/lib/api.ts` follow the backend schemas. Live API not yet called from the app. |
| 2 | Build interface (Explore, Compare, Evidence, sidebar, top bar, summary, map, legend, inspector) | WRITTEN | `src/` |
| 3 | `tsc` + production build | PARTIAL | Non-map code type-checked here (`tsc --strict`, OK). Full `npm run build` NOT YET (needs `npm install` on the laptop; this workspace cannot reach the npm registry). |
| 4 | Focused tests (unavailable values, arrival units, stale requests, proxy/API errors, UTM, scenario naming) | DONE here, 21/21 | Run with a small stand-in for vitest. `npm test` (real vitest) NOT YET. |
| 5 | Real-browser inspection: 4 scenarios × extent/depth/velocity/arrival | NOT YET | Needs the app running next to the backend. |
| 6 | Downloads per asset role | NOT YET | Links built from API `layers` + `links`. |
| 7 | Backend-offline handling | WRITTEN / NOT YET observed | Banner + status pill + auto-reload on reconnect. |
| 8 | Offline use after install | NOT YET | No CDN or remote tiles are referenced. |
| 9 | Desktop + small layouts | NOT YET | CSS breakpoints at 1100 px and 760 px. |
| 10 | Final recheck | NOT YET | |
| 11 | Launchers and docs | DONE | `START_FRONTEND.cmd`, `START_FRONTEND_PREVIEW.cmd`, `FRONTEND_START_HERE.md`. |
| 12 | Screenshots in `evidence\` | NOT YET | |

No ZIP, Git, cloud, authentication or public deployment was used. `package-lock.json` will be created by the first `npm install`.
