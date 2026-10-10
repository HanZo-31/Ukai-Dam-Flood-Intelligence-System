# Team 2 — corrected engineering delivery v05

Baseline: `D:\Window C2\Projects Works\Ukai_SSD_Ready`; package ID `2ccf20b727ac4588a7f3ac39ba68b9ca`. Team2 source is in the separate `team2_work` folder. This plain overlay requires the complete verified baseline; it does not contain bundled runtimes, live database, mutable jobs or credentials.

## Current result

All three audit findings are corrected in this source:

- Duplicate startup verifies owned status, actual four-reference catalog and candidate capability instead of trusting only the proxy identity. Stale/failed instances return failure; explicitly candidate-degraded reference operation remains supported.
- New and cached lookups hash all manifest-bound input files, as well as the manifest, assets and evidence. Unsafe/nonportable paths and altered/missing inputs fail safely.
- Candidate `/docs` is a self-contained offline reference with local links and no external JavaScript/CSS/favicon. It is not interactive Swagger; raw `/openapi.json` stays available.

Fresh applicable backend regression: **985 passed, 4 skipped, 1 existing warning**, 111.82 seconds. This includes 902 baseline checks plus83 Team2 checks. Packaging checks: **13 passed**. Five quality checks pass; actual schema/examples still match frozen1.0.0. Read the indexed reports, not older source hashes, for current proof.

## Reading order

1. [DELIVERY.md](DELIVERY.md) and [AUDIT_FIXES_AND_INTEGRATION_STATUS.md](AUDIT_FIXES_AND_INTEGRATION_STATUS.md).
2. [WORK_CHECKLIST.md](WORK_CHECKLIST.md), [WORK_EVIDENCE.md](WORK_EVIDENCE.md).
3. [ASSEMBLY_AND_RUN_GUIDE.md](ASSEMBLY_AND_RUN_GUIDE.md), [DEMO_AND_ACCEPTANCE.md](DEMO_AND_ACCEPTANCE.md).
4. [Contract](TEAM1_CANDIDATE_CONTRACT.md), [OpenAPI](contract-drop-v02/candidate-openapi-v1.json), [examples](contract-drop-v02/candidate-examples.json).
5. [Evidence index](DELIVERY_EVIDENCE.json), [model diagnostic](diagnostic-v01/evaluation.json) and [original audit](evidence/four-scenario-audit-v01.json).

## Run

From this delivered `team2_work` folder:

```powershell
.\START_TEAM2.cmd "D:\Window C2\Projects Works\Ukai_SSD_Ready"
```

Use the actual complete baseline location on the receiver. Wait for READY; open `http://127.0.0.1:5176/`. Candidate reference docs are `http://127.0.0.1:8770/docs`. Stop with Ctrl+C or STOP_TEAM2.cmd with the same baseline path; wait for Stopped. Do not remove storage while services are running.

The served frontend is still the baseline build. Team1's status report describes completed frontend features/111 tests, but its actual delivery folder is not present here. That report alone is not an independently verified build or a final What-if integration.

## Remaining acceptance

Team1 must supply its actual plain-folder source/build/adapter, delivery ID, inventory and checksums. Compare ownership and adapt its capability reader to these exact fields before assembly into a new project copy. Existing candidate endpoints/routing/launcher are ready; do not create duplicate model APIs.

Final Team1 timeline/comparison/zones/What-if, actual browser/device/physical-offline acceptance and rehearsal/recording remain unperformed. Local HTTP/unit checks cannot replace them.

ML stays disabled. Four unchanged HEC-RAS references support stored lookup, computed:false, not new flood calculation. H01/H03 fit versus H02 holdout is a limited partial-domain diagnostic; reconstructed2006 is a different forcing family. The optional solver-based surrogate gate is unmet. Newly received fast_solver.zip contains source/binary/results, but is not extracted, adapted, runnable-verified or integrated.

Previous v03 and acceptance supplement remain unchanged historical artifacts. Final v04 checksum verification is performed after its last edit; inspect the emitted receipt or reproduce verification using the delivered helper.


## Additional Windows state-path correction and live verification

First creation under the packaged Windows app redirected the state directory after its initial identity was calculated. The live supervisor/database used the canonical identity while the earlier owner marker used the unresolved alias. This real restart failure was diagnosed and fixed: canonicalize after creation; recognize only the exact self-consistent legacy alias, matching physical root, current database target/object/scratch/protected roots and live/status identity. No unrelated database/profile can be adopted. A validated correction retains the original marker as combined-owner-precanonical.json before normalization.

Six additional ownership tests pass. The default owned app stopped cleanly, restarted with the existing database/imports/jobs preserved, and its duplicate readiness recheck passed without creating children. Three real stored requests and cached GET/source detail identities matched, computed:false; nearest25000 returned actual20000. Server lookup/hash timings were approximately0.023s; HTTP response times0.029–0.114s, not browser-ready or simulation latency.

Supported in-app browser smoke was performed on the baseline Explore depth map, Compare H01/H02 and Evidence, and the corrected offline docs with a visible keyboard focus. Actual screenshots were captured. This is partial current-machine baseline/documentation evidence, not Team1 final-interface/full accessibility/physically offline/second-laptop/rehearsal acceptance. Those still require the actual Team1 delivery and device work.

Current indexed source evidence uses final-regression-v03, final-quality-v07, packaging-check-v04 and contract-reconciliation-v03. The supplied frozen schema and examples remain unchanged. Final v04 seal is verified after the last documentation edit; current live services are running at5176.


Publication note: TEAM2_ENGINEERING_DELIVERY_V05 corrects the draft v04 documentation's candidate-port typo. The tested implementation and indexed evidence are byte-identical to v04; actual candidate port is8770. Keep v04 as a known documentation-defective draft, not the preferred receiving package. Final v05 transfer hashes/links/source correspondence are checked again after the correction.
