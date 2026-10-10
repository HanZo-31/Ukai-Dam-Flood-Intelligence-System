"""Exact-target safety guards for local container verification."""
from pathlib import Path

import pytest

from scripts import rehearse_b2_container as rehearsal


@pytest.mark.parametrize("name", ["ukai_postgres", "postgres_data", "b2_container_x", "b2_container_" + "a" * 32])
def test_only_generated_container_identity_can_be_managed(name):
    with pytest.raises(ValueError):
        rehearsal.identity(name)


def test_generated_container_identity_is_accepted():
    assert rehearsal.identity("b2_container_" + "a" * 16)


def test_container_rehearsal_refuses_outside_directory_before_db(tmp_path, monkeypatch):
    monkeypatch.setattr(rehearsal, "source_url", lambda: pytest.fail("database accessed"))
    with pytest.raises(ValueError):
        rehearsal.rehearse(tmp_path / "outside")


def test_container_rehearsal_refuses_existing_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(rehearsal, "ROOT", tmp_path)
    directory = tmp_path / "data/handoff/existing"
    directory.mkdir(parents=True)
    with pytest.raises(ValueError):
        rehearsal.destination(directory)


def test_container_guide_explains_uri_and_health_boundaries():
    root = Path(__file__).resolve().parents[3]
    guide = (root / "docs/runbooks/b2-api-container.md").read_text()
    assert "Windows `file:///D:/...`" in guide
    assert "liveness only" in guide and "SELECT-only" in guide
    assert "not an encrypted" in guide and "Git/CI" in guide
