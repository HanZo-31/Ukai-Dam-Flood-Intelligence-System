"""Published impact values travel from B1 registration to public JSON unchanged."""
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from services.api.app.api_schemas.impact import ScenarioImpactResponse
from services.api.app.db.models import ImpactSummary
from services.api.app.repositories.published_repository import PublishedScenarioRepository


def test_impact_matches_candidate_example_and_detail_summary(b2_client, scenario_factory):
    item = scenario_factory()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/impact")
    assert response.status_code == 200
    assert response.json() == json.loads((Path(__file__).parent / "fixtures/impact.json").read_text())
    ScenarioImpactResponse.model_validate(response.json())
    detail = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}").json()
    for field, value in detail["summary"].items():
        assert response.json()[field] == value
    for private in ("file:", "created_at", "storage_uri", "manifest_json"):
        assert private not in response.text


def test_supplied_exposure_counts_and_units_are_preserved(b2_client, scenario_factory):
    supplied = {"population_exposed": 5, "buildings_exposed": 3,
                "roads_affected_km": 1.25, "critical_facilities_exposed": 2}
    item = scenario_factory(summary_updates=supplied)
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/impact")
    assert response.status_code == 200
    for field, value in supplied.items():
        assert response.json()[field] == value


@pytest.mark.parametrize("status", ["draft", "rejected", "revoked"])
def test_impact_hides_unpublished_scenarios(b2_client, scenario_factory, status):
    item = scenario_factory(status=status)
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/impact")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


def test_missing_wrong_mode_and_revocation_are_enforced(b2_client, b2_session, scenario_factory):
    item = scenario_factory()
    url = f"/api/v1/scenarios/{item.scenario_id}/impact"
    assert b2_client.get(url + "?data_mode=production").status_code == 404
    assert b2_client.get("/api/v1/scenarios/missing-scenario/impact").status_code == 404
    PublishedScenarioRepository(b2_session).revoke(item.scenario_id, actor="b2-test-operator", reason="Synthetic withdrawal")
    assert b2_client.get(url).status_code == 404


@pytest.mark.parametrize("change", ["missing", "wrong_mode"])
def test_unavailable_registered_summary_returns_safe_503(b2_client, b2_session, scenario_factory, change):
    item = scenario_factory()
    row = b2_session.scalar(select(ImpactSummary))
    if change == "missing":
        b2_session.delete(row)
    else:
        row.data_mode = "production"
    b2_session.flush()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/impact")
    assert response.status_code == 503
    assert response.json()["detail"] == "The registered impact summary is unavailable."


@pytest.mark.parametrize("bad_value", [-1.0, float("nan"), float("inf")])
def test_invalid_impact_measurements_cannot_be_serialized(b2_client, b2_session, scenario_factory, bad_value):
    item = scenario_factory()
    row = b2_session.scalar(select(ImpactSummary))
    row.max_depth_m = bad_value
    b2_session.flush()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/impact")
    assert response.status_code == 503
    assert response.json()["detail"] == "The registered impact summary is unavailable."
    assert "NaN" not in response.text and "Infinity" not in response.text
