# B1 local operations and recovery (step 13)

Run commands from `D:\Dam Projects`. This runbook does not authorize overwriting
the working database, approving the synthetic fixture, deploying to cloud,
installing a scheduled task, or approving real results. The separate
[step 14 rehearsal](handoff-rehearsal.md) now covers a disposable local B1 workflow;
its synthetic approval labels never promote the saved working fixture.

## Ownership and source of truth

B1 maintains catalogs, provenance, technical validation, local storage and
recovery. Team A supplies precomputed outputs and scientific approval. B2 serves
read-only data through FastAPI; it does not execute simulations. Public reads
must use PublishedScenarioRepository with explicit demo/production mode.
Legacy/admin repositories and the internal run CLI are not public interfaces.

Keep `.env`, credentials, backups and privileged operator allowlists private.
Do not paste connection URLs into reports. An allowlisted name is not identity
authentication. Do not expose the local database's administrative test role as
B2's public service account.

## Normal local checks

```powershell
docker compose ps
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Expected head: `g05b8eab1001`. No drift; no failing/skipped tests. Test results
prove technical behavior, not scientific accuracy. For first-time environment
creation see [local setup](local-setup.md); do not replace an existing .env.

The demo seed command is safe to repeat but writes/verifies demo records:

```powershell
.\.venv\Scripts\python.exe scripts\seed_db.py
```

Use `demo-monsoon-local-002` for the verified CSV demo. The retained earlier
`demo-monsoon-001` has two unverified S3 placeholders. Neither constitutes an
approved published flood prediction.

## Incoming published bundle

1. Agree the candidate contract and formats with Team A/B2; never invent an
   approver, dataset provenance, metric or missing measurement.
2. Put files under a new immutable versioned root using the object-storage layout.
   Register each exact input dataset version in the catalog before importing.
   Historical replays additionally require the matching event/version links.
3. Validate metadata, then actual GIS files. Example for the existing draft:

```powershell
.\.venv\Scripts\python.exe scripts\validate_published_manifest.py data\object-store\scenarios\synthetic-gis-local-003\manifest.json --allow-draft
.\.venv\Scripts\python.exe scripts\validate_gis_bundle.py data\object-store\scenarios\synthetic-gis-local-003\manifest.json --bundle-root "file:///D:/Dam%20Projects/data/object-store/scenarios/synthetic-gis-local-003/"
```

4. An authorized operator imports through register_published_bundle.py; consult
   `--help` and [registry rules](../contracts/published-registry.md) for trusted
   operator/reviewer arguments. The default importer checks actual GIS content.
   Metadata-only demo bypass is not suitable for production or real GIS acceptance.
5. Database registration is atomic and respects the caller transaction. Draft
   data stays hidden from approved-only reads. Rejected imports do not create
   partial registry rows; existing staged files are not deleted by the importer.

## Version and correction policy without Git

- Never edit an applied migration; record the old/new revision and take a
  pre-change backup. Use a new forward migration for fixes. Do not downgrade public.
- Input versions and referenced object keys are append-only through supported
  interfaces. Corrections receive a new dataset version, run/scenario identity
  and object root; do not rewrite a referenced file or stored manifest.
- Revoke an incorrect publication through the trusted administrative repository
  with actor/reason. Keep its original snapshot/audit. Do not hide history by deletion.
- The candidate schema is v1.0.0, not a jointly frozen agreement. Update the
  contract changelog and review compatibility with both consumers when it changes.
- Before code/dependency changes, retain a dated private source copy, requirements,
  exported schema and revision record alongside the recovery evidence. There is
  no Git or automatic source archive here; pg_dump does not back up source code.
- Database/object backups do not include `.env` or secrets. Keep those in a
  separately protected recovery location, never inside a public handoff package.

## Backup checklist and retention

Pause all application/ingestion writes, including object-store writes. Use a NEW
directory name per run (replace the placeholder timestamp/label):

```powershell
.\.venv\Scripts\python.exe scripts\backup_db.py backup data\backups\b1-YYYYMMDD-HHMM-prechange
.\.venv\Scripts\python.exe scripts\backup_db.py restore-check data\backups\b1-YYYYMMDD-HHMM-prechange
```

A complete backup has database.dump, objects/ and backup.json. A successful drill
adds restore-check.json. Check its revision, table counts/hashes, sequence state,
PostGIS flag, local-reference count and unresolved external references. Those
external references are warnings/dependencies, not successfully backed-up bytes.
Archive/table/path preflight rejects corruption and unsupported inventory before
database access where applicable. Backups must still come from a trusted source:
the manifest is not signed and pg_restore executes archive contents.

Policy: daily while actively changing data, 35 daily copies, one monthly copy
for 12 months, pre-migration/pre-change copy, quarterly restore drill and a drill
after changing recovery code. These are manual obligations, not scheduled jobs.
RPO target is at most one day ONLY if daily backups actually occur; no measured
RTO/service guarantee exists. Restore-check is a verification tool, not promotion.

Copy a verified complete backup and the compatible source/dependency record to
an independent/off-host protected location. Keeping all copies on D: does not
protect against drive loss. Verify that independent copy before pruning; retain
at least one proven recovery point and any version needed for old artifacts.
No automatic copying or deletion is installed, and no backups are pruned by this
batch. Record operator, time, archive path, revision, test outcome and exceptions.

## If recovery is needed

1. Stop writes and preserve the damaged database/files for investigation.
2. Choose a trusted verified backup plus compatible source/dependencies and
   protected configuration. Verify archive/object checksums before proceeding.
3. Run restore-check: it creates ONLY a new generated `b1_restore_<uuid>` DB,
   restores/checks data and removes that drill DB afterward. It never restores
   over the working database. Older supported 6/11/14-table archives remain valid.
4. Actual recovery requires a separately created replacement DB and restored
   object tree. Keep the recorded absolute file root or review an explicit URI
   remapping migration; moving files alone breaks saved file:// references.
5. Check the recorded Alembic revision before selecting compatible code or
   applying new migrations. Validate local references, provenance, geometry and
   publication controls. Resolve external dependencies separately.
6. Obtain operator approval before changing DATABASE_URL/storage configuration
   or promoting the replacement. Retain the previous environment until acceptance.

No automatic destructive recovery/promotion command is supplied. This checklist
documents the decision boundaries; a host-transfer/promoted recovery has not
been rehearsed and is not claimed complete.

## Troubleshooting

| Symptom | Safe response |
| --- | --- |
| Database connection fails | Check Docker health and private configuration; do not print secrets or recreate volumes. |
| Duplicate version/scenario/run | Inspect the existing identity; corrections need new versions, not overwrite. |
| Hash mismatch / missing file | Quarantine the candidate; verify staging/root and request correct bytes. Never change the checksum merely to pass. |
| GIS validation fails | Read the role-specific error; check units, CRS, alignment and supported format limits. Do not bypass production checks. |
| Empty public queries | Check explicit mode, publication status, completed run and approval; completed legacy demo is not an approved bundle. |
| Restore check fails | Retain the backup/evidence and try another trusted recovery point. Never promote a failed restore. |
| Migration drift | Review models/revisions; do not edit applied migrations or manually stamp away drift. |

Related: [database details](database.md), [acceptance tests](../b1-acceptance.md),
[storage layout](../object-storage-layout.md), [current status](../b1-status.md).
