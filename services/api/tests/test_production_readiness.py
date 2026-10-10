"""Step 1 configuration, safe operational responses and failure-path coverage."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from services.api.app import readiness
from services.api.app.main import app
from services.api.app.settings import production_settings, business_database_url
from services.api.app.container_runtime import configure


@pytest.fixture
def env(tmp_path):
    objects, scratch = tmp_path / "objects", tmp_path / "scratch"
    objects.mkdir(); scratch.mkdir()
    return {"B2_ENV": "production", "DATABASE_URL": "postgresql+psycopg://reader:private-token@catalogue/db",
            "OBJECT_STORAGE_ROOT": str(objects), "TMPDIR": str(scratch), "B2_STORAGE_ID": "test-store"}


@pytest.mark.parametrize("change", [
    {"B2_ENV": "invalid"}, {"B2_STORAGE_ID": ""}, {"B2_STORAGE_ID": "../private"},
    {"TMPDIR": "relative"}, {"B2_SCRATCH_MIN_BYTES": "0"}, {"B2_SCRATCH_MIN_BYTES": "1073741825"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@127.0.0.2/db"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@LOCALHOST./db"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@catalogue/db?host=evil"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@catalogue/db?options=-c+default_transaction_read_only=off"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@catalogue/db?sslmode=bogus"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@catalogue/db?sslmode=require&sslmode=disable"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@catalogue:99999/db"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@catalogue:0/db"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@[::ffff:127.0.0.1]/db"},
    {"DATABASE_URL": "private-token" * 900}, {"DATABASE_URL": "private-token\n"},
])
def test_production_config_fails_closed(env, change):
    env.update(change)
    with pytest.raises(ValueError) as error:
        production_settings(env)
    assert "private-token" not in str(error.value)


def test_container_cannot_opt_back_into_local_fallback(env):
    env["B2_ENV"] = "local"
    with pytest.raises(ValueError):
        configure(env)


def test_local_behavior_and_secret_resolution_are_explicit(env, tmp_path):
    assert production_settings({}) is None
    secret = tmp_path / "secret"
    secret.write_text(env.pop("DATABASE_URL"))
    env["DATABASE_URL_FILE"] = str(secret)
    assert configure(env) == 1
    assert "DATABASE_URL_FILE" not in env
    assert production_settings(env) is not None
    assert "private-token" not in repr(production_settings(env))
    bounded = business_database_url(production_settings(env))
    assert "connect_timeout=2" in bounded and "default_transaction_read_only" in bounded


def test_scratch_cannot_overlap_objects(env):
    env["TMPDIR"] = env["OBJECT_STORAGE_ROOT"]
    with pytest.raises(ValueError):
        production_settings(env)


def test_large_secret_rejected(env, tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("x" * 10000)
    env.pop("DATABASE_URL"); env["DATABASE_URL_FILE"] = str(secret)
    with pytest.raises(ValueError):
        production_settings(env)


def test_direct_production_import_rejects_missing_url_before_b1_fallback():
    environment = dict(os.environ, B2_ENV="production")
    environment.pop("DATABASE_URL", None); environment.pop("DATABASE_URL_FILE", None)
    run = subprocess.run([sys.executable, "-c", "import services.api.app.main"],
                         env=environment, capture_output=True, text=True, timeout=20)
    assert run.returncode != 0 and "configuration is invalid" in run.stderr
    assert "ukai:ukai" not in run.stderr


def test_required_revision_tracks_unchanged_b1_migrations():
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "database/migrations"))
    assert ScriptDirectory.from_config(config).get_heads() == [readiness.EXPECTED_REVISION]


def marker(settings, content=None):
    (settings.object_root / readiness.MARKER).write_text(json.dumps(
        content if content is not None else {"schema_version": 1, "store_id": settings.storage_id}))


def test_storage_probe_reads_marker_and_cleans_scratch(env):
    settings = production_settings(env)
    marker(settings)
    readiness.storage_probe(settings)
    assert list(settings.scratch_root.iterdir()) == []


@pytest.mark.parametrize("content", [None, {}, {"schema_version": 1, "store_id": "wrong"},
                                     {"schema_version": True, "store_id": "test-store"},
                                     {"schema_version": 2, "store_id": "test-store"}])
def test_missing_wrong_storage_fails(env, content):
    settings = production_settings(env)
    if content is not None:
        marker(settings, content)
    with pytest.raises((ValueError, OSError)):
        readiness.storage_probe(settings)


def test_full_scratch_is_not_ready(env, monkeypatch):
    settings = production_settings(env); marker(settings)
    monkeypatch.setattr(readiness.shutil, "disk_usage", lambda path: SimpleNamespace(free=0))
    with pytest.raises(ValueError):
        readiness.storage_probe(settings)


def test_unwritable_scratch_is_not_ready(env, monkeypatch):
    settings = production_settings(env); marker(settings)
    def denied(**kwargs):
        raise PermissionError("private path")
    monkeypatch.setattr(readiness.tempfile, "TemporaryFile", denied)
    with pytest.raises(PermissionError):
        readiness.storage_probe(settings)


def test_ready_route_is_safe_and_separate_from_business_spec(monkeypatch):
    class Probe:
        result = False
        async def check(self):
            return self.result
    probe = Probe(); monkeypatch.setattr(app.state, "readiness", probe)
    with TestClient(app) as client:
        response = client.get("/readyz?private-token=secret")
        assert response.status_code == 503 and response.headers["retry-after"] == "1"
        assert response.headers["cache-control"] == "no-store"
        assert "private-token" not in response.text
        assert client.get("/api/v1/health").status_code == 200
        probe.result = True
        assert client.get("/readyz").json() == {"status": "ready"}
        assert "/readyz" not in client.get("/openapi.json").json()["paths"]


def test_no_cached_success_and_concurrent_probes_are_bounded(env, monkeypatch):
    settings = production_settings(env); marker(settings)
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def database(settings):
            entered.set(); await release.wait()
        monkeypatch.setattr(readiness, "database_probe", database)
        probe = readiness.Readiness(settings)
        first = asyncio.create_task(probe.check()); await entered.wait()
        assert await probe.check() is False
        release.set(); assert await first is True
        async def failed(settings):
            raise OSError("private-token")
        monkeypatch.setattr(readiness, "database_probe", failed)
        assert await probe.check() is False
        assert not probe._gate.locked()
        assert await readiness.Readiness(None).check() is False
    asyncio.run(run())


def test_slow_dependency_returns_on_deadline_without_probe_accumulation(env, monkeypatch):
    settings = production_settings(env); marker(settings)
    monkeypatch.setattr(readiness, "RESPONSE_BUDGET_SECONDS", .02)
    async def run():
        release = asyncio.Event()
        async def slow(settings):
            await release.wait()
        monkeypatch.setattr(readiness, "database_probe", slow)
        probe = readiness.Readiness(settings)
        assert await probe.check() is False
        assert probe._gate.locked()
        assert probe._task is not None
        assert await probe.check() is False
        release.set(); await asyncio.sleep(.02)
        assert not probe._gate.locked()
        assert probe._task is None
        assert await probe.check() is True
    asyncio.run(run())
