import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from services.api.app.schemas import ScenarioManifest


FIXTURE = Path(__file__).parent / "fixtures" / "scenario_manifest.json"


def test_valid_manifest_fixture() -> None:
    manifest = ScenarioManifest.model_validate_json(FIXTURE.read_text())
    assert manifest.scenario_id == "test-rainfall-001"
    assert manifest.inputs[0].storage_uri.startswith("file://")


@pytest.mark.parametrize("field,value", [("crs", "WGS84"), ("scenario_id", "Not Allowed"), ("data_mode", "live")])
def test_manifest_rejects_invalid_values(field: str, value: str) -> None:
    data = json.loads(FIXTURE.read_text())
    data[field] = value
    with pytest.raises(ValidationError):
        ScenarioManifest.model_validate(data)


def test_manifest_rejects_unknown_fields() -> None:
    data = json.loads(FIXTURE.read_text())
    data["untracked"] = True
    with pytest.raises(ValidationError):
        ScenarioManifest.model_validate(data)
