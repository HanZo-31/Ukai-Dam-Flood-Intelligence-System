# Team 2 evidence ledger

All local dates use +05:30 unless a report explicitly records UTC. Machine-local state/logs are not transferable credentials. Reports include exact check times and source hashes.

| Work | Result and scope | Evidence |
| --- | --- | --- |
| Four-scenario audit | 18:15:59–18:16:00; input/asset/context hashes, registered grids and hypothetical forcing compatibility pass; 2006 differs | evidence/four-scenario-audit-v01.json |
| Model diagnostic | H01/H03 fit, H02 holdout; saved-weight reload; partial coverage and error denominators; surrogate gate false | diagnostic-v01/evaluation.json; diagnostic-model.npz |
| Initial candidate API | 17 passes, one inherited HTTPX warning; expanded to 24 with cache/source/run/link/bounded-evidence checks | evidence/candidate-check-v05 and candidate-check-v08 reports |
| Contract export | v02 is the complete frozen typed contract and four lookup examples; v01 failed partial attempt retained locally | contract-drop-v02 JSON files |
| Real separate process | Three real HTTP stored lookups, approximately 0.033 s each, clean stop; not simulation or browser latency | evidence/loopback-probe-v01/report.json |
| Initial same-origin probe | Actual Node and candidate service, built static frontend; reference upstream explicitly a routing double; candidate failure isolated | evidence/assembly-proxy-v02/report.json |
| Combined lifecycle | 2026-10-08T19:22:33–19:24:28+05:30; 22 recorded checks pass; fresh owned DB imports four references, actual API, real asset checksum, duplicate reuse, candidate failure, warm restart and job recovery, clean stop | evidence/combined-runtime-v01/report.json |
| Focused combined tests | 37 pass, one inherited HTTPX/Starlette warning; current runtime then had an unused test import, fixed and tested again in final regression | evidence/combined-focused-v01/report.json |
| Quality correction | v01 identified unused imports; v02 identified gradual-type issues; corrected without schema change; v03 all five checks pass | evidence/final-quality-v03/report.json |
| Frozen contract recheck | Current implemented OpenAPI equals export; four examples validate; no contract version bump | evidence/contract-reconciliation-v02/report.json |
| Final backend regression | 2026-10-08T19:39:54–19:43:46+05:30; 939 pass, 4 skip, one warning, 97.97 s; owned DB, unchanged actual four-reference catalog, exit 0, clean stop and source hashes unchanged | evidence/final-regression-v01/report.json; tests.log |
| Browser attempt | No app rendering was observed; stopped by computer-use safety URL confidence check; no retry/bypass or fake screenshots | DEMO_AND_ACCEPTANCE.md |
| Final packaging checks | 11 synthetic packaging tests pass in 0.20 s; all five refreshed quality checks pass; receiver preflight verifies 70 digests, 12 links, 19 regression-source matches and five entry-point/syntax commands without starting services | evidence/packaging-check-v02; evidence/final-quality-v05; workspace-only receiver-preflight-verification.json |
| Final publication | Publisher repeats exact copy, inventory, digest, links, entry points and source/evidence checks after the final documentation update; an external receipt is written only after success. Re-run the delivered read-only verifier for the receiver's current bytes | verify_delivery.py; workspace-only evidence/final-delivery-verification.json |

## Evidence correspondence

The combined lifecycle report records its original supervisor hash. Later type-only import-loader checks/setattr and Literal typing fixes are covered by the final regression's current hashes. Do not claim the old lifecycle report was generated from the current hash.

The final regression froze all then-present Team 2 Python files, proxy and quality configs, plus applicable baseline code and reference files. New packaging/receiver helpers are checked separately; they are not retroactively included in the 939 count. Final quality includes those helpers.

Baseline package evidence (902 backend tests, 21 frontend tests, all 24 downloads and 22,382 file hashes) is retained as recorded history. The cold combined initialization performed the baseline 22,382-file verification. The fresh final backend run includes the 902 baseline passes plus 37 Team 2 passes. It does not establish a new Team 1 frontend build or physical offline acceptance.

## Failed attempts and corrections

Restricted Windows asyncio socketpair creation stalled initial API tests; completed runs used approved scoped local process/socket access. Restricted contract export could not publish immutable job evidence; successful export is v02. Failed attempts and earlier deliveries remain preserved locally. No success is inferred from a mere evidence-file existence.

The new packaging runner initially could not import its sibling module because embedded Python isolates its search path. Explicit local-path bootstrap fixed the issue; packaging tests then passed. A separate preflight receiving folder is verified before publishing the final plain folder; final hashes are checked again after the last documentation update.

Scientific acceptance remains distinct from engineering/API evidence. No new physical scenario, approval, model accuracy, flood-extent expansion or fresh simulation speed is claimed.

Final seal receipts reside outside the immutable outgoing folder so no report hashes itself. They are local publication evidence; they are not included as broken relative links in the delivery. The receiver can reproduce them with the delivered read-only command. The preserved preflight has earlier documentation snapshots; its checksum digest must not be presented as the outgoing folder's digest.

## Final Team2 acceptance continuation

| Check | Fresh result | New evidence / unchanged artifact |
| --- | --- | --- |
| Actual packaged v03 services | 2026-10-08T20:29:32–20:30:32+05:30; all24 original full resources/hashes and HEAD/range/If-Range/unsatisfiable-range checks pass through the actual combined proxy; frontend resources served; stored-only capability; no reimports; clean owned shutdown | final_acceptance_supplement_v01/runtime-resource-check/report.json |
| Exact timeline samples | 20:28:55+05:30; all4 original arrival hashes verified before/after; real180-minute boundary cells and real masked0,0 cells supplied, with CRS/coordinates/IDs/valid maxima; no scientific bytes modified | final_acceptance_supplement_v01/arrival-samples.json |
| Supplement source | Scoped correctness lint passes for the2 new scripts; generated reports contain matching script hashes; no unchanged broad-suite rerun | verify_delivered_runtime.py; extract_arrival_samples.py in supplement |
| Public evidence delivery | TEAM2_ACCEPTANCE_SUPPLEMENT_V01 sealed:9 files,8 verified digests; report-script hashes match; links resolve; runtime logs/private state not copied | deliveries/TEAM2_ACCEPTANCE_SUPPLEMENT_V01 |
| V03 preservation | Actual before/after receiver checks pass;70 digests; checksum-manifest digest stays ce0624671e4553d1deacee159aa3b9fc11333da87f1f9cdef7fc2b803d3d8b08 | Original TEAM2_ENGINEERING_DELIVERY_V03 unchanged |

Original-plan scientific requirements are not silently substituted: a stored HEC-RAS lookup is not the fast-solver pipeline or a validated surrogate. The plan's reference-only fallback permits a limited final demo without requiring optional ML activation/observational calibration. Final Team1 source/build, actual UI timing, browser/device/physical offline and recordings remain external prerequisites.

## Audit correction release v04

The three later audit findings were fixed in working code after the user's explicit implementation request. T2-F01 rechecks live readiness on duplicate reuse; T2-F02 hashes all bound inputs/portable paths on new/cached requests; T2-F03 serves local static documentation with no CDN. Targeted tests cover the previously missing failure cases.

| Check | Current result | Evidence |
| --- | --- | --- |
| Focused service/supervisor |77 passes,1 inherited warning,4.39s | evidence/audit-fixes-focused-v01/report.json; tests.log |
| Frozen contract | Actual schema equals frozen1.0.0;4 examples validate | evidence/contract-reconciliation-v03/report.json |
| Quality | Five checks pass; current source hashes frozen | evidence/final-quality-v06/report.json |
| Applicable backend regression |979 passes,4 POSIX-only skips on Windows,1 warning,116.37s; isolated owned target, unchanged catalog, clean stop and source hashes | evidence/final-regression-v02/report.json; tests.log |
| Packaging |13 passes,0.33s; indexed evidence path/role safety | evidence/packaging-check-v03/report.json; tests.log |

Earlier evidence remains historical with its original hashes/counts. DELIVERY_EVIDENCE.json identifies the current release proof. Team1's status report/111-test claims were read, but its actual delivery files are unavailable; no independent Team1 build/merge acceptance is inferred.

### Additional real Windows path-alias recovery

The attempted default restart was initially refused: initial unresolved state ownership differed from the canonical identity used after Windows packaged-app directory creation. No marker was blindly overwritten and no unrelated process was stopped. A narrowly validated transition now requires self-consistent original identity, matching canonical directory, existing target database and object/scratch/protected roots, plus status/live identity. New state is canonicalized after creation; the prior marker is backed up before validated normalization.

Six additional ownership regressions pass. Current results:83 focused checks (audit-fixes-focused-v02),985 full backend passes/4 skips/1 inherited warning in111.82s (final-regression-v03),13 packaging passes (packaging-check-v04) and all five quality checks (final-quality-v07). Frozen contract proof remains contract-reconciliation-v03 because candidate schema/source was unchanged by the ownership-only patch.

The default owned app stopped and restarted successfully with the same existing database/imports. Actual H01/H02/opt-in-nearest25000 requests and cached GET/detail run identities matched; computed:false. HTTP timings0.029–0.114s are lookup-response times only. Duplicate launch rechecked readiness and produced no extra child processes. Live docs returned200 with zero external asset URLs.

Browser proof became available via the supported in-app provider: baseline Explore H01 depth, Compare H01/H02 and Evidence screenshots, plus corrected offline docs and Tab focus on its local OpenAPI link. These partial checks do not establish Team1 UI/What-if, all16 maps, full keyboard/no-WebGL/slow-load, physical adapter disconnection, second device or recordings. See evidence/browser-smoke-v01.
