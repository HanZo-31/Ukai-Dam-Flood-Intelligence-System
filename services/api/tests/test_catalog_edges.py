"""Boundary and positive replay/spatial coverage for the public list endpoint."""
import pytest


def test_historical_replay_is_filterable_and_preserves_event_identity(b2_client, scenario_factory):
    scenario_factory("b2-hypothetical")
    item = scenario_factory("b2-replay", historical_event_id="b2-synthetic-event")
    response = b2_client.get("/api/v1/scenarios", params={
        "scenario_type": "historical_replay", "historical_event_id": item.historical_event_id,
    })
    assert response.status_code == 200
    assert [row["scenario_id"] for row in response.json()["items"]] == [item.scenario_id]
    assert response.json()["items"][0]["historical_event_id"] == item.historical_event_id


def test_spatial_bbox_filters_use_registered_geometry(b2_client, b2_session, scenario_factory):
    from geoalchemy2.shape import to_shape
    from sqlalchemy import select
    from services.api.app.db.models import ScenarioSpatialMetadata
    item = scenario_factory()
    bounds = to_shape(b2_session.scalar(select(ScenarioSpatialMetadata)).geom).bounds
    response = b2_client.get("/api/v1/scenarios", params={"bbox": ",".join(map(str, bounds))})
    assert response.status_code == 200
    assert [row["scenario_id"] for row in response.json()["items"]] == [item.scenario_id]
    assert b2_client.get("/api/v1/scenarios?bbox=0,0,1,1").json()["items"] == []


def test_time_overlap_boundary_and_max_page_size(b2_client, scenario_factory):
    scenario_factory()
    response = b2_client.get("/api/v1/scenarios", params={
        "start": "2026-01-01T11:30:00+05:30", "end": "2026-01-01T11:30:00+05:30", "limit": 999,
    })
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["pagination"] == {"limit": 999, "offset": 0, "next_offset": None}
    response = b2_client.get("/api/v1/scenarios?offset=100&limit=2")
    assert response.json() == {"items": [], "pagination": {"limit": 2, "offset": 100, "next_offset": None}}


@pytest.mark.parametrize("query", [
    {"limit": 1000}, {"scenario_type": "flood_forecast"}, {"data_kind": "live"},
    {"start": "2026-01-01"}, {"start": "1767225600"}, {"bbox": "1,0,0,1"},
    {"bbox": "0,0,181,1"}, {"bbox": "0,0,nan,1"}, {"bbox": "0,0,inf,1"},
    {"bbox": "0,0,1"},
])
def test_query_edges_have_problem_envelopes(b2_client, query):
    response = b2_client.get("/api/v1/scenarios", params=query)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["instance"] == "/api/v1/scenarios"
    assert set(response.json()) == {"type", "title", "status", "detail", "instance"}


def test_sql_like_model_filter_is_treated_as_a_value(b2_client, scenario_factory):
    scenario_factory()
    response = b2_client.get("/api/v1/scenarios", params={"model_version": "'; DROP TABLE scenarios; --"})
    assert response.status_code == 200 and response.json()["items"] == []
    assert len(b2_client.get("/api/v1/scenarios").json()["items"]) == 1
