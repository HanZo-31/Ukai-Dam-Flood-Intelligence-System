# Ukai combined application — polished integration V02

Read [POLISH_STATUS.md](POLISH_STATUS.md) first for this version's changes, fresh checks and remaining operator gates. `INTEGRATION_STATUS.md` and `integration_evidence/` retain the V01 history. New evidence is under `polish_evidence/`. V01 and original team deliveries remain untouched.

New in V02: comparison briefing Markdown download, keyboard skip/focus support, improved contrast, map/comparison retry controls, corrected geographic extent projection and explicit outline fallback. Demo instructions stay in separate documentation, not the product navigation. See [launch card](demo_evidence/LAUNCH_AND_RECOVERY_CARD.md), [demo script](demo_evidence/DEMO_SCRIPT_AND_QA.md) and [static screenshot backup](DEMO_BACKUP.html). Model/data/publication behavior is unchanged.

This is the complete working copy: baseline runtime/data/backend, Team 1 frontend and Team 2 candidate service/supervisor. Original inputs are preserved. Read [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) for fresh results; older reports are historical, not this version's acceptance.

## Run locally

1. Run `VERIFY_COPY.cmd` after transfer or suspected corruption.
2. Run `START_COMBINED.cmd` (or `START_SIMULATION.cmd` / `START_UKAI.cmd`). Wait for READY.
3. Open **http://127.0.0.1:5176/**. Keep the launcher window open.
4. Stop using Ctrl+C or `STOP_COMBINED.cmd` / `STOP_SIMULATION.cmd`; wait for Stopped before ejecting an SSD.

All services bind `127.0.0.1`: web 5176, reference API 8767, candidate 8770, PostgreSQL 55434. Port collisions are refused; unrelated processes are not killed. Do not run legacy `scripts/simulation_runtime.py` directly expecting candidate support.

`CHECK_SIMULATION.cmd` / `RUN_FULL_RECHECK.cmd` retain the historical baseline-only diagnostic workflow and do **not** constitute combined candidate acceptance. The current combined verification logs and exact commands are delivered under `integration_evidence`; use those helpers for a planned fresh check rather than starting a second legacy profile.

Private state is outside this distribution in `%LOCALAPPDATA%\UkaiTeam2\<source-path-hash>` (Windows may resolve this to app-local cache). No live database or credentials are copied. A new computer/path creates a separate profile and imports four portable receipts. Use bundled Python 3.12.4, Node and PostgreSQL; no installation, Git, login, cloud or internet is required.

## Delivered features

- Explore: elapsed-hour arrival reveal, reset, play/pause, colour-by; maxima revealed by arrival are not time-varying hydraulics.
- Compare: synchronized maps, wet-footprint and paired arrival differences; reproducible coordinate review zones, not villages or evacuation priorities.
- What-if: **stored lookup only**, exact 15000 / 20000 / 30000 m³/s; other bounded peaks require explicit nearest opt-in and show requested/actual values. No new simulation or ML prediction.
- Evidence: methods, units, provenance and limits; unknown impacts stay unavailable.
- Combined launch: same-origin routing, owned state, safe failures and recovery.

All four references remain drafts, uncalibrated and not scientifically validated; approved-only publication rules are unchanged. Reconstructed 2006 is not observed truth. Additional-release solver generation and enabled ML are not delivered.

## Reading order

1. [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md): status and evidence.
2. [Receiving verification](integration_evidence/RECEIVING_VERIFICATION.json): delivery IDs/hashes.
3. `frontend/src/`: Team 1 code plus corrections; `frontend/dist/`: newly rebuilt UI.
4. `team2_work/`: service, supervisor, proxy, frozen contract and backend tests.
5. `integration_inputs/`: exact received overlays/reports, including their historical blockers.
6. `docs/HACKATHON_20_HOUR_PLAN.md`: preserved plan; device/operator gates still apply.

Exchange the complete sealed plain folder, not an overlay. Mutable runtime/test scratch and credentials must stay outside. No ZIP.
