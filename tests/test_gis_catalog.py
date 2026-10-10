"""Actual synthetic GIS fixtures and isolated PostGIS queries; never science claims."""
from datetime import timedelta
import json
from pathlib import Path
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import box, shape, mapping, MultiPolygon, Polygon

from test_b1_integration import isolated_database, session
from scripts.gis_fixture import build_fixture, cog_bytes, GRID
from services.api.app.storage import LocalObjectStore
from services.api.app.gis_validation import GISInspector
from services.api.app.published_registry import register_published_bundle
from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate
from services.api.app.db.models import Scenario, AssetSpatialMetadata, ScenarioSpatialMetadata
from services.api.app.repositories.catalog_repository import DatasetRepository
from services.api.app.repositories.published_repository import PublishedScenarioRepository


def prepared(session, tmp_path, *, status="approved"):
    store = LocalObjectStore(tmp_path / "objects")
    item, root, _ = build_fixture(store)
    if status == "approved":
        item.status = "approved"
        item.quality.validation_status = "pass"
        item.quality.approved_by = "synthetic-fixture-reviewer"
        item.quality.approved_at = item.run_timestamp + timedelta(minutes=15)
    datasets = DatasetRepository(session)
    for source in item.datasets:
        datasets.register(DatasetCreate(dataset_id=source.dataset_id, name="Synthetic GIS input", description="No observations", data_mode="demo"))
        values = source.model_dump()
        values["source_reference"] = store.resolve_uri(root + source.source_reference).as_uri()
        datasets.register_version(DatasetVersionCreate.model_validate(values))
    return item, store, root


def register(session, item, store, root):
    return register_published_bundle(session, item, store, bundle_root_uri=root, registered_by="local-test", trusted_approvers={"synthetic-fixture-reviewer"}, asset_inspector=GISInspector())


def replace_asset(item, store, root, role, content):
    key = root.removeprefix(store.root.as_uri() + "/") + "changed/" + role
    uri, checksum = store.put(key, content)
    item.assets[role] = uri
    item.asset_metadata[role].checksum = checksum


def test_real_gis_registration_and_spatial_reads(session, tmp_path):
    item, store, root = prepared(session, tmp_path)
    register(session, item, store, root)
    rows = session.scalars(select(AssetSpatialMetadata)).all()
    assert len(rows) == 4
    raster = next(row for row in rows if row.details.get("width"))
    assert raster.details["width"] == 256 and raster.details["height"] == 256
    assert raster.details["valid_cells"] == 192 * 192 and raster.details["cog_valid"]
    spatial = session.scalar(select(ScenarioSpatialMetadata))
    extent = to_shape(spatial.geom)
    assert extent.geom_type == "MultiPolygon" and extent.is_valid
    repo = PublishedScenarioRepository(session)
    assert repo.list(data_mode="demo", bbox=extent.bounds)[0].scenario_id == item.scenario_id
    assert repo.list(data_mode="demo", bbox=(0, 0, 1, 1)) == []
    assert json.loads(repo.footprint(item.scenario_id, data_mode="demo"))["type"] == "MultiPolygon"
    assert len(repo.spatial_assets(item.scenario_id, data_mode="demo")) == 4
    assert repo.footprint(item.scenario_id, data_mode="production") is None
    repo.revoke(item.scenario_id, actor="local-test", reason="Synthetic withdrawal")
    assert repo.footprint(item.scenario_id, data_mode="demo") is None
    assert repo.spatial_assets(item.scenario_id, data_mode="demo") == []
    assert repo.list(data_mode="demo", bbox=extent.bounds) == []


def test_broad_filters_and_stable_pages(session, tmp_path):
    item, store, root = prepared(session, tmp_path)
    register(session, item, store, root)
    for identity in ("aaa-gis", "zzz-gis"):
        other = item.model_copy(deep=True)
        other.scenario_id, other.run_id = identity, identity + "-run"
        register(session, other, store, root)
    repo = PublishedScenarioRepository(session)
    assert [row.scenario_id for row in repo.list(data_mode="demo", limit=1, offset=0)] == ["aaa-gis"]
    assert [row.scenario_id for row in repo.list(data_mode="demo", limit=1, offset=1)] == [item.scenario_id]
    assert len(repo.list(data_mode="demo", model_version=item.model_version, dataset_id=item.datasets[0].dataset_id, dataset_version="1.0.0", start=item.time_coverage.start, end=item.time_coverage.end, data_kind="demo")) == 3
    assert repo.list(data_mode="demo", model_version="missing") == []
    assert repo.list(data_mode="demo", model_version="'; DROP TABLE scenarios; --") == []
    assert repo.list(data_mode="demo", dataset_id="missing") == []
    assert repo.list(data_mode="demo", dataset_id=item.datasets[0].dataset_id, dataset_version="missing") == []
    assert repo.list(data_mode="demo", start="2027-01-01T00:00:00Z") == []
    assert repo.list(data_mode="demo", end="2020-01-01T00:00:00Z") == []
    assert len(repo.assets(item.scenario_id, data_mode="demo", format="cog")) == 3
    assert len(repo.assets(item.scenario_id, data_mode="demo", asset_type="max_depth_cog")) == 1
    assert len(repo.assets(item.scenario_id, data_mode="demo", limit=1, offset=1)) == 1
    assert DatasetRepository(session).list_versions(item.datasets[0].dataset_id, source_label="demo")
    assert DatasetRepository(session).list_versions(item.datasets[0].dataset_id, source_label="observed") == []


@pytest.mark.parametrize("kwargs", [
    {"bbox": (2, 0, 1, 1)}, {"bbox": (0, 0, 181, 1)}, {"bbox": (True, 0, 1, 1)},
    {"bbox": (0, 0, float("nan"), 1)}, {"bbox": (0, 0, 1)},
    {"start": "2026-01-01"}, {"start": "2027-01-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"},
    {"dataset_version": "v1"}, {"data_kind": "invalid"}, {"scenario_type": "invalid"},
])
def test_invalid_query_filters(session, kwargs):
    with pytest.raises(ValueError):
        PublishedScenarioRepository(session).list(data_mode="demo", **kwargs)


@pytest.mark.parametrize("change", ["crs", "unit", "nodata", "alignment", "negative", "infinite", "not-tiff", "empty", "coverage"])
def test_bad_raster_content_cannot_register(session, tmp_path, change):
    item, store, root = prepared(session, tmp_path)
    coverage = item.time_coverage.model_dump(mode="json")
    value, unit, crs, nodata, transform = 0.5, "m", "EPSG:32643", -9999, GRID
    if change == "crs":
        crs = "EPSG:32644"
    elif change == "unit":
        unit = "cm"
    elif change == "nodata":
        nodata = -1
    elif change == "alignment":
        transform = GRID * GRID.translation(1, 0)
    elif change == "negative":
        value = -0.5
    elif change == "infinite":
        value = float("inf")
    elif change == "empty":
        value = nodata
    elif change == "coverage":
        coverage["start"] = "2026-01-01T01:00:00Z"
    content = b"not a TIFF" if change == "not-tiff" else cog_bytes(value, unit, coverage, crs=crs, nodata=nodata, transform=transform)
    replace_asset(item, store, root, "max_depth_cog", content)
    with pytest.raises(ValueError):
        register(session, item, store, root)
    assert session.scalars(select(Scenario)).all() == []
    assert session.scalars(select(AssetSpatialMetadata)).all() == []


@pytest.mark.parametrize("geometry", [
    {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]},
    {"type": "Point", "coordinates": [1, 1]},
    {"type": "Polygon", "coordinates": [[[181, 0], [182, 0], [182, 1], [181, 0]]]},
    mapping(box(0, 0, 1, 1)),
])
def test_invalid_or_outside_extent_rejected(session, tmp_path, geometry):
    item, store, root = prepared(session, tmp_path)
    content = json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": geometry}]}).encode()
    replace_asset(item, store, root, "extent_geojson", content)
    with pytest.raises(ValueError):
        register(session, item, store, root)


def test_actual_extent_intersection_not_just_bbox(session, tmp_path):
    item, store, root = prepared(session, tmp_path)
    original = json.loads(store.resolve_uri(root + item.assets["extent_geojson"]).read_text())
    outer = shape(original["features"][0]["geometry"])
    west, south, east, north = outer.bounds
    hole = box(west + (east-west)*0.4, south + (north-south)*0.4, west + (east-west)*0.6, south + (north-south)*0.6)
    original["features"][0]["geometry"] = mapping(outer.difference(hole))
    replace_asset(item, store, root, "extent_geojson", json.dumps(original).encode())
    register(session, item, store, root)
    small = (west + (east-west)*0.45, south + (north-south)*0.45, west + (east-west)*0.55, south + (north-south)*0.55)
    assert PublishedScenarioRepository(session).list(data_mode="demo", bbox=small) == []


def test_gist_indexes_and_database_geometry_integrity(session, isolated_database, tmp_path):
    item, store, root = prepared(session, tmp_path)
    register(session, item, store, root)
    engine, _ = isolated_database
    with engine.connect() as connection:
        indexes = connection.execute(text("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname=current_schema() AND indexname IN ('ix_asset_spatial_geom','ix_scenario_spatial_geom')")).all()
        assert len(indexes) == 2 and all("USING gist" in row.indexdef for row in indexes)
    row = session.scalar(select(ScenarioSpatialMetadata))
    invalid = MultiPolygon([Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)])])
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            row.geom = from_shape(invalid, srid=4326)
            session.flush()


def test_real_draft_has_no_approved_spatial_reads(session, tmp_path):
    item, store, root = prepared(session, tmp_path, status="draft")
    register(session, item, store, root)
    assert len(session.scalars(select(AssetSpatialMetadata)).all()) == 4
    assert PublishedScenarioRepository(session).footprint(item.scenario_id, data_mode="demo") is None


def test_gis_fixture_generation_is_idempotent(tmp_path):
    store = LocalObjectStore(tmp_path)
    first = build_fixture(store)
    assert build_fixture(store)[0].model_dump() == first[0].model_dump()


def test_legacy_admin_filters_and_status_scope(session, tmp_path):
    from services.api.app.repositories.scenario_repository import ScenarioRepository
    from services.api.app.repositories.run_repository import RunRepository
    from services.api.app.repositories.asset_repository import AssetRepository
    from services.api.app.repositories.status_repository import StatusRepository
    item, store, root = prepared(session, tmp_path)
    register(session, item, store, root)
    scenarios = ScenarioRepository(session)
    assert scenarios.list(status="completed", data_mode="demo", model_version=item.model_version)[0].scenario_id == item.scenario_id
    assert scenarios.list(status="failed") == []
    assert scenarios.list(offset=1) == []
    assert RunRepository(session).list_for_scenario(item.scenario_id, status="completed", stage="precomputed_import")[0].run_id == item.run_id
    assert RunRepository(session).list_for_scenario(item.scenario_id, status="running") == []
    assert len(AssetRepository(session).list_for_scenario(item.scenario_id, run_id=item.run_id, format="cog", limit=2)) == 2
    statuses = StatusRepository(session)
    statuses.add(reading_time=item.time_coverage.start, data_mode="demo", reservoir_level_m=1.0)
    statuses.add(reading_time=item.time_coverage.end, data_mode="production", reservoir_level_m=2.0)
    assert statuses.latest(data_mode="demo").reservoir_level_m == 1.0
    assert statuses.latest(data_mode="production").reservoir_level_m == 2.0
    assert statuses.list(data_mode="demo", start=item.time_coverage.end) == []
    with pytest.raises(ValueError):
        statuses.list(start="2026-01-01")


def test_metric_and_event_query_windows(session):
    from test_catalogs import catalog, metric
    from services.api.app.repositories.catalog_repository import ValidationMetricRepository, HistoricalEventRepository
    catalog(session)
    metrics = ValidationMetricRepository(session)
    row = metrics.register(metric())
    assert metrics.list(data_mode="demo", start=row.computed_at, end=row.computed_at)[0].id == row.id
    assert metrics.list(data_mode="production") == []
    assert metrics.list(run_id="unknown") == []
    assert metrics.list(end="1999-01-01T00:00:00Z") == []
    for repo in (metrics, HistoricalEventRepository(session)):
        with pytest.raises(ValueError):
            repo.list(start="2001-01-01T00:00:00Z", end="2000-01-01T00:00:00Z")


def test_geometry_registration_rolls_back_with_caller(session, tmp_path):
    item, store, root = prepared(session, tmp_path)
    register(session, item, store, root)
    session.rollback()
    assert session.scalars(select(AssetSpatialMetadata)).all() == []
    assert session.scalars(select(ScenarioSpatialMetadata)).all() == []


def test_bounded_content_inspection(session, tmp_path):
    item, store, root = prepared(session, tmp_path)
    path = store.resolve_uri(root + item.assets["max_depth_cog"])
    with pytest.raises(ValueError, match="bounded"):
        GISInspector(max_pixels=1)(path, "max_depth_cog", item.asset_metadata["max_depth_cog"])
    vector = store.resolve_uri(root + item.assets["extent_geojson"])
    with pytest.raises(ValueError, match="size limit"):
        GISInspector(max_vector_bytes=1)(vector, "extent_geojson", item.asset_metadata["extent_geojson"])


def test_plain_large_geotiff_is_not_accepted_as_cog(session, tmp_path):
    import numpy as np
    from rasterio.io import MemoryFile
    item, store, root = prepared(session, tmp_path)
    with MemoryFile() as memory:
        with memory.open(driver="GTiff", width=1024, height=1024, count=1, dtype="float32", crs="EPSG:32643", transform=GRID, nodata=-9999) as dataset:
            dataset.write(np.ones((1024, 1024), dtype="float32"), 1)
        content = memory.read()
    replace_asset(item, store, root, "max_depth_cog", content)
    with pytest.raises(ValueError, match="COG structure"):
        register(session, item, store, root)


def test_production_cannot_relabel_tagged_synthetic_assets(session, tmp_path):
    from services.api.app.db.models import Dataset
    item, store, root = prepared(session, tmp_path)
    parent = session.scalar(select(Dataset))
    parent.data_mode = "production"
    source = DatasetRepository(session).get_version(item.datasets[0].dataset_id, item.datasets[0].version)
    source.source_label = "observed"
    item.datasets[0].source_label = "observed"
    item.data_mode, item.data_kind = "production", "simulated"
    session.flush()
    with pytest.raises(ValueError, match="synthetic GIS"):
        register(session, item, store, root)


def test_default_cli_uses_real_gis_checks(session, isolated_database, tmp_path):
    import os
    import subprocess
    import sys
    from services.api.app.db.models import PublicationAction, PublishedBundle, ScenarioDatasetVersion, ResultAsset, ImpactSummary, ProcessingRun, DatasetVersion, Dataset
    engine, _ = isolated_database
    item, store, root = prepared(session, tmp_path)
    session.commit()
    manifest_file = tmp_path / "gis-manifest.json"
    manifest_file.write_text(item.model_dump_json(), encoding="utf-8")
    args = [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/register_published_bundle.py"), str(manifest_file), "--bundle-root", root, "--registered-by", "local-test", "--trusted-approver", "synthetic-fixture-reviewer"]
    try:
        result = subprocess.run(args, cwd=Path(__file__).resolve().parents[1], env=dict(os.environ, OBJECT_STORAGE_ROOT=str(store.root)), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        session.expire_all()
        assert len(PublishedScenarioRepository(session).spatial_assets(item.scenario_id, data_mode="demo")) == 4
    finally:
        session.rollback()
        # This engine addresses only the generated disposable schema.
        with engine.begin() as connection:
            for table in ("scenario_spatial_metadata", "asset_spatial_metadata", "publication_actions", "published_bundles", "scenario_dataset_versions", "result_assets", "impact_summaries", "processing_runs", "scenarios", "dataset_versions", "datasets"):
                connection.execute(text(f'DELETE FROM "{table}"'))


def test_stale_spatial_source_hash_fails_closed(session, tmp_path):
    item, store, root = prepared(session, tmp_path)
    register(session, item, store, root)
    row = session.scalar(select(ScenarioSpatialMetadata))
    bounds = to_shape(row.geom).bounds
    row.source_checksum = "sha256:" + "0" * 64
    session.flush()
    repo = PublishedScenarioRepository(session)
    assert repo.footprint(item.scenario_id, data_mode="demo") is None
    assert repo.list(data_mode="demo", bbox=bounds) == []
    metadata = session.scalars(select(AssetSpatialMetadata)).all()
    for asset in metadata:
        asset.source_checksum = "sha256:" + "0" * 64
    session.flush()
    assert repo.spatial_assets(item.scenario_id, data_mode="demo") == []


def test_readonly_gis_validation_cli(session, tmp_path):
    import os
    import subprocess
    import sys
    item, store, root = prepared(session, tmp_path, status="draft")
    manifest_file = tmp_path / "readonly-manifest.json"
    manifest_file.write_text(item.model_dump_json(), encoding="utf-8")
    project = Path(__file__).resolve().parents[1]
    args = [sys.executable, str(project / "scripts/validate_gis_bundle.py"), str(manifest_file), "--bundle-root", root]
    env = dict(os.environ, OBJECT_STORAGE_ROOT=str(store.root))
    result = subprocess.run(args, cwd=project, env=env, capture_output=True, text=True)
    assert result.returncode == 0 and "status=draft" in result.stdout
    assert "no database writes" in result.stdout
    assert session.scalars(select(Scenario)).all() == []
    replace_asset(item, store, root, "max_depth_cog", b"not a TIFF")
    manifest_file.write_text(item.model_dump_json(), encoding="utf-8")
    assert subprocess.run(args, cwd=project, env=env, capture_output=True, text=True).returncode == 1
