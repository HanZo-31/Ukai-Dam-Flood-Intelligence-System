# B1 completion and B2 handoff

Date: 5 October 2026. Project: Ukai Dam Flood Intelligence, `D:\Dam Projects`.

## Decision

**B1's supported local engineering deliverables are complete and verified,
excluding step 12 (Git/CI). Ready for handoff to B2 for read-only API development
and integration. No known blocking defect remains within the verified local scope.**

This is an engineering sign-off, not a guarantee of zero defects in every future
environment or format. Joint contract approval, real Team A scientific acceptance,
B2 HTTP integration and production release acceptance remain separate gates.

## Completed responsibilities

| B1 responsibility | Delivered and verified |
| --- | --- |
| Local environment | Docker PostgreSQL/PostGIS, healthy persistent database, localhost-only port |
| Migrations and entities | Seven preserved applied revisions; head `g05b8eab1001`; 16 application tables |
| Demo seed | Real synthetic local inputs/output, internal run audit, impact and status; safe identical reruns |
| Dataset provenance | Dataset/version identities, sources, licences, checksums, coverage, units and quality notes |
| Historical catalog | Event metadata and explicit dataset-version links |
| Validation metrics | Supplied finite metrics, units/configuration/report provenance; B1 does not calculate scientific accuracy |
| Result metadata | Scenario/run/asset/impact fields, model/input identity, coverage and nullable unavailable measurements |
| Manifest registry | Candidate v1.0.0 schema/semantic validation, verified files, trusted operator context, atomic registration |
| Publication controls | Approved-only reads, explicit mode, draft/rejected/revoked hiding, retained snapshots and revocation audit |
| Repository access | Stable pagination, model/dataset/event/time filters, assets, impacts, provenance and demo status |
| Spatial/GIS support | Indexed lightweight geometry, actual extent intersections, supported COG/GeoJSON inspection |
| Storage | Append-only versioned local objects, real SHA-256 hashes, concurrent-write protection |
| Step 11 testing | 262 passing tests, including 19 final-audit regression cases |
| Step 13 operations | Setup, runbooks, troubleshooting, manual backup/retention/version policy and verified restore tooling |
| Step 14 rehearsal | Clean source-copy → empty DB → seed → catalog/import → consumer reads → rejection/revocation → backup/restore |
| Step 12 Git/CI | Deliberately excluded; no Git setup, commit, push or merge |

## Final audit and fixes

The audit reviewed active models, applied revisions, input/published contracts,
repositories, storage, GIS inspection, registration scripts, recovery tooling,
source packaging and operational documentation. It added failure-case tests and
corrected the following:

1. Legacy registration and completion now revalidate objects modified after
   parsing. Invalid modes and negative/nonfinite declared impacts are rejected
   before persistence.
2. Internal completion owns a savepoint, preventing partial outputs if a caller
   catches a late error and keeps using its outer transaction.
3. Completion supports the database's full 150-character run ID; failure transitions
   reject inconsistent scenario state.
4. GIS inspection detects synthetic flags on individual features/properties as
   well as the collection. Existing production gates reject tagged synthetic data.
5. Source packaging excludes nested private .env files/configuration directories
   and refuses symlinks/junctions in allowed source targets. Only .env.example is
   intentionally included at the root; working private configuration is not shared.
6. Internal CLI failures no longer echo invalid payload values or credentials.
7. Malformed backup metadata/object inventories fail cleanly before database access.
8. Docker's port is bound to 127.0.0.1. Localhost connections normalize to IPv4
   and default to a five-second connection timeout, preserving an explicit timeout.
9. Stale worker-role, table-count and completion wording was corrected. B2 is the
   read-only API/integration owner, not the hydraulic simulation worker.

No applied revision or published JSON Schema version was rewritten. Migration
environment connection handling changed, not the schema revision history.

## Verification evidence

| Check | Observed result |
| --- | --- |
| Full active regression suite | 262 passed; no failures, skips or warnings reported |
| Full suite from copied source/fresh seeded DB | 262 passed in the clean rehearsal |
| Clean rehearsal | All 20 checks passed |
| Alembic parity | No new upgrade operations detected |
| Dependencies | pip check clean; every explicitly pinned installed version matched requirements.txt |
| Python syntax | All 59 active Python source files parsed successfully |
| Runtime | Verified Python 3.13 environment; PostgreSQL 16.15; PostGIS 3.6.4 |
| Clean populated restore | 16 tables, PostGIS, geometry, table hashes, sequences and 35 local references verified |
| Working backup before port change | 16 tables, all 13 local objects and three local catalog references verified |
| Working-data preservation | Saved rows/hashes, ID sequence state and all original 13 file hashes unchanged |
| Revision preservation | All seven applied migration file hashes unchanged |
| Local exposure | Healthy container publishes only 127.0.0.1:5432; existing persistent volume retained |

The working database still contains two scenarios, four inputs, one run, one
result asset, one impact summary and one status reading. New production/catalog/
publication/spatial records were NOT fabricated in the working database. The
saved GIS fixture remains draft; test approval exists only in isolated test or
rehearsal data. Two retained legacy S3 placeholders remain explicitly unresolved.
They are not used by the verified clean handoff fixture, whose external-reference
inventory is empty.

## Handoff package

Final audited package, relative to the project root:
`data/handoff/b1-final-audit-20261005-03/`.

- `source/`: dated source, pinned requirements, Compose, migrations, tests,
  contracts and documentation, including this completion file.
- `objects/`: actual synthetic GIS/input/report/manifest artifacts; the intentionally
  invalid manifest is retained solely as rejection evidence.
- `backup/`: matching database archive, object inventory and successful restore report.
- `rehearsal.json`: per-check outcomes, full clean-suite result, source/object
  hashes, preserved-working-data flag and removed-temporary-database flag.

Only use a package whose result is passed and both preservation/cleanup flags are
true. Earlier attempts are retained for traceability, not the latest sign-off.
The interrupted temporary database was explicitly checked and removed; no
working database or volume was deleted. Compatible restore points are retained.

The package is not a live database or a deployment installer. It reuses the
installed Docker server and Python environment; a new-host install was not tested.
Absolute file:// references must be regenerated or deliberately remapped when
moving hosts. Checksums detect drift, not authenticity; restore only trusted archives.

## B2 receiving checklist

1. Review candidate schema/spec and freeze shared decisions with Team A/B1.
2. Choose the supported Python runtime. 3.13 is verified; the blueprint's 3.12
   compatibility has not been verified. Set up private local configuration; do not
   copy or expose B1's .env.
3. Run migrations, seed, tests and the rehearsal in B2's own environment. Use a
   new rehearsal output directory; do not point at a former temporary DB.
4. Use PublishedScenarioRepository for public scenario, asset, impact, provenance
   and spatial reads, with explicit demo/production mode. Use explicit modes for
   catalog/status queries too. Do not expose unrestricted admin writes.
5. Implement read-only FastAPI responses, OpenAPI, safe served asset links,
   pagination/error envelopes and API integration tests. Never return raw local
   paths, private bundle snapshots or credentials to clients. No public simulation
   execution endpoint is authorized.
6. Integrate actual Team A approved results when supplied; jointly verify the
   real provenance → manifest → catalog → API roundtrip and agreed performance.

## Remaining gates, not hidden completion claims

- Shared contract freeze: vertical datum, roles/exports, quality thresholds,
  identifiers and reviewer authority still require Team A/B1/B2 agreement.
- Scientific review and real result bundles belong to Team A. B1 verifies/catalogs
  their supplied bytes and metadata; B2 serves them.
- Current local GIS formats have documented limits; KML, rotated/multiband grids
  and domain-specific refinements need agreed scope/adapters if required.
- Production least-privilege/authentication, remote storage if chosen, scheduled
  backups, independently protected copies and promoted recovery are later work.
  Manual backup policy/tools exist; scheduling and off-host copying are not installed.
- Supabase, Tiger Data and S3 are not required to start supported local integration.

These shared/deployment gates do not block giving B2 the local candidate now.
They do block declaring the complete backend scientifically accepted or production-ready.

Related: [handoff checklist](b1-handoff-checklist.md), [acceptance coverage](b1-acceptance.md),
[operations](runbooks/b1-operations.md), [rehearsal](runbooks/handoff-rehearsal.md),
[candidate contract](contracts/README.md).
