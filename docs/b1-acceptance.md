# B1 local acceptance (step 11)

Scope: regression acceptance of the local B1 catalog, repositories, storage,
registration and recovery implementation. This is NOT step 14's final handoff
rehearsal, B2 HTTP integration, scientific acceptance or production sign-off.

Step 11/13 verified 2026-10-05: 240 passed, including 38 new acceptance cases.
Step 14 initially passed 243 tests. Final audit adds 19 cases: **262 passed**;
the copied-source rehearsal reruns the full suite against a fresh seeded DB.
Schema/dependency/recovery checks passed.
See [verification record](b1-verification-2026-10-05.md).

## Run and interpret

Run from the project root with the local Docker database healthy:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pip check
```

Pass criteria: no failed/skipped tests, no schema drift, consistent dependencies.
Tests perform writes only in generated `b1_verify_<uuid>` schemas or dedicated
generated drill databases and temporary object stores. Do not run parallel pytest
workers: the fixtures temporarily change DATABASE_URL for subprocess tests.
The suite needs a local role able to create test schemas/databases; that is NOT
a recommended public-service role. Tests clean their generated resources in
finally blocks. A terminated process may leave test resources; investigate exact
names and active sessions before manually removing anything. Never remove public.

## Coverage and evidence map

| Acceptance requirement | Executable evidence |
| --- | --- |
| Fresh migrations, upgrades, disposable downgrades, model parity | test_b1_integration.py, test_migrations.py, test_catalogs.py, test_published_registry.py |
| Repeatable synthetic seed, original demo preserved, legacy run transactions | test_b1_integration.py |
| Contract units, nulls, timezone coverage, hashes and invalid metadata | test_manifest.py, test_published_contract.py |
| Dataset versions, event links, finite metrics and DB constraints | test_catalogs.py |
| Bundle provenance, duplicate rejection, atomic savepoint/caller rollback | test_published_registry.py |
| Reviewer allowlist, approval gates and audited revocation | test_published_registry.py, test_b1_acceptance.py |
| All seven public accessors fail closed, including actual spatial results | test_b1_acceptance.py |
| Real COG/GeoJSON inspection, spatial indexes/holes, filters and limits | test_gis_catalog.py |
| Immutable files, concurrent same-byte reuse and conflicting publication | test_storage.py, test_b1_acceptance.py |
| Corrupt archives/objects, traversal and unsupported table inventory rejected | test_backup_integrity.py |
| Actual populated pg_dump/pg_restore including spatial rows and object references | test_published_registry.py::test_populated_bundle_backup_and_restore |
| Safe rehearsal target/output and secret-excluding source snapshot | test_handoff_rehearsal.py; scripts/rehearse_b1_handoff.py actual clean execution |
| Mutated DTO rejection, atomic internal completion, full-length IDs, safe CLI errors, nested secrets/link exclusion, synthetic feature markers | test_b1_final_audit.py |
| Malformed backup metadata and IPv4 connection timeout policy | test_backup_integrity.py |

The gate matrix covers draft/rejected/revoked, failed scenario, failed run,
failed quality status, missing registry snapshot and wrong mode. Each case starts
with a registered real synthetic GIS bundle and confirms all public reads hide
it. Additional cases require an explicit mode for every public accessor.

## Limits of acceptance

- A synthetic reviewer exists only inside test fixtures. No scientific approval
  is added to the working draft GIS bundle.
- Tests do not certify hydraulic accuracy, authenticate reviewers or validate
  a supplied real Team A bundle; no such bundle has been supplied.
- B2 owns HTTP responses, safe asset links, OpenAPI and API integration tests.
- The candidate manifest contract needs joint agreement. Current GIS format
  limits are recorded in contracts/spatial-gis-catalog.md.
- Checksums detect inconsistency, not authenticity against an attacker who can
  rewrite both artifacts and their inventories. Restore only trusted backups.
- Working dataset/publication/spatial catalogs need not be populated to pass:
  test data is intentionally isolated and discarded, not live project data.

See [current status](b1-status.md) and [operations](runbooks/b1-operations.md).
Step 14's separately executed workflow is documented in
[handoff rehearsal](runbooks/handoff-rehearsal.md); this coverage map does not
claim real Team A/B2 HTTP or scientific acceptance.
