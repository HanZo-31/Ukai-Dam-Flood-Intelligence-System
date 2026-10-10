# Team B (B1 + B2) — local completion and handoff checklist

Scope: trusted local computers, Python 3.13, local project files/data, no public
deployment or application login. Git/CI is deferred. Hand over only a package
whose current source/evidence/manifest and independent delivery verification pass.

## Completed independent local work

- [x] B1 PostgreSQL/PostGIS, seven migrations, sixteen tables and model/schema parity.
- [x] Repeatable demo seed, processing-run adapter, datasets/events/metrics catalogues.
- [x] Manifest/GIS verification, approval/revocation/mode gates and B2-facing repositories.
- [x] Immutable local object storage, checksum integrity, backup and restore checks.
- [x] B2 eight read-only business endpoints, typed public schemas and operational readiness.
- [x] Verified layer/export/assumptions links, complete/range/HEAD downloads and safe errors.
- [x] Strict configuration/readiness and tested reader/storage/scratch privileges.
- [x] Trusted-local network/security controls; no login or public service added.
- [x] Scoped dependency/image vulnerability review with raw findings and expiry retained.
- [x] Independent local correctness lint and gradual application typing; no strict/all-rules claim.
- [x] Real 341 MiB COG storage, capacity, disconnect and fault-recovery checks.
- [x] Provisional local resource/performance checkpoint, not Team A's real-data SLA.
- [x] Combined B1/B2 regressions, OpenAPI freshness/conformance and dependency checks.
- [x] Current receiving/setup/pending instructions and source/evidence/checksummed ZIP workflow.
- [x] Preservation of working B1 data/foundation and owned test-resource cleanup.

Steps 1–6 of the latest B2 readiness sequence refer to the local checks above.
Original B1/B2 step numbers and historical counts remain in their dated records;
do not confuse them with final joint acceptance. The current package's evidence
gives the actual latest test counts, image IDs, source hashes and checksums.

## Not prerequisites for this local handoff

- Git/CI: explicitly deferred by the user.
- Public hosting, public keys, external HTTPS and application login: out of scope.
- Remote object-store adapters or scheduled/off-host backups: later operations if chosen.

Localhost is a trusted-computer boundary, not file-possession authentication:
other processes/users on that computer can call a running local API. Private DB
credentials and scientific reviewer provenance are separate from user login.
The API serves B1-registered approved results; it does not train/run ML or hydraulic models.

## Joint tasks when Team A provides the inputs

- [ ] Team A model/code and real representative reviewed output bundles available.
- [ ] API/scientific/storage namespace, units/datum/role and reviewer-policy agreement.
- [ ] KML GIS validation path agreed if required, or explicitly exclude the derivative.
- [ ] Real size/format/concurrency/host budgets and formal workload acceptance agreed.
- [ ] Receiver verifies their actual Python/Docker/data setup and records acknowledgement.
- [ ] Team A output -> manifest -> B1 -> B2 -> consumer/model workflow passes jointly.

An agreed representative subset can be integrated before all Team A work finishes.
These cannot be signed off solely by Team B or inferred from synthetic tests.
Default tested capacity is 512 MiB per artifact, 1 GiB scratch and 2 GiB API memory;
files above that cap need coordinated sizing and fresh checks. Windows asset URIs
must be registered in the agreed Linux namespace when using the hardened container.

## Current handoff audit corrections

The audit hardens portable archive names against case aliases, reserved Windows
devices, trailing dots/spaces, noncanonical/control-character paths and special
ZIP members. Private/cache exclusions are case-insensitive. The supplied quality
runtime is explicitly checked as Python 3.13. Benchmark provenance covers the
actual load-generator/fixture/profile files; unrelated handoff-doc changes no
longer falsely require a new performance measurement. Runtime source is still
checked separately against the exact measured image, and all delivery source
hashes remain frozen. Added regressions verify these rules.

References: [Windows naming rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file),
[local quality/privacy scope](runbooks/b2-local-quality.md),
[handoff guide](runbooks/b2-local-handoff.md), [pending joint gates](b2-pending-items.md).
