# B2 HTTP API v1 - candidate contract

Status: local implementation candidate, pending B1/Team A review. Git/CI is
deferred by the team. This document does not change B1's published manifest
contract or register scientific approval.

## Implemented endpoints

`GET /api/v1/health` returns API liveness: HTTP 200 and
`{"status":"ok","service":"ukai-flood-api","api_version":"v1"}`.
It makes no database request. Step 1 implemented a separate operational `/readyz`
dependency probe outside the business OpenAPI; deployment/readiness policy still
needs joint freeze. See Step 5's [storage/input-output review](b2-storage-io-agreement-candidate.md).

`GET /api/v1/scenarios` returns `items` and `pagination`. Public items allow only
scenario identity/type, approved publication status, model/input versions, CRS,
deployment `data_mode`, provenance `data_kind`, historical event ID and coverage
timestamps. B1's internal processing status is not the public publication status.
No ORM object, assumptions path, private manifest, log or storage reference is
serialized into this catalogue. Example: `services/api/tests/fixtures/scenario-list.json`.

| Query | Candidate behavior |
| --- | --- |
| `data_mode` | `demo` (local default) or `production`; always passed explicitly to B1 |
| `limit` | Integer 1..999; default 20; reserves one of B1's maximum 1000 rows for lookahead |
| `offset` | Nonnegative integer; default 0 |
| `scenario_type` | `hypothetical` or `historical_replay` |
| `data_kind` | `demo`, `observed`, `simulated`, `assumed` |
| `historical_event_id`, `model_version` | Exact-match filters |
| `dataset_id`, `dataset_version` | Version requires dataset ID |
| `start`, `end` | ISO-8601 timestamps with timezone; inclusive coverage-overlap filters; start must not follow end |
| `bbox` | Comma-separated west,south,east,north WGS84 bounds; finite, ordered and within longitude/latitude limits; uses B1's registered extent geometry |

Rows are ordered by B1's `scenario_id`. Pagination returns `limit`, `offset` and
`next_offset` (null at the end). Offsets are stable for an unchanged catalogue;
concurrent publications/revocations can change later pages. No snapshot guarantee
or cursor contract is claimed. An empty approved catalogue is a successful 200.

B1 gates reads by completed imported bundle/run, passed validation, reviewer
metadata, approved publication state and selected mode. Draft/rejected/revoked
records and legacy completed scenarios without the published bundle are hidden.

## Scenario details, layers and local artifact delivery

`GET /api/v1/scenarios/{scenario_id}` returns the catalogue identity/provenance
fields plus schema version, timestep, parameters and companion units, registered
impact summary, run ID/timestamp, passing quality review and reviewer/time,
dataset-version provenance, an assumptions link/checksum and self/layers links.
Only explicit public fields are serialized. Dataset object references, quality
report paths, run logs and private manifest snapshots are omitted. Null summary
measurements stay null. B1's approved asset accessor identifies the published
run before the B2 service reads its quality fields through B1's run repository.

`GET /api/v1/scenarios/{scenario_id}/layers` returns scenario/model/input identity,
mode/kind and registered map layers ordered by asset role. Each layer has
`asset_type`, `format`, `crs`, `unit`, `nodata`, `checksum`, coverage timestamps
and a served `url`. Export roles are excluded from map layers. No style or hazard
legend is invented; style/classification contracts still need team review.

Links use relative `/api/v1/scenarios/...` routes and include the selected
`data_mode`. The same approval and mode gates protect every resource request:

- `GET`/`HEAD /api/v1/scenarios/{scenario_id}/assets/{asset_type}` serves only a
  registered role for that approved scenario's published bundle.
- `GET`/`HEAD /api/v1/scenarios/{scenario_id}/assumptions` serves the registered
  assumptions artifact as plain text.

Each local download is resolved through B1's configured `LocalObjectStore`
under `OBJECT_STORAGE_ROOT` and hashed into a disk-backed temporary snapshot.
Only snapshot bytes matching the registered SHA-256 are streamed to the client.
Missing, changed, out-of-root or unsupported remote objects return a generic
503 without exposing their URI. This local adapter does not fetch S3 or redirect
clients to raw references. The configured local filesystem remains trusted.

Binary assets use TIFF/GeoJSON/KML media types according to registered format
and role/unit agreement. The local synthetic integration fixture verifies TIFF
and GeoJSON through B1's GIS inspector. A separate KML transport unit test uses
synthetic bytes and a stub repository, without registering a KML approval. It
does not establish GIS validation or scientific export acceptance.
Downloads use safe role-based filenames, `Cache-Control: no-store` and
`X-Content-Type-Options: nosniff`. Approval is checked on each new request;
an already-started transfer is not cancelled automatically by later revocation.

The adapter supports one byte range (206), open-ended and suffix ranges, HEAD
metadata and ETag-based If-Range fallback. Unsupported/multiple or unsatisfiable
ranges return 416 with Content-Range. It verifies the full source object even
for a range/HEAD request. This favors integrity. Step 4 has verified local
delivery, concurrency and scratch recovery with 341 MiB COGs. Final Team A
size/concurrency/SLA acceptance and immutable-storage optimization remain open.

## Registered impact summary

`GET /api/v1/scenarios/{scenario_id}/impact?data_mode=demo|production` uses the
same approved scenario gate and B1's mode-scoped summary accessor. It returns
scenario/model/input identity, mode/kind and these registered measurements as
top-level fields: `max_depth_m`, `flooded_area_km2`, `population_exposed`,
`buildings_exposed`, `roads_affected_km`, `critical_facilities_exposed`.
Field suffixes identify physical units; exposure fields are counts. Null values
remain null. B2 does not calculate or infer exposure/hazard statistics. A hidden
scenario returns 404; a missing, wrong-mode or invalid registered summary returns
503. Example: `services/api/tests/fixtures/impact.json`.

## Historical-event catalog and replay coverage

`GET /api/v1/historical-events` accepts `data_mode` (`demo` local default or
`production`), `limit` (1..999; default 20), `offset` (default 0), and timezone-aware
`start`/`end` coverage-overlap filters. Start must not follow end. Ordering follows
B1's coverage-start/event-ID order; continuation uses `next_offset`.

Each item returns registered event identity/name, coverage timestamps and
observed-coverage description, public source URLs, mode and linked dataset-version
provenance. `source_labels` is the distinct set of those datasets' supplied
labels; an event with no linked datasets returns an empty set rather than an
invented observed/demo claim. Internal quality notes and object references are
not serialized. Source links are never fetched. Credential-bearing, query/signed,
fragment, local-file and local-network URLs are omitted from the public list,
without rewriting B1's catalog records. This candidate policy needs team review
if a legitimate reference requires a query or fragment.

Event metadata is independent of publication of a scenario replay. Each item's
`replay` object contains `available`, a mode/event-filtered `scenarios_url`, and
an `example` approved scenario summary (or null). The example's coverage is its
actual registered period; it is not an aggregate guarantee of full event/replay
coverage. Follow the paginated scenarios link for all approved replay scenarios.
Draft, rejected, revoked, incomplete and wrong-mode scenarios cannot make replay
availability true. After revocation availability is re-evaluated on each request.

An empty catalog returns 200 with empty items. The API does not fabricate
1998/2003/2006 records when those events have not been registered. Example:
`services/api/tests/fixtures/historical-events.json` is explicitly synthetic.

## Current V1 demo status

`GET /api/v1/status/current` reads B1's latest persisted demo status, ordered by
reading time and then row ID. The optional HTTP `data_mode` accepts only `demo`;
production/live values return 422. The repository is always called with an
explicit demo mode, so a newer production row cannot accidentally be exposed.

Fields: `reservoir_level_m`, `inflow_m3s`, `release_m3s`, `timestamp`,
`data_mode: demo`, `data_kind: demo`, `is_live: false`. Measurements use their
unit suffixes and preserve nulls. The timestamp is the actual stored reading
time, never the request time; an old seed is not presented as a fresh live
reading. No reading returns 404. Invalid/nonfinite measurements return 503.
No scenario/model identifiers are fabricated for this operational reading.
Example: `services/api/tests/fixtures/current-status.json`.

## Registered exports

`GET /api/v1/exports/{scenario_id}?format=geojson|kml&data_mode=demo|production`
requires an explicit format; mode defaults to demo. It looks up only the
corresponding `export_geojson` or `export_kml` role through B1's approval-aware,
published-run/mode-scoped asset accessor. No generation, conversion, or fallback
to `extent_geojson` is performed. The derivative must actually be registered.

The response includes scenario/model/input identity, mode/kind, asset role,
format, declared CRS/unit, checksum, coverage timestamps and `download_url`.
The URL is a relative, mode-preserving approved asset route, not a local path,
object-store reference or external redirect. Discovery checks metadata and
hashes a local snapshot before advertising the link, then closes it. The actual
download rechecks approval and byte integrity, including after revocation or
file changes. A successful discovery is not a future availability lease.
Discovery and downloads use `Cache-Control: no-store`.

Hidden/missing scenarios and absent derivatives return 404; invalid formats or
modes return 422; missing/tampered/unsafe objects or invalid registered metadata
return a generic 503 without a download link. B1's current GIS verifier cannot
validate KML; existing KML transport support does not resolve that handoff gate.

Public JSON uses snake_case, explicit provenance labels/versions, declared units
and timezone-aware timestamps. Internal file:// paths and credentials stay private.

## Errors and OpenAPI

Implemented routes return RFC 7807-style `application/problem+json` envelopes
with `type: about:blank`, `title`, `status`, safe `detail` and a path-only
`instance`. Invalid queries return 422, inaccessible/missing scenarios or roles
return 404, unsatisfiable ranges return 416, database/artifact unavailability
returns 503 and unexpected failures return a generic 500. Invalid registered
Pydantic data and invalid FastAPI response shapes return 503, not client-query
422. Query prevalidation happens before service execution on both catalog routes.
Unsupported methods return 405 and retain the Allow header; 416 retains
Content-Range. All problem responses include no-store/nosniff headers. Rejected
input values, queries, SQL and credentials are not copied into problem details.
Cross-endpoint tests cover these behaviors; joint team approval remains pending.

In local development FastAPI serves `/openapi.json`, `/docs` and `/redoc` from the same enriched
OpenAPI 3.1 builder used by `scripts/export_b2_openapi.py`. The saved candidate
is `docs/contracts/b2-openapi-v1.json`. `--check` is read-only and fails on
missing/stale output. Enum ordering is canonicalized to avoid import-order
drift without changing accepted values. Both artifact GETs and HEADs are
documented with accurate media types, range/If-Range parameters, status codes
and headers; HEAD has no response body.

`services/api/app/api_examples/v1.json` contains all eight successful JSON
endpoint examples, verified synthetic download headers/GeoJSON/assumptions,
and captured safe problem envelopes. It is not a database seed or a scientific
approval. Swagger/ReDoc embed successful, empty-catalog and safe-error examples.
Documentation tests validate OpenAPI 3.1 conformance, embedded JSON examples
against response schemas, real isolated HTTP equality, complete route/operation
coverage, no private-field leaks, query-free generation and artifact drift checks.
Install `services/api/requirements-dev.txt` for those validators. Production HTTP
docs are disabled by Step 2; Step 3 made the authorized compatible shared framework
upgrade. Neither is changed by this contract review. See `docs/runbooks/b2-api-usage.md` for usage,
regeneration, security/interpretation limits and remaining handoff gates.

## Review decisions required before final freeze

1. Keep offset pagination or adopt an agreed cursor scheme; agree maximum page size.
2. Keep the local demo default or require an explicit HTTP mode in the final API.
3. Agree the already-implemented separate readiness/liveness deployment policy.
4. Agree how assumptions/layers/exports are safely served and which unavailable
   formats are supported. B1's current GIS verifier does not cover KML.
5. Freeze detail/provenance fields, datum representation, quality meanings and
   approver authority with the owning teams.
6. Adopt final problem schemas and status codes across all endpoints.
7. Agree performance expectations and approved sample bundles for joint acceptance.

Local tests validate engineering behavior on clearly labelled synthetic GIS
assets in disposable schemas. They do not complete scientific or production acceptance.
