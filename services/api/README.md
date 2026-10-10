# B2 local API development

The API lives in the existing Ukai project at `D:\Dam Projects`. Use Python 3.13
(verified locally as 3.13.15). B1's models, migrations, repositories, manifest
validation and GIS/storage tools are reused. Public response schemas live in
`app/api_schemas/` because B1 already owns the module `app/schemas.py`.

## Local setup

Run commands from the project root. For a new local checkout, create a private
virtual environment with your installed Python 3.13, then install dependencies:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The current machine already has a working `.venv`; do not replace it. If the
Python launcher does not list 3.13, use the full path to the installed 3.13
interpreter for environment creation.

Create your own private configuration following `.env.example` and B1's local
setup runbook. Never copy or share another developer's `.env`. The database layer
loads the root `.env` at import time; an existing `DATABASE_URL` environment
variable takes precedence. B2 does not need a second copy of B1's private file.

Start the existing database service and apply B1's migrations/legacy demo seed
as described in `docs/runbooks/local-setup.md`:

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts\seed_db.py
```

The seed is a legacy demo, not an approved published bundle. An empty public
scenario list in the working database is therefore expected. Do not promote the
saved draft GIS fixture just to populate a demo response.

## Run the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive documentation. Current endpoints:

Step 16 documentation: `http://127.0.0.1:8000/redoc`, `/openapi.json`, the saved
`docs/contracts/b2-openapi-v1.json`, and packaged verified synthetic examples in
`app/api_examples/v1.json`. See [the usage guide](../../docs/runbooks/b2-api-usage.md)
for the complete read-only walkthrough, download headers, interpretation,
development security boundaries and regeneration/check commands.

- `http://127.0.0.1:8000/api/v1/health` (API liveness, independent of database).
- `http://127.0.0.1:8000/api/v1/scenarios?data_mode=demo&limit=20&offset=0`.
- `/api/v1/scenarios/{scenario_id}?data_mode=demo`: parameters, units, summary,
  run/quality/dataset provenance and assumptions/layer links.
- `/api/v1/scenarios/{scenario_id}/layers?data_mode=demo`: registered map layers
  with usable download links and declared units/CRS/coverage.
- `GET`/`HEAD /api/v1/scenarios/{scenario_id}/assets/{asset_type}?data_mode=demo`:
  checksum-verified bytes; includes single-range support for COG consumers.
- `GET`/`HEAD /api/v1/scenarios/{scenario_id}/assumptions?data_mode=demo`:
  verified assumptions text.
- `/api/v1/scenarios/{scenario_id}/impact?data_mode=demo`: registered exposure
  measurements, units in field names, model/input identity and preserved nulls.
- `/api/v1/historical-events?data_mode=demo&limit=20&offset=0`: catalogued event
  coverage, public source/dataset provenance and approved replay availability.
- `/api/v1/status/current`: latest stored demo reading; always demo-labelled with
  `is_live: false`. A production/live mode cannot be requested in V1.
- `/api/v1/exports/{scenario_id}?format=geojson|kml&data_mode=demo`: metadata and
  safe download link for an existing registered export. Format is required;
  unavailable derivatives return 404, never a relabelled extent or invented file.

Set `OBJECT_STORAGE_ROOT` in your private environment to the existing B1 local
object-store directory when it differs from the project default. Downloads
reject files outside that root. A registered but unavailable or changed object
returns a generic 503; clients never receive the underlying local URI. Relative
links retain the chosen data mode and check publication approval on every request.
Integrity verification uses a temporary disk snapshot, including for range/HEAD
requests. Final Team A size/concurrency requirements still need agreement.
Step 4 introduces bounded per-object/scratch admission and disconnect cleanup;
see [storage/download reliability](../../docs/runbooks/b2-step-4-storage.md) for
the >300 MiB real-COG rehearsal and capacity settings. Team A's exact size/SLA
agreement remains separate from measured synthetic reliability.
Export discovery also verifies the object before advertising its link; the
subsequent download rechecks approval and integrity. This is not a guarantee of
future availability. No raw storage URI is returned, and B2 does not generate
or convert export files. B1's current GIS inspector cannot validate KML: the
KML transport unit test verifies bytes/media/safety only, not GIS or scientific
acceptance. The GeoJSON integration fixture is inspected by B1's actual verifier.

Error responses use `application/problem+json` with safe details, no-store and
nosniff headers. Invalid requests return 422; malformed registered/response data
and database/artifact unavailability return 503; unexpected failures return 500.
Client validation is separated from service execution so corrupt stored data
is not misreported as a bad query. Missing/unpublished resources return 404;
unsupported methods return 405; unsatisfiable ranges return 416.

## Test locally

The full B2/combined suites now include OpenAPI conformance tests. Install B2's
development-only validators before running them. Step 3 made an authorized
shared framework upgrade to FastAPI 0.142.2 / Starlette 1.7.0 with required
opentelemetry-api 1.45.0; scientific/database pins and B1 core code are unchanged:

```powershell
.\.venv\Scripts\python.exe -m pip install -r services/api/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/export_b2_openapi.py --check
.\.venv\Scripts\python.exe -m openapi_spec_validator docs/contracts/b2-openapi-v1.json
.\.venv\Scripts\python.exe -m pip check
```

The default pytest command discovers both B1 and B2 tests. The B2 integration
tests reuse B1's disposable `b1_verify_<random>` schema fixture and apply the
preserved migration chain there. Fixtures generate actual synthetic COG/GeoJSON
files under pytest's temporary directory and register matching dataset provenance.
The test reviewer is trusted only inside the fixture, and `data_mode/data_kind`
remain `demo`. Request dependencies inject the isolated session into the real B1
repository and B2 service. Transactions roll back and the fixture removes its
generated schema. No approval is written to the working public catalogue.

Database integration tests require the local PostGIS database to be running and
the developer's test connection to allow temporary schema creation/drop. Never
point these integration tests at a production database. Unit endpoint tests can
run without a database using:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_health.py services/api/tests/test_scenarios.py -q
```

## Troubleshooting and remaining work

- Connection refused: check the existing database container, localhost port and
  your private DATABASE_URL; avoid printing credentials in reports.
- Missing dependency: use the project `.venv` and install `requirements.txt`.
- Empty catalogue: public reads require an approved imported bundle; a completed
  legacy seed or a saved draft does not qualify.
- Empty historical catalog: event records must be registered; the API does not
  invent the blueprint's 1998/2003/2006 events. An event may have metadata without
  an approved replay; follow its scenario link for available replay coverage.
- Old status timestamp: the endpoint preserves the persisted demo reading time,
  not the time of the request. No demo reading returns 404; unavailable/invalid
  registered data returns a safe problem response.
- Failed integration fixture: preserve the test failure; review schema/fixture
  cleanup before retrying, rather than altering working scenario approvals.

See `docs/contracts/b2-api-v1-candidate.md` for candidate filters/paging and open
review decisions. All eight blueprint endpoints and step 16's saved/validated
OpenAPI, verified examples and usage guide are complete locally. Joint contract
approval, agreed production storage/performance validation and final receiving
acceptance remain pending. A separate same-host receiving rehearsal verifies a
new Python 3.13 environment, empty migrated database, full copied-source suite
and actual loopback HTTP acceptance; it does not establish new-host or scientific
acceptance. Functional tests
cover exports, cross-endpoint failure/validation envelopes, dependency cleanup,
and one synthetic replay plus three hypothetical scenarios end to end. This
does not establish a line-coverage percentage or real-data acceptance. Git/CI remains deferred.
API containerization was deferred in the earlier batches; the standalone
container setup is now available below. Git/CI remains deferred.

For step 18's separate clean-copy/new-Python-environment receiving and actual
loopback HTTP/performance rehearsal, see
[the receiving runbook](../../docs/runbooks/b2-receiving-rehearsal.md).
It creates/removes only its generated database, retains safe source/fixture
evidence, and never copies B1's private .env. Performance measurements are a
baseline until representative assets and target limits are agreed.

For Step 19's local source/evidence handoff, start with
[the handoff guide](../../docs/runbooks/b2-local-handoff.md),
[receiver setup](../../docs/runbooks/b2-receiver-setup.md) and
[pending acceptance gates](../../docs/b2-pending-items.md).
The package excludes private configuration/live data and carries checksums;
receiver acknowledgement, formal performance and joint scientific acceptance
remain pending. Git/CI is still deferred; container setup is described below.

API containerization is now available separately in `services/api/compose.yaml` and
`services/api/Dockerfile`. See [the container runbook](../../docs/runbooks/b2-api-container.md)
for isolated local verification, private runtime configuration, Linux object-URI
portability and remaining production gates. The earlier Step 19 archive is a
historical source snapshot, not this updated containerized source. Git/CI stays
deferred; local container verification does not grant production approval.

Production Step 1 adds strict configuration and the separate `/readyz`
dependency-readiness probe; Docker health now uses readiness, not liveness.
See [the Step 1 runbook](../../docs/runbooks/b2-step-1-readiness.md) for the
required reader, object-store identity marker and scratch-space policy. The
unchanged `/api/v1/health` remains liveness only. Local development mode does
not claim production readiness. Security and final deployment acceptance
remain separate gates.

Step 2's local security baseline is documented in
[the security runbook](../../docs/runbooks/b2-step-2-security.md).
Production HTTP docs are disabled; local development docs are unchanged.
For the user-confirmed local-only project, this tested baseline is accepted.
The public-versus-protected access decision and TLS/proxy deployment are deferred
until external deployment is requested. Keep the API loopback-only.

Step 3's dependency/container review and repeatable exact-image gate are in
[the vulnerability runbook](../../docs/runbooks/b2-step-3-vulnerability-review.md).
The gate preserves raw OS findings, verifies patched Python/native parser
versions and rejects new critical/high findings or a changed deployment profile.
No OTel SDK/exporter is installed. No monitoring data is exported by this change.
Older handoff archives and initial failed scan reports are historical evidence,
not a current release package or a claim that the image has no vulnerabilities.

Current item-6 delivery includes container/readiness/security, large-file and
provisional performance evidence. Start with [refreshed handoff](../../docs/runbooks/b2-local-handoff.md)
and [receiver setup](../../docs/runbooks/b2-receiver-setup.md). Use --profile refreshed,
not the packager's historical Step 19 compatibility profile. Record receipt using
[the blank receiver record](../../docs/runbooks/b2-receiver-acceptance.md).
Joint contract/science/SLA and actual receiver acceptance remain open. The
[local quality/privacy gate](../../docs/runbooks/b2-local-quality.md) is now required
independently. Trusted-local/no-login use is confirmed; Git/CI remains deferred.
