# Current V05 layout-cleanup evidence

Read `../LAYOUT_CLEANUP_STATUS.md` first. Current acceptance is `final/report.json` and `final/build.log` / `final/test.log`: production build plus 296 passing tests, zero failures/skips, bound to the final frontend source hashes.

- `BROWSER_CHECKS.json`, responsive `*_LAYOUT.json` and `desktop-clean.jpg`, `short-screen-clean.jpg`, `mobile-clean.jpg` are fresh checks/captures of the actual application.
- `PRESERVATION.json` compares the original sealed V05 against the cleanup, including identical map/back-end/solver files and timeline clock/handlers.
- `BEFORE_CHANGE.json` and `V05_BEFORE_CLEANUP_CHECKSUMS.sha256` retain the original-copy receipt, not the current delivery checksum manifest.
- `live/COMPUTE_REGRESSION.json` records the first real native run in the new isolated profile (not cache). `refined/` and `final/` verify subsequent cache/product/comparison regressions. None is scientific validation.
- `first/`, `preliminary/`, `live/` and `refined/` are intermediate check history; they must not override `final/` source-bound acceptance. The first helper invocation only completed a build before a console-encoding issue; the helper was fixed and subsequent checks completed.
- `RUNTIME_READY.json` / `RUNTIME_STOPPED.json` describe temporary localhost verification. Normal launcher ports and package/profile identity remain unchanged.

All test writes stayed within V05. The agent-created private snapshot/database/object files, solver-job products, caches and private logs were removed after their services stopped. Existing project assets and the user's normal profile/database were not removed or modified. Retained helper source in `../_layout_recheck/tools/` documents the verification method; it is not part of normal startup. The snapshot helper is tied to the original pre-cleanup checksum receipt and is not intended to run against the updated delivery without a new verification plan.

`FILE_INVENTORY.csv` and `SSD_CHECKSUMS.sha256` at the project root are refreshed for the current deliverable. Final inventory/seal verification prints its result rather than creating a post-seal report that would introduce a checksum self-reference. Physical SSD/another-device tests and the full backend suite were not repeated during this UI task.
