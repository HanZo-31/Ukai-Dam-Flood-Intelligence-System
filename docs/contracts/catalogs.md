# B1 catalog batch: datasets, historical events and validation metrics

Implemented by additive revision `d02c3e4b1001`, following `c01b8f01b101`.
Existing migrations, demo fixtures and published manifest schema are unchanged.
This is the storage/data-access implementation of steps 2–4, not full B1 completion.

## Dataset provenance

`datasets` identifies a named dataset and its demo/production mode.
`dataset_versions` uniquely identifies `(dataset_id, version)` and records an
artifact reference, optional HTTP(S) provenance source URL, source label,
licence, SHA-256 checksum, nullable EPSG CRS, nullable UTC-aware time coverage,
quality notes and field-to-unit mapping. Null CRS/coverage explicitly means not
applicable or unknown; quality notes must explain limitations. Coverage dates
must be supplied together and ordered. Every version needs explicit provenance.

Use `DatasetCreate` and `DatasetVersionCreate` with `DatasetRepository.register`
and `register_version`. Duplicate registrations raise `ValueError`; corrected
data requires a new version. The repository deliberately offers no version
update/delete method. Privileged raw SQL can still change rows: restrict writer
access operationally; this is append-only application behavior, not a DB-wide
immutability trigger. Referenced rows cannot be deleted because of RESTRICT FKs.

Artifact references are safe relative object keys or absolute file/S3 URIs.
Relative keys resolve under the configured object-store root. Suggested layout:
`datasets/<dataset-id>/<version>/<filename>`. Catalogue registration validates
metadata, not artifact existence, file contents, scientific quality or licences.
The published-bundle verification/ingestion step must verify real artifact bytes.

## Historical events

`historical_events` stores identity, name, start/end timestamps, observed coverage
description, quality/gap notes, source URLs and data mode. Use
`HistoricalEventRepository.register(HistoricalEventCreate(...))` followed by
`link_dataset(event_id, dataset_id, version)`. Links are unique and idempotent.
Event and dataset modes must match. Referenced versions retain their provenance.
The event list supports overlapping start/end windows, mode and stable pagination.
Geometries and spatial queries are reserved for the later spatial-catalog step.

## Validation metrics

`validation_metrics` stores one named, finite value with event, reference dataset
version, model version, optional station and processing-run reference, units,
optional positive sample count, calculation timestamp, nonempty finite JSON
calculation configuration, report reference and report SHA-256 checksum.

Use `ValidationMetricRepository.register(ValidationMetricCreate(...))`.
The observation version must already be linked to that event and be labelled
`observed` or explicitly `demo`, never `simulated`/`assumed`. A supplied run must
be completed and its scenario must match model version and demo/production mode.
Run is nullable because Team A may supply externally calculated results before
run-registry integration. Duplicate metric IDs are rejected, not overwritten.

Supported names: `rmse`, `mae`, `peak_stage_error`, `timing_error`, `iou`,
`flood_area_agreement`. RMSE/MAE are nonnegative. Signed stage/timing errors are
allowed; calculation configuration must define their sign convention. Overlap
metrics use normalized `[0, 1]` values and unit `fraction`. Configuration must
record formula, alignment/time window, exclusions/missing-data policy and any
thresholds needed to reproduce the calculation. No scientific approval threshold
is invented here. Team A computes and supplies actual metrics and reports.

Database constraints additionally enforce finite values, ranges, sample counts,
checksums and event/version links. Higher-level run-state/mode/source checks are
repository guarantees, not universal raw-SQL guarantees. List queries filter
event, station, model version and metric name with stable pagination.

## Transactions and verification

Repositories flush but never commit. Group dataset, version, event, link and
metric writes in a caller-owned transaction, for example:

```python
with SessionLocal.begin() as session:
    datasets = DatasetRepository(session)
    datasets.register(dataset_dto)
    datasets.register_version(version_dto)
    events = HistoricalEventRepository(session)
    events.register(event_dto)
    events.link_dataset(event_dto.event_id, version_dto.dataset_id, version_dto.version)
    ValidationMetricRepository(session).register(metric_dto)
```

DTOs live in `services.api.app.catalog_schemas`; repositories in
`services.api.app.repositories.catalog_repository`. Page limits are 1–1000,
offsets are nonnegative, and date filters should be timezone-aware.

Run `alembic upgrade head`, `alembic check` and `python -m pytest -q`.
Tests use isolated schemas, synthetic demo metadata and rollback. They exercise
fresh migrations, additive upgrade/downgrade preservation, provenance constraints,
repository filters, duplicate handling, rollback and signed/ranged metrics.
No real historical event or scientific metric is seeded into the working DB.

## Backup and recovery

This batch initially covered 11 tables. Current backups include all 16 application
tables and their sequences. Restore drills also support older 6/11/14-table
archives using the archive's recorded table list.
Local catalog artifact/report references must resolve inside the configured
object store and match their checksums during a restore drill. S3 catalog
references are reported as unresolved external references, not claimed verified.
An empty new catalog is valid until Team A's approved data is registered.

Before upgrade, make a backup with `scripts/backup_db.py backup <new-directory>`.
Validate it with `restore-check <directory>`; restore drills create disposable
databases and do not overwrite the working DB. Never downgrade a populated
production database to undo this batch: downgrade drops the new catalog tables.
Review a backup and recovery plan first. Migration rollback tests are isolated.

## Handoff boundary

B2 can now consume these catalog repositories in read-only endpoints. Shared
contract approval, spatial fixtures, CI and the final cross-team rehearsal are
separate pending steps. These catalogs do not implement B2 APIs.

## Subsequent batch update

Local published-bundle registration, fuller run/asset/impact metadata and
approval-aware reads are now implemented. See `published-registry.md` for
their current guarantees and production GIS/trust boundaries. The original
catalog contracts above remain unchanged. The scenario/asset spatial catalog,
broader queries and clean B1-only rehearsal are now implemented. Domain-specific
geometry refinements, B2 API and real-data acceptance remain shared work; Git/CI
is intentionally deferred. See ../b1-handoff-checklist.md for current status.
