# B1 → B2 handoff

Current status: **local B1 deliverables ready for B2 development handoff; formal
joint acceptance pending**. The working input/demo flow
below is a legacy interface, not the blueprint's approved published-result
registry. See `docs/contracts/README.md` for the new candidate contract.
B2 owns the read-only FastAPI routes, schemas and API integration tests.

The legacy internal adapter retains these guarantees (not B2's public contract):

- `scenarios` is the source of truth for an accepted manifest. A newly registered scenario has status `registered`.
- `scenario_inputs` stores immutable source objects, version identifiers, and SHA-256 checksums.
- `processing_runs` is the execution audit record. Internal producers use unique run IDs and record execution metadata; B2 consumes precomputed results.
- `result_assets` records durable outputs; `impact_summaries` contains one roll-up per scenario. The importing adapter writes outputs and completion together.
- Storage keys must follow `docs/object-storage-layout.md` and data modes must stay `demo` or `production`.

Internal legacy state flow: `registered → queued → running → completed | failed`. It is not a public simulation API. Failed runs remain auditable.

Before accepting the handoff, B2 should run `alembic upgrade head`,
`scripts/seed_db.py`, and the test suite against a clean local database.
`ScenarioManifest` describes the current legacy input flow;
`PublishedScenarioManifest` defines the candidate published-output metadata.
Local published-bundle ingestion and approval-aware reads are implemented; use
`PublishedScenarioRepository` for every public scenario/asset/summary/provenance
read, with an explicit demo/production mode. See
`docs/contracts/published-registry.md` for trust, provenance and production GIS
gates. Dataset/version provenance, historical events and validation metrics are
implemented; see `docs/contracts/catalogs.md`. Never infer versions or checksums.

## Implemented B1 contract adapter

`manifest_registry.register_manifest(session, manifest, store)` verifies real
input checksums before registration. `result_registration.start_run`,
`complete_run`, and `fail_run` provide the internal/offline producer transaction contract, not B2's public API.
Call each inside `SessionLocal.begin()`. Completion validates every object,
checks CRS, and writes outputs, the impact summary, and terminal run/scenario
states together. An error rolls back that transaction. Failed runs remain in
the audit trail, and a retry requires a new `run_id`.

The equivalent local command interface is:

```powershell
.\.venv\Scripts\python.exe scripts\run_contract.py start <scenario-id> <new-run-id>
.\.venv\Scripts\python.exe scripts\run_contract.py complete <completion-bundle.json>
.\.venv\Scripts\python.exe scripts\run_contract.py fail <run-id> <error-code>
```

Completion bundles contain `run_id`, an `assets` list with `asset_type`,
`storage_uri`, SHA-256 `checksum`, and optional `crs`, plus an `impact` object
with nonnegative metrics. The validated Python contract is `CompletedBundle`.

## Entity coverage and remaining integration

Sixteen application tables now cover the original six entities, dataset/version
provenance, historical events/version links, validation metrics, verified bundle
snapshots, scenario/version links and publication audit. Fuller run/asset/impact
metadata and local approved-only repositories are implemented. The candidate
contract still requires joint Part A/B1/B2 review; no real Part A bundle has
been supplied. Production ingestion uses the implemented GIS inspector for its
supported formats and still requires real approved artifacts and operator controls.

Local `GISInspector`, actual synthetic COG/GeoJSON fixtures, query filters and
scenario/asset spatial metadata with GiST indexes are now available. All spatial
reads retain the approved/mode gate. See `docs/contracts/spatial-gis-catalog.md`.
The saved GIS fixture is draft and generation does not register scientific
approval. Git/CI remains deferred; B2 HTTP integration and real Team A acceptance
remain separate from local B1 testing.

The synthetic seed exercises the complete B1 adapter in PostgreSQL. It is not
a B2 numerical model or an integration test against a separately delivered
B2 service. The clean B1-only rehearsal is now complete. Remaining integration:
agree the candidate contract/runtime, connect B2's API, and map Team A's real approved bundle. Local storage
is allowed by the blueprint; production object storage is a later deployment
choice. The existing run CLI is an internal/offline adapter, not authorization
for a public simulation-execution endpoint.

Step 11's expanded regression acceptance and step 13's consolidated runbooks are
documented in [acceptance](b1-acceptance.md) and [operations](runbooks/b1-operations.md).
Step 14 evidence and limitations are in [rehearsal](runbooks/handoff-rehearsal.md).
See [handoff checklist](b1-handoff-checklist.md) and [current status](b1-status.md)
for the local sign-off versus remaining joint acceptance gates.
