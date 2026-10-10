# V04 light frontend — scope and verification

Release: `ukai-combined-20261010-v04-light-ui`. This is a new, complete plain project folder; sealed V03 and original deliveries are preserved. No ZIP, Git, hosting, login or extra dependency installation was introduced.

## Implemented

- White sidebar, pale-blue active navigation and scenario cards, blue icons, restrained card borders and light panel styling based on concepts 1 and 3.
- Removed only the `Uncalibrated simulation` badge beside the API status. Checking/connected/unreachable status is still truthful. Calibration, validation and missing-product information remain in scenario details and Evidence; no data or publication gate was relaxed.
- Cleaner scenario inspector: essential status visible, run metadata and limitations in accessible native disclosures, existing Evidence/download action retained.
- Comparison selectors moved above the existing maps. Existing reference table/charts remain available below the maps in `Reference metrics and overview`. No proposed/decorative map or invented comparison operation was implemented.
- Preserved original map dimensions at the checked viewport by matching the old status-row height without displaying its removed badge.

## Exact implementation files

| File | Change |
| --- | --- |
| `frontend/src/interface.css` | New scoped surrounding-interface styles; no map, legend or timeline rules overridden. |
| `frontend/src/main.tsx` | Loads the new stylesheet after the unchanged original. |
| `frontend/src/components/TopBar.tsx` | Removes the single top status-area badge. |
| `frontend/src/components/Inspector.tsx` | Reorganizes the same metadata into readable sections/disclosures. |
| `frontend/src/pages/Compare.tsx` | Surrounding layout only; rendering, controls and state logic preserved. |
| `frontend/src/components/interface.test.tsx` | Nine presentation-only tests with a clearly synthetic fixture. |
| `frontend/vite.config.ts` | Includes component `.test.tsx` files in tests; proxy and build configuration unchanged. |
| `frontend/dist/` | Rebuilt actual production frontend from the changed source. |
| Root startup notes, IDs and inventories | Identify this new copy and distinguish fresh from historical evidence. |

## Fresh checks for this UI change

- TypeScript/typecheck and production Vite build passed.
- **277 tests passed, 0 skipped, 0 failed**, including actual local API/candidate regression, stored raster comparisons and timeline tests. Final logs and source-bound report: `ui_refresh_evidence/frontend-final/`.
- Nine new component tests cover health states, selected navigation, loading state, retained limitations and accessible disclosures. These fixtures are synthetic unit-test data, never runtime results.
- Browser: light design, header badge removal, scenario switching, timeline End/Reset, comparison selectors/Swap, expandable metrics, What-if and Evidence, keyboard navigation and 760-pixel narrow layout. No captured browser warnings/errors. See `BROWSER_CHECKS.json` and actual screenshots.
- Baseline and protected-file hashes, actual Explore/timeline geometry and settled comparison map dimensions are independently compared; see `PRESERVATION.json`. All map code, original `styles.css`, decoding/scales, layer controls, timeline controls, scientific inputs, backend and solver remain byte-identical. Comparison rendering/control/state blocks are identical.
- Fresh preservation result: all **25,403 V03 baseline entries** verified; **25,380 protected files identical**, zero protected mismatches. One fitted H01 depth-view capture is **822 × 682 pixels with zero decoded pixel differences** between old/new interfaces. This sampled visual check is not scientific validation or a claim to have inspected every camera position.
- The final root checksum file and `FILE_INVENTORY.csv` cover this delivered copy, not the old V03 seal. Final integrity report is kept in the companion `UKAI_COMBINED_V04_VERIFICATION` folder to avoid a circular self-checksum claim.

## What this does not claim

The UI tests and browser comparison used unchanged V03 backend services with its existing isolated verification profile. The real 25,000 request reused validated cache; this is frontend regression, not a new hydraulic run. The full backend suite was not repeated because backend/source/assets are unchanged. Historical V03 reports remain labelled historical.

Fresh V04-profile initialization, receiving-laptop/SSD startup, physically disconnected/offline operation, every possible screen size/camera state and scientific calibration/validation were not performed for this UI-only request. Existing scientific limitations, four stored references and unavailable ML/exposure data are unchanged. No new release recommendation, populated-place impact estimate or scientific approval is implied.

## Run the changed frontend

1. Use **this V04 folder**, not an older folder or the old 5176 page.
2. Stop another Ukai instance first. Run `VERIFY_COPY.cmd`, then `START_COMPUTED.cmd`.
3. Open `http://127.0.0.1:5178/`. Explore shows the light sidebar/inspector; Compare shows the new selector-first layout.
4. Stop with this folder's `STOP_COMPUTED.cmd`; wait for the stop confirmation before disconnecting SSD.

All host services remain bound to `127.0.0.1`. The old and new code are separate folders, not a mutation of an old running frontend.
