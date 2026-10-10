# Steps 11 and 13 verification — 2026-10-05

Scope: local acceptance regression tests and consolidated documentation/recovery
policy ONLY. Step 14's final handoff rehearsal and step 12's Git/CI remain deferred.

## Changes

- Added test_b1_acceptance.py: 32 cases covering the eight-state real-GIS public
  read gate matrix, explicit mode on all seven accessors, concurrent immutable
  object publication and missing-scenario behavior.
- Extended test_backup_integrity.py by six cases covering traversal, unsupported
  table inventories and refusal to overwrite an existing backup directory.
- The table-inventory tests first failed: rejection occurred after recovery
  started database access. backup_db.py now performs the allowlist preflight
  before any database connection/restore. Supported older subsets still work.
- A preservation check found an older smoke test wrote into public and rolled
  back its rows but still advanced two nontransactional PostgreSQL ID sequences.
  It now uses an isolated schema and asserts the complete public snapshot,
  including sequence positions, remains unchanged.
- Added current status, acceptance coverage and consolidated local operations/
  recovery/version-policy documents; corrected stale producer/B2 wording.
- No schema/model/migration change, scientific approval or working-data ingestion.

## Observed results

| Check | Result |
| --- | --- |
| Final complete pytest suite | 240 passed in 26.56 seconds; no failures, skips or warnings reported |
| Alembic check | No new upgrade operations detected |
| Dependency check | No broken requirements found |
| Documented metadata command with --allow-draft | Valid demo/draft; no registration |
| Documented actual GIS validation command | Four assets verified; draft; no DB writes or scientific approval |
| Fresh backup b1-acceptance-20261005-01 | 13 objects; 16-table snapshot; retained |
| Fresh backup restore-check | 16 tables, PostGIS, sequences/hashes and three local catalog references verified |
| Earlier b1-publication-20261005-01 restore-check | 14 tables, PostGIS and three local catalog references verified |
| Existing suite populated-GIS restore test | Passed; disposable approved fixture, geometry and seven references checked |
| Working DB and object fingerprints | All saved rows/hashes and 13 files unchanged; first run advanced scenarios/scenario_inputs counters by one via the older smoke test, corrected before final rerun |
| Final rerun preservation | Complete working snapshot identical before/after the corrected suite, including all ID sequences and 13 object hashes |

The fresh restore report retains two unresolved legacy S3 references. They are
not claimed as recovered or verified remote objects. Working dataset/publication/
spatial catalogs stay empty and the saved synthetic GIS manifest stays draft.
All application migrations remain unchanged at head g05b8eab1001.

## Remaining operational boundaries

Daily/monthly retention is documented, not automatically scheduled or pruned.
No independent/off-host backup copy or promoted/host-transfer recovery was done.
Backups are checksum-protected inventories, not signed/authenticated archives;
only trusted archives should be restored. Git, hosted DB/storage deployment,
reviewer authentication, Team A science and B2 HTTP integration are outside this
batch. Step 13 completes the local runbook/policy scope, not a deployed disaster
recovery service. Step 14 remains explicitly unperformed.
