# Part A local prototype integration — delivery contract

Version 1.0.0, issued 7 October 2026 under revision-2 Team B execution work order. This freezes the bounded engineering delivery design; scientific approval and actual Part A-manifest reconciliation remain separate. B-01 supplies this contract to A1/A2 for producing compatible derivative bundles.

## Scope and owners

All work is local, Python 3.13; plain folders exchanged by SSD. Stored scenarios first. Windows/local preview is the initial target; hardened-container preview is excluded. Existing approved API/query/schema behavior must remain compatible. No new migrations are planned. No Git/cloud/authentication/model-running/admin API, frontend, incidental style/KML/privacy changes or new engine adoption.

A2 supplies original and derivative GIS bytes, conversion/alignment QA, actual engine/model/timing facts and source-to-derivative records. A1 supplies real input bytes, dataset release/version identity, labels/licences and historical-event evidence. B1 validates receipt/GIS/provenance/catalog registration in an isolated target. B2 defines context/preview contracts, implements eligibility/admission/delivery and records API checks. Missing scientific facts return to A; B does not infer them.

## Published manifest remains unchanged

Use actual PublishedScenarioManifest JSON/Pydantic schema 1.0.0. Do not insert inline calibration, engine or known-issues fields. Map source hypothetical_release to hypothetical, preserving original type in context; historical_replay requires genuine existing event linkage. Keep draft; map source not_validated to pending, retaining source label in context. Set approved_by and approved_at to null. Genuine simulated output uses production/simulated. Production here is an existing stored-data mode name, not a claim of deployment or scientific approval. Synthetic examples remain demo/demo and cannot be admitted to actual preview.

Keep unique new derivative scenario/run identities, for example <source>-hr-int-v1 with a distinct run ID, within the existing lowercase 3..150 identifier constraints. Never overwrite/upsert old IDs, edit a saved draft into approved or replace existing object bytes. Revisions use new IDs/keys. Record source scenario/type/manifest raw hash, engine and explicit scenario_family without inferring relationships from suffixes.

time_step_minutes means the positive integer temporal RESULT OUTPUT interval documented by A2. Distinguish computation step, forcing interval, mapping interval and arrival effective resolution in context. run_timestamp is producing-run completion, not file-copy or import time. Scenario coverage and arrival reference require explicit timezone or justified model-clock evidence; hypothetical anchors are not observations. Do not invent missing intervals/times/versions/licences to pass validation.

## Supported first delivery and transformations

Require depth/velocity/arrival COGs and extent GeoJSON for initial preview completeness; the underlying draft schema permits fewer assets but this delivery requires the four core roles. Depth m, velocity m/s, arrival min, extent unit 1. Duration/hazard/exposure/exports remain absent unless genuine reviewed evidence and scoped requirements justify them. WSE is preserved separately with hash and unknown datum, not registered or served. No KML in this preview.

A2 creates new derivative folders. Arrival hours -> minutes multiplies valid cells by 60 and preserves nodata. Derive window from actual geotransforms onto exact depth grid where integer-lattice alignment is verified; do not hard-code 256. If meaningful source valid cells lie outside the window, return the conflict. Different grids need an explicit method agreed with A2. Check full arrays/masks with documented dtype tolerance, not selected pixels alone.

All registered rasters must be actual strict single-band north-up COGs with matching CRS/grid/dimensions, finite nonnegative cells, unit/nodata metadata and coverage tags. Default B1 pixel limit is 20 million, separate from B2 file cap. GeoJSON must use actual WGS84 coordinates, valid finite 2D polygons, no top-level CRS override and valid raster containment. Preserve source threshold/simplification/small-part rules and explain raster/vector area differences. Preserve original and derivative inventories; never recompute an expected mismatch away.

## Prototype context 1.0.0

Set assumptions_url to the portable relative prototype-context.json artifact; assumptions_checksum hashes its raw bytes. quality.report_reference/checksum separately binds actual QA. Context is strict JSON <=64 KiB, duplicate keys rejected, unknown fields forbidden; no HTML/remote fetching/executable content. Exact fields are defined by prototype_context.py and prototype-context.schema.json.

Required groups: schema/derivative identity; explicit engine name/software version/build and source hash (nullable with exact reasons); scenario_family; fixed uncalibrated/not_validated/prototype labels; original status/type/scenario/raw-manifest/source-asset hashes; forcing kind/description/assumed label, dataset references/evidence/uncertainties; arrival min/simulation_start/reference/0.1 m/resolution/original h x60 conversion; separate timing intervals/clock evidence; explicit calibration, terrain/bathymetry, datum and exposure limitations plus source uncertainty; nonempty assumptions; unavailable products/reasons; optional preserved WSE; derivation processor/version/source identity/operations/evidence.

Binding checks: derivative IDs and model/input releases match manifest; arrival reference equals coverage start; documented result-output interval equals time_step_minutes; historical/hypothetical forcing and clock meaning are coherent; forcing dataset/version links exist in manifest and are assumed for the reconstructed/hypothetical forcing in this delivery; original source identities match derivation; source/arrival/WSE hashes cross-bind; unknown impact values have reasons. Reasons for missing engine/timing values are required, not arbitrary defaults. Missing exposure remains null. Package examples are synthetic metadata only and do not establish any actual GIS/provenance fact.

## Preview contract and admission

Separate prototype repository, response schemas, service and routes; never widen approved_statement or inherit approved/pass defaults. Initial routes: GET list/detail/layers/impact; GET/HEAD exact-run assets/assumptions/quality-report under /api/v1/prototypes/scenarios. No write or export-generation endpoints. See prototype-preview-api-v1-candidate.md and prototype-preview-api-v1.design.json (DESIGN artifact; routes are not implemented in Stage 2).

B2_ENABLE_PROTOTYPE_PREVIEW defaults false. Enabled preview requires B2_ENV=local and B2_PROTOTYPE_ADMISSION_FILE. Admission JSON <=1 MiB / 1000 entries, version 1.0.0, exact scenario/run/canonical manifest hash, no duplicates/unknown fields/wildcards. Reread safely per request; empty list exposes none, malformed/unreadable input fails closed. Recheck each new download; already sent bytes cannot be recalled.

Eligibility requires ALL: admission identity/hash match; registered bundle; completed scenario/linked run; draft publication; pending validation; null approval fields; production mode and simulated kind; matching scenario/run; revalidated stored canonical manifest and valid bound context; structured GIS metadata tied to selected asset/run/checksum. Exclude approved/rejected/revoked/demo/legacy/failed/incomplete/unregistered/mismatched records even if admitted. Require loopback peer; never trust forwarded client headers. Local launcher binds 127.0.0.1. Preview disabled means 404 and no preview in default OpenAPI; enabled schema is separate.

Use existing verified_download/snapshot/range/budget/cleanup mechanics. All emitted URLs remain in prototype namespace; no raw paths or source-provenance references are serving permissions. Success downloads carry Cache-Control: no-store and X-Ukai-Prototype: true / X-Ukai-Scientific-Validation: not_validated. Preserve MIME/filename/ETag/HEAD/range behavior. Assumptions here are context JSON, while existing approved assumptions delivery remains unchanged. Safe 404 for missing/unadmitted/ineligible, 503 for unavailable/incoherent artifacts, existing problem envelopes; invalid request queries 422 and invalid ranges 416.

## Paths, checksums and registration prerequisites

Portable manifest/context evidence references use POSIX relative keys, no ../, absolute Windows paths, credentials/query/fragment or remote fetching. Resolve at receipt in a NEW trusted local object root. Input catalog keys are store-root relative; manifest keys are bundle-root relative and must identify identical bytes. Stored normalized file:// URIs remain receiver-specific; do not reuse sender absolute DB rows or rewrite working rows for SSD receipt.

Artifact hashes: sha256:<64 lowercase hex> of raw bytes. Source manifest raw hash differs from canonical validated stored manifest hash (sorted keys/compact UTF-8 JSON). Admission uses the STORED canonical hash. Context must not contain its own checksum. Package CHECKSUMS.sha256 uses raw hashes without prefix and excludes itself.

Register actual datasets/versions and exact provenance first; historical events explicitly link all input versions. Duplicate scenario/run IDs reject; dataset versions are append-only through supported registration. Existing register_published_bundle supports draft storage; no trusted approver is supplied for these drafts and no new --allow-draft import flag exists. Metadata validator --allow-draft is a different command. Do not use metadata-only-demo for real Part A GIS.

## Exchange and verification gates

B-01: actual published/context schema, pure supporting validators, standalone metadata checker, instructions and integration/preview design, examples, inventory/hashes. A-01: complete original + compatible derivative H02 with inputs/context/QA/transform evidence. B-02: itemized requirement-ID failures and accepted IDs/run/hash/contract mappings. A-02: corrected H02 plus independently ready H01/H03/2006. B-03: final source/evidence/plain folder with incomplete gates.

Standalone checker opens only explicitly supplied manifest/context JSON. It must not load .env, DB/session/GIS/app modules, create connections or serve HTTP. It checks metadata and context raw hash/binding; it does not establish actual input/asset bytes, GIS validity, DB state or science. Synthetic metadata mode is explicit and never an actual preview-admission path.

Stage 2 source-side review can compare existing B1/B2 implementation, but D06 stays open until actual Part A manifests are received. No production data import is implied by B-01. Stage 3 creates/test-checks isolated resources; genuine H02 technical roundtrip, SSD/receiver and scientific acceptance remain distinct later gates.
