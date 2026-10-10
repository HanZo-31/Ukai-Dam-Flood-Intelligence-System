# Compare blank-scroll fix — V05

2026-10-10, Asia/Kolkata. Changes are exclusively inside V05.

Cause: absolutely positioned screen-reader table captions escaped Compare's unpositioned container. After results loaded, they extended the outer document beyond the viewport, causing a second scrollbar and a blank tail beneath the real Compare scroll area.

Fix: `frontend/src/compare-scroll.css` adds only `.compare-page { position: relative; }`; `frontend/src/pages/Compare.tsx` imports it. No clipping, row limits, fixed result heights or hidden captions. Map dimensions, terrain, simulation, comparison calculations, API and original data are unchanged.

Fresh evidence:

- Build/TypeScript passed; **335 frontend tests passed, eight candidate/model-job live checks skipped**. Includes read-only HTTP checks of all four stored scenarios. `simulation_polish_evidence/compare-scroll-final/`.
- New regression guard: `frontend/src/components/compare-scroll.test.ts` checks the actual CSS rule without permitting clipping or map-layout overrides.
- Before: outer document 2931 px tall for a 524 px viewport after comparison results loaded. After: document equals viewport height; scrolling stays inside Compare.
- Desktop 1920 × 900: document height 900, final note ends around 872 px at the bottom of Compare; all 53 flagged rows remain, both screen-reader captions remain. No extra outer blank tail.
- Mobile 320 × 720: real long content preserved; document bottom matches Compare bottom with only normal end spacing. No horizontal document overflow.
- Browser console warnings/errors: none captured. `simulation_polish_evidence/COMPARE_SCROLL_BROWSER_CHECKS.json`; screenshot `compare-scroll-fixed.png`.
- `COMPARE_SCROLL_PRESERVATION.json` checks unchanged original files and verifies Compare differs only by the CSS import. Inventory/checksums are refreshed and normal copy verification is run.

The first regression test read CSS through an import that Vitest stubs to an empty string. Its failed log is retained under `compare-scroll/`; the corrected guard reads the actual file, and the final run passed. No production behavior was relaxed.

The pre-existing localhost runtime was already running and is left running. Refresh the browser to load the rebuilt frontend. No model jobs, imports, approvals, new integrations or full backend suite were run for this one-rule layout fix. Previous reports remain historical evidence for their earlier source states.
