# B2 handoff status and pending gates

Status as of 2026-10-06: local-only scope confirmed; item-6 refreshed handoff
instructions/workflow available. Deliver only a successfully verified refreshed
archive; the earlier Step 19 archive is historical.
No receiver acknowledgement, scientific approval,
agreed performance acceptance or production release is claimed.

## Completed locally

- [x] Python 3.13 setup, existing B1 reuse and isolated synthetic fixtures.
- [x] Eight read-only business endpoints and Pydantic response/request schemas.
- [x] Safe approved/mode-scoped layer, assumptions and export links/downloads.
- [x] Impact/event provenance and explicitly demo/non-live status.
- [x] Safe problem responses, functional/integration regression tests.
- [x] Step 16 OpenAPI 3.1, verified synthetic examples and usage guide.
- [x] Step 18 clean same-host receiving, actual HTTP checks and bounded baseline.
- [x] Step 19 local source package, setup guide, test evidence and pending list.
- [x] Production Step 1 implementation: fail-closed configuration, dependency
  readiness, read-only privileges, mount identity and scratch checks. Completion
  requires the fresh Step 1 host/container verification evidence, not health alone.
- [x] Step 2 security baseline accepted for the confirmed local-only scope.
- [x] Step 3 compatible shared framework upgrade, hardened/rebuilt XML runtime,
  complete Python audits and exact-image local vulnerability gate. Original closure
  regression: 647 Windows passed; 646 Linux passed with one documented host-only
  exclusion. Working B1 foundation/data preserved; owned rehearsal resources removed.
- [x] Step 4 local storage/download implementation and realistic failure rehearsal:
  real strict-valid 341 MiB COGs, two slow concurrent readers, safe admission
  backpressure, byte integrity/ranges/HEAD, client abort cleanup, fault recovery,
  bounded verification/streaming and early catalogue-connection release. Final
  original suite: 678 Windows passed (four Linux-only skips); 681 Linux passed (one host-only
  exclusion). New exact-image vulnerability gate passed. Final Team A capacity/SLA
  and representative real-data approval remain pending, not implied by this result.
- [x] Performance/resource item 5: user-delegated provisional local targets passed
  in sustained standalone/mixed traffic against 105 approved synthetic catalogue
  entries and a real 341 MiB COG. 19,017 measured requests, zero unexpected errors/OOM,
  complete scratch recovery and preserved B1 data. Original suites: 712 Windows passed
  (four Linux-only skips); 715 Linux passed (one host-only exclusion). This does
  not close Team A's final workload/SLA or formal scientific/performance acceptance.

- [x] Item 6 refreshed setup/receiving instructions, blank receiver decision
  record and evidence packaging workflow. The refreshed package requires fresh
  source/Windows/Linux checks and checksums; actual delivery results belong in
  its evidence/manifest, not an invented acknowledgement.
- [x] Local pre-merge correctness lint and gradual application type gate now
  implemented and required by refreshed packaging. See [quality/privacy policy](runbooks/b2-local-quality.md).
  The delivered report records actual passes and scope; strict/all-rules typing
  or jointly agreed CI approval is not claimed.

## Still pending before full acceptance

The storage/input-output agreement track (previously labelled Step 5) has started:
the [storage/input-output agreement candidate](contracts/b2-storage-io-agreement-candidate.md)
documents implemented paths, portable reference conventions, role/unit/trust
boundaries and the remaining team decisions. No working data/runtime/schema was
changed. It is prepared for review, **not jointly agreed or frozen**. Team A need
not complete all modelling before reviewing it. The reviewer-identity disclosure
policy conflict must be resolved before final contract freeze.

Performance/resource testing is now item 5 of the latest six-item checklist.
The user delegated target selection; provisional local checkpoints are defined
before measuring in `docs/contracts/b2-performance-targets.local.json`. See
[the repeatable workload runbook](runbooks/b2-performance-resource-testing.md).
Original item-5 evidence passed those provisional checkpoints: worst JSON p95
199.209 ms, full-download p95 4.391 s standalone / 9.238 s mixed, HEAD 1.103 s,
range 1.063 s. No limits were relaxed after measurement. Final Team A workload/SLA
and receiving-owner approval remain pending; this is not a public production SLA.
The later quality follow-up remeasured the changed image: 19,854 requests, worst
JSON p95 193.139 ms and mixed full-transfer p95 8.133 s. Current handoff evidence
identifies the exact image and latest source checks. See [combined Team B checklist](team-b-local-handoff-checklist.md).

Step 2's tested local host/CORS/header/request-boundary baseline is accepted for
the user-confirmed local-only scope. Public login/keys/hosting/external HTTPS and
proxy integration are deferred and do not block local merging. Earlier Step 2
reports are historical, not rewritten. See [Step 2 security](runbooks/b2-step-2-security.md).

Step 3 is **complete for the exact tested, local-only Linux API runtime**. The
authorized shared upgrade changes FastAPI/Starlette and adds required OTel API;
B1's other scientific/database pins and core code remain unchanged. Scans report
zero critical and Python-package findings. Eight unique high OS advisories
(44 package/advisory pairs) remain raw and visible, with evidence-based,
expiry-bound "not affected" applicability dispositions for this runtime. This
is not a vulnerability-free certification or owner risk acceptance. Medium,
low and unknown OS findings also remain visible. Re-review before 2026-11-06,
or sooner on changed advisories/code/profile/base/external exposure. See
[Step 3 review](runbooks/b2-step-3-vulnerability-review.md) and the fresh workspace
completion report; older failed review reports remain historical.

| Gate | Expected coordinating owner (not an assigned person) | Closure evidence |
| --- | --- | --- |
| Step 17: Git/CI and future shared engineering policy | Part B engineering team | Git/CI deliberately deferred; independent local correctness lint/gradual B2 type checks are included. Broader shared policies can be coordinated later |
| Step 18 formal performance sign-off | Receiving/performance owner with B1/B2/Team A | Agreed workload/limits and measured pass against representative approved assets |
| Candidate API/shared scientific contract freeze | Team A, B1, B2 and frontend consumer | Written agreement on paging/mode default/readiness, fields/units/datum, quality/authority, error and asset policies |
| Real approved result bundles | Team A scientific owner, B1 publication owner | Actual traceable reviewed output bytes, checksums, provenance and documented approver authority |
| Step 20 joint backend acceptance | Team A, B1, B2 and receiver | Approved outputs -> manifest -> B1 verification/catalog -> B2 JSON/downloads; agreed scientific/performance cases pass |
| KML GIS acceptance, if required | Team A GIS owner and B1 | Agreed inspector/validation path and approved real KML derivative; otherwise agree to exclude the format |
| Final storage/large-file acceptance | B1/storage owner and B2 with Team A | Tested local profile is available; agree actual maximum size by format, concurrency, disk/RAM budget and SLA; repeat with real approved assets. Remote adapters are not implemented or needed for the current local-only scope |
| Frontend/security/deployment integration | Deployment/frontend owner with Part B | Agree real frontend origins and receiving setup; no login/public infrastructure is required in the confirmed trusted-local scope. External exposure is out of scope |
| Receiving-team acknowledgement | Named receiver, to be nominated | Review of package manifest/setup/tests, their receiving result and explicit acceptance of remaining gates |
| Receiving verification of refreshed archive | Named receiver, to be nominated | Verify the item-6 manifest and repeat agreed checks on the actual receiving setup; old Step 19 remains historical |

These are coordination areas, not fabricated assignments or approvals. Do not
implement a shared contract or infrastructure change without the owners' agreement.

## Performance agreement worksheet

Container follow-up: see [API container setup](runbooks/b2-api-container.md) for
the API-only Compose file, local verification and production boundaries. The
earlier Step 19 archive is historical. Use the item-6 refreshed profile and
[current guide](runbooks/b2-local-handoff.md) for delivery. Step 1 adds readiness/configuration
policy and rehearsal. Steps 2/3 now close the scoped local security/vulnerability
baseline only. Real-storage review, formal performance and joint acceptance remain
pending. Local lint/type checks are independently recorded, not inferred from regression tests.

Record all of the following before closing Step 18's formal sign-off:

- [ ] Named acceptance owner and date of agreement.
- [ ] p95 limit by workload, permitted error rate and required sampling method.
- [ ] Concurrent requests/users, duration and warmup/cache conditions.
- [ ] Representative approved scenario/catalog counts and valid COG/export sizes.
- [ ] Host/storage/network specifications, memory and temporary-disk budget.
- [ ] Required scientific sample bundles and reviewer authority.
- [ ] Repeat the agreed workload and attach result/approval evidence.

The earlier Step 18 synthetic COG is 2,400 bytes. The separate 16 MiB blob is an opaque
adapter-IO check, not a valid large COG or large-raster HTTP benchmark. That earlier
run did not establish sustained capacity, peak resource measurements or a production SLA.
Step 4 adds a separate real 8192×8192 COG rehearsal (357,571,424-byte max-depth raster),
two concurrent slow-client integrity checks and actual resource/failure evidence.
This does not retroactively change Step 18's historical measurements or constitute
an agreed production SLA. The exact Team A file maximum is not known yet.
The performance/resource item-5 follow-up records repeated percentiles and sampled
memory/CPU/scratch/FD counters, not just a single GET. Its current provisional
local checkpoint passed; formal Step 18/Team A sign-off still needs the worksheet's
external inputs and representative approved outputs.

## Safe stopping point

After this local handoff, pause dependent joint acceptance until the agreed
approved representative bundles and acceptance decisions arrive. Team A need not
finish its entire project before an agreed subset can be jointly tested. Step 20
is pending external inputs, not a failed endpoint implementation. Do not erase
the other deferred gates or call an untested combined Team A/B build accepted.
The verified B2 local package can be handed over for integration while those
joint inputs remain open. The user's trusted-local/no-login scope is confirmed.
