# Published registry and approval-aware reads (steps 5–7)

Status: implemented and tested locally against the candidate manifest contract.
This does not freeze the cross-team contract, authenticate scientific reviewers,
provide real GIS outputs, configure S3, or implement B2's HTTP service.

## Metadata and migrations

`e03b5e7b1001` adds nullable metadata to scenarios, runs, assets and impacts,
plus `published_bundles`, `scenario_dataset_versions` and `publication_actions`.
`f04b5e7b1001` closes the SQL NULL approval-integrity gap without changing the
applied revision. Existing values remain unchanged; unknown metadata stay NULL.

- Scenario: publication status, schema version, data kind, parameter units,
  temporal coverage, optional historical-event FK and assumptions checksum.
- Run: explicit model/input-release versions, producing timestamp, quality
  report pointer/checksum, validation status and approver/time. `processing_runs`
  implements the blueprint's logical simulation-run entity, without a rename.
  Run IDs now support the candidate contract's full 150 characters.
- Asset: producing run FK, format, unit, temporal coverage and nodata; one asset
  per role per producing run.
- Impact: affected road kilometres and critical-facility count. Null is not zero.

Run `alembic upgrade head`. Downgrade only in disposable environments: it drops
new metadata/catalog tables and refuses to truncate IDs longer than the former
100-character limit. Tests never downgrade the working database.

## Registration boundary

`published_registry.register_published_bundle(session, manifest, store, ...)`
imports precomputed results; it never runs a model, changes existing files,
creates scientific approval or overwrites scenario/run identities.

1. Revalidate the entire manifest, including nested mutated models.
2. Validate a trusted caller-supplied local bundle root inside the configured
   store. Relative references resolve under it, not the working directory.
3. Require pre-registered dataset/version provenance to match the manifest:
   artifact, source label, licence, checksum, CRS, coverage and quality notes.
   Existing dataset names/source URLs/units are retained, not invented.
4. Require matching data modes. Historical replay needs an existing event and
   explicit event links to every input dataset version.
5. Verify bytes/checksums for all input datasets, assets, assumptions and quality
   reports. Reject missing files, paths outside the store and resolved asset
   aliases. The local adapter explicitly refuses remote S3 verification.
6. Approved imports require the declared reviewer in a caller-controlled explicit
   allowlist. This is an operator trust boundary, not reviewer authentication.
   Neither the allowlist nor registering operator comes from the manifest.
7. Production imports additionally require an injected
   `asset_inspector(path, role, metadata)` that raises for invalid GIS content.
   The CLI now uses the local `GISInspector` by default and requires structured
   results for production. Tagged synthetic assets cannot claim production.
   `--metadata-only-demo` explicitly retains older fake-byte tests only in demo
   mode. See `spatial-gis-catalog.md` for actual COG/GeoJSON checks and limits.
8. Write scenario, completed offline run, assets, impact, dataset links,
   canonical manifest snapshot/checksum and registration audit atomically.

The manifest checksum hashes canonical UTF-8 JSON of the validated snapshot
(sorted keys, compact separators), not original file whitespace. The snapshot
retains input references; metadata rows store normalized absolute local URIs.
Ingestion does not create a manifest file, so DB errors cannot leave partially
published objects. All objects must already exist immutably. The caller owns
commit/rollback; an internal savepoint removes every import row after late
failure even if the caller catches the error and commits unrelated work.

Operator interface (supply actual trusted values, not placeholder approval):

```powershell
.\.venv\Scripts\python.exe scripts\register_published_bundle.py <manifest.json> --bundle-root <trusted-file-URI-ending-in-slash> --registered-by <operator> --trusted-approver <reviewer>
```

Prepare dataset/version and event provenance via catalog repositories first.
The checked-in example has placeholder hashes and no real artifacts: it is NOT
an importable approved GIS bundle. Do not invent trust values to bypass review.
Draft/rejected manifests can be registered for internal review but are never
publicly returned. Revised publication/approval submissions require a new ID;
in-place draft promotion is intentionally not implemented.

## B2 read contract

Use `PublishedScenarioRepository`, not unrestricted legacy/admin repositories,
for public scenario, asset, impact and provenance responses. Every accessor
requires explicit `data_mode='demo'` or `data_mode='production'`.

Reads require a registered bundle, approved publication, completed scenario/run,
passing validation and complete approval identity/time. Legacy completed demos,
drafts, rejected and revoked records are hidden through all accessors. Lists
have stable scenario-ID ordering, bounded pagination and type/event filters.
Assets are additionally restricted to the registered bundle's producing run.
Hidden/missing scenarios and summaries return None; asset/dataset lists are empty.

These are Python repositories, not HTTP endpoints. B2 owns safe response schemas
and link generation: never expose raw local file URIs, internal snapshots or
reviewer identities directly to clients.

Administrative `revoke(scenario_id, actor=..., reason=...)` locks the scenario,
hides it from approved reads and appends an audit record. It preserves the
original snapshot/approval declaration. Actor identity must come from trusted
administrative context; this is not a public anonymous write operation.
There is no automatic reapproval or scientific metric calculation.

Trust, provenance and source-mode rules are application guarantees, not security
against privileged SQL. DB checks enforce FKs, uniqueness, timestamps, finite
nodata/impact extensions and complete passing approval metadata. No row-level
security policy is introduced. Large rasters remain outside PostgreSQL.

## Recovery and tests

Backups include all 16 application tables and their sequences; older six-,
eleven- and fourteen-table archives still restore. The inventory verifies local dataset
sources, validation reports, assumptions and quality reports when those columns
exist, as well as inputs/results. S3 references remain explicitly unresolved.

`tests/test_published_registry.py` covers all read gates, revocation/audit,
provenance links, missing/bad bytes, trust, production verifier gating, duplicates,
late DB failure, caller rollback, CLI ingestion, full-length IDs and migration
roundtrips. A real pg_dump/pg_restore test uses disposable databases containing
a registered synthetic bundle and seven verified local references.

## Pending integration

Joint contract approval, real Team A artifacts/scientific review, domain-specific
spatial refinements, B2 FastAPI and final cross-team rehearsal remain. Local GIS
integrity checks, scenario/asset spatial catalog and broader queries are now
implemented. Git/CI setup is deferred at the user's request.
S3 is deployment-dependent. No public run-simulation endpoint is added. This is
local batch completion, not merged production or complete B1 acceptance.
