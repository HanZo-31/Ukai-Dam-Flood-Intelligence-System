import json

import pytest

from scripts.backup_db import restore_check, snapshot
from services.api.app.storage import sha256_file


def test_restore_refuses_corrupt_archive_before_creating_database(tmp_path):
    (tmp_path / "database.dump").write_bytes(b"corrupted")
    (tmp_path / "backup.json").write_text(json.dumps({"dump_checksum": "sha256:" + "0" * 64}))
    with pytest.raises(ValueError, match="archive checksum mismatch"):
        restore_check(tmp_path)


def test_restore_refuses_corrupt_object_before_creating_database(tmp_path):
    dump = tmp_path / "database.dump"
    dump.write_bytes(b"archive")
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / "input.csv").write_bytes(b"changed")
    (tmp_path / "backup.json").write_text(json.dumps({"dump_checksum": sha256_file(dump), "objects": {"input.csv": "sha256:" + "0" * 64}}))
    with pytest.raises(ValueError, match="object checksum mismatch"):
        restore_check(tmp_path)


def test_snapshot_rejects_untrusted_table_names_before_querying():
    with pytest.raises(ValueError, match="unsupported table"):
        snapshot(None, tables=["datasets; DROP TABLE scenarios"])


def archive(tmp_path, objects=None, tables=None):
    dump = tmp_path / "database.dump"
    dump.write_bytes(b"test archive; no Docker operation permitted")
    (tmp_path / "objects").mkdir()
    (tmp_path / "backup.json").write_text(json.dumps({
        "dump_checksum": sha256_file(dump), "objects": objects or {},
        "tables": {"scenarios": {}} if tables is None else tables,
    }))


@pytest.mark.parametrize("relative", ["../outside.txt", "../../outside.txt"])
def test_restore_refuses_traversal_before_database_access(tmp_path, monkeypatch, relative):
    archive(tmp_path, objects={relative: "sha256:" + "0" * 64})
    monkeypatch.setattr("scripts.backup_db.source_url", lambda: pytest.fail("database was accessed"))
    with pytest.raises(ValueError, match="object checksum mismatch"):
        restore_check(tmp_path)


@pytest.mark.parametrize("tables", [{}, {"scenarios; DROP TABLE scenarios": {}}, {"unrecognised_table": {}}])
def test_restore_refuses_untrusted_table_inventory_before_database_access(tmp_path, monkeypatch, tables):
    archive(tmp_path, tables=tables)
    monkeypatch.setattr("scripts.backup_db.source_url", lambda: pytest.fail("database was accessed"))
    with pytest.raises(ValueError, match="unsupported table"):
        restore_check(tmp_path)


def test_backup_never_overwrites_existing_directory(tmp_path, monkeypatch):
    from scripts.backup_db import backup
    marker = tmp_path / "keep.txt"
    marker.write_text("existing backup")
    monkeypatch.setattr("scripts.backup_db.source_url", lambda: pytest.fail("database was accessed"))
    with pytest.raises(ValueError, match="new directory"):
        backup(tmp_path)
    assert marker.read_text() == "existing backup"


@pytest.mark.parametrize("metadata", [[], None, {"objects": []}, {"objects": None}])
def test_restore_rejects_malformed_metadata_cleanly(tmp_path, monkeypatch, metadata):
    dump = tmp_path / "database.dump"
    dump.write_bytes(b"archive")
    if isinstance(metadata, dict):
        metadata["dump_checksum"] = sha256_file(dump)
    (tmp_path / "backup.json").write_text(json.dumps(metadata))
    monkeypatch.setattr("scripts.backup_db.source_url", lambda: pytest.fail("database was accessed"))
    with pytest.raises(ValueError):
        restore_check(tmp_path)


@pytest.mark.parametrize("configured_timeout", [None, "7"])
def test_local_backup_connection_uses_ipv4_and_bounded_timeout(monkeypatch, configured_timeout):
    from scripts.backup_db import source_url
    value = "postgresql+psycopg://test:test@localhost:5432/test"
    if configured_timeout:
        value += "?connect_timeout=" + configured_timeout
    monkeypatch.setenv("DATABASE_URL", value)
    url = source_url()
    assert url.host == "127.0.0.1"
    assert url.query["connect_timeout"] == (configured_timeout or "5")
