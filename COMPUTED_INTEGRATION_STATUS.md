# Computed integration V03 — verified work and remaining device gates

9 October 2026, Asia/Kolkata. Release `ukai-combined-20261009-v03-computed`.

## Sources and ownership

Claude's actual work folder was `E:/Disaster/UKAI_COMBINED_V02_work`. It was reviewed read-only, not overwritten. Against the common V02 baseline, three existing frontend source files changed and 32 frontend files were new; selected original data, backend source and release identities matched. Its historical status documents and stale checksum list were not treated as evidence for the new feature. Received runtime/dependencies were not used: the independently verified local baseline supplied them.

V02 had 22,701 valid manifest entries; BACKEND_DELIVERY_V02 had 2,664. The new folder combines only frontend-owned changes and the sealed backend overlay, followed by documented integration fixes. Existing V01/V02 and original deliveries remain untouched. No Git, cloud, LAN, login or ZIP deliverable was introduced.

## Completed implementation

- [x] Preserve the four reference scenarios, stored What-if, Explore/Compare/Evidence and approved-only publication gates.
- [x] Wire Claude's new computed view to real same-origin compute-v2, with strict capabilities, exact peak/config/identity validation, asynchronous job polling, verified product downloads, experimental provenance and honest cache handling.
- [x] Render maximum depth, hourly arrival, velocity component and classified difference previews with geographic extent projected to UTM. Display colours are not scientific hazard classes.
- [x] Compare real candidate/H02 rasters with unknown coverage separate from confirmed gained/lost flooding; reconcile nonoverlapping 5 km coordinate review-zone totals and guarded arrival ranking.
- [x] Correct metre-scale grid shifts accepted by relative coordinate tolerance; use absolute metric tolerance instead.
- [x] Correct the misleading 100 m displayed-cell label: approximately 29 m derivatives retain approximately 100 m native hydraulic resolution. Show the real velocity definition; never subtract it from HEC-RAS speed magnitude.
- [x] Keep usable depth comparison when optional reference arrival is missing/unavailable; preserve null rather than fabricate timing.
- [x] Resume the same completed job after leaving during product downloads; keep the previous verified result visible during a new download/failure.
- [x] Distinguish original generation timings from cached lookup duration; describe unhighlighted difference cells without implying dry/safe land. Small positive zone areas no longer display as zero.
- [x] Add validated product download links, field help/error associations and V03 development-proxy settings.
- [x] Add Windows kill-on-owner-exit protection: an abruptly stopped candidate service cannot leave its owned native worker running. Physics, original DLL/driver, input hashes and frozen scientific configuration are unchanged.
- [x] Make backend tests self-contained with unchanged contract/examples/fixtures and a genuine recorded packaging fixture. Add package typing metadata; do not relax the gradual quality gate.
- [x] Provide a matched loopback-only `START_COMPUTED.cmd` / `STOP_COMPUTED.cmd` pair and separate local-state profile. See `START_COMPUTED_HERE.md`.

## Fresh checks on this device

| Check | Actual result | Public evidence |
| --- | --- | --- |
| Final frontend build/typecheck + unit/reference/live checks | 268 passed, zero failed/skipped; final build from the delivered source | `computed_integration_evidence/frontend-final-v06/` |
| Combined database/API/candidate/native regression | 1,052 passed, four existing platform skips, one inherited Starlette/HTTPX warning | `computed_integration_evidence/backend-final-v03/` |
| Genuine fresh first 25,000 producer -> frontend consumer | Passed; all four product checksums/decoders, comparison, zones and cache reuse | `computed_integration_evidence/REAL_CONSUMER_RESULT.json` |
| Native ownership/recovery after final backend fix | Fresh real 25,000 run, checked assets, actual native child killed on service crash, interrupted job explicitly failed on restart; completed result/cache preserved | `computed_integration_evidence/native-lifecycle-final-v01/` |
| All original reference downloads | 24 passed checksum/HEAD/range/If-Range checks; no reimports | `computed_integration_evidence/resources-final-v01/` |
| Existing quality gate | Dependency consistency, correctness lint, gradual types, proxy syntax and frozen v1 OpenAPI checks passed, no installs | `computed_integration_evidence/quality-final-v02/` |
| Actual browser journey/recovery and final seal | See final browser/closure reports for the performed outcomes; do not infer completion from a plan | `computed_integration_evidence/browser-final-v01/`; companion `FINAL_RECEIPT.json` |

The original full native run and a later guarded repetition both use the SAME 25,000 release condition. Repeating it does not create extra independent training data. The interrupted 26,000 lifecycle probe did not complete and is not an accepted scenario. Final frontend repetitions used the checked real cache; the fresh first-run record is preserved separately. Timings vary with concurrent work and are not an SLA or scientific validation.

The `py.typed` marker was added after the full backend suite; it has no runtime code effect and the subsequent unchanged gradual quality gate passed. The final closure verifies all executed backend source hashes plus the separately checked metadata addition.

Earlier failed attempts are retained outside the package: sandbox Vite realpath refusal, missing external test-packet dependency, and the initially missing typing marker. They are not counted as passing checks. The first lint invocation used the application runtime, which lacks Ruff; the successful check used the existing separate quality runtime, without installation.

## Recorded prior evidence versus new acceptance

V02's 147 frontend / 985 backend passes and backend delivery V02's 119 tests/native proof are historical evidence. They are not substituted for the fresh results above. Old `POLISH_STATUS.md`, `INTEGRATION_STATUS.md` and `frontend/FRONTEND_STATUS.md` remain labelled history by the new start guide. Private database passwords, URLs, job state and test scratch stay outside the delivered project.

## Genuinely remaining

- [ ] Physically disconnect the network and cold-launch on the target computer. Localhost and absence of remote resources do not prove physical disconnection.
- [ ] Copy this FINAL plain folder onto the SSD and run `VERIFY_COPY.cmd` there. The supplied older E: work folder is not the new V03 release.
- [ ] On another device, verify its own native runtime/map behaviour if that device is used. Same-device checks cannot prove universal portability.
- [ ] Perform user-specific assistive-technology/accessibility acceptance if required; engineering keyboard/help/table checks are not certification.

No scientific calibration, observed-flood validation, safety recommendations or usable ML predictor is claimed. These are scientific/product limitations, not concealed successful checks. Rehearsals and video are excluded from the agreed scope.
