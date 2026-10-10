# Overlap review — shared files Team 1 modified

Team 1 modified 11 files that exist in the baseline package `Ukai_SSD_Ready` (ID `2ccf20b727ac4588a7f3ac39ba68b9ca`). Compare these against Team 2's versions deliberately; do not overwrite blindly. Full SHA-256 values below. `baseline_originals/frontend/<path>` = original, `source_overlay/frontend/<path>` = Team 1 version.

| File (under `frontend/`) | Baseline SHA-256 | Team 1 SHA-256 |
|---|---|---|
| `src/App.tsx` | `13a1e77e51a5bfe297007b45dc60427e78e14273b3c928bb822f67a39c260655` | `052cb73e807bf0e4cf893301fb99750dcec89ff200dea9eb9f55c06940230b80` |
| `src/components/Legend.tsx` | `d4bf09d483102e006ca98afecc1ff14465f2eda2908c484498bc6d3b6d8b34a2` | `168aa73756407ad19d7fabab8213d991948107dd5a9a6b6633623e522079faeb` |
| `src/components/MapControls.tsx` | `7d876d3c710e52d29fe55d6c77b44163d78f1bac92337163fe76e83e2fe8d5c1` | `7d2cc855137f7d79aa2a26a373d169e6b9a15c21f0e8f305969dbcbecfd6c4e5` |
| `src/components/Sidebar.tsx` | `0532ad20a446eb0ec6248e08e7ed7b33bc9b619b8da55571178924620a079b01` | `444d68c10912ce8209f152440cb7f9b1a8be9637ca3baf81a45b6543f6f3619a` |
| `src/lib/scales.ts` | `505a8c87ce821b443babfc870ca15aed831ec64f8c3be82dd57a44a0d5923f3d` | `596bef4ce42c9eba9e3743dd7f838a5b61c4ab12408bd28961922598a6471686` |
| `src/map/FloodMap.tsx` | `c5d23c9d2df22f0bd97446340fa90c4635ed2730a487c116345acef8e1812e1e` | `bb94a84bd84a1b77f5397bed70e1ad365a6f151f902f01d62e081e1d43f47a1f` |
| `src/pages/Compare.tsx` | `cd99e36f205abc0b185eb57080022ec8f6bac92629bd410dd859177898f78e63` | `c49a8209d3a5cc0b1291fd451c4e3ebcee3e995fbc297a938c452f2bba647012` |
| `src/pages/Evidence.tsx` | `5d5052c04af29228f1a6b502b9372095a4a3af4163de0b07713216e7a191e38f` | `4b10d4d3b53a336bca9cc1e526ab612eb5f6800a3c7127078199f02b1fc9a91f` |
| `src/pages/Explore.tsx` | `af00823bfb3e573bb01257f0651507e185a35c3cc5b19fedd0b9ddf863aa2b29` | `fe3ec3a9e2d393326815fb76f682facf83b768e0ec0cbe03094d3f5e072ce691` |
| `src/styles.css` | `c830e04a3ac56adceccf1d0c3c64e6bf6a316df3f24d613fd7ac90deedd448a0` | `d52dfcfeb1037215d8983d11a9250072ee07a1c80cdac83bd889b41a0fa1f5ef` |
| `vite.config.ts` | `a93953e376b47110c31635183ead713f5a5ff8f2c1ff36887415312218979d22` | `f54b5c908a51481a299cb06cce85670bcf41c2bbb834c092f41c6a9418a6b0ce` |

## Notes
- `vite.config.ts`: Team 1's change is a **dev-server proxy rule only** (port 5175, `/api/v1/candidates` → candidate service). It does not affect the production build or the packaged app.
- Production routing for `/api/v1/candidates` lives in the shared `ssd_web_server.cjs`, which Team 1 did **not** edit. See `patches/ssd_web_server.candidates.PATCH.md`; Team 2's combined proxy likely supersedes it (Team 1 has not seen or run that proxy).
- `App.tsx`, `Sidebar.tsx`: add the What-if page/navigation entry — most likely to overlap if Team 2 also touched navigation.
- `Explore.tsx`, `FloodMap.tsx`, `MapControls.tsx`, `Legend.tsx`, `scales.ts`: arrival timeline and colour-by; reconcile by diffing against the baseline originals, not by replacing.
- `Compare.tsx`, `Evidence.tsx`, `styles.css`: compare-v1 differences, review zones, limits text, and table styling.
- 27 added files (pages/WhatIf, lib/candidate*, lib/compare*, zones, tests, fixtures) have no baseline counterpart; check only for name collisions with Team 2's tree.
- Team 2's own two contract files (`candidate_examples.json`, `candidate_openapi_v1.json`) are included unchanged under `src/lib/fixtures/`.
- Not verified: whether Team 2 modified any of these 11 files. Team 1 has not seen Team 2's frontend tree.
