# Polished application V02

This is the combined Team 1 + Team 2 application with V02 UI polish and corrected extent projection. Use [START_INTEGRATION.md](START_INTEGRATION.md), run `START_COMBINED.cmd`, and open **http://127.0.0.1:5176/**. Fresh checks and remaining operator gates are in [POLISH_STATUS.md](POLISH_STATUS.md). The older integration/SSD/B1 notes below are preserved history. Demo instructions are separate documents, not a product Review guide.

# Historical portable SSD copy

Use [START_HERE_SIMULATION.md](START_HERE_SIMULATION.md). Start with START_SIMULATION.cmd; this copy uses http://127.0.0.1:5174. The notes below are retained as original development history.

---

# Ukai Dam B1 data foundation

B1 provides the PostgreSQL/PostGIS catalog, registration contracts, demo seed,
and data-access layer for B2's read-only FastAPI integration service.

Final local sign-off: [B1 completion and B2 handoff](docs/B1_COMPLETION_AND_B2_HANDOFF.md).

The [candidate published-result contract](docs/contracts/README.md) now defines
the blueprint-facing metadata boundary. Its validator, local published-bundle
registration and approved-only repositories are implemented and tested; see
[registry contract](docs/contracts/published-registry.md). Dataset/version
provenance, historical events and validation metrics are now implemented;
see [catalog contract](docs/contracts/catalogs.md). Local B1 deliverables are ready
for B2 development handoff; formal joint backend acceptance remains pending.

Local query filters, indexed spatial metadata and an actual synthetic COG/GeoJSON
fixture are implemented; see [spatial/GIS contract](docs/contracts/spatial-gis-catalog.md).
Git/CI setup is deferred. No hosted database service is needed for this testing.

Quick start:

```powershell
docker compose up -d --build
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts\seed_db.py
.\.venv\Scripts\python.exe -m pytest
```

See [database operations](docs/runbooks/database.md), [local setup](docs/runbooks/local-setup.md), and the [B2 handoff](docs/b1-to-b2-handoff.md).

For the consolidated current scope, use [B1 status](docs/b1-status.md),
[acceptance coverage](docs/b1-acceptance.md) and [operations/recovery](docs/runbooks/b1-operations.md).
Steps 11, 13 and 14 now cover local acceptance, documentation and a clean B1-only
handoff rehearsal. See [handoff checklist](docs/b1-handoff-checklist.md) and
[rehearsal runbook](docs/runbooks/handoff-rehearsal.md). Step 12's Git/CI remains
deferred; scientific/B2 HTTP acceptance is not implied.

The verified local demo is `demo-monsoon-local-002`. All files and results are
synthetic contract fixtures. The earlier `demo-monsoon-001` is retained as
legacy metadata and still has unverified placeholder S3 references.

Local backups and restore drills are available through `scripts/backup_db.py`.
The legacy internal run adapter is `scripts/run_contract.py`;
precomputed import is `scripts/register_published_bundle.py`.
Real Team A bundles and B2 read-only API integration remain cross-team steps.
Production S3 is deployment-dependent; local versioned storage remains supported.
