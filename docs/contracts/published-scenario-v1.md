# Candidate published scenario V1 (1.0.0)

This is a proposed versioned contract for precomputed Part A outputs. It is not
an instruction to run HEC-RAS, nor an API endpoint. Production scientific
approval remains the responsibility of the publishing team.

## Required identity and provenance

| Field | Meaning |
|---|---|
| `schema_version` | Literal `1.0.0` for this candidate; reject unsupported versions. |
| `scenario_id` | Immutable lower-case identifier; changed results require a new scenario/version. |
| `scenario_type` | `historical_replay` or `hypothetical`; no live forecast execution in V1. |
| `status` | Publication state: `draft`, `approved`, `rejected`. Separate from execution state. |
| `model_version` | Exact producing model/package version supplied by Part A. |
| `input_dataset_version` | Version of the complete input release; individual datasets have independent versions below. |
| `crs` | Explicit scenario/model CRS identifier. Example uses EPSG:32643; no default CRS is inferred. |
| `time_step_minutes` | Positive integer output timestep. |
| `data_mode` | Deployment/demo context: `demo` or `production`. |
| `data_kind` | Scientific label: `observed`, `simulated`, `assumed`, `demo`. Demo mode requires demo kind. |
| `run_id` | Immutable identifier of the offline producing run. |
| `run_timestamp` | Time the producing run finished, supplied by Part A, not ingestion time. |
| `time_coverage` | Scenario/event period represented, independent of the wall-clock run timestamp. |
| `historical_event_id` | Required for historical replay; null/absent for hypothetical scenarios. |
| `datasets` | Nonempty unique dataset/version records with explicit source reference, source label, licence, checksum, quality notes and nullable coverage/CRS. |

Dataset source bytes are addressed by `source_reference`. This is the immutable
source artifact, not a general provenance website. Dataset catalogue work may
add a separate source URL later; catalogue/registry links must remain explicit.
Production cannot use a dataset labelled `demo`.

## Parameters and units

All five parameter keys below must be present. Null means unavailable or not
applicable. Missing values are never converted to zero. All numbers must be
finite JSON numbers; counts cannot be floats, strings or booleans.

| Parameter | Required companion unit | Rule |
|---|---|---|
| `reservoir_level_m` | `m` | Finite elevation or null. Datum must be confirmed in the producing dataset/model provenance. |
| `peak_inflow_m3s` | `m3/s` | Nonnegative or null. |
| `peak_release_m3s` | `m3/s` | Nonnegative or null. |
| `breach_width_m` | `m` | Positive or null. No-breach/not-applicable uses null. |
| `breach_formation_minutes` | `min` | Positive or null. |

These units live in `parameter_units`; suffixes are also preserved. Extra fields
are rejected in this initial candidate. A new agreed parameter/role requires a
contract change and example/test update, not an undocumented arbitrary value.

## Result references and metadata

`assets` retains the blueprint's role-to-reference mapping. `asset_metadata`
must have exactly the same keys. Each role has a SHA-256 checksum, format,
CRS, unit, nodata (explicit null if not applicable), and time coverage.

| Role | Format | Unit | Candidate requirement |
|---|---|---|---|
| `max_depth_cog` | `cog` | `m` | Required for approved publication |
| `max_velocity_cog` | `cog` | `m/s` | Required for approved publication |
| `arrival_time_cog` | `cog` | `min` | Required for approved publication |
| `extent_geojson` | `geojson` | `1` | Required for approved publication |
| `duration_cog` | `cog` | `min` | Supported; final completeness gate needs Part A agreement |
| `hazard_cog` | `cog` | `class` | Supported; classification scheme needs Part A agreement |
| `exposure_geojson` | `geojson` | `count` | Supported; feature properties need Part A agreement |
| `export_geojson` | `geojson` | `1` | Optional derivative |
| `export_kml` | `kml` | `1` | Optional derivative |

All raster CRS values must match the scenario CRS. Derived vector assets can
declare a different CRS explicitly (the example declares EPSG:4326). Per-asset
coverage must be ordered and lie within the scenario period. This metadata
check does not inspect raster alignment, geometry, nodata content or file
format; those belong in subsequent asset-registration/Part A QA gates.

Approved manifests need the four roles explicitly shown in the blueprint
manifest. The broader blueprint scope includes duration/exposure/hazard; their
scientific definitions and final mandatory set remain review items, not claims
that the four-role example finishes all V1 output requirements.

## Summary and missing values

`summary` requires depth, flooded area, population and building exposure keys.
Roads affected in kilometres and critical-facility count are supported as
nullable extensions. Nonnegative finite metrics and integral counts are
enforced. Nulls remain null. Field suffixes carry summary units: metres,
square kilometres, kilometres, or counts. No scientific metrics are computed
by this contract.

## Assumptions and quality review

`assumptions_url` identifies an immutable assumptions artifact and
`assumptions_checksum` is its SHA-256. `quality` identifies a checksummed report
and `validation_status` (`pending`, `pass`, `fail`).

Approved state requires `pass`, a nonblank `approved_by`, and a timezone-aware
`approved_at` at or after `run_timestamp`. Draft/rejected states cannot carry
approval fields. `require_publishable` rejects any non-approved state.
These checks validate an approval declaration, not the approver's identity or
scientific conclusion. Local registration now requires a caller-configured
approver allowlist and approved-only reads are implemented; see
`published-registry.md`. Joint authority policy and scientific review remain
cross-team acceptance requirements.

## Timestamp and reference rules

- Times use ISO 8601 with timezone; naive timestamps and numeric Unix timestamps
  are rejected. Comparisons respect UTC offsets. JSON serialization retains
  timezone information.
- Checksums use `sha256:` followed by 64 lower-case hexadecimal characters.
- Relative POSIX references resolve under an explicit trusted bundle root
  supplied by the importer, never under the current working directory.
- Absolute `file://` and `s3://` object references are also allowed. Credentials,
  signed-query URLs, fragments, traversal, remote file authorities and control
  characters are rejected. Relative references are preserved as references.
- `resolve_reference(base_uri, reference)` provides deterministic resolution.
  The local importer checks allowed roots, existence and bytes/checksums.
  Production still requires a configured real GIS content verifier. Remote
  bucket verification is not implemented by the local adapter.
- Database identifiers, versions and checksums are never inferred from names.
  API responses must use safe asset links, not expose local file paths.

## Acceptance boundaries and open decisions

1. Structural JSON Schema check.
2. Runtime semantic validation: matched asset roles, consistent units/CRS/time,
   duplicate prevention, historical links, and approval/data-label consistency.
3. Local storage verification and atomic registry write are implemented; GIS
   content verification remains a production gate.
4. Approved-only repositories are implemented; B2 owns HTTP/OpenAPI models.

Review before team freeze: vertical datum representation; exact minimum role
set; hazard/exposure feature schemas; quality metrics/pass thresholds; source
catalog identifiers; trusted approver policy; and export coverage requirements.
No scientific thresholds are invented by this step. Adding explicit unit/CRS
metadata is not scientific calibration/validation.
