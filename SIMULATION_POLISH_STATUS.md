# Simulation naming and website polish — V05

## Latest narrow follow-up: sidebar footer removal

Only the user-selected sidebar footer text ("Simulated, uncalibrated prototype. Not scientifically validated.") was removed from `frontend/src/components/Sidebar.tsx`. Its presentation test now asserts that the footer is absent. No other website content, CSS, simulation/data logic, API or integration was changed by this follow-up. Scientific status and caveats elsewhere remain intact.

Fresh follow-up build/typecheck and tests are in `simulation_polish_evidence/footer-removal/`. The frontend run passed 326 tests; 13 live HTTP/model-job tests were intentionally not run. The 331-test/browser/startup evidence below records the preceding polish verification, not fresh browser/integration evidence for this one-line removal. The preservation report and current inventory/checksums were refreshed.

---

## Scope and completion

- [x] Rename active SSD-branded launchers, package files, guides and helper filenames to Simulation.
- [x] Update their current code, launcher and documentation references.
- [x] Preserve the package identity, database/profile ownership and existing scenarios.
- [x] Polish the existing light website without changing the 2D simulation.
- [x] Build, typecheck, targeted startup tests, real-raster reads and responsive browser checks.
- [x] Refresh the current file inventory and checksum manifest; use `VERIFY_COPY.cmd` to confirm a transferred copy.

All project edits are confined to `integrated/UKAI_COMBINED_V05`. No other version/folder was renamed or modified. No dependencies were installed or upgraded. No new integration, API capabilities, scenarios, model jobs, imports or scientific approvals were introduced. Ordinary test startup reused the existing local V05 profile; it did not create new scenarios. The test instance was stopped after verification.

## Run this copy

1. Open this V05 folder, not a previous copy.
2. Run `VERIFY_COPY.cmd`; wait for **COPY VERIFIED**.
3. Run **`START_SIMULATION.cmd`**; open http://127.0.0.1:5176/ when ready.
4. Keep the server window open while using the website.
5. Run **`STOP_SIMULATION.cmd`** and wait for **Stopped** when finished.

`START_COMBINED.cmd`, `START_UKAI.cmd`, `START_FRONTEND.cmd` and `START_FRONTEND_PREVIEW.cmd` point to the same Simulation launcher. The separate existing computed profile continues to use `START_COMPUTED.cmd` (5178) and `STOP_COMPUTED.cmd`. Do not use the wrong profile's stop script. Everything remains loopback-only.

`CHECK_SIMULATION.cmd` is the retained **baseline-only** 5174/8766/55433 diagnostic. It is explicitly labelled and is not a combined-profile acceptance check. Use the fresh evidence below for this presentation/naming change; do not interpret old baseline reports as new integration results.

## Active filename changes

| Previous name | Current name |
| --- | --- |
| `START_SSD.cmd` | `START_SIMULATION.cmd` |
| `STOP_SSD.cmd` | `STOP_SIMULATION.cmd` |
| `CHECK_SSD.cmd` | `CHECK_SIMULATION.cmd` |
| `START_HERE_SSD.md` | `START_HERE_SIMULATION.md` |
| `SSD_CHECKSUMS.sha256` | `SIMULATION_CHECKSUMS.sha256` |
| `SSD_PACKAGE_ID.txt` | `SIMULATION_PACKAGE_ID.txt` |
| `SSD_PACKAGE_REPORT.json` | `SIMULATION_PACKAGE_REPORT.json` |
| `docs/SSD_SETUP_AND_WORK_GUIDE.md` | `docs/SIMULATION_SETUP_AND_WORK_GUIDE.md` |
| `scripts/ssd_runtime.py` | `scripts/simulation_runtime.py` |
| `scripts/ssd_web_server.cjs` | `scripts/simulation_web_server.cjs` |
| `scripts/seal_ssd_copy.py` | `scripts/seal_simulation_copy.py` |
| `scripts/build_ssd_copy.py` | `scripts/build_simulation_copy.py` |
| `scripts/check_ssd_browser.cjs` | `scripts/check_simulation_browser.cjs` |
| `team2_work/assembly/ssd_web_server.cjs` | `team2_work/assembly/simulation_web_server.cjs` |
| `tests/test_ssd_runtime.py` | `tests/test_simulation_runtime.py` |

`CHANGE_SCOPE.json` lists the exact rename map and approved existing-file edits. Current launcher, integrity-verifier, packaging/quality/probe code and current guide references were updated. The old filename launchers are not retained as extra SSD aliases. `FILE_INVENTORY.csv` describes current delivered files; the updated manifest is `SIMULATION_CHECKSUMS.sha256`.

### Intentional compatibility/history exceptions

- The package-ID file's **bytes/value are unchanged**: `7e9432a8165f49da89b093fde5845c61`. Changing its identity would target a different local database/profile.
- Internal identifiers such as `ukai_ssd`, `ukai_b_integration_ssd`, `Ukai SSD`, `UkaiSSD`, old import-delivery IDs and actor identifiers remain unchanged. These are compatibility identifiers, not website branding. No database migration, credential change, copied private configuration or profile-folder rename was performed.
- Earlier evidence, received original deliveries and their historical path/checksum references remain untouched. Their filenames can still contain SSD because they are audit records, not current launchers.
- `SIMULATION_PACKAGE_REPORT.json` is a byte-preserved historical report after renaming. Its old source paths and 902/21 test counts are recorded baseline results, not fresh results for this release. Use this document and the current evidence folder instead.
- Old evidence helpers that address old SSD filenames describe earlier releases. For current checks use the tools under `simulation_polish_evidence/tools`; do not rerun old release-sealing helpers against this renamed copy.
- The older transfer guides carry a current V05 preamble; their following original transfer details/ports are clearly labelled historical.

## Website polish

Presentation changes are isolated in `frontend/src/simulation-polish.css`, imported by `main.tsx`:

- Subtle light-theme navigation states and reduced-motion-safe hover transitions.
- A compact, truthful **Local API connected** status chip; connection is explicitly not scientific validation.
- More consistent headings, cards, text spacing and evidence/download readability.
- Clearer inspector separation, table formatting, input focus and action styling.
- Four-section mobile navigation with a compact two-column scenario grid.
- Narrow-screen wrapping for page headings, controls and download rows without page overflow.

The single-map inspector now correctly says **Click the map**; Compare retains **Click either map**. The startup error message points to the newly named launcher. Existing uncertainty, missing-value messages, model identities, publication gates and scientific caveats are retained. The removed topbar uncalibrated badge was not reintroduced.

No changes were made to `FloodMap.tsx`, raster/timeline/colour logic, scenario-selection handlers, API routes/contracts, original data, solver implementation, frontend dependencies or the model clock. The existing point-reader and comparison calculations remain unchanged. The optional old browser helper's output path was corrected to remain inside this V05 folder; that helper was syntax-checked, not used for browser control in this verification.

## Fresh verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Production build and TypeScript | Passed | `simulation_polish_evidence/final/build.log` |
| Frontend suite | **331 passed; 8 skipped; 339 total** | `final/test.log`, `final/report.json` |
| Four real scenarios, original cells and bounded HTTP ranges | Passed, read-only | `final/range-http/` and frontend tests |
| Startup ownership, malformed checksum inventories, locks, stop/error paths | **40 passed** | `backend-final/startup-unit-tests.log` |
| Renamed proxies/browser-helper JavaScript syntax | Passed | `backend-final/syntax-*.log` |
| Correctness lint for changed Python/tooling | Passed | `backend-final/python-lint.log` |
| Source/data preservation and 15 active renames | Passed; no protected mismatches | `PRESERVATION.json` |
| Desktop/mobile/laptop browser checks | Passed; no captured warnings/errors | `BROWSER_CHECKS.json`, screenshots |
| Real combined startup using renamed files | Ready: four references, existing candidate fallback | Startup verified on 5176; source/profile identity retained |

Evidence paths in this table are relative to `simulation_polish_evidence/` unless already fully prefixed. `final/report.json` records the exact frontend source hashes covered by the build/tests. The initial test run (without HTTP) passed 326 tests and skipped 13; it is superseded by the final 331-pass run. Eight existing candidate/model-job tests remain deliberately unrun because this task did not authorize new integration/model execution.

Browser checks covered 1440×900 desktop, 1280×592 laptop and 320×720 narrow mobile: all primary sections, four scenario cards, three raster modes, real point values, +0.63 m H01/H02 point difference, the declared 114-hour timeline window, preserved download links, internal table/drawer scrolling and no horizontal page overflow. The final desktop screenshot was taken after tile rendering settled, not from an intermediate partial-load frame. The maps still use the existing graticule background and original raster appearance.

The first startup test-harness run placed temporary mutable state inside the real source directory, and the production safety guard correctly rejected it. The harness was fixed to use disjoint tiny source/state fixtures **both inside V05**, without relaxing the application guard. All 40 tests then passed. That unit fixture's placeholder control file was never executed and is removed with the temporary test cache before sealing. The earlier failed log is retained as transparent history, not an unresolved product failure. A browser assertion initially used an exact text locator that excluded a cell's existing explanatory child text; the full accessible cell confirmed the correct +0.63 m value.

## Recheck commands (bundled tools only)

```powershell
.\runtime\python\python.exe -B scripts\simulation_runtime.py --verify-copy
.\runtime\python\python.exe -B simulation_polish_evidence\tools\verify_update.py
```

`verify_update.py` writes a new preservation report, so intentionally reseal afterwards with `SEAL_WORKING_COPY.cmd` and re-run `VERIFY_COPY.cmd`. The new evidence helper `tools/seal.py` also regenerates the current CSV inventory and independently checks every final checksum; it was used for this task. Evidence-producing helpers invalidate the strict copy inventory until resealed; never suppress that gate or reseal a damaged transfer as a workaround.

## Not claimed / deliberately unchanged

This update is complete for **Simulation naming and website polish**. It is not a new production/scientific acceptance claim. New integration, model training/execution, real contours, scientific calibration/validation, exposure assessment, engine harmonization, public hosting, authentication, Git and receiving-device testing were not performed. Earlier scientific/terrain/ML limitations remain unchanged; there is no new operational-safety or forecasting capability.
