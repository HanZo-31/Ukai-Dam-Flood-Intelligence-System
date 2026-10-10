# B2 receiver setup — local Python 3.13 and hardened Linux container

Use a NEW extracted source folder on a trusted local machine. Preserve existing
B1 stacks. Sender runtimes: Windows Python 3.13.15, Linux Python 3.13.16.
Sender same-host rehearsals are not new-host receiver approval.

## 1. Inspect and install in a new environment

Review manifest, evidence and [pending gates](../b2-pending-items.md). Confirm the
archive SHA-256 through a trusted team channel, extract into a new folder and open
PowerShell in source. Have Python 3.13 and Docker's Linux engine available.
Do not replace an existing environment or downgrade:

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services/api/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

Development dependencies include root runtime pins. Do not upgrade shared pins
just to suppress the recorded HTTPX test-client deprecation warning. Dependency
access is needed; no virtual environment or image tar is packaged.

## 2. Private development configuration/database

Create a private .env from .env.example only if none exists. Set your own local
DATABASE_URL and OBJECT_STORAGE_ROOT. Keep credentials out of reports. Shell values
override .env: check inherited settings privately. Use B2_ENV=local for Windows
development, not hardened deployment.

Review compose.yaml port/container/volume names first. Do not start a competing
stack against another developer's DB/volume. On a genuinely fresh isolated machine,
start B1's DB, wait for health and privately confirm the intended development
database before applying migrations/seed:

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe scripts/seed_db.py
```

The legacy seed is not an approved bundle. An empty scenario list is expected
until owners register actual reviewed outputs. Never promote drafts just to
populate responses. See [B1 setup](local-setup.md) and [operations](b1-operations.md).

## 3. Host verification

Tests create/drop disposable schemas and need dedicated local test privileges.
Never run them against production or alongside other application writes:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/export_b2_openapi.py --check
.\.venv\Scripts\python.exe -m openapi_spec_validator docs/contracts/b2-openapi-v1.json
.\.venv\Scripts\python.exe -m pip check
```

Windows skips four Linux-only descriptor/FIFO/symlink/admission cases. Linux runs
them but excludes B1's host-only populated backup drill, which stays in Windows.
Use current item-6 evidence, not historical counts. Lint/type checks are separate
and independently recorded. Repeat [the local quality gate](b2-local-quality.md);
regression tests do not imply it passed.

## 4. Development smoke check — not dependency-ready deployment

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000
```

In development /docs, /redoc and /openapi.json are available. Check:

- /api/v1/health: 200; process liveness only.
- /readyz: 503 in local mode, intentionally not claiming hardened readiness.
- /api/v1/scenarios?data_mode=demo: 200; empty is valid without approved bundles.
- /api/v1/status/current: stored demo timestamp, is_live=false; 404 if none.
- Invalid mode production: safe 422; unavailable/changed registered bytes: safe 503.

Stop with Ctrl+C. Keep loopback-only. No public hosting/login/keys were added.

## 5. Hardened Linux verification and deployment

Use [container instructions](b2-api-container.md) as the authoritative launch
runbook. services/api/compose.yaml is API-only: do not combine it with B1's root
Compose command. Build only API targets:

```powershell
docker build --target runtime -f services/api/Dockerfile -t ukai-b2-api:local .
docker build --target verification -f services/api/Dockerfile -t ukai-b2-api:verification .
.\.venv\Scripts\python.exe scripts/rehearse_b2_container.py --large-assets --output data/handoff/b2-receiver-container-NEW
```

The rehearsal creates/cleans only uniquely owned synthetic resources. Require all
checks passed, working-data/source preservation and owned cleanup. A working B1
connection is used read-only for preservation checks; do not run beside writes.
A rebuild can change OS packages/image identity: repeat [the exact-image review](b2-step-3-vulnerability-review.md)
rather than treating the sender's prior gate as approval of a different image.
Serve only the runtime image; verification retains installers/test tooling.

Before connecting to an agreed real catalogue, its owners must supply:

- SELECT-only reader, correct B1 revision/PostGIS/schema and private URL secret
  using a container-reachable host, not localhost.
- Agreed external Docker network and readable container-compatible object root.
- .b2-storage-ready.json marker matching B2_STORAGE_ID, provisioned by the owner,
  not automatically created by the API in B1's working store.
- Verified asset references resolvable inside Linux /objects. Windows file:///D:/...
  URIs do not become portable through a bind mount. Owning teams must register
  outputs in the agreed namespace; do not casually rewrite live records.
- Host allowlist and exact frontend CORS origins. Default CORS is closed, not
  authentication. Published binding remains 127.0.0.1.

Follow the container runbook's private path-based configuration/launch commands.
Startup fails closed. Route traffic only after /readyz=200. Production /docs,
/redoc and /openapi.json are disabled: use the packaged OpenAPI file. DB outage
retains health=200 but readiness/business reads fail safely. Startup never
automatically migrates, seeds or repairs permissions.

Starting budget: one CPU, 2 GiB RAM, 1 GiB scratch, 512 MiB per asset. Full integrity
snapshots consume scratch even for HEAD/range/export discovery. Oversize/capacity
errors are safe 503. Raising only the asset cap is unsafe: jointly size RAM/scratch/
concurrency and repeat [storage](b2-step-4-storage.md) and [performance](b2-performance-resource-testing.md).

Stop ONLY the API project as documented. Never globally prune, reset the DB or
run B1 down -v to fix receipt. Roll back to a retained reviewed image and private
configuration without changing data; restart after secret rotation. DB backup/
restore remains B1-owned.

## 6. Record receipt and open acceptance

The optional [old clean-copy receiving rehearsal](b2-receiving-rehearsal.md) uses
a new Python environment/disposable DB, but is a development baseline, not the
large-file hardened profile. Prefer current container/storage/performance checks
for hardened verification. Neither path establishes scientific approval.

Complete [receiver record](b2-receiver-acceptance.md) with actual environment,
image identity, checks and exceptions. Team A's reviewed outputs, storage/reviewer
policy agreement, formal workload/SLA and joint acceptance remain separate.
Successful receipt does not silently close them.
