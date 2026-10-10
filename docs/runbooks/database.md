# Database operations and recovery

For the consolidated operator checklist, version policy, failure handling and
recovery promotion boundaries, see [B1 operations](b1-operations.md).

## Migration policy

- Never edit an applied migration. Add a new, reviewed Alembic revision for every schema change.
- Apply with `alembic upgrade head`; downgrade only in a disposable local environment.
- Migration revisions are ordered from `08e497d20176` through `g05b8eab1001`. The extension-owned `spatial_ref_sys` table is deliberately outside Alembic management.
- Before release, run the test suite and apply the migrations to a clean database as well as the upgrade environment.

## Backup and version policy

- Take a daily logical `pg_dump --format=custom` backup and retain 35 daily copies; retain one monthly backup for 12 months.
- Take a pre-migration backup and label it with the Alembic revision being left behind. Restore drills are required quarterly.
- Keep object storage versioning enabled. Input and result objects are immutable: publish corrections under a new versioned key, never overwrite a referenced object.
- Store each manifest, model version, dataset version, and SHA-256 checksum with its scenario. Database backups do not replace object-storage backups.

## Recovery sequence

1. Restore the database backup to an isolated database.
2. Check `alembic_version`; use that exact revision to select compatible service code.
3. Verify every `scenario_inputs` and `result_assets` checksum against the object store.
4. Promote only after the manifest and output inventory reconcile.

## Executable local backup and restore drill

Pause application writes while creating a backup. Choose a new directory for
each run; an existing backup directory is never overwritten.

```powershell
.\.venv\Scripts\python.exe scripts\backup_db.py backup data\backups\b1-YYYYMMDD-unique
.\.venv\Scripts\python.exe scripts\backup_db.py restore-check data\backups\b1-YYYYMMDD-unique
```

The backup includes a PostgreSQL custom-format archive, all local immutable
objects, SHA-256 inventory, migration revision, table hashes/counts, and sequence
positions. Restore-check creates a fresh `b1_restore_<uuid>` database, restores
PostGIS and the archive's application tables (16 at the current head), checks
data and sequences, and verifies local inputs/results, dataset sources, validation
reports, published assumptions and run quality reports against copied objects.
Older six-/eleven-/fourteen-table archives remain supported. The temporary
database and container dump are removed afterward; the backup is retained.

The script is scoped to the local Docker database `ukai_postgres` and local
storage. It records unverified external S3 references separately. The legacy
`demo-monsoon-001` has placeholder S3 references; use `demo-monsoon-local-002`
for a verified demo. Restore-check does not claim those legacy objects exist.

For actual recovery on another host, restore the archive to a new database,
restore the objects to the recorded storage root, or supply a reviewed URI
remapping migration. Restore-check verifies the backup in place and is not a
command for promoting a restored database into production.

The retention periods above are policy, not an installed scheduler. Keep daily
and monthly copies on separate storage before pruning local backups. This
implementation does not automatically delete backups or schedule recurring jobs.
