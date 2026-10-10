"""Current status uses only the latest persisted demo reading."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from services.api.app.api_schemas.status import CurrentStatusResponse
from services.api.app.repositories.status_repository import StatusRepository

TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_status_matches_candidate_example_and_keeps_persisted_time(b2_client, b2_session):
    StatusRepository(b2_session).add(reading_time=TIME, reservoir_level_m=101.25,
        inflow_m3s=20.0, release_m3s=15.0, data_mode="demo")
    response = b2_client.get("/api/v1/status/current")
    assert response.status_code == 200
    assert response.json() == json.loads((Path(__file__).parent / "fixtures/current-status.json").read_text())
    CurrentStatusResponse.model_validate(response.json())
    assert "created_at" not in response.text and '"id"' not in response.text
    assert b2_client.get("/api/v1/status/current").json()["timestamp"] == response.json()["timestamp"]


def test_newest_demo_wins_and_newer_production_reading_is_excluded(b2_client, b2_session):
    repo = StatusRepository(b2_session)
    repo.add(reading_time=TIME, reservoir_level_m=101.0, data_mode="demo")
    later = TIME.replace(day=2)
    repo.add(reading_time=later, reservoir_level_m=102.0, data_mode="demo")
    repo.add(reading_time=later, reservoir_level_m=103.0, data_mode="demo")
    repo.add(reading_time=TIME.replace(day=3), reservoir_level_m=999.0, data_mode="production")
    response = b2_client.get("/api/v1/status/current?data_mode=demo")
    assert response.status_code == 200
    assert response.json()["reservoir_level_m"] == 103.0
    assert response.json()["timestamp"] == "2026-01-02T00:00:00Z"
    assert response.json()["data_mode"] == response.json()["data_kind"] == "demo"
    assert response.json()["is_live"] is False


def test_null_readings_are_not_replaced_with_zero(b2_client, b2_session):
    StatusRepository(b2_session).add(reading_time=TIME, data_mode="demo")
    response = b2_client.get("/api/v1/status/current")
    assert response.status_code == 200
    for field in ("reservoir_level_m", "inflow_m3s", "release_m3s"):
        assert response.json()[field] is None


@pytest.mark.parametrize("production_only", [False, True])
def test_no_demo_reading_returns_404_instead_of_a_fabricated_value(b2_client, b2_session, production_only):
    if production_only:
        StatusRepository(b2_session).add(reading_time=TIME, reservoir_level_m=999.0, data_mode="production")
    response = b2_client.get("/api/v1/status/current")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "No demo status reading is available."


@pytest.mark.parametrize("mode", ["production", "live", "unsafe"])
def test_status_endpoint_cannot_be_switched_to_non_demo(b2_client, mode):
    response = b2_client.get("/api/v1/status/current", params={"data_mode": mode})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize("values", [{"inflow_m3s": -1.0}, {"release_m3s": -1.0},
    {"reservoir_level_m": float("nan")}, {"inflow_m3s": float("inf")}])
def test_invalid_demo_measurements_fail_without_exposing_values(b2_client, b2_session, values):
    StatusRepository(b2_session).add(reading_time=TIME, data_mode="demo", **values)
    response = b2_client.get("/api/v1/status/current")
    assert response.status_code == 503
    assert response.json()["detail"] == "The registered demo reading is unavailable."
    assert "NaN" not in response.text and "Infinity" not in response.text
