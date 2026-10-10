"""Back up local B1 PostGIS + objects; restore only into a new drill database."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from services.api.app.db.models import Base
from services.api.app.storage import default_store, sha256_file

load_dotenv(ROOT / ".env")
TABLES = sorted(Base.metadata.tables)


def docker(*args):
    subprocess.run(["docker", *args], check=True, capture_output=True)


def native_pg(command, url, *args, database=None):
    """Explicit portable PostgreSQL adapter; credentials stay out of arguments."""
    directory = Path(os.environ["UKAI_PG_BIN"]).resolve()
    executable = directory / (command + (".exe" if os.name == "nt" else ""))
    if not executable.is_file():
        raise ValueError("configured native PostgreSQL tool unavailable")
    environment = dict(os.environ, PGHOST=url.host, PGPORT=str(url.port or 5432),
        PGUSER=url.username, PGPASSWORD=url.password or "", PGDATABASE=database or url.database,
        PGCONNECT_TIMEOUT="5")
    environment.pop("PGOPTIONS", None)
    subprocess.run([str(executable), *args], env=environment, check=True, capture_output=True)


def source_url():
    url = make_url(os.environ["DATABASE_URL"])
    if url.host not in {"localhost", "127.0.0.1"}:
        raise ValueError("this backup adapter is for the configured local Docker database")
    # Docker is deliberately bound to IPv4 loopback; avoid slow IPv6 fallback.
    timeout = url.query.get("connect_timeout", "5")
    if not isinstance(timeout, str):
        raise ValueError("a single local connection timeout is required")
    return url.set(host="127.0.0.1").update_query_dict({"connect_timeout": timeout})


def artifact_references(connection, tables):
    """Inspect the archive's actual columns to support older schema revisions."""
    references = []
    inspector = inspect(connection)
    for table, reference, checksum in (
        ("scenario_inputs", "storage_uri", "checksum"),
        ("result_assets", "storage_uri", "checksum"),
        ("dataset_versions", "source_reference", "checksum"),
        ("validation_metrics", "report_reference", "report_checksum"),
        ("scenarios", "assumptions_url", "assumptions_checksum"),
        ("processing_runs", "quality_report_uri", "quality_report_checksum"),
    ):
        if table in tables:
            columns = {item["name"] for item in inspector.get_columns(table, schema="public")}
            if {reference, checksum} <= columns:
                references.extend(connection.execute(text(f'SELECT "{reference}", "{checksum}" FROM public."{table}" WHERE "{reference}" IS NOT NULL AND "{checksum}" IS NOT NULL')).all())
    return references


def snapshot(engine, tables=None):
    tables = TABLES if tables is None else sorted(tables)
    if not tables or not set(tables).issubset(TABLES):
        raise ValueError("backup contains unsupported table names")
    inventory = {}
    sequences = {}
    with engine.connect() as connection:
        connection.execute(text("SET TIME ZONE 'UTC'"))
        revision = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
        for table in tables:
            rows = connection.execute(text(f'SELECT row_to_json(t)::text FROM (SELECT * FROM public."{table}" ORDER BY id) t')).scalars().all()
            digest = hashlib.sha256("\n".join(rows).encode()).hexdigest()
            inventory[table] = {"rows": len(rows), "sha256": digest}
            state = connection.execute(text(f'SELECT last_value, is_called FROM public."{table}_id_seq"')).one()
            sequences[table + "_id_seq"] = {"last_value": state[0], "is_called": state[1]}
        external = connection.execute(text("SELECT storage_uri FROM public.scenario_inputs WHERE storage_uri NOT LIKE 'file://%' UNION SELECT storage_uri FROM public.result_assets WHERE storage_uri NOT LIKE 'file://%'" )).scalars().all()
        external.extend(uri for uri, _ in artifact_references(connection, tables) if uri.startswith("s3://"))
    return {"alembic_revision": revision, "tables": inventory, "sequences": sequences, "unresolved_external_references": sorted(set(external))}


def backup(destination: Path):
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("backup destination must be a new directory")
    destination.mkdir(parents=True)
    url = source_url()
    container = os.getenv("DB_CONTAINER", "ukai_postgres")
    temporary_dump = "/tmp/b1_backup_" + uuid.uuid4().hex + ".dump"
    engine = create_engine(url)
    try:
        before = snapshot(engine)
        if os.environ.get("UKAI_PG_BIN"):
            native_pg("pg_dump", url, "--format=custom", "--file=" + str(destination / "database.dump"))
        else:
            docker("exec", container, "pg_dump", "-U", url.username, "-d", url.database, "--format=custom", "--file=" + temporary_dump)
            docker("cp", container + ":" + temporary_dump, str(destination / "database.dump"))
        after = snapshot(engine)
        if before != after:
            raise ValueError("database changed during backup; rerun when writes are paused")
        store = default_store()
        source_files = list(store.root.rglob("*")) if store.root.exists() else []
        if any(path.is_symlink() for path in source_files):
            raise ValueError("object-store symlinks cannot be backed up")
        shutil.copytree(store.root, destination / "objects")
        files = {}
        for path in (destination / "objects").rglob("*"):
            if path.is_file():
                relative = path.relative_to(destination / "objects").as_posix()
                checksum = sha256_file(path)
                if checksum != sha256_file(store.root / relative):
                    raise ValueError("object changed during backup")
                files[relative] = checksum
        metadata = dict(before, created_at=datetime.now(timezone.utc).isoformat(), source_storage_root=str(store.root), dump_checksum=sha256_file(destination / "database.dump"), objects=files)
        (destination / "backup.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(f"backup ready: {destination}; objects={len(files)}; external references={len(before['unresolved_external_references'])}")
    finally:
        engine.dispose()
        if not os.environ.get("UKAI_PG_BIN"):
            docker("exec", container, "rm", "-f", temporary_dump)
    return destination


def restore_check(destination: Path):
    destination = destination.resolve()
    metadata = json.loads((destination / "backup.json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("invalid backup metadata")
    if sha256_file(destination / "database.dump") != metadata.get("dump_checksum"):
        raise ValueError("backup archive checksum mismatch")
    objects = (destination / "objects").resolve()
    inventory = metadata.get("objects")
    if not isinstance(inventory, dict):
        raise ValueError("invalid backup object inventory")
    for relative, expected in inventory.items():
        path = (objects / relative).resolve()
        if not path.is_relative_to(objects) or sha256_file(path) != expected:
            raise ValueError("backup object checksum mismatch")
    # Reject unsupported inventory before any connection or pg_restore operation.
    # Older archives may contain a supported subset of the current tables.
    tables = metadata.get("tables")
    if not isinstance(tables, dict) or not tables or not set(tables).issubset(TABLES):
        raise ValueError("backup contains unsupported table names")
    url = source_url()
    name = "b1_restore_" + uuid.uuid4().hex
    assert re.fullmatch(r"b1_restore_[0-9a-f]{32}", name)
    container = os.getenv("DB_CONTAINER", "ukai_postgres")
    temporary_dump = "/tmp/" + name + ".dump"
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    restored = None
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
            created = True
        if os.environ.get("UKAI_PG_BIN"):
            native_pg("pg_restore", url, "--exit-on-error", "--no-owner", "--no-privileges",
                "--dbname=" + name, str(destination / "database.dump"), database=name)
        else:
            docker("cp", str(destination / "database.dump"), container + ":" + temporary_dump)
            docker("exec", container, "pg_restore", "-U", url.username, "--dbname=" + name, "--exit-on-error", "--no-owner", "--no-privileges", temporary_dump)
        restored = create_engine(url.set(database=name))
        # Old backups remain restorable after new additive catalog migrations.
        actual = snapshot(restored, tables=metadata["tables"])
        expected = {key: metadata[key] for key in actual}
        if actual != expected:
            raise ValueError("restored database differs from backup inventory")
        from services.api.app.storage import LocalObjectStore
        source_store = LocalObjectStore(Path(metadata["source_storage_root"]))
        with restored.connect() as connection:
            assert connection.execute(text("SELECT extversion FROM pg_extension WHERE extname='postgis'")).scalar()
            references = [(uri, checksum) for uri, checksum in artifact_references(connection, actual["tables"]) if not uri.startswith("s3://")]
            for uri, checksum in references:
                relative = source_store.resolve_uri(uri).relative_to(source_store.root) if uri.startswith("file://") else Path(uri)
                target = (objects / relative).resolve()
                if not target.is_relative_to(objects):
                    raise ValueError("catalog reference is outside the backed-up object store")
                if not checksum or sha256_file(target) != checksum:
                    raise ValueError("restored object differs from its database reference")
        report = dict(verified_at=datetime.now(timezone.utc).isoformat(), restored_tables=actual["tables"], postgis_verified=True, local_references_verified=len(references), unresolved_external_references=actual["unresolved_external_references"])
        (destination / "restore-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"restore verified: {len(actual['tables'])} tables, PostGIS, {len(references)} local input/output checksums; external references={len(actual['unresolved_external_references'])}")
    finally:
        if restored:
            restored.dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
        if not os.environ.get("UKAI_PG_BIN"):
            docker("exec", container, "rm", "-f", temporary_dump)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore-check"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        (backup if args.action == "backup" else restore_check)(args.directory)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        # Do not print database URLs or Docker output containing connection data.
        print(f"{args.action} failed: {type(exc).__name__}: {str(exc) if not isinstance(exc, subprocess.CalledProcessError) else 'Docker operation failed'}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
