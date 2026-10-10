# B2 API V1 - local usage and documentation verification

Status: local implementation candidate. Shared B1/B2/Team A contract freeze,
real scientific examples and production acceptance remain pending. This guide
covers step 16 only; it is not the final receiving-setup rehearsal.

## Start and inspect

Use Python 3.13 (verified locally as 3.13.15), the existing project environment,
and your own private configuration. Follow B1's local setup runbook if setting
up a database from scratch; do not replace the existing environment/database.
From the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000
```

- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Live specification: `http://127.0.0.1:8000/openapi.json`
- Saved candidate specification: [b2-openapi-v1.json](../contracts/b2-openapi-v1.json)
- Verified synthetic responses/download headers: [v1.json](../../services/api/app/api_examples/v1.json)
- Detailed filters and review decisions: [candidate contract](../contracts/b2-api-v1-candidate.md)

The saved OpenAPI 3.1 specification and live document share one builder. Export
does not query the database, require an approved working scenario or run a
simulation. The packaged example file is a documentation artifact, not a seed
or a source of scenario responses.

## Endpoint reference

All public business endpoints below are GET. Asset/assumptions downloads also
support HEAD; all 12 operations are included in the specification.

| Route under `/api/v1` | Purpose | Key request rules |
| --- | --- | --- |
| `/health` | API liveness only | No database readiness or telemetry guarantee |
| `/scenarios` | Approved scenario catalog | Mode, paging, exact type/event/model/dataset/kind filters, time overlap and WGS84 bbox |
| `/scenarios/{scenario_id}` | Parameters/units, impacts, quality and dataset provenance | Approved identifier and selected mode |
| `/scenarios/{scenario_id}/layers` | Registered map layers and safe links | Export roles excluded; use declared CRS/units |
| `/scenarios/{scenario_id}/impact` | Stored impact/exposure summary | No B2 calculation; unavailable measurements remain null |
| `/historical-events` | Registered event metadata and replay availability | Mode, paging, time overlap; event can exist without a replay |
| `/status/current` | Latest stored demo reading | Only demo mode; persisted timestamp; is_live always false |
| `/exports/{scenario_id}` | Existing registered derivative and verified download link | Required format geojson or kml; absent derivative returns 404 |
| `/scenarios/{scenario_id}/assets/{asset_type}` | Verified artifact bytes | Registered role only; GET/HEAD; single byte range on GET |
| `/scenarios/{scenario_id}/assumptions` | Verified assumptions text | GET/HEAD; same approval/integrity checks |

General mode defaults to `demo`; `production` is accepted except on current
status. Mode is always passed explicitly to B1 and retained in served links.
Provenance `data_kind` is separate from deployment `data_mode`.

Catalog pages have `items` and `pagination` (`limit`, `offset`, `next_offset`).
Limit is 1..999, default 20; offset is nonnegative, default zero. Follow
next_offset until null. Concurrent publication/revocation can shift later pages;
no snapshot pagination guarantee is claimed. Empty items is a successful 200.

Times require ISO date/time, seconds and an explicit timezone. Start/end apply
inclusive overlap; start must not follow end. Dataset version requires dataset
ID. Bbox is four finite, ordered WGS84 west,south,east,north values, within
longitude/latitude limits; no dateline wrapping. Other string filters are exact
matches. See OpenAPI for enums, schema fields, nullability and examples.

## Read-only walkthrough (PowerShell)

Run these after starting the API. No command here registers data or approval.

```powershell
$apiBase = 'http://127.0.0.1:8000'
Invoke-RestMethod "$apiBase/api/v1/health"
$catalog = Invoke-RestMethod "$apiBase/api/v1/scenarios?data_mode=demo&limit=20&offset=0"
Invoke-RestMethod "$apiBase/api/v1/historical-events?data_mode=demo"
Invoke-RestMethod "$apiBase/api/v1/status/current"
```

The current working catalog has no approved published scenarios, so an empty
catalog is expected. Legacy completed seeds and saved draft manifests do not
qualify. Historical events may also be empty; absent demo status returns 404.
An old stored status timestamp is not a fresh live reading.

Only continue the scenario walkthrough when the catalog has an approved item:

```powershell
if ($catalog.items.Count -eq 0) { throw 'No approved demo scenario; use the synthetic tests or wait for an authorized bundle.' }
$scenarioID = $catalog.items[0].scenario_id
$detail = Invoke-RestMethod "$apiBase/api/v1/scenarios/$scenarioID`?data_mode=demo"
$layers = Invoke-RestMethod "$apiBase/api/v1/scenarios/$scenarioID/layers?data_mode=demo"
$impact = Invoke-RestMethod "$apiBase/api/v1/scenarios/$scenarioID/impact?data_mode=demo"
$export = Invoke-RestMethod "$apiBase/api/v1/exports/$scenarioID`?format=geojson&data_mode=demo"
Invoke-WebRequest -Uri ($apiBase + $export.download_url) -Method Head
Invoke-WebRequest -Uri ($apiBase + $layers.layers[0].url) -Headers @{ Range = 'bytes=0-15' }
Invoke-WebRequest -Uri ($apiBase + $detail.assumptions.url)
```

An approved scenario may lack an optional derivative; export discovery then
returns 404. Do not replace it with an extent URL or invent a download link.
The example scenario ID `b2-approved-001` exists only in the disposable test
schema, not the working catalog. Do not promote fixtures just to make this
walkthrough return populated data.

## Units, interpretation and safe downloads

Use the declared CRS; rasters may be projected while GeoJSON exports are
WGS84. B2 performs no reprojection, hydraulic simulation or exposure calculation.
Parameters have companion units. Impact/status physical units appear in field
names; exposure fields are counts. Null means unavailable/not applicable, not
zero. Vertical datum, hazard styles/classes and quality authority remain joint
contract decisions.

Follow API-returned relative links against the same trusted API origin. Clients
never need local file paths, raw object references or private configuration.
Every new request checks approval/mode; previously issued links stop working
after revocation. A transfer already underway is not automatically cancelled.

Downloads advertise TIFF (`image/tiff`), GeoJSON (`application/geo+json`), KML
(`application/vnd.google-earth.kml+xml`) or assumptions (`text/plain`, UTF-8).
Safe attachment filenames, quoted SHA-256 ETags, Content-Length, Accept-Ranges,
no-store and nosniff headers are used. GET supports one bytes range and returns
206 with Content-Range. If-Range must exactly match the current ETag; another
value requests the full representation. Invalid/multiple/unsatisfiable ranges
return 416 with `Content-Range: bytes */size`. HEAD returns verified full-file
headers and no body, ignoring Range.

Files are fully hashed into a temporary disk snapshot, including discovery,
range and HEAD checks. A later download verifies again. Production storage,
large-file throughput and temporary-disk capacity remain acceptance gates.
KML transport is implemented, but B1's current GIS inspector does not validate
KML; no approved scientific KML example is claimed by these docs.

## Errors and deployment boundaries

Errors use application/problem+json with `type`, `title`, `status`, safe `detail`
and a path-only `instance`. No query values, SQL, credentials or storage paths
are copied into details. Problem responses use no-store and nosniff.

| Status | Meaning |
| --- | --- |
| 404 | Missing/unpublished/wrong-mode resource, absent derivative or no demo reading |
| 405 | Method not allowed; Allow header retained |
| 416 | Unsatisfiable/unsupported range; Content-Range retained |
| 422 | Invalid client parameters |
| 503 | Database/artifact unavailable or malformed registered/response data |
| 500 | Unexpected internal failure; generic detail |

Development has no public authentication/authorization policy or configured
cross-origin browser access. Keep the server bound to 127.0.0.1. A frontend on
another origin needs an agreed proxy/CORS/security policy before integration;
the same-origin OpenAPI server entry does not grant cross-origin permission.
Production mode selection is a data filter, not an authorization boundary.
The Step 2 local security baseline adds production host validation, explicit
browser-origin configuration, protective headers and hidden production HTTP
documentation. Login/public-access and external TLS/proxy policy still need
agreement; see `b2-step-2-security.md`. Local documentation remains available.

## Regenerate and verify documentation

Install the pinned B2 development validators in Python 3.13; existing B1 runtime
pins remain in the root requirements file unchanged:

```powershell
.\.venv\Scripts\python.exe -m pip install -r services/api/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_openapi_contract.py -q
.\.venv\Scripts\python.exe scripts/export_b2_openapi.py --check
.\.venv\Scripts\python.exe -m openapi_spec_validator docs/contracts/b2-openapi-v1.json
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

The default combined suite now includes documentation tests and therefore
requires these B2 development dependencies. Standard OpenAPI conformance uses
[OpenAPI Spec Validator](https://openapi-spec-validator.readthedocs.io/), with
JSON Schema validation of embedded response examples and real HTTP/schema parity
checks. These engineering checks do not establish scientific acceptance.

When intentional API/example changes are reviewed, regenerate explicitly:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_openapi_contract.py::test_documented_examples_match_real_isolated_http_responses --b2-examples-output services/api/app/api_examples/v1.json -q
.\.venv\Scripts\python.exe scripts/export_b2_openapi.py
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_openapi_contract.py -q
.\.venv\Scripts\python.exe scripts/export_b2_openapi.py --check
```

Example regeneration uses real synthetic GIS bytes and B1's disposable migrated
schema, then rolls back/cleans up. Ordinary tests and `--check` never rewrite
the examples or specification. No scientific/working catalog approvals are
created. Review artifact changes instead of regenerating automatically to hide
a failing test. Git/CI, receiving rehearsal and final handoff remain separate
steps; they were not performed as part of step 16.
