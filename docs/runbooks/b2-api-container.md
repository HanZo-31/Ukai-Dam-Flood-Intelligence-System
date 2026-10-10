# B2 API container - local verification and production boundaries

This is API containerization, not a production release or final scientific
acceptance. Git/CI remains deferred. B1's `compose.yaml`, database image, live
database/objects are preserved. Step 3's authorized shared dependency update is
FastAPI 0.142.2, Starlette 1.7.0 and required opentelemetry-api 1.45.0; the other
B1 scientific/database pins are unchanged. `services/api/compose.yaml` is a
standalone API-only configuration and must not be combined with B1's Compose
file to rebuild its service.

## Build

From the project root with Docker Desktop's Linux engine running:

```powershell
docker build --target runtime -f services/api/Dockerfile -t ukai-b2-api:local .
docker build --target verification -f services/api/Dockerfile -t ukai-b2-api:verification .
```

The official Python 3.13 base is digest-pinned. Runtime dependency versions,
including transitives, are in `services/api/requirements-container.lock`; all
current shared root pins are matched. The base is Debian 13 (Trixie).
Debian GIS support libraries are installed from the
base distribution's security repositories; they are not snapshot/hash locked.
Refresh the base/package lock through a reviewed rebuild and recorded tests.
Wheel hashes and release-image signing remain release-hardening gates.
See [Step 3 review](b2-step-3-vulnerability-review.md) for fresh vulnerability
evidence and the narrowly supported runtime applicability gate.

Expat 2.9.0 is built from SHA-256 verified upstream source and passes its own
tests. CPython's matching 3.13.16 `pyexpat` extension is rebuilt against that
library from separately hash-verified Python source; six upstream XML test
modules run during the build. Both parser versions are asserted in the running
API, because replacing the system library alone does not patch Python's bundled
parser. Source provenance is in the Dockerfile and `expat-sbom.cdx.json`.
Build compilers and source archives are not copied into the release layer.
Runtime pip/ensurepip, Perl interpreters and unnecessary affected administrative
commands are removed, and privileged executable bits are stripped. The test
target deliberately retains installers; it is not a deployable release image.

The runtime layer contains application source, not tests/migration scripts or
private `.env` files. A separate verification target contains the B1/B2 test
tooling. B1's broad runtime requirements currently include pytest/GIS utilities;
removing unnecessary runtime packages needs a separate reviewed dependency split.
The Dockerfile-specific ignore file excludes caches/private files and does not
change B1's database build context.

## Safe local verification

Use the verified local Python 3.13 environment and a NEW output folder:

```powershell
.\.venv\Scripts\python.exe scripts/rehearse_b2_container.py --output data/handoff/b2-container-NEW
```

The helper creates a uniquely named test bridge network, synthetic object volume,
temporary PostGIS container and API-only Compose project. It does not attach to,
restart or change B1's working database. A working local B1 connection is read
only for before/after preservation checks. The temporary DB has no published
port; its test data directory is memory-backed. Temporary credentials are
generated and supplied through environment/secret files, not command arguments
or evidence. Only the API is published, at an ephemeral IPv4 loopback port.

Checks include Linux migrations/schema parity/seed, B2/applicable B1 tests, OpenAPI,
actual GIS-aware synthetic imports, all eight API endpoints, verified downloads,
ranges/HEAD, publication/mode gates, export revocation/tampering, non-root/read-only
runtime, SELECT-only SQL grants, restart, safe DB outage and graceful shutdown.
Cleanup removes only the exact generated containers/network/volume. The working
DB/objects, migrations/config/current shared pins must match before/after. The image/cache and
safe JSON report are retained; disposable fixture data is reproducible, not retained.

Review `container-verification.json`; require result=passed, all checks passed,
owned_resources_removed=true and working_data_preserved=true. Do not run beside
working application writes. An empty/failed report is not an acceptance result.
Images must be rebuilt after code/test changes before rerunning.

B1's host-only populated backup drill is explicitly deselected inside Linux:
it requires a host Docker CLI/socket, its named host database and loopback-only
configuration. B1's guard is not weakened and the Docker socket is never mounted
in these images. That test stays in the complete Windows/local regression suite.
The Linux count/exclusion is recorded, not described as every B1 test passing.
Native synthetic COG byte hashes/sizes can differ between GDAL wheels on Windows
and Linux. The B2 example test compares fixture-specific byte metadata to the
actual platform-generated artifacts while keeping fields/units/values/order and
errors exact; every downloaded checksum, ETag, size, range and HEAD is verified.
Saved documentation examples and OpenAPI are not regenerated to hide drift.

## Launch against an agreed deployment catalogue

Have B1 provision a SELECT-only account, approved catalogue, existing Docker
network and container-compatible object directory. Do not use the admin account.
Create a private text file containing only its full `postgresql+psycopg://...`
connection URL. Use URL-encoded credentials. Never paste the URL into command
arguments, reports or Git. Export only configuration paths/network/port:

```powershell
$env:B2_DATABASE_URL_FILE = 'C:\private\b2-database-url.txt'
$env:B2_DATABASE_NETWORK = 'agreed-existing-database-network'
$env:B2_OBJECT_STORAGE_PATH = 'C:\deployment\approved-container-objects'
$env:B2_API_PORT = '8000'
$env:B2_STORAGE_ID = 'agreed-store-id'
docker compose -f services/api/compose.yaml -p ukai-b2-api config --quiet
docker compose -f services/api/compose.yaml -p ukai-b2-api up -d --no-build
docker compose -f services/api/compose.yaml -p ukai-b2-api ps
```

Those are illustrative paths, not created private configuration or permission
to connect the API to another team's database. On this machine B1's network is
`damprojects_default`; selecting it alone does not fix URI portability or grant
a safe reader account. No working B1 deployment was modified by the rehearsal.

The mounted secret supplies `DATABASE_URL_FILE`. Startup requires exactly one
URL source, an explicit psycopg PostgreSQL URL with a non-loopback container DB
host, a readable absolute object directory and workers 1..8 (default 1). Invalid
configuration fails with a generic message, without silently falling back to
B1's local development credentials. Restart after secret rotation; the loaded
URL is kept in process memory. Local Compose secret mounts are not an encrypted
secret-management service and need host file-access protection.

The API runs as UID/GID 10001, with read-only root/object mounts, all capabilities
dropped, no-new-privileges, bounded memory/CPU/PIDs, rotated logs and a writable
bounded `/tmp` tmpfs. Full-object integrity snapshots consume this temporary
space, including HEAD/range/export-discovery. Step 4 changes the starting profile
to 1 GiB tmpfs / 2 GiB memory with a 512 MiB per-artifact cap and admission/cleanup
checks. See [storage reliability](b2-step-4-storage.md); final Team A maximum sizes,
concurrency and host budgets still require agreement and fresh measurements.

## URI portability - required B1/Team A coordination

Windows `file:///D:/...` references registered by B1 are NOT made portable by a
Linux bind mount. Local registered references must resolve to Linux `/objects/...`
inside the container, or use an agreed storage adapter. The rehearsal generates
fixtures/imports through unchanged B1 tooling inside Linux so those references
are truthful. It never rewrites existing Windows references or scientific records.
Real Team A bundles must be verified/registered in the agreed deployment storage
namespace by the owning team. This remains a real-data deployment acceptance gate.

## Health, visibility and shutdown

`/api/v1/health` remains API liveness only. The Docker healthcheck now calls
`/readyz` (operational, outside the business OpenAPI contract). Readiness checks
the current B1 revision and model columns/types/nullability, PostGIS, effective
SELECT-only database privileges, the agreed storage marker, and usable scratch
space. DB outage retains liveness=200; readiness and catalogue reads return safe
503. Route deployment traffic only to readiness=200 instances. Docker's unhealthy
status does not itself restart or remove traffic from a container.
See [Step 1 readiness/configuration](b2-step-1-readiness.md) for the exact policy,
storage marker and configuration requirements. Local development mode is not
production readiness and returns readiness=503.
The Step 2 baseline adds host validation, explicit allowlisted CORS, protective
headers and disabled production HTTP docs; see [the security runbook](b2-step-2-security.md).
No user authentication or external TLS/proxy trust is invented. Keep loopback
binding; external exposure requires the deployment/security owner to approve
and verify proxy/auth/network policy. Uvicorn access logs, server-identification
headers and unreviewed proxy headers are disabled.

Stop/remove ONLY this API stack:

```powershell
docker compose -f services/api/compose.yaml -p ukai-b2-api down --timeout 20
```

This does not manage the external DB network or bind-mounted data. Never use
`down -v` on B1's project, prune global Docker resources or reset its volume.
Review a new image and container receiving test before deployment. Use the
[refreshed item-6 handoff](b2-local-handoff.md) with current source checks,
raw performance/security evidence and receiver record. Step 19 stays historical.

Graceful-stop verification requires fresh application/server shutdown completion
logs and no OOM/SIGKILL. Exit 0 or 143 (normal SIGTERM re-raise) is accepted only
with that completion evidence; an unexplained signal exit is not called graceful.

## Remaining gates

Git/CI remains deferred; local lint/type checks have their [independent gate](b2-local-quality.md).
Step 1 readiness/configuration is implemented and locally verified.
Step 3 uses exact-image audits,
an unsuppressed OS scan and expiry-bound runtime applicability checks; see its
runbook for closure evidence. Production storage
namespace and Team A joint acceptance remain separate. Provisional local
performance/resource targets passed; see [measurement scope](b2-performance-resource-testing.md).
Formal real-output workload/SLA acceptance remains open. Auth/proxy/TLS decisions
are deferred until external exposure is requested. The container is locally verifiable,
not automatically approved for production because it builds or returns health=200.

Design references: [Docker build guidance](https://docs.docker.com/build/building/best-practices/)
and [Compose service settings](https://docs.docker.com/reference/compose-file/services/).
