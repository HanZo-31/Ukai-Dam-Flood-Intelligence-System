# B1 local readiness — 2 October 2026

Historical report for the initial demo only, not current full B1 acceptance.
See [current B1 status](b1-status.md), `b1-to-b2-handoff.md` and `contracts/published-registry.md` for current
implementation and remaining integration boundaries.

The local B1 demo and B2-facing contract adapter are implemented and verified.
Final suite: **34 passed**. `alembic check` reports no model/schema drift.

## Resolved and verified

- The processing-run unique constraint is represented in the model. No applied
  migration was changed, and migration SHA-256 hashes remain identical.
- Alembic escapes percent signs in connection URLs. Fresh migrations and
  downgrade/re-upgrade are tested using an encoded connection-option URL in a
  disposable schema.
- A local immutable object store publishes actual synthetic inputs and outputs.
  Registration and completion verify their SHA-256 checksums. Invalid URIs,
  path traversal, missing objects, altered objects, and conflicting writes fail.
- `demo-monsoon-local-002` seeds all six application entity types. Repeated seeds
  verify existing metadata and avoid duplicates. The old demo is preserved.
- B2-facing start/fail/complete adapters and CLI are tested in PostgreSQL.
  Database failures roll back results, failed runs stay auditable, retry creates
  a new run, and duplicate completion is rejected.
- A database/object backup and restore drill passed. The restore checks all six
  tables by count and content hash, sequence positions, PostGIS, and three local
  input/output references. Five object files were backed up, including the
  assumptions and canonical manifest.
- Setup, storage, backup/recovery, migration policy, and B2 handoff runbooks were
  updated to match the actual implementation.

Backup evidence: `data/backups/b1-20261002-verified-02/backup.json` and
`restore-check.json`. The backup is retained. Disposable test schemas, restore
databases, and temporary container dump files are removed by the tools.

## Remaining external acceptance

- Production S3 backend, credentials, bucket versioning, and remote restore
  verification: not supplied. The working storage adapter is local/demo.
- Real B2 read-only API integration: not present in this historical snapshot.
  The internal B1 adapter is tested; model behavior belongs to Team A, not B2.
- Team A's real bundle and any additional required entity contract: pending.
  The implemented six entities cover the currently available local workflow.
- Two legacy demo S3 input references remain unverified and are explicitly
  recorded by backup inventory. They are not used by the verified local demo.
- Retention and daily/monthly backups are documented policy. No recurring
  scheduler or external backup location has been configured.

All runnable local checks pass. This is a local/demo B1 readiness statement,
not full production deployment or real-data B2 integration sign-off.
