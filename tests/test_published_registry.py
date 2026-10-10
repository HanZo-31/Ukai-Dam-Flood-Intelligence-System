"""Local metadata/hash integration fixtures, deliberately not real GIS results."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from test_b1_integration import isolated_database, session, manifest as legacy_manifest
from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate, HistoricalEventCreate
from services.api.app.db.models import Scenario, ProcessingRun, ResultAsset, ImpactSummary, PublishedBundle, ScenarioDatasetVersion, PublicationAction
from services.api.app.published_contract import PublishedScenarioManifest
from services.api.app.published_registry import register_published_bundle
from services.api.app.repositories.catalog_repository import DatasetRepository, HistoricalEventRepository
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.repositories.scenario_repository import ScenarioRepository
from services.api.app.storage import LocalObjectStore

ROOT = Path(__file__).resolve().parents[1]
TRUSTED = {"synthetic-fixture-reviewer"}


def bundle(session, tmp_path, *, status="approved", data_mode="demo", event=False):
    payload = json.loads((ROOT / "docs/contracts/examples/published-scenario-demo.json").read_text())
    payload["status"] = status
    payload["data_mode"] = data_mode
    payload["data_kind"] = "demo" if data_mode == "demo" else "simulated"
    if status != "approved":
        payload["quality"].update(approved_by=None, approved_at=None, validation_status="pending" if status == "draft" else "fail")
    payload["summary"].update(roads_affected_km=0.3, critical_facilities_exposed=2)
    store = LocalObjectStore(tmp_path / "objects")
    for role, reference in payload["assets"].items():
        # Bytes exist and hashes are real, but TIFFs are NOT scientific fixtures.
        content = (f"Synthetic non-GIS test bytes for {role}\n").encode()
        _, checksum = store.put(reference, content)
        payload["asset_metadata"][role]["checksum"] = checksum
    _, payload["assumptions_checksum"] = store.put(payload["assumptions_url"], b"Synthetic assumptions; not scientific approval.\n")
    _, payload["quality"]["report_checksum"] = store.put(payload["quality"]["report_reference"], b'{"synthetic":true}')
    datasets = DatasetRepository(session)
    for item in payload["datasets"]:
        item["source_label"] = "demo" if data_mode == "demo" else "observed"
        uri, item["checksum"] = store.put(item["source_reference"], b"time,value\n0,1\n")
        datasets.register(DatasetCreate(dataset_id=item["dataset_id"], name="Synthetic input", description="Registry test only", data_mode=data_mode))
        version = dict(item, source_reference=uri)
        datasets.register_version(DatasetVersionCreate.model_validate(version))
    if event:
        payload["historical_event_id"] = "synthetic-event"
        payload["scenario_type"] = "historical_replay"
        events = HistoricalEventRepository(session)
        events.register(HistoricalEventCreate(event_id="synthetic-event", name="Synthetic event", time_coverage=payload["time_coverage"], observed_coverage="Test only", quality_notes="No observed event claimed", source_urls=["https://example.org/synthetic"], data_mode=data_mode))
        for item in payload["datasets"]:
            events.link_dataset("synthetic-event", item["dataset_id"], item["version"])
    return PublishedScenarioManifest.model_validate(payload), store


def register(session, manifest, store, **kwargs):
    return register_published_bundle(session, manifest, store, bundle_root_uri=store.root.as_uri() + "/", registered_by="test-operator", trusted_approvers=TRUSTED, **kwargs)


def test_complete_snapshot_and_approved_reads(session, tmp_path):
    item, store = bundle(session, tmp_path)
    row = register(session, item, store)
    assert row.manifest_checksum.startswith("sha256:")
    assert row.manifest_json == item.model_dump(mode="json")
    repo = PublishedScenarioRepository(session)
    scenario = repo.get(item.scenario_id, data_mode="demo")
    assert scenario.status == "completed" and scenario.publication_status == "approved"
    assert scenario.parameter_units == item.parameter_units.model_dump()
    assert scenario.assumptions_checksum == item.assumptions_checksum
    assert scenario.coverage_start == item.time_coverage.start
    run = session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == item.run_id))
    assert run.stage == "precomputed_import" and run.started_at is None
    assert run.run_timestamp == item.run_timestamp == run.completed_at
    assert run.approved_by == item.quality.approved_by and run.validation_status == "pass"
    assert len(repo.assets(item.scenario_id, data_mode="demo")) == 4
    depth = next(a for a in repo.assets(item.scenario_id, data_mode="demo") if a.asset_type == "max_depth_cog")
    assert depth.unit == "m" and depth.format == "cog" and depth.nodata == -9999
    assert depth.run_id == item.run_id and depth.coverage_end == item.time_coverage.end
    summary = repo.summary(item.scenario_id, data_mode="demo")
    assert summary.population_exposed is None and summary.roads_affected_km == 0.3
    assert summary.critical_facilities_exposed == 2
    assert repo.datasets(item.scenario_id, data_mode="demo")[0].version == "1.0.0"
    assert len(repo.list(data_mode="demo", scenario_type="hypothetical", limit=1)) == 1
    assert repo.list(data_mode="demo", offset=1) == []
    assert repo.list(data_mode="demo", historical_event_id="missing") == []
    assert repo.get(item.scenario_id, data_mode="production") is None
    assert repo.assets(item.scenario_id, data_mode="production") == []


@pytest.mark.parametrize("status", ["draft", "rejected"])
def test_unapproved_records_are_hidden_for_every_accessor(session, tmp_path, status):
    item, store = bundle(session, tmp_path, status=status)
    register(session, item, store)
    repo = PublishedScenarioRepository(session)
    assert repo.list(data_mode="demo") == []
    assert repo.get(item.scenario_id, data_mode="demo") is None
    assert repo.assets(item.scenario_id, data_mode="demo") == []
    assert repo.summary(item.scenario_id, data_mode="demo") is None
    assert repo.datasets(item.scenario_id, data_mode="demo") == []


def test_legacy_completed_scenario_is_not_publication_approval(session):
    scenario = ScenarioRepository(session).register(legacy_manifest())
    scenario.status = "completed"
    scenario.publication_status = "approved"  # No verified bundle: still hidden.
    session.flush()
    assert PublishedScenarioRepository(session).get(scenario.scenario_id, data_mode="demo") is None


def test_explicit_approval_trust_required(session, tmp_path):
    item, store = bundle(session, tmp_path)
    with pytest.raises(ValueError, match="trusted approver"):
        register_published_bundle(session, item, store, bundle_root_uri=store.root.as_uri() + "/", registered_by="test")
    assert session.scalars(select(Scenario)).all() == []
    with pytest.raises(ValueError, match="collection"):
        register_published_bundle(session, item, store, bundle_root_uri=store.root.as_uri() + "/", registered_by="test", trusted_approvers="prefix-synthetic-fixture-reviewer-suffix")


def test_production_requires_content_inspection(session, tmp_path):
    item, store = bundle(session, tmp_path, data_mode="production")
    with pytest.raises(ValueError, match="GIS content verifier"):
        register(session, item, store)
    calls = []
    # Test the injected boundary, not actual production/GIS validation.
    with pytest.raises(ValueError, match="structured GIS"):
        register(session, item, store, asset_inspector=lambda path, role, metadata: calls.append(role))
    assert calls
    assert PublishedScenarioRepository(session).list(data_mode="production") == []


@pytest.mark.parametrize("target", ["asset", "dataset", "assumptions", "report"])
def test_bad_checksum_registers_nothing(session, tmp_path, target):
    item, store = bundle(session, tmp_path)
    bad = "sha256:" + "0" * 64
    if target == "asset":
        item.asset_metadata["max_depth_cog"].checksum = bad
    elif target == "dataset":
        item.datasets[0].checksum = bad
    elif target == "assumptions":
        item.assumptions_checksum = bad
    else:
        item.quality.report_checksum = bad
    with pytest.raises(ValueError, match="checksum mismatch"):
        register(session, item, store)
    for model in (Scenario, ProcessingRun, ResultAsset, ImpactSummary, PublishedBundle, ScenarioDatasetVersion, PublicationAction):
        assert session.scalars(select(model)).all() == []


def test_registered_provenance_must_match(session, tmp_path):
    item, store = bundle(session, tmp_path)
    item.datasets[0].license = "Different licence"
    with pytest.raises(ValueError, match="provenance differs"):
        register(session, item, store)


def test_missing_file_rejected(session, tmp_path):
    item, store = bundle(session, tmp_path)
    item.assets["max_depth_cog"] = "missing.tif"
    with pytest.raises(ValueError, match="does not exist"):
        register(session, item, store)


def test_storage_root_and_resolved_asset_aliases(session, tmp_path):
    item, store = bundle(session, tmp_path)
    with pytest.raises(ValueError, match="outside"):
        register_published_bundle(session, item, store, bundle_root_uri=tmp_path.as_uri() + "/", registered_by="test", trusted_approvers=TRUSTED)
    item.assets["max_velocity_cog"] = store.path_for_key(item.assets["max_depth_cog"]).as_uri()
    item.asset_metadata["max_velocity_cog"].checksum = item.asset_metadata["max_depth_cog"].checksum
    with pytest.raises(ValueError, match="same object"):
        register(session, item, store)


def test_duplicate_import_is_rejected(session, tmp_path):
    item, store = bundle(session, tmp_path)
    register(session, item, store)
    with pytest.raises(ValueError, match="already exists"):
        register(session, item, store)
    assert len(session.scalars(select(PublishedBundle)).all()) == 1
    item.scenario_id = "other-scenario"
    with pytest.raises(ValueError, match="run already exists"):
        register(session, item, store)


def test_inspection_failure_registers_nothing(session, tmp_path):
    item, store = bundle(session, tmp_path)
    def fail(*args):
        raise ValueError("bad GIS content")
    with pytest.raises(ValueError, match="bad GIS"):
        register(session, item, store, asset_inspector=fail)
    assert session.scalars(select(Scenario)).all() == []


def test_late_database_failure_rolls_back_savepoint(session, tmp_path, monkeypatch):
    import services.api.app.published_registry as registry
    item, store = bundle(session, tmp_path)
    original = registry.PublishedBundle
    def invalid_row(**values):
        values["manifest_checksum"] = "bad"
        return original(**values)
    monkeypatch.setattr(registry, "PublishedBundle", invalid_row)
    with pytest.raises(IntegrityError):
        register(session, item, store)
    for model in (Scenario, ProcessingRun, ResultAsset, ImpactSummary, PublishedBundle, ScenarioDatasetVersion, PublicationAction):
        assert session.scalars(select(model)).all() == []
    # Caller may recover and commit unrelated work: the import stays absent.
    assert DatasetRepository(session).get("synthetic-input-001") is not None


def test_caller_rollback_removes_successful_import(session, tmp_path):
    item, store = bundle(session, tmp_path)
    register(session, item, store)
    session.rollback()
    assert session.scalars(select(PublishedBundle)).all() == []
    assert session.scalars(select(Scenario)).all() == []


def test_historical_replay_requires_catalog_and_links(session, tmp_path):
    item, store = bundle(session, tmp_path, event=True)
    register(session, item, store)
    repo = PublishedScenarioRepository(session)
    assert repo.list(data_mode="demo", historical_event_id="synthetic-event")[0].scenario_id == item.scenario_id


def test_missing_event_and_event_version_link(session, tmp_path):
    item, store = bundle(session, tmp_path, event=True)
    session.execute(text("DELETE FROM historical_event_datasets"))
    with pytest.raises(ValueError, match="explicitly link"):
        register(session, item, store)
    session.execute(text("DELETE FROM historical_events"))
    with pytest.raises(ValueError, match="historical event must exist"):
        register(session, item, store)


def test_revoke_hides_all_accessors_and_preserves_snapshot(session, tmp_path):
    item, store = bundle(session, tmp_path)
    row = register(session, item, store)
    original_checksum = row.manifest_checksum
    repo = PublishedScenarioRepository(session)
    repo.revoke(item.scenario_id, actor="test-admin", reason="Synthetic withdrawal")
    assert repo.list(data_mode="demo") == []
    assert repo.assets(item.scenario_id, data_mode="demo") == []
    assert repo.summary(item.scenario_id, data_mode="demo") is None
    assert row.manifest_checksum == original_checksum and row.manifest_json["status"] == "approved"
    assert len(session.scalars(select(PublicationAction)).all()) == 2
    with pytest.raises(ValueError, match="only an approved"):
        repo.revoke(item.scenario_id, actor="test-admin", reason="Repeat")


@pytest.mark.parametrize("field,value", [("validation_status", "fail"), ("status", "failed"), ("approved_by", None)])
def test_read_gate_defends_against_incomplete_run_metadata(session, tmp_path, field, value):
    item, store = bundle(session, tmp_path)
    register(session, item, store)
    run = session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == item.run_id))
    # Remove approval time for writes that would rightly violate the DB check.
    if field in {"validation_status", "approved_by"}:
        run.approved_at = None
        run.approved_by = None
    setattr(run, field, value)
    session.flush()
    assert PublishedScenarioRepository(session).list(data_mode="demo") == []


@pytest.mark.parametrize("kwargs", [{"data_mode": None}, {"data_mode": "unknown"}, {"data_mode": "demo", "limit": 0}, {"data_mode": "demo", "offset": -1}])
def test_approved_queries_require_valid_scope(session, kwargs):
    with pytest.raises(ValueError):
        PublishedScenarioRepository(session).list(**kwargs)


def test_manifest_run_id_full_supported_length(session, tmp_path):
    item, store = bundle(session, tmp_path)
    item.run_id = "r" * 150
    assert register(session, item, store).run_id == item.run_id


def test_metadata_check_constraints_are_installed(isolated_database):
    engine, _ = isolated_database
    inspector = inspect(engine)
    for table, names in (("processing_runs", {"ck_run_approval", "ck_run_validation"}), ("scenarios", {"ck_scenario_publication_status", "ck_scenario_coverage"}), ("result_assets", {"ck_asset_coverage", "ck_asset_nodata"}), ("impact_summaries", {"ck_impact_roads", "ck_impact_facilities"})):
        assert names <= {c["name"] for c in inspector.get_check_constraints(table)}


def test_new_revision_roundtrip_preserves_old_metadata(isolated_database):
    engine, config = isolated_database
    command.downgrade(config, "d02c3e4b1001")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO scenarios (scenario_id,scenario_type,status,model_version,input_dataset_version,crs,parameters,data_mode) VALUES ('old-metadata','demo','completed','old-v1','inputs-v1','EPSG:4326','{}','demo')"))
        before = connection.execute(text("SELECT row_to_json(s) FROM scenarios s WHERE scenario_id='old-metadata'")).scalar_one()
    try:
        command.upgrade(config, "head")
        command.check(config)
        with engine.connect() as connection:
            after = connection.execute(text("SELECT row_to_json(s) FROM scenarios s WHERE scenario_id='old-metadata'")).scalar_one()
            assert {key: after[key] for key in before} == before
            assert after["publication_status"] is None
        command.downgrade(config, "d02c3e4b1001")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT row_to_json(s) FROM scenarios s WHERE scenario_id='old-metadata'")).scalar_one() == before
        command.upgrade(config, "head")
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM scenarios WHERE scenario_id='old-metadata'"))


def test_cli_registration_and_duplicate_failure(session, isolated_database, tmp_path):
    engine, _ = isolated_database
    item, store = bundle(session, tmp_path)
    session.commit()  # CLI is another process and must see the provenance rows.
    manifest_file = tmp_path / "published.json"
    manifest_file.write_text(item.model_dump_json(), encoding="utf-8")
    args = [sys.executable, str(ROOT / "scripts/register_published_bundle.py"), str(manifest_file), "--bundle-root", store.root.as_uri() + "/", "--registered-by", "test-operator", "--trusted-approver", "synthetic-fixture-reviewer", "--metadata-only-demo"]
    env = dict(os.environ, OBJECT_STORAGE_ROOT=str(store.root))
    try:
        result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        duplicate = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
        assert duplicate.returncode == 1 and "rolled back" not in duplicate.stdout
        session.expire_all()
        repo = PublishedScenarioRepository(session)
        assert repo.get(item.scenario_id, data_mode="demo") is not None
        assert len(repo.assets(item.scenario_id, data_mode="demo")) == 4
    finally:
        session.rollback()
        with engine.begin() as connection:
            for table in ("publication_actions", "published_bundles", "scenario_dataset_versions", "result_assets", "impact_summaries", "processing_runs", "scenarios", "dataset_versions", "datasets"):
                connection.execute(text(f'DELETE FROM "{table}"'))


def test_downgrade_refuses_to_truncate_long_run_id(isolated_database):
    engine, config = isolated_database
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO scenarios (scenario_id,scenario_type,status,model_version,input_dataset_version,crs,parameters,data_mode) VALUES ('length-test','demo','completed','v1','v1','EPSG:4326','{}','demo')"))
        connection.execute(text("INSERT INTO processing_runs (scenario_id,run_id,stage,status,metadata_json) VALUES ('length-test',:run,'test','completed','{}')"), {"run": "r" * 150})
    try:
        with pytest.raises(RuntimeError, match="longer than 100"):
            command.downgrade(config, "d02c3e4b1001")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM processing_runs WHERE scenario_id='length-test'"))
            connection.execute(text("DELETE FROM scenarios WHERE scenario_id='length-test'"))


def test_populated_bundle_backup_and_restore(isolated_database, tmp_path, monkeypatch):
    """Real pg_dump/pg_restore with registered synthetic bundles, never public data."""
    from scripts.backup_db import backup, restore_check
    _, config = isolated_database
    original_url = make_url(os.environ["DATABASE_URL"])
    name = "b1_pub_drill_" + uuid.uuid4().hex
    assert name.startswith("b1_pub_drill_") and len(name) == 45
    admin = create_engine(original_url, isolation_level="AUTOCOMMIT")
    target = original_url.set(database=name).update_query_dict({"options": "-csearch_path=public"})
    engine = None
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
            created = True
        engine = create_engine(target)
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION postgis"))
        monkeypatch.setenv("DATABASE_URL", target.render_as_string(hide_password=False))
        command.upgrade(config, "head")
        with Session(engine) as writer, writer.begin():
            from test_gis_catalog import prepared as gis_prepared, register as gis_register
            item, store, bundle_root = gis_prepared(writer, tmp_path)
            gis_register(writer, item, store, bundle_root)
        monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(store.root))
        destination = backup(tmp_path / "populated-backup")
        restore_check(destination)
        report = json.loads((destination / "restore-check.json").read_text())
        assert report["restored_tables"]["published_bundles"]["rows"] == 1
        assert report["restored_tables"]["scenario_dataset_versions"]["rows"] == 1
        assert report["restored_tables"]["publication_actions"]["rows"] == 1
        assert report["restored_tables"]["asset_spatial_metadata"]["rows"] == 4
        assert report["restored_tables"]["scenario_spatial_metadata"]["rows"] == 1
        assert report["local_references_verified"] == 7
        assert report["postgis_verified"] is True
        assert report["unresolved_external_references"] == []
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


@pytest.mark.parametrize("field,value", [("validation_status", None), ("approved_by", ""), ("approved_by", None), ("approved_at", None)])
def test_database_rejects_incomplete_approval(session, tmp_path, field, value):
    item, store = bundle(session, tmp_path)
    register(session, item, store)
    run = session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == item.run_id))
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            setattr(run, field, value)
            session.flush()
