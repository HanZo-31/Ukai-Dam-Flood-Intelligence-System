# Performance/resource testing — item 5 of the current six-item checklist

This is separate from the earlier storage/input-output agreement candidate that
was also called Step 5. It measures local engineering targets, not Team A scientific
acceptance or public-production capacity. Git, public hosting and login remain deferred.

## Targets chosen before measuring

On 2026-10-06 the user delegated selection of the preferable option. The previously
proposed local targets were selected as **provisional engineering checkpoints** in
`docs/contracts/b2-performance-targets.local.json`. This is not an invented Team A
SLA, receiving-owner approval or scientific sign-off.

| Workload | Checkpoint |
| --- | --- |
| Eight JSON workloads, five concurrent closed-loop clients | Per-route total-request p95 ≤500 ms |
| Full 341 MiB COG, two concurrent clients | p95 complete transfer and client SHA256 check ≤15 s |
| HEAD or a 64 KiB middle range on that COG, two concurrent clients | p95 ≤5 s |
| Mixed traffic: five JSON plus two full-COG clients | Same per-workload targets |
| Functional integrity | Zero unexpected statuses, IO/timeout/validation/checksum errors |
| Memory | Sampled current and cumulative kernel peak ≤90% of the 2 GiB container limit |
| Scratch / recovery | At least 8 MiB reserve; recovery to starting free space within 4 MiB |
| Stability | No OOM events/kills, unexpected API restarts or fixture mutation; liveness/readiness recover |

The catalogue contains 100 additional clearly synthetic identities plus the existing
fixtures. Additional identities reuse genuinely verified small GIS files and preserve
the existing dataset provenance. They are catalogue-scale probes, not 100 independent
scientific simulations. The large fixture is the real strict-valid uncompressed
8192×8192 COG from Step 4, not a byte blob.

## Method and measurement limits

The workload runs from Windows Python 3.13 over the actual Docker IPv4 loopback
publication to the hardened Linux API. Each client is closed-loop with zero think time:
it submits the next request after the previous finishes. This is **not** an open-loop
arrival-rate or universal requests-per-second capacity test; queueing under a fixed
external arrival rate can be worse. Metadata and artifact cases run separately,
then together to observe interference.

Warmups are validated but excluded from percentiles. Filesystem, DB and connection
caches are warm; no global cache-drop operation is performed or cold-cache claim made.
JSON/mixed phases last at least 60 seconds; each artifact phase at least 45 seconds.
They continue to obtain at least 100 samples per JSON route / 40 artifact samples,
up to a 240-second phase ceiling. In-flight requests drain afterward; HTTP IO timeout
is 60 seconds and API stream deadline remains 300 seconds. These are bounded short
runs, not an overnight soak or leak-free certification. Insufficient samples/duration
or changed workload/targets cannot be called a pass.

Record nearest-rank p50/p95/p99/max, counts, statuses, bytes and full raw request timings.
Artifact times include client streamed hashing; no 341 MiB response is buffered in RAM
by the load generator. HEAD/ranges still require full server SHA256 snapshot verification.
Client SHA256/response validation remains enabled during the workload.

A read-only one-second cgroup observer reports memory.current, memory.peak, OOM
counters, CPU usage/throttling, process RSS/FD counts, PIDs and scratch availability.
It runs as the existing unprivileged container user, reads no environment/private
data, mounts no Docker socket and adds a small measured observer overhead. The
observer exits through its own stdin on completion; failure to clean up blocks acceptance.
Sampled values can miss sub-second spikes; kernel memory.peak is retained but is
cumulative since container creation, including earlier scratch-failure checks.
The gate uses that cumulative peak conservatively rather than resetting kernel state.
Sampling gaps over three seconds or incomplete interval coverage block acceptance.

Before/after fingerprints cover the disposable catalogue and all synthetic object
bytes. Working B1 DB/objects and foundation/config preservation remain the surrounding
rehearsal's independent checks. No benchmark writes to working B1 data.

## Repeat safely

Do not run other local stress tests, builds or application writes during measurement.
Rebuild the verification target after adding/changing probe code; this work does not
change release API code, schemas, dependencies, resource defaults or its image ID.

```powershell
docker build --target verification -f services/api/Dockerfile -t ukai-b2-api:verification .
.\.venv\Scripts\python.exe scripts/rehearse_b2_container.py --performance-profile docs/contracts/b2-performance-targets.local.json --output data/handoff/b2-performance-NEW
```

Use a new folder; never overwrite historical results. The profile implies large-asset
fixture preparation and retains prior functional/outage/restart/shutdown checks.
`performance-resource.json` contains raw requests, telemetry, each phase and the local
target gate; `container-verification.json` independently records engineering receiving,
image IDs, fingerprints/cleanup and performance outcome. A functional container pass
does **not** imply a performance pass. Inspect `performance_gate.local_provisional_acceptance`.
No failed target is automatically relaxed or relabelled a pass.

## Latest local checkpoint evidence

The 2026-10-06 run passed all predeclared local targets. It measured 19,017 requests
(27 functional warmups excluded) over five phases. Worst JSON p95 was 97.037 ms
standalone and 199.209 ms mixed; full COG p95 4.391 s standalone / 9.238 s mixed;
HEAD/range p95 1.103 / 1.063 s. There were zero unexpected errors, no OOM events,
no unexpected API restarts and complete scratch recovery. The sampler stopped.
Every resource phase met sampling-coverage checks. No thresholds were loosened.

The mixed phase extended to 160.827 seconds to collect the required 40 large-transfer
samples (41 completed); short minimum durations were not used to hide missing samples.
This is still one warm-cache trial, not a cross-host repeat or statistical guarantee.
Fresh combined suites passed: 712 Windows with four Linux-only skips; 715 Linux
with one host-only exclusion. B1 working data and 40 core files were preserved.

Evidence is in `data/handoff/b2-performance-01/performance-resource.json` and
`container-verification.json`, plus the workspace `outputs/B2-step-5-performance-`
verification/report files. Release image remains
`sha256:532d5f93799126b26a349b8f5d699c8033d6c6bf1e414ceb45b54338052dc30d`.
Its unchanged image/package audit applicability gate was revalidated against the
new receiving report and same-day scans; no new image scan was necessary or claimed.

## Remaining final acceptance

Even a passing local checkpoint still needs agreed actual scenario counts, maximum
asset sizes/formats, frontend/GDAL range patterns, concurrency/arrival rate, duration,
host/storage/network budgets, latency/error targets and representative approved Team A
bundles. The current 512 MiB cap and 341 MiB fixture do not establish capacity above
that cap. KML/large vector scientific ingestion limits are separate. The earlier
storage/input-output/reviewer-policy agreement also remains pending joint review.

References: [cgroup v2 measurements](https://docs.kernel.org/admin-guide/cgroup-v2.html),
[Docker memory/CPU constraints](https://docs.docker.com/engine/containers/resource_constraints/),
[HTTPX client pooling](https://www.python-httpx.org/advanced/clients/).
