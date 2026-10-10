# Local repository, spatial catalog and GIS fixture (steps 8–10)

Current local implementation, without Git/CI or hosted database services.
Migration `g05b8eab1001` follows `f04b5e7b1001`, adding only two tables.
Existing migrations and records are unchanged.

## Query boundary

`PublishedScenarioRepository.list` requires an explicit demo/production mode and
supports scenario type, historical event, model version, input dataset/version,
data kind, overlapping timezone-aware coverage, WGS84 bbox and bounded paging.
Dataset-version filtering requires dataset ID and uses EXISTS, avoiding duplicate
scenario rows. Ordering is stable by scenario ID; limits are 1–1000 and offsets
nonnegative. Invalid/naive/reversed time ranges and invalid bbox values fail.

Approved asset reads additionally support role, format and paging. The approved
gate applies to footprints and spatial-asset reads too: draft/rejected/revoked,
legacy/unregistered and wrong-mode scenarios return no public spatial data.
`footprint` returns a GeoJSON string or None; `spatial_assets` returns metadata.
B2 remains responsible for HTTP schemas, pagination envelopes and safe URLs.

Internal admin repositories additionally support scenario status/model/mode,
asset role/run/format, run status/stage, status-reading mode/time ranges and stable
paging. Dataset versions support source/CRS/coverage filtering; historical events
use overlapping windows; metrics support event/station/model/name/run/mode and
computation time windows. These unrestricted repositories are not public APIs.

## PostGIS design

- `asset_spatial_metadata`: verified WGS84 MULTIPOLYGON bounds/coverage, source
  asset FK/checksum and inspection details (dimensions, dtype, resolution,
  transform, native CRS, valid cells/min/max, COG status or feature count).
- `scenario_spatial_metadata`: actual polygonal extent geometry from the verified
  extent GeoJSON, scenario/source-asset FKs and checksum. It is NOT inferred from
  raster bounds. Raster coverage bounds are not claimed to be wet/flood extent.
- Both geometry columns have GiST indexes, SRID/type enforcement and nonempty/
  valid-geometry checks. Bbox selection uses ST_Intersects on the actual extent,
  so a bbox contained in an extent's hole does not match.

Only verified content produces these rows. Existing metadata-only demos are not
given invented footprints. Large raster bytes remain in object storage. This is
a scenario/asset spatial catalog; station/exposure/domain-specific geometry and
dataset/event coverage refinements still require the shared GIS/API design.

## Actual synthetic fixture

`scripts/gis_fixture.py` generates eight immutable objects under
`scenarios/synthetic-gis-local-003/`: three real tiled COG rasters (depth,
velocity, arrival time), a valid WGS84 extent FeatureCollection, synthetic input
CSV, assumptions, quality report and manifest. Values are invented for testing,
not flood predictions or historical observations. The saved manifest is DRAFT,
with pending review and no approver. Generation writes no database rows and
does not promote the existing completed CSV demo into an approved publication.

```powershell
.\.venv\Scripts\python.exe scripts\gis_fixture.py
.\.venv\Scripts\python.exe scripts\validate_gis_bundle.py data\object-store\scenarios\synthetic-gis-local-003\manifest.json --bundle-root "file:///D:/Dam%20Projects/data/object-store/scenarios/synthetic-gis-local-003/"
```

If OBJECT_STORAGE_ROOT is overridden, use that root's URI/path instead. Repeating
generation is safe with unchanged pinned dependencies and unchanged bytes.
Changed fixtures must use new versioned keys rather than overwrite objects.

## GIS validation policy

The CLI importer now uses `GISInspector` by default. It performs real local
checks before DB writes: strict COG structure, single band, exact declared CRS,
band unit and nodata, coverage tags, finite north-up transform, aligned raster
grids, finite nonnegative valid cells and bounded resource use. Extent GeoJSON
must be a valid nonempty polygon FeatureCollection in EPSG:4326 without a CRS
override, with finite 2D coordinates inside WGS84 bounds and inside the common
raster coverage. Rasters are inspected before vectors, independent of JSON order.

COG checks use the [rio-cogeo validator](https://cogeotiff.github.io/rio-cogeo/api/).
Fixtures use GDAL's [COG creation driver](https://gdal.org/en/stable/drivers/raster/cog.html)
through Rasterio's [in-memory files](https://rasterio.readthedocs.io/en/stable/topics/memory-files.html).

The default local limits are 20 million raster pixels, 20 MB vector JSON and
10,000 features, configurable per inspector. Current checks support north-up
single-band COGs and nondegenerate vector coverage; KML, dateline wrapping,
3D/degenerate bounds and rotated grids are explicitly unsupported. Embedded
`coverage_start`/`coverage_end` tags and band units are required. These are the
current local acceptance rules, not claims that every Team A format is supported.

Explicit `--metadata-only-demo` preserves legacy fake-byte test workflows only
for demo mode; no spatial rows are created and it never bypasses production
checks. Production requires structured inspection results and refuses artifacts
tagged synthetic. Actual scientific approval/provenance remains Team A's job;
an operator allowlist is not reviewer identity authentication. A configured GIS
verifier is necessary but not sufficient for deployment/scientific acceptance.

## Verification and remaining boundary

Tests cover real GIS reads, alignment/units/nodata/coverage, invalid/empty/nonfinite
cells, non-COG TIFFs, invalid/outside vector geometry, spatial holes, indexes,
geometry constraints, filters, stable pages, rollback, revocation and real CLI
ingestion. A populated restore drill verifies geometry rows and seven local
artifact references in disposable databases. Existing demo records stay intact.

The database has 16 application tables at this head; older 6/11/14-table backups
remain restorable. Step 11's broader acceptance tests and step 13's consolidated
operations/recovery documentation are now added; see ../b1-acceptance.md and
../runbooks/b1-operations.md. Step 14's clean B1-only rehearsal is now complete;
see ../runbooks/handoff-rehearsal.md. Real B2/Team A integration remains external.
Step 12's Git/CI
work is deliberately DEFERRED at the user's request; it does not block local tests.
