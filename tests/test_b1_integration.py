"""B1 verification; all writes use a uniquely named disposable schema."""
import json
import os
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from services.api.app.db.models import Scenario, ScenarioInput, ProcessingRun
from services.api.app.repositories.scenario_repository import ScenarioRepository
from services.api.app.repositories.asset_repository import AssetRepository
from services.api.app.repositories.impact_repository import ImpactRepository
from services.api.app.repositories.status_repository import StatusRepository
from services.api.app.repositories.run_repository import RunRepository
from services.api.app.schemas import ScenarioManifest


@pytest.fixture(scope="module")
def isolated_database():
    schema = "b1_verify_" + uuid.uuid4().hex
    assert schema.startswith("b1_verify_") and len(schema) == 42
    original_url = os.environ["DATABASE_URL"]
    connection_url = make_url(original_url)
    if connection_url.host == "localhost":
        connection_url = connection_url.set(host="127.0.0.1")
    connection_url = connection_url.update_query_dict({"connect_timeout": "5"})
    admin = create_engine(connection_url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        # Shadow the public version table before exposing extension functions.
        connection.execute(text(f'CREATE TABLE "{schema}".alembic_version (version_num varchar(32) PRIMARY KEY)'))
    url = connection_url.update_query_dict({"options": f"-csearch_path={schema},public"})
    engine = create_engine(url)
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    config = Config(str(ROOT / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        yield engine, config
    finally:
        os.environ["DATABASE_URL"] = original_url
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def session(isolated_database):
    engine, _ = isolated_database
    with Session(engine) as session:
        yield session
        session.rollback()


def manifest():
    return ScenarioManifest.model_validate_json((ROOT / "tests/fixtures/scenario_manifest.json").read_text())


def test_registration_duplicate_and_rollback(session, isolated_database):
    repo = ScenarioRepository(session)
    item = repo.register(manifest())
    assert item.status == "registered"
    assert len(session.scalars(select(ScenarioInput)).all()) == 1
    with pytest.raises(ValueError, match="already exists"):
        repo.register(manifest())
    session.rollback()
    assert repo.get(item.scenario_id) is None


def test_repository_output_and_run_lifecycle(session):
    scenario = ScenarioRepository(session).register(manifest())
    assets = AssetRepository(session)
    asset = assets.add(scenario_id=scenario.scenario_id, asset_type="depth", storage_uri="s3://test/depth.tif", data_mode="demo")
    assert assets.list_for_scenario(scenario.scenario_id)[0].id == asset.id
    impacts = ImpactRepository(session)
    summary = impacts.upsert(scenario.scenario_id, max_depth_m=1.2, data_mode="demo")
    assert impacts.upsert(scenario.scenario_id, max_depth_m=2.4).id == summary.id
    assert impacts.get(scenario.scenario_id).max_depth_m == 2.4
    runs = RunRepository(session)
    run = runs.start(scenario_id=scenario.scenario_id, run_id="verify-run", stage="model")
    assert runs.get("verify-run").status == "running"
    with pytest.raises(ValueError):
        runs.finish(run, status="unknown")
    runs.finish(run, status="completed", metadata_json={"outputs": 1})
    assert run.completed_at >= run.started_at
    assert run.metadata_json == {"outputs": 1}
    status = StatusRepository(session)
    older = status.add(reading_time=datetime(2020, 1, 1, tzinfo=timezone.utc), reservoir_level_m=10, data_mode="demo")
    newer = status.add(reading_time=datetime(2021, 1, 1, tzinfo=timezone.utc), reservoir_level_m=11, data_mode="demo")
    assert status.latest().id == newer.id


def test_foreign_keys_and_cascade(session):
    scenario = ScenarioRepository(session).register(manifest())
    RunRepository(session).start(scenario_id=scenario.scenario_id, run_id="cascade-run", stage="model")
    session.delete(scenario)
    session.flush()
    assert session.scalars(select(ScenarioInput)).all() == []
    assert session.scalars(select(ProcessingRun)).all() == []


def test_demo_seed_contract():
    seeds = json.loads((ROOT / "database/seeds/demo_scenarios.json").read_text())
    assert seeds
    for seed in seeds:
        assert ScenarioManifest.model_validate(seed).data_mode == "demo"


def test_fresh_migration_roundtrip(isolated_database):
    engine, config = isolated_database
    command.downgrade(config, "base")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'scenarios'")).scalar() == 0
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == ScriptDirectory.from_config(config).get_current_head()


def test_schema_matches_models(isolated_database):
    _, config = isolated_database
    command.check(config)


def test_verified_demo_seed_is_idempotent(session, tmp_path):
    from scripts.demo_seed import seed
    from services.api.app.db.models import ResultAsset, ImpactSummary
    from services.api.app.storage import LocalObjectStore
    store = LocalObjectStore(tmp_path)
    first = seed(session, store)
    assert first[1] == "completed"
    assert seed(session, store) == first
    assert len(session.scalars(select(ResultAsset)).all()) == 1
    assert len(session.scalars(select(ImpactSummary)).all()) == 1


def test_invalid_output_does_not_complete_run(session, tmp_path):
    from scripts.demo_seed import build_demo
    from services.api.app.manifest_registry import register_manifest
    from services.api.app.result_registration import complete_run, start_run
    from services.api.app.db.models import ResultAsset
    from services.api.app.storage import LocalObjectStore
    store = LocalObjectStore(tmp_path)
    manifest, bundle = build_demo(store)
    scenario = register_manifest(session, manifest, store)
    run = start_run(session, scenario.scenario_id, bundle.run_id)
    bundle.assets[0].checksum = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="mismatch"):
        complete_run(session, bundle, store)
    assert run.status == "running"
    assert scenario.status == "running"
    assert session.scalars(select(ResultAsset)).all() == []


def test_manifest_checksum_failure_registers_nothing(session, tmp_path):
    from scripts.demo_seed import build_demo
    from services.api.app.manifest_registry import register_manifest
    from services.api.app.storage import LocalObjectStore
    store = LocalObjectStore(tmp_path)
    manifest, _ = build_demo(store)
    manifest.inputs[0].checksum = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="mismatch"):
        register_manifest(session, manifest, store)
    assert ScenarioRepository(session).get(manifest.scenario_id) is None
    assert not store.path_for_key(f"scenarios/{manifest.scenario_id}/manifest.json").exists()


def test_output_transaction_rolls_back_on_database_failure(session, tmp_path, monkeypatch):
    from scripts.demo_seed import build_demo
    from services.api.app.manifest_registry import register_manifest
    from services.api.app.result_registration import complete_run, start_run
    from services.api.app.repositories.impact_repository import ImpactRepository
    from services.api.app.db.models import ResultAsset
    from services.api.app.storage import LocalObjectStore
    store = LocalObjectStore(tmp_path)
    manifest, bundle = build_demo(store)
    scenario = register_manifest(session, manifest, store)
    run = start_run(session, scenario.scenario_id, bundle.run_id)
    def database_failure(*args, **kwargs):
        raise RuntimeError("simulated database failure")
    monkeypatch.setattr(ImpactRepository, "upsert", database_failure)
    with pytest.raises(RuntimeError):
        with session.begin_nested():
            complete_run(session, bundle, store)
    assert session.scalars(select(ResultAsset)).all() == []
    assert run.status == "running"


def test_failed_run_is_auditable_and_retry_uses_new_run(session, tmp_path):
    from scripts.demo_seed import build_demo
    from services.api.app.manifest_registry import register_manifest
    from services.api.app.result_registration import fail_run, start_run
    from services.api.app.repositories.run_repository import RunRepository
    from services.api.app.storage import LocalObjectStore
    store = LocalObjectStore(tmp_path)
    manifest, bundle = build_demo(store)
    scenario = register_manifest(session, manifest, store)
    first = start_run(session, scenario.scenario_id, bundle.run_id)
    fail_run(session, first.run_id, "MODEL_TIMEOUT")
    assert scenario.status == "failed"
    second = start_run(session, scenario.scenario_id, "retry-run-002")
    assert second.status == "running"
    assert RunRepository(session).get(first.run_id).status == "failed"


def test_b2_command_line_handoff(isolated_database, tmp_path):
    import subprocess
    from scripts.demo_seed import build_demo
    from services.api.app.storage import LocalObjectStore
    engine, _ = isolated_database
    store = LocalObjectStore(tmp_path / "objects")
    manifest, bundle = build_demo(store)
    manifest.scenario_id = "cli-demo-001"
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(manifest.model_dump_json(), encoding="utf-8")
    env = dict(os.environ, OBJECT_STORAGE_ROOT=str(store.root))
    def invoke(script, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)], cwd=ROOT, env=env, capture_output=True, text=True)
    try:
        assert invoke("register_scenario.py", manifest_file).returncode == 0
        assert invoke("register_scenario.py", manifest_file).returncode == 1
        bundle.run_id = "cli-first-run"
        assert invoke("run_contract.py", "start", manifest.scenario_id, bundle.run_id).returncode == 0
        assert invoke("run_contract.py", "fail", bundle.run_id, "MODEL_TIMEOUT").returncode == 0
        bundle.run_id = "cli-retry-run"
        assert invoke("run_contract.py", "start", manifest.scenario_id, bundle.run_id).returncode == 0
        bundle_file = tmp_path / "bundle.json"
        bundle_file.write_text(bundle.model_dump_json(), encoding="utf-8")
        assert invoke("run_contract.py", "complete", bundle_file).returncode == 0
        assert invoke("run_contract.py", "complete", bundle_file).returncode == 1
        with Session(engine) as session:
            scenario = ScenarioRepository(session).get(manifest.scenario_id)
            assert scenario.status == "completed"
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM scenarios WHERE scenario_id = :scenario_id"), {"scenario_id": manifest.scenario_id})


def test_configured_database_head_and_postgis():
    connection_url = make_url(os.environ["DATABASE_URL"])
    if connection_url.host == "localhost":
        connection_url = connection_url.set(host="127.0.0.1")
    engine = create_engine(connection_url, connect_args={"options": "-csearch_path=public", "connect_timeout": 5})
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar() == ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_current_head()
        assert connection.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")).scalar()
        # A fresh seeded database need not contain the user's old legacy demo.
        # Rehearsal snapshot preservation separately protects existing live rows.
    engine.dispose()
