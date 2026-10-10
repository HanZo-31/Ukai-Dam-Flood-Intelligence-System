# B2 production Step 1: configuration and readiness

Scope: dependency readiness and fail-closed production configuration only.
Completing this step is not final production acceptance. B1 code, migrations,
working database, object files and local Python 3.13 environment are preserved.
Git/CI and Step 2 security/external deployment policy are not implemented here.

## Two distinct signals

| Signal | Meaning | Dependency failure |
| --- | --- | --- |
| `GET /api/v1/health` | Process can answer requests | Stays 200 |
| `GET /readyz` | Configured dependencies and access are usable | 503 problem envelope |

Readiness is an operational endpoint, excluded from business OpenAPI. Existing
business routes, examples, response schemas and publication gates are unchanged.
No cache is allowed. Failures have generic messages and `Retry-After: 1`; URLs,
credentials, paths, revisions and rejected values are not exposed. Docker's
healthcheck uses readiness. Deployment routing must check it too; Compose alone
does not provide an automatic load-balancer or restart unhealthy containers.

Each worker permits only one outstanding probe. The HTTP readiness response has
a four-second wait budget, using asynchronous database DNS/connect/query work and
off-event-loop filesystem checks. Concurrent probes fail closed immediately.
No last-known-green cache is used. A stalled filesystem worker or driver cleanup
retains the gate until it finishes, preventing repeated probes from creating an
unbounded queue. Readiness is not a benchmark or a guarantee that every individual
scientific artifact can be downloaded. OS scheduling can add small response overhead.

## Production configuration

Container startup uses `B2_ENV=production`; selecting `local` in the container is
rejected. Direct production application imports also validate configuration before
importing B1's database loader. Ordinary Windows local development remains
unchanged; `/readyz` returns 503 in local mode rather than claiming production readiness.
The supported production runtime for this step is the verified Linux container.

Required:

- Exactly one nonempty `DATABASE_URL` or `DATABASE_URL_FILE`. Secret reads are
  bounded to 8 KiB; the resolved URL stays only in process memory. URL syntax:
  `postgresql+psycopg://...`, explicit user/password/host/database, valid port.
  No loopback/unspecified, socket, multi-host or host/query override configuration.
- Existing absolute readable `OBJECT_STORAGE_ROOT` and separate existing absolute
  readable/writable `TMPDIR`. Neither directory can contain the other.
- `B2_STORAGE_ID`: 1–64 characters, letters/numbers/dot/underscore/hyphen,
  starting with a letter or number. It identifies the agreed mounted store.

Optional `B2_WORKERS` is 1–8, default 1. `B2_SCRATCH_MIN_BYTES` is between 1 MiB
and 1 GiB, default 8 MiB. This minimum is a readiness reserve, not a proven COG
size/concurrency budget. Step 4's large-file starting profile uses 1 GiB tmpfs /
2 GiB API memory; see [storage reliability](b2-step-4-storage.md). The reserve
probe is not a guarantee of admission for every simultaneous full snapshot.

Only single-valued `sslmode`, `sslrootcert`, `sslcert`, `sslkey`, `sslcrl` URL
query parameters are accepted. TLS policy/certificate provisioning remain Step 2;
supporting these parameters does not mean external transport is approved. Connection
and session options cannot be supplied by URL to bypass enforced settings.
Business connections use connect timeout 2 s, statement timeout 10 s, lock timeout
1 s, `public,pg_catalog` search path and read-only transaction defaults. Unchanged
B1 session/repository code consumes that configured URL. DB grants, not read-only
defaults alone, must forbid writes. Restart after any secret/configuration change.

## Readiness prerequisites owned by the deployment operator

Readiness makes fresh SELECT-only connections, separate from the business pool,
and closes them after each check. It never migrates, seeds, imports, repairs,
grants privileges or changes the catalogue. It requires:

- Exactly B1 revision `g05b8eab1001`, PostGIS installed, all unchanged B1 model
  tables/columns with expected PostgreSQL types and nullability.
- A dedicated reader with SELECT on the B1 tables and `public.alembic_version`;
  no effective public table/column write or sequence USAGE/UPDATE grants, schema
  CREATE or database CREATE privileges. Superuser/CREATEDB/CREATEROLE/BYPASSRLS
  attributes, including powerful role membership, are rejected.
- Correct object-store identity marker, and scratch write/read/delete plus reserve.

The storage owner must provision this small marker in the agreed object-store
root before mounting it read-only. The API does not create it in B1's working
store. Contents must be exactly this object with the agreed identifier:

```json
{"schema_version": 1, "store_id": "agreed-store-id"}
```

Filename: `.b2-storage-ready.json`, UTF-8, at most 4 KiB, regular file (not a
symlink). A missing/wrong/invalid marker returns 503, even if an empty directory
is readable. This is mount identity, not cryptographic or scientific approval.
No approved scenarios are required merely to be dependency-ready: an empty
catalogue can be operationally healthy. Existing scientific/publication gates
continue to decide what is actually visible. Windows registered asset URIs still
require the agreed Linux storage namespace; readiness does not rewrite them.

The current working B1 administrator account is not an acceptable production
reader. Provisioning that reader, the real mounted store and deployment credentials
requires coordination with its owner; the verification uses only disposable roles,
synthetic objects and generated temporary credentials. No working B1 deployment
is modified or declared production-approved by this step.

## Rehearsal and acceptance evidence

Build both targets after any source/test change, then run the existing container
rehearsal with a NEW output directory as described in `b2-api-container.md`.
Require every check passed, working B1 data/source/config preserved and all owned
temporary containers/volumes/networks removed. The rehearsal additionally verifies
real readiness failures and recovery for revision, columns/types, SELECT grants,
table/column/sequence write permissions, powerful account/schema CREATE, missing
or wrong storage marker, paused/stopped database, API restart and both probe commands.

Run the complete Windows suite too, including B1's host-only backup test excluded
inside Linux. Check saved OpenAPI freshness/conformance and dependency consistency.
Do not silently rewrite old Step 19/container evidence or call the old handoff
archive current after these changes. Final release packaging comes later.

References: [Psycopg asynchronous connections](https://www.psycopg.org/psycopg3/docs/advanced/async.html)
and [PostgreSQL 16 privilege functions](https://www.postgresql.org/docs/16/functions-info.html).
