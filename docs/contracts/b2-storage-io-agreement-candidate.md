# Step 5 — asset paths and Team A/B1/B2 input-output agreement

Status: **candidate for joint review, not an agreed/frozen contract**.
Prepared 2026-10-06 against the existing published manifest 1.0.0 and B2 API v1.
No schema, runtime, migration, stored URI, scientific record or approval was changed.
Step 4's local engineering checks passed; final real-data capacity acceptance is
still separate. Team A need not finish all modelling before reviewing this proposal.

## 1. Scope and existing sources of truth

- Team A supplies offline model results, input provenance, assumptions, impact
  measurements and scientific quality evidence. B2 does not execute models,
  calculate missing statistics or manufacture historical observations.
- B1 verifies/catalogues immutable bytes and manifests, checks GIS/trust/provenance,
  registers atomically, and administers revocation. Its existing schema remains
  [published scenario 1.0.0](published-scenario.schema.json), with additional
  executable cross-field checks in `services/api/app/published_contract.py`.
- B2 uses approval/mode-aware repositories and returns explicit public JSON plus
  relative download links; [saved OpenAPI](b2-openapi-v1.json) defines HTTP responses.
- Current deployment is **local files only**. No bucket, keys, public authentication,
  remote adapter or public hosting is required by this proposal. S3 syntax in the
  manifest does not mean remote bytes can be verified or served by the current adapter.

## 2. Proposed logical asset paths

Keep keys immutable and POSIX-style. Use the same object-relative keys on Windows
and Linux; only the operator-configured root differs. This naming convention is a
proposal, **not a new enforced B1 rule**. Existing valid layouts remain valid.

```text
<OBJECT_STORAGE_ROOT>/
  datasets/<dataset-id>/<version>/<input-filename>
  scenarios/<scenario-id>/
    manifest.json
    runs/<run-id>/
      outputs/<asset-role>.tif|geojson|kml
      assumptions.txt
      quality/report.json
      logs/<log-name>.log       (optional, never an API download role)
```

Proposed canonical import convention: the trusted **bundle root is the object-store
root**, supplied by the receiving operator, not inferred from the manifest filename.
All manifest references are object-root-relative full keys, for example:

| Manifest field | Proposed reference |
| --- | --- |
| `datasets[].source_reference` | `datasets/<dataset-id>/<version>/<input-filename>` |
| `assets.max_depth_cog` | `scenarios/<scenario-id>/runs/<run-id>/outputs/max_depth_cog.tif` |
| `assumptions_url` | `scenarios/<scenario-id>/runs/<run-id>/assumptions.txt` |
| `quality.report_reference` | `scenarios/<scenario-id>/runs/<run-id>/quality/report.json` |

For this convention, a container import root is `file:///objects/`. A host-development
root is the configured local object directory (default `D:\Dam Projects\data\object-store`),
converted to a file URI ending in `/` by the receiving tool. Never resolve these keys
under the working directory or automatically under `scenarios/<id>/manifest.json`.
Catalogue-relative dataset references also use the object root, so reuse of the same
dataset/version can point to one immutable artifact rather than scenario-specific copies.

An existing scenario-specific bundle root is still supported, but every relative
reference must be consistently relative to that root; globally shared datasets then
need an explicit valid target-namespace reference matching the catalogue. No `../`
links, mutable `latest`, credentials, signed queries, fragments or public raw file URIs.
Do not mix these two reference conventions implicitly.

Windows `file:///D:/...` DB references are not made Linux-compatible merely by mounting
the files at `/objects`. Register new bundles/catalogue references through B1 in their
intended receiving namespace. Do not rewrite existing working DB rows to change paths.
The portable manifest keys do not authorize moving/rekeying live objects.

Changed input bytes require a new dataset version/key; changed published results
require new scenario/run identities under current B1 rules. Do not overwrite keys,
promote drafts in place, re-register immutable dataset versions with another URI,
or infer versions/checksums from filenames.

## 3. Team A delivery contents

- Manifest 1.0.0 with explicit scenario/run/model/input-release identities, mode/kind,
  producing timestamp, timezone-aware coverage, CRS and output timestep.
- Nonempty input dataset/version records matching the B1 catalogue: immutable source
  reference, source label, licence, actual SHA256, CRS/coverage or explained nulls,
  and quality notes. Historical replay additionally needs the event and dataset links.
- All five parameter keys plus their existing companion units; explicit null means
  missing/not applicable, not zero. No NaN/Infinity, guessed datum or implicit CRS.
- Actual asset bytes, role metadata, assumptions bytes/checksum and quality-report
  bytes/checksum. `assets` and `asset_metadata` must contain exactly the same roles.
- Registered impact values with unit-bearing fields and preserved nulls. Team A
  computes these; neither B1 registration nor B2 delivery makes them scientifically valid.
- For approved publication: passing quality, declared approver/time and actual reviewer
  authority agreed outside the manifest. The importer independently supplies its trusted
  approver allowlist; Team A cannot make its own identity trusted through a payload field.

The existing four-role approval minimum is:

| Role | Format | Unit | Current status |
| --- | --- | --- | --- |
| `max_depth_cog` | COG | `m` | Required by current candidate |
| `max_velocity_cog` | COG | `m/s` | Required by current candidate |
| `arrival_time_cog` | COG | `min` | Required by current candidate |
| `extent_geojson` | GeoJSON | `1` | Required by current candidate |
| `duration_cog` | COG | `min` | Supported; final necessity/definition needs Team A |
| `hazard_cog` | COG | `class` | Supported; class meaning/legend/thresholds need Team A |
| `exposure_geojson` | GeoJSON | `count` | Supported; feature properties/meaning need Team A |
| `export_geojson` | GeoJSON | `1` | Optional existing derivative, not generated by B2 |
| `export_kml` | KML | `1` | Transport only; B1 GIS acceptance is not implemented |

The four-role example is not proof that all blueprint scientific outputs are complete.
Agree duration/hazard/exposure obligations before final acceptance. Do not fabricate
missing layers, relabel an extent as an export, or invent hazard classifications.
Current raster checks enforce a common grid/CRS, units, nodata, coverage, finite
nonnegative valid cells and strict COG structure; vectors need declared CRS and valid
geometry. The current GeoJSON inspector requires EPSG:4326. Vertical datum and
scientific pass thresholds remain explicit review questions, not new guessed fields.

`sha256:<64 lower-case hex>` hashes actual artifact bytes. The DB manifest checksum
instead hashes B1's canonical validated JSON snapshot; it is not the original
manifest file's whitespace-sensitive byte checksum. Keep these meanings separate.

## 4. B1 receiving and B2 output boundary

1. Receive complete immutable object bytes privately into the agreed root/key layout.
   Use existing atomic immutable publication; no partially published result keys.
2. Register dataset versions/event links and genuine provenance in B1 before import.
3. Validate metadata/semantics, then use the actual B1 GIS-aware importer with the
   trusted explicit root, operator and reviewer allowlist. For larger rasters, agree
   an explicit `--max-raster-pixels`; the existing default remains 20 million.
   Demo/synthetic fixtures must never be relabelled production. Metadata-only demo
   mode is not an approved GIS/scientific receiving path.
4. Registration commits atomically or rolls back. Duplicate identities, missing or
   changed files, mismatched provenance or failed GIS/trust checks do not publish.
5. B2 exposes only approved/completed/passed/mode-matching registered bundles.
   Download URLs are `/api/v1/scenarios/<id>/assets/<role>?data_mode=<mode>` or the
   assumptions route. Raw object URIs, credentials, logs and quality-report paths
   stay private. Export discovery advertises only a registered verified derivative.
6. Each new request rechecks approval/integrity; revocation hides subsequent reads.
   It cannot recall bytes already sent. Missing/unavailable artifacts return safe 503,
   hidden/absent records 404, invalid parameters 422, invalid ranges 416.

Current local API defaults remain demo mode, offset paging (20 default, 999 maximum)
and separate liveness `/api/v1/health` versus operational readiness `/readyz`.
Step 4 defaults are 512 MiB per object, 1 GiB scratch, 2 GiB API RAM, full SHA256 even
for HEAD/ranges, 60-second cooperative verification and 300-second streaming deadline.
Two 341 MiB slow-reader streams passed; a third is rejected safely under reserved-space
pressure. This is a measured synthetic baseline, not a Team A workload/SLA agreement.

### Known reviewer-identity policy conflict

Current B2 detail JSON exposes `quality.approved_by` and `approved_at`; the older B1
registry guide says reviewer identities should not be exposed directly. The teams
must agree whether this is a public review label, restricted identity or a field to
remove/redact. No identity is silently relabelled/redacted here. A changed public
shape requires coordinated schemas, OpenAPI, examples and tests, with compatibility
and provenance meaning agreed first.

## 5. Decisions required to call Step 5 agreed

Expected reviewing groups below are not nominated people or fabricated approvals.

| Decision | Current proposal / unresolved item | Reviewing groups |
| --- | --- | --- |
| Storage namespace | Local files; object-root-relative canonical keys above; actual mount path/store ID/operator to be confirmed | B1, B2, receiving/storage owner |
| Required output set | Keep current four-role gate pending duration/hazard/exposure/export agreement | Team A, B1, B2 |
| Scientific meaning | CRS/grid/datum, arrival/duration origin, hazard legend, exposure fields/nulls and pass criteria | Team A scientific owner, B1, frontend |
| Quality authority/privacy | Genuine approver authority/allowlist and resolution of the reviewer-identity conflict | Team A, B1, B2, receiving/privacy owner |
| Dataset/event provenance | Exact catalogue IDs/versions, source labels/licences, event links and coverage | Team A, B1 |
| HTTP freeze | Existing fields/errors/paging/mode defaults/readiness and safe download semantics | B1, B2, frontend/receiver |
| Capacity/formats | Exact maximum bytes/pixels/vector sizes by format, concurrency/SLA, agreed scratch/RAM; KML exclusion or real verifier plan | Team A, B1, B2, receiver |
| Receiving evidence | Named receiver and a representative approved subset, not merely synthetic fixtures | Team A, B1, B2, receiver |

Record agreed choices, named authority, date, reviewed manifest/API versions and
evidence/reference for each decision. An agreement may be obtained before Team A
finishes all outputs; final scientific/large-file acceptance still needs real samples.

## 6. Status checklist

- [x] Existing executable manifest, repository and HTTP boundaries inspected.
- [x] Storage-path/reference proposal prepared without relocating working objects.
- [x] Input/output/role/unit/trust/error responsibilities documented.
- [x] Known identity/privacy conflict and missing scientific/capacity choices recorded.
- [ ] Named Team A/B1/B2/frontend/receiving reviewers confirmed.
- [ ] Choices above explicitly agreed and recorded; schemas/API jointly frozen.
- [ ] Any agreed contract changes implemented with migration/compatibility/test review.
- [ ] Representative real approved bundle received, imported and verified end-to-end.

Step 5 is **prepared, pending joint agreement**. This document is not a signature,
scientific approval, permission to overwrite data or completion of joint acceptance.
