# Test results — what was actually run, and by whom

| Run | Who | Result | Status |
|---|---|---|---|
| 8 Oct ~20:16 `REBUILD_FRONTEND.cmd` | User (pasted log) | 110 tests passed; build succeeded | Real vitest result, before zone-table CSS fix |
| 8 Oct ~20:46 `REBUILD_FRONTEND.cmd` | User (pasted log) | 13 test files, 111 tests passed; build succeeded | Real vitest result. This is the "111 passes" in the status report |
| 8 Oct evening, after contract alignment: `REBUILD_FRONTEND.cmd` | User | Build succeeded (bundle `index-DwdKibgl.js`, CSS `index-B0V8CshZ.css`). **Vitest output was not shown to Team 1** | **Unconfirmed.** Expected 14 files / 121 tests |
| Same source | Team 1, stand-in runner (not vitest; lacks some matchers) | 121 / 121 passed | Indicative only |
| Same source | Team 1, real `tsc` 6.0.3 on a scratch project with stub types | 0 errors | Indicative only; not the project's own `tsc --noEmit` |
| `VERIFY_COPY.cmd` on the 20:46 build | User | Reported as completed; output not seen by Team 1 | Not independently seen |

## What is not evidence
- Fixture and mocked-HTTP tests (`candidate.test.ts`, `candidate.contract.test.ts`) check the adapter against Team 2's published schema and examples. They are **not** a run against the real candidate service.
- Browser checks by Team 1 (timeline, Compare, zones, Evidence, swap, narrow-width tables, Tab focus, What-if unavailable state) were made by viewing the packaged app on 127.0.0.1:5174; no screenshots beyond those in `demo/screenshots/`.

## Not performed
Offline/disconnected run, backend stop/recovery, no-WebGL, full keyboard-only pass, second laptop, two rehearsals, What-if against the real service.

Re-run on the integrated tree: `REBUILD_FRONTEND.cmd` (runs `tsc --noEmit`, `vite build`, `npm test`) and record the real output here.
