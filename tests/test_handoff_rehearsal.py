"""Safety/unit checks for the clean rehearsal; actual execution is recorded separately."""
import pytest
from scripts.rehearse_b1_handoff import rehearsal, source_package


def test_handoff_refuses_existing_output(tmp_path):
    with pytest.raises(ValueError, match="new directory"):
        rehearsal(tmp_path)


def test_handoff_refuses_output_outside_handoff_root(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.rehearse_b1_handoff.source_url", lambda: pytest.fail("database was accessed"))
    with pytest.raises(ValueError, match="under data/handoff"):
        rehearsal(tmp_path / "not-in-project")


def test_source_package_excludes_private_configuration(tmp_path):
    package = tmp_path / "source"
    inventory = source_package(package)
    assert ".env.example" in inventory and "requirements.txt" in inventory
    assert "pytest.ini" in inventory
    assert "scripts/rehearse_b1_handoff.py" in inventory
    assert "docs/contracts/published-scenario.schema.json" in inventory
    assert not any(key.startswith(("data/", ".venv/", ".git/")) or key == ".env" or "__pycache__" in key for key in inventory)
