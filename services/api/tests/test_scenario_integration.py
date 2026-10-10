"""Real B1 registration -> approved repository -> FastAPI -> public JSON."""
import json
from pathlib import Path

import pytest
from sqlalchemy import select, text

from services.api.app.api_schemas.scenario import ScenarioListResponse
from services.api.app.db.models import AssetSpatialMetadata, PublishedBundle


def test_approved_gis_bundle_matches_public_contract(b2_client, b2_session, scenario_factory):
    item = scenario_factory()
    assert b2_session.scalar(text("SELECT current_schema()" )).startswith("b1_verify_")
    assert len(b2_session.scalars(select(AssetSpatialMetadata)).all()) == 4
    bundle = b2_session.scalar(select(PublishedBundle))
    assert bundle.manifest_json["scenario_id"] == item.scenario_id
    response = b2_client.get("/api/v1/scenarios?data_mode=demo")
    assert response.status_code == 200
    expected = json.loads((Path(__file__).parent / "fixtures/scenario-list.json").read_text())
    assert response.json() == expected
    ScenarioListResponse.model_validate(response.json())
    # Internal snapshot/path fields must never enter the public catalogue.
    for private in ("file:", "storage_uri", "bundle_root_uri", "manifest_json", "registered_by"):
        assert private not in response.text


@pytest.mark.parametrize("status", ["draft", "rejected", "revoked"])
def test_publication_gate_is_enforced_through_http(b2_client, scenario_factory, status):
    scenario_factory("b2-visible")
    scenario_factory("b2-hidden", status=status)
    response = b2_client.get("/api/v1/scenarios?data_mode=demo")
    assert response.status_code == 200
    assert [row["scenario_id"] for row in response.json()["items"]] == ["b2-visible"]


def test_demo_fixture_cannot_appear_in_production(b2_client, scenario_factory):
    scenario_factory()
    response = b2_client.get("/api/v1/scenarios?data_mode=production")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["pagination"]["next_offset"] is None


def test_multiple_pages_have_a_stable_order_and_end(b2_client, scenario_factory):
    for identity in ("b2-z", "b2-a", "b2-m"):
        scenario_factory(identity)
    offset = 0
    seen = []
    for _ in range(3):
        response = b2_client.get("/api/v1/scenarios", params={"limit": 1, "offset": offset})
        assert response.status_code == 200
        payload = response.json()
        seen.extend(row["scenario_id"] for row in payload["items"])
        offset = payload["pagination"]["next_offset"]
        if offset is None:
            break
    assert seen == ["b2-a", "b2-m", "b2-z"]
    assert offset is None


def test_b1_filters_are_applied_by_http_endpoint(b2_client, scenario_factory):
    item = scenario_factory()
    filters = {
        "scenario_type": "hypothetical", "data_kind": "demo",
        "model_version": item.model_version, "dataset_id": item.datasets[0].dataset_id,
        "dataset_version": item.datasets[0].version,
        "start": "2026-01-01T01:00:00Z", "end": "2026-01-01T02:00:00Z",
    }
    response = b2_client.get("/api/v1/scenarios", params=filters)
    assert response.status_code == 200
    assert [row["scenario_id"] for row in response.json()["items"]] == [item.scenario_id]
    for change in ({"model_version": "missing"}, {"dataset_version": "missing"},
                   {"scenario_type": "historical_replay"}, {"historical_event_id": "missing"}):
        response = b2_client.get("/api/v1/scenarios", params=filters | change)
        assert response.status_code == 200
        assert response.json()["items"] == []


@pytest.mark.parametrize("query", [
    {"dataset_version": "1.0.0"},
    {"start": "2026-01-02T00:00:00Z", "end": "2026-01-01T00:00:00Z"},
    {"start": "2026-01-01T00:00:00"},
    {"limit": 0}, {"offset": -1},
])
def test_invalid_filter_queries_fail_safely(b2_client, query):
    response = b2_client.get("/api/v1/scenarios", params=query)
    assert response.status_code == 422
    assert "postgresql" not in response.text and "file:" not in response.text
