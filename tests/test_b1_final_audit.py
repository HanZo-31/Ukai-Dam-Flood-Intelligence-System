"""Final audit regressions; synthetic files and disposable schemas only."""
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from test_b1_integration import isolated_database, session
from test_gis_catalog import prepared, replace_asset, register
from test_catalogs import dataset, version, event
from scripts.demo_seed import build_demo
from services.api.app.db.models import Scenario, ResultAsset
from services.api.app.gis_validation import GISInspector
from services.api.app.manifest_registry import register_manifest
from services.api.app.repositories.catalog_repository import DatasetRepository, HistoricalEventRepository
from services.api.app.result_registration import CompletedBundle, complete_run, start_run, fail_run
from services.api.app.storage import LocalObjectStore


def test_mutated_legacy_manifest_cannot_write_invalid_mode(session, tmp_path):
    store = LocalObjectStore(tmp_path)
    item, _ = build_demo(store)
    item.data_mode = "invalid"
    with pytest.raises(ValidationError):
        register_manifest(session, item, store)
    assert session.scalars(select(Scenario)).all() == []
    assert not store.path_for_key(f"scenarios/{item.scenario_id}/manifest.json").exists()


def test_mutated_completion_cannot_persist_negative_impact(session, tmp_path):
    store = LocalObjectStore(tmp_path)
    item, bundle = build_demo(store)
    scenario = register_manifest(session, item, store)
    run = start_run(session, scenario.scenario_id, bundle.run_id)
    bundle.impact.max_depth_m = -1.0
    with pytest.raises(ValidationError):
        complete_run(session, bundle, store)
    assert run.status == scenario.status == "running"
    assert session.scalars(select(ResultAsset)).all() == []


@pytest.mark.parametrize("target", ["version", "event"])
def test_catalog_revalidates_mutated_nested_time_coverage(session, target):
    repo = DatasetRepository(session)
    repo.register(dataset())
    item = version() if target == "version" else event()
    item.time_coverage.end = item.time_coverage.start.replace(year=1999)
    with pytest.raises(ValidationError):
        (repo.register_version if target == "version" else HistoricalEventRepository(session).register)(item)


@pytest.mark.parametrize("marker", ["feature", "properties"])
def test_feature_level_synthetic_flag_is_detected(session, tmp_path, marker):
    item, store, root = prepared(session, tmp_path)
    payload = json.loads(store.resolve_uri(root + item.assets["extent_geojson"]).read_text())
    payload.pop("synthetic")
    feature = payload["features"][0]
    feature["properties"] = {}
    (feature if marker == "feature" else feature["properties"])["synthetic"] = True
    replace_asset(item, store, root, "extent_geojson", json.dumps(payload).encode())
    inspection = GISInspector()(store.resolve_uri(item.assets["extent_geojson"]), "extent_geojson", item.asset_metadata["extent_geojson"])
    assert inspection.synthetic is True


def test_source_package_excludes_nested_private_configuration(tmp_path, monkeypatch):
    from scripts.rehearse_b1_handoff import source_package
    source = tmp_path / "project"
    source.mkdir()
    for name in ("database", "services", "scripts", "tests", "docs"):
        (source / name).mkdir()
        (source / name / "safe.py").write_text("# synthetic source")
        (source / name / ".env").write_text("SYNTHETIC_PRIVATE_VALUE=not-a-real-secret")
        (source / name / ".env.local").write_text("synthetic private config")
    for name in ("README.md", "requirements.txt", "compose.yaml", "alembic.ini", "pytest.ini", ".env.example"):
        (source / name).write_text("synthetic example")
    monkeypatch.setattr("scripts.rehearse_b1_handoff.ROOT", source)
    inventory = source_package(tmp_path / "package")
    assert ".env.example" in inventory
    assert not any(key.endswith(("/.env", "/.env.local")) for key in inventory)


def test_completion_accepts_full_supported_run_id(session, tmp_path):
    store = LocalObjectStore(tmp_path)
    item, bundle = build_demo(store)
    bundle.run_id = "r" * 150
    bundle = CompletedBundle.model_validate(bundle.model_dump())
    scenario = register_manifest(session, item, store)
    start_run(session, scenario.scenario_id, bundle.run_id)
    assert complete_run(session, bundle, store).status == "completed"


def test_completion_savepoint_prevents_partial_writes_when_error_is_caught(session, tmp_path, monkeypatch):
    from services.api.app.repositories.impact_repository import ImpactRepository
    store = LocalObjectStore(tmp_path)
    item, bundle = build_demo(store)
    scenario = register_manifest(session, item, store)
    run = start_run(session, scenario.scenario_id, bundle.run_id)
    def late_failure(*args, **kwargs):
        raise RuntimeError("synthetic late failure")
    monkeypatch.setattr(ImpactRepository, "upsert", late_failure)
    with pytest.raises(RuntimeError, match="late failure"):
        complete_run(session, bundle, store)
    assert session.scalars(select(ResultAsset)).all() == []
    assert run.status == scenario.status == "running"
    session.flush()


def test_fail_run_rejects_inconsistent_scenario_state(session, tmp_path):
    store = LocalObjectStore(tmp_path)
    item, bundle = build_demo(store)
    scenario = register_manifest(session, item, store)
    run = start_run(session, scenario.scenario_id, bundle.run_id)
    scenario.status = "registered"
    session.flush()
    with pytest.raises(ValueError, match="scenario must be running"):
        fail_run(session, run.run_id, "SYNTHETIC")
    assert run.status == "running"


def test_internal_cli_does_not_echo_sensitive_invalid_values(session, tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    sentinel = "SYNTHETIC_PRIVATE_SENTINEL"
    payload = {"run_id": "test", "assets": [{"asset_type": "depth", "storage_uri": "s3://user:" + sentinel + "@bucket/key", "checksum": "sha256:" + "0" * 64}], "impact": {}}
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload))
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(project / "scripts/run_contract.py"), "complete", str(path)], cwd=project, env=dict(os.environ), capture_output=True, text=True)
    assert result.returncode == 1
    assert sentinel not in result.stdout + result.stderr


@pytest.mark.parametrize("linked_name", ["docs", ".env.example"])
def test_source_package_refuses_linked_allowlist_targets(tmp_path, monkeypatch, linked_name):
    from pathlib import Path
    from scripts.rehearse_b1_handoff import source_package, ROOT
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == ROOT / linked_name or original(path))
    with pytest.raises(ValueError, match="refuses symlinks"):
        source_package(tmp_path / "source")
