"""Container startup validation and isolation from B1 local setup."""
from pathlib import Path

import pytest

from services.api.app.container_runtime import configure


@pytest.fixture
def environment(tmp_path):
    objects, scratch = tmp_path / "objects", tmp_path / "scratch"
    objects.mkdir(); scratch.mkdir()
    return {"DATABASE_URL": "postgresql+psycopg://reader:test-only@catalogue/demo",
            "OBJECT_STORAGE_ROOT": str(objects), "TMPDIR": str(scratch),
            "B2_STORAGE_ID": "test-store", "B2_WORKERS": "1"}


def test_valid_explicit_container_config(environment):
    assert configure(environment) == 1


def test_private_secret_file_supported_without_importing_db(environment, tmp_path):
    secret = tmp_path / "url.txt"
    secret.write_text(environment.pop("DATABASE_URL"))
    environment["DATABASE_URL_FILE"] = str(secret)
    assert configure(environment) == 1
    assert environment["DATABASE_URL"].startswith("postgresql+psycopg:")


@pytest.mark.parametrize("changes", [
    {"DATABASE_URL": ""}, {"DATABASE_URL_FILE": "missing-file"},
    {"DATABASE_URL": "postgresql+psycopg://reader:private-token@localhost/db"},
    {"DATABASE_URL": "sqlite:///local"}, {"DATABASE_URL": "invalid-private-token"},
    {"DATABASE_URL": "postgresql+psycopg://reader@catalogue/db"},
    {"OBJECT_STORAGE_ROOT": "relative"}, {"OBJECT_STORAGE_ROOT": ""},
    {"B2_WORKERS": "0"}, {"B2_WORKERS": "9"}, {"B2_WORKERS": "not-a-number"},
])
def test_bad_configuration_is_rejected_without_private_values(environment, changes):
    environment.update(changes)
    with pytest.raises(ValueError) as caught:
        configure(environment)
    assert "private-token" not in str(caught.value)
    assert environment["OBJECT_STORAGE_ROOT"] not in str(caught.value) or not environment["OBJECT_STORAGE_ROOT"]


def test_missing_secret_is_safe(environment):
    environment.pop("DATABASE_URL")
    environment["DATABASE_URL_FILE"] = "missing-private-file"
    with pytest.raises(ValueError, match="invalid"):
        configure(environment)


def test_container_files_do_not_change_b1_compose_contract():
    root = Path(__file__).resolve().parents[3]
    compose = (root / "services/api/compose.yaml").read_text()
    dockerfile = (root / "services/api/Dockerfile").read_text()
    assert "read_only: true" in compose and "cap_drop: [ALL]" in compose
    assert "external: true" in compose and "create_host_path: false" in compose
    assert "DATABASE_URL_FILE" in compose and "127.0.0.1:" in compose
    assert "USER 10001:10001" in dockerfile and "@sha256:" in dockerfile
    assert "AS verification" in dockerfile


def test_container_lock_preserves_every_root_pin():
    root = Path(__file__).resolve().parents[3]
    pins = lambda file: {line.strip().lower() for line in file.read_text().splitlines()
                        if line.strip() and not line.startswith("#")}
    assert pins(root / "requirements.txt") <= pins(root / "services/api/requirements-container.lock")
