# B1 handoff decision — updated 2026-10-06

**B1 foundation and B2 integration are ready for the confirmed trusted-local
handoff to Team A. Not yet accepted as the merged scientific/model system.**
The B1-only counts below are historical 2026-10-05 evidence. Current combined
checks and scope are in [Team B local checklist](team-b-local-handoff-checklist.md)
and the refreshed package's evidence/manifest.

## B1 deliverables verified locally

| Deliverable | Status / evidence |
| --- | --- |
| Docker local DB, PostgreSQL/PostGIS | Implemented; reused running Docker server, new empty DB/extensions verified |
| Alembic and required catalog entities | Complete local scope: seven unchanged migrations, head g05b8eab1001, 16 tables |
| Repeatable seed and internal run adapter | Implemented; actual CLI seeded clean DB twice without changes |
| Dataset versions, events and supplied metrics | Implemented; populated synthetic catalog exercised |
| Manifest validation / registration | Implemented candidate contract; actual CLI imports and rejects invalid/duplicate bundles |
| Repository layer, approval/mode gates and revocation | Implemented; B2-facing reads and audit exercised |
| Immutable versioned local object storage | Implemented; real checksums, actual COG/GeoJSON fixtures, no working-file changes |
| Spatial queries and supported GIS validation | Implemented within documented limits; real spatial metadata/queries verified |
| Step 11 acceptance tests | Complete local scope; 262 tests pass, including 19 final-audit regression cases |
| Step 13 docs, backup/version policy | Complete local documentation/policy scope; executable restore checks passed |
| Step 14 clean B1-only rehearsal | Complete: full copied-source suite, bundle workflow, recovery and preservation evidence |
| Step 12 Git/CI | Explicitly excluded/deferred |

No known additional core B1 implementation task is required to give B2 this
local candidate for development. B1 still participates in the shared acceptance
items below and may need compatibility changes when real artifacts arrive.

## Still required before formal joint acceptance

| Remaining item | Owner / concrete action |
| --- | --- |
| Candidate contract agreement | Team A + B1 + B2 review/freeze units, vertical datum representation, role/export requirements, catalog IDs, quality thresholds and authority policy. No approval is inferred from local tests. |
| Receiving runtime/environment | Python 3.13 is adopted for the user-confirmed local scope; receiving team verifies their own setup. Python 3.12 is not a current local handoff prerequisite. |
| Real approved result ingestion | Team A supplies traceable scientifically reviewed outputs; B1 verifies/catalogs exact bytes/provenance and adapts unsupported formats only after agreement. |
| Joint roundtrip acceptance | Team A + B1 + B2 prove provenance → real manifest → catalog → API for agreed samples, including performance/scientific checks. |

These do not prevent sharing the local candidate or starting B2 development.
They DO prevent calling the unseen Team A/B merged system finally accepted.
B2's actual API/repository integration, safe URLs, schemas/OpenAPI and endpoint
tests have been implemented and verified; no run-simulation endpoint is invented.

## Later deployment/operations work, not mandatory for current local handoff

Least-privilege reader controls are locally implemented/tested. Later external
identity policy and chosen remote
storage/S3 adapter if needed; backup scheduling and independently protected copy;
fresh-host installation, dependency/security audit and promoted recovery validation.
The API runtime's local vulnerability review and receiving/container rehearsal
are available in current B2 evidence; no application login is required or added.
Supabase/Tiger Data/S3 are not mandatory substitutes for the local supported stack.
Manual backup policy exists; schedules/off-host copies are not configured.

## What to give B2

- Finalized audited package at data/handoff/b1-final-audit-20261005-03/: source, synthetic
  files/manifests, matching backup and machine-readable rehearsal/restore evidence.
- Candidate contract/schema/spec and examples under docs/contracts/.
- B1 operations, current status, acceptance coverage and handoff references.
- Local tests and reproducible rehearsal command; no private .env or real credentials.

Working DB rows/catalogs stay as before; synthetic approval occurs only in the
removed rehearsal DB and its private retained archive. Empty approved-only reads
against the normal working DB are expected until a reviewed bundle is registered.
