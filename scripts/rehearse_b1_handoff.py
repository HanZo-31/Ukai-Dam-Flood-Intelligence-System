"""Step 14: clean local B1-only rehearsal; synthetic fixtures, no API/science sign-off."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from scripts.backup_db import backup, restore_check, snapshot, source_url
from scripts.gis_fixture import build_fixture
from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate, HistoricalEventCreate, ValidationMetricCreate
from services.api.app.repositories.catalog_repository import DatasetRepository, HistoricalEventRepository, ValidationMetricRepository
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.repositories.status_repository import StatusRepository
from services.api.app.storage import LocalObjectStore, default_store, sha256_file

REVIEWER = "synthetic-rehearsal-reviewer"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def object_inventory(store):
    return {path.relative_to(store.root).as_posix(): sha256_file(path)
            for path in store.root.rglob("*") if path.is_file()}


def source_package(destination):
    """Explicit allowlist: no .env, live data, .venv, credentials or Git history."""
    destination.mkdir()
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".env", ".env.*", ".git", ".aws", ".ssh")
    for name in ("database", "services", "scripts", "tests", "docs"):
        require(not (ROOT / name).is_symlink() and not (ROOT / name).is_junction(),
                "source package refuses symlinks/junctions; review the source tree")
        require(not any(path.is_symlink() or path.is_junction() for path in (ROOT / name).rglob("*")),
                "source package refuses symlinks/junctions; review the source tree")
        shutil.copytree(ROOT / name, destination / name, ignore=ignore)
    for name in ("README.md", "requirements.txt", "compose.yaml", "alembic.ini", "pytest.ini", ".env.example"):
        require(not (ROOT / name).is_symlink() and not (ROOT / name).is_junction(),
                "source package refuses symlinks/junctions; review source files")
        shutil.copy2(ROOT / name, destination / name)
    require(not (destination / ".env").exists(), "private configuration was packaged")
    return object_inventory(LocalObjectStore(destination))


@contextmanager
def environment(values):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def catalog_fixture(session, item, store, bundle_root):
    """Persist truthful demo provenance, a synthetic event and a supplied demo metric."""
    datasets = DatasetRepository(session)
    for source in item.datasets:
        datasets.register(DatasetCreate(dataset_id=source.dataset_id, name="Synthetic handoff input",
                                       description="Invented contract fixture, not observations", data_mode="demo"))
        values = source.model_dump()
        values["source_reference"] = store.resolve_uri(bundle_root + source.source_reference).as_uri()
        datasets.register_version(DatasetVersionCreate.model_validate(values))
    events = HistoricalEventRepository(session)
    events.register(HistoricalEventCreate(event_id="synthetic-handoff-event", name="Synthetic event fixture",
                    time_coverage=item.time_coverage, observed_coverage="No actual observations",
                    quality_notes="Invented event for contract testing only", source_urls=["https://example.org/synthetic"], data_mode="demo"))
    for source in item.datasets:
        events.link_dataset("synthetic-handoff-event", source.dataset_id, source.version)
    source = item.datasets[0]
    ValidationMetricRepository(session).register(ValidationMetricCreate(
        metric_id="synthetic-handoff-rmse", event_id="synthetic-handoff-event",
        dataset_id=source.dataset_id, dataset_version=source.version, model_version=item.model_version,
        metric_name="rmse", value=0.5, unit="m", sample_count=2, computed_at=item.run_timestamp,
        calculation_config={"synthetic": True, "not_computed_by_b1": True},
        report_reference=store.resolve_uri(bundle_root + item.quality.report_reference).as_uri(),
        report_checksum=item.quality.report_checksum))


def approved_fixture(draft, identity, *, historical=False):
    item = draft.model_copy(deep=True)
    item.scenario_id, item.run_id = identity, identity + "-run"
    item.status = "approved"
    item.quality.validation_status = "pass"
    item.quality.approved_by = REVIEWER
    item.quality.approved_at = item.run_timestamp + timedelta(minutes=15)
    if historical:
        item.scenario_type = "historical_replay"
        item.historical_event_id = "synthetic-handoff-event"
    return item


def rehearsal(destination):
    destination = destination.resolve()
    require(not destination.exists(), "rehearsal destination must be a new directory")
    require(destination.is_relative_to(ROOT / "data" / "handoff"), "destination must be under data/handoff")
    original_url = source_url()
    live = create_engine(original_url)
    original_store = default_store()
    before = {"database": snapshot(live), "objects": object_inventory(original_store)}
    name = "b1_handoff_" + uuid.uuid4().hex
    require(bool(re.fullmatch(r"b1_handoff_[0-9a-f]{32}", name)), "unsafe rehearsal database identity")
    target = original_url.set(database=name).update_query_dict({"options": "-csearch_path=public"})
    destination.mkdir(parents=True)
    package = destination / "source"
    source_hashes = source_package(package)
    store = LocalObjectStore(destination / "objects")
    env = dict(os.environ, DATABASE_URL=target.render_as_string(hide_password=False), OBJECT_STORAGE_ROOT=str(store.root),
               PYTHONDONTWRITEBYTECODE="1")
    admin = create_engine(original_url, isolation_level="AUTOCOMMIT")
    engine = None
    created = False
    steps = []
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "scope": "B1-only synthetic local rehearsal",
              "database_name": name, "scientific_approval": False, "b2_api_tested": False,
              "fresh_python_environment": False, "source_hashes": source_hashes, "steps": steps, "result": "failed"}

    def run(label, args, expected=0):
        result = subprocess.run([sys.executable, *args], cwd=package, env=env, capture_output=True, text=True, timeout=120)
        # Commands never receive a connection URL in argv or echo it in evidence.
        require(result.returncode == expected, f"{label}: unexpected exit {result.returncode}; inspect privately")
        steps.append({"check": label, "passed": True, "expected_exit": expected})
        return result

    def import_manifest(item, label, expected=0):
        uri, _ = store.put("rehearsal-manifests/" + item.scenario_id + ".json", item.model_dump_json(indent=2).encode())
        path = store.resolve_uri(uri)
        run(label, ["scripts/register_published_bundle.py", str(path), "--bundle-root", bundle_root,
                    "--registered-by", "synthetic-rehearsal-operator", "--trusted-approver", REVIEWER], expected)

    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
            created = True
        engine = create_engine(target)
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION postgis"))
        run("all migrations on empty database from source copy", ["-m", "alembic", "upgrade", "head"])
        require(len(snapshot(engine)["tables"]) == 16, "incorrect table inventory")
        run("model/schema parity", ["-m", "alembic", "check"])
        run("pinned dependency consistency", ["-m", "pip", "check"])
        run("first seed", ["scripts/seed_db.py"])
        seeded = {"database": snapshot(engine), "objects": object_inventory(store)}
        run("repeat seed", ["scripts/seed_db.py"])
        require(seeded == {"database": snapshot(engine), "objects": object_inventory(store)}, "seed is not idempotent")
        steps.append({"check": "seed repeat preserves rows, sequences and files", "passed": True})
        tests = run("complete regression suite from source copy against fresh seeded database",
                    ["-m", "pytest", "-q", "-p", "no:cacheprovider"])
        summary = re.search(r"(\d+) passed[^\n]*", tests.stdout)
        require(summary is not None, "clean regression summary unavailable")
        report["clean_suite_summary"] = summary.group(0)
        require(seeded == {"database": snapshot(engine), "objects": object_inventory(store)}, "clean suite changed seeded baseline")
        draft, bundle_root, manifest_uri = build_fixture(store)
        run("draft metadata validation", ["scripts/validate_published_manifest.py", str(store.resolve_uri(manifest_uri)), "--allow-draft"])
        run("actual GIS validation", ["scripts/validate_gis_bundle.py", str(store.resolve_uri(manifest_uri)), "--bundle-root", bundle_root])
        with Session(engine) as session, session.begin():
            catalog_fixture(session, draft, store, bundle_root)
        draft.scenario_id, draft.run_id = "handoff-draft", "handoff-draft-run"
        import_manifest(draft, "draft import stays hidden")
        identities = ["handoff-historical", "handoff-hypothetical-1", "handoff-hypothetical-2", "handoff-hypothetical-3"]
        for index, identity in enumerate(identities):
            import_manifest(approved_fixture(draft, identity, historical=index == 0), "synthetic import " + identity)
        with Session(engine) as session:
            repo = PublishedScenarioRepository(session)
            require([row.scenario_id for row in repo.list(data_mode="demo")] == identities, "approved catalog differs")
            require(repo.get(draft.scenario_id, data_mode="demo") is None, "draft leaked")
            require(repo.list(data_mode="production") == [], "demo leaked into production")
            require(repo.list(data_mode="demo", historical_event_id="synthetic-handoff-event")[0].scenario_id == identities[0], "event filter failed")
            for identity in identities:
                require(repo.get(identity, data_mode="demo") is not None, "scenario missing")
                require(len(repo.assets(identity, data_mode="demo")) == 4, "layers missing")
                require(repo.summary(identity, data_mode="demo").population_exposed is None, "unknown exposure was invented")
                require(len(repo.datasets(identity, data_mode="demo")) == 1, "provenance missing")
                require(repo.footprint(identity, data_mode="demo") is not None, "extent missing")
                require(len(repo.spatial_assets(identity, data_mode="demo")) == 4, "spatial layers missing")
            require([row.scenario_id for row in repo.list(data_mode="demo", limit=1, offset=1)] == [identities[1]], "pagination failed")
            require(StatusRepository(session).latest(data_mode="demo").data_mode == "demo", "demo status missing")
            require(len(HistoricalEventRepository(session).list(data_mode="demo")) == 1, "event missing")
            require(len(ValidationMetricRepository(session).list(data_mode="demo")) == 1, "metric missing")
            source = draft.datasets[0]
            require(len(repo.list(data_mode="demo", dataset_id=source.dataset_id, dataset_version=source.version,
                                 model_version=draft.model_version, start=draft.time_coverage.start,
                                 end=draft.time_coverage.end)) == 4, "combined provenance/time filters failed")
            from shapely.geometry import shape
            bounds = shape(json.loads(repo.footprint(identities[0], data_mode="demo"))).bounds
            require(len(repo.list(data_mode="demo", bbox=bounds)) == 4, "spatial query failed")
            require(repo.list(data_mode="demo", bbox=(0, 0, 1, 1)) == [], "nonintersecting query failed")
        steps.append({"check": "B2-facing repository reads: historical + three hypothetical fixtures, approval/mode, layers, impact, provenance, spatial, paging and status", "passed": True})
        stable = snapshot(engine)
        import_manifest(approved_fixture(draft, identities[0], historical=True), "duplicate rejection", expected=1)
        invalid = approved_fixture(draft, "handoff-invalid")
        invalid.asset_metadata["max_depth_cog"].checksum = "sha256:" + "0" * 64
        import_manifest(invalid, "bad checksum rejection", expected=1)
        require(stable == snapshot(engine), "invalid or duplicate registration changed database")
        steps.append({"check": "rejections leave complete database snapshot unchanged", "passed": True})
        with Session(engine) as session, session.begin():
            repo = PublishedScenarioRepository(session)
            identity = identities[-1]
            repo.revoke(identity, actor="synthetic-rehearsal-operator", reason="Synthetic withdrawal, not a science decision")
            require(repo.get(identity, data_mode="demo") is None and repo.summary(identity, data_mode="demo") is None
                    and repo.footprint(identity, data_mode="demo") is None, "revoked scalar reads leaked")
            require(repo.assets(identity, data_mode="demo") == [] and repo.datasets(identity, data_mode="demo") == []
                    and repo.spatial_assets(identity, data_mode="demo") == [], "revoked child reads leaked")
            require(len(repo.list(data_mode="demo")) == 3, "revocation catalog failed")
        steps.append({"check": "audited revocation hides all public reads while retaining original bundle", "passed": True})
        with environment({"DATABASE_URL": env["DATABASE_URL"], "OBJECT_STORAGE_ROOT": env["OBJECT_STORAGE_ROOT"]}):
            backup(destination / "backup")
            restore_check(destination / "backup")
        report["restore"] = json.loads((destination / "backup" / "restore-check.json").read_text())
        report["database"] = snapshot(engine)
        report["object_hashes"] = object_inventory(store)
        require(not report["database"]["unresolved_external_references"], "unexpected external dependencies in clean fixture")
        require(source_hashes == object_inventory(LocalObjectStore(package)), "source package changed during rehearsal")
        steps.append({"check": "actual clean populated backup/restore and unchanged source copy", "passed": True})
        report["result"] = "passed"
    except ValueError as error:
        report["failure_check"] = str(error)
        raise
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            # Only the exact generated DB created above; never the user's DB.
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{name}"'))
            report["disposable_database_removed"] = True
        admin.dispose()
        after = {"database": snapshot(live), "objects": object_inventory(original_store)}
        live.dispose()
        report["working_data_preserved"] = before == after
        if before != after:
            report["result"] = "failed"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (destination / "rehearsal.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    require(report["result"] == "passed", "working database or objects changed")
    print(f"B1 local rehearsal passed: {len(steps)} checks; working data preserved; disposable DB removed; evidence={destination}")
    print("Synthetic demo approval only. B2 HTTP/scientific acceptance and fresh Python installation are NOT claimed.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory under data/handoff; retains source/fixtures/backup/evidence")
    args = parser.parse_args()
    try:
        rehearsal(args.output)
    except (ValueError, OSError, subprocess.SubprocessError):
        print("B1 rehearsal failed; inspect local evidence privately; no handoff sign-off", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
