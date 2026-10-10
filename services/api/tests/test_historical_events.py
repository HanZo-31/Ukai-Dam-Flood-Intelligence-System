"""Historical catalog metadata is distinct from approved replay availability."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from services.api.app.api_schemas.historical_event import HistoricalEventListResponse
from services.api.app.catalog_schemas import HistoricalEventCreate
from services.api.app.repositories.catalog_repository import HistoricalEventRepository
from services.api.app.repositories.published_repository import PublishedScenarioRepository


def event(b2_session, identity="b2-catalog-event", *, data_mode="demo", year=1998):
    return HistoricalEventRepository(b2_session).register(HistoricalEventCreate(
        event_id=identity, name="Synthetic event metadata for HTTP testing",
        time_coverage={"start": datetime(year, 1, 1, tzinfo=timezone.utc),
                       "end": datetime(year, 1, 2, tzinfo=timezone.utc)},
        observed_coverage="Synthetic fixture; no observed historical data claimed",
        quality_notes="Internal test note", source_urls=["https://example.org/synthetic-event"],
        data_mode=data_mode,
    ))


def test_empty_catalog_does_not_invent_blueprint_events(b2_client):
    response = b2_client.get("/api/v1/historical-events")
    assert response.status_code == 200
    assert response.json() == {"items": [], "pagination": {"limit": 20, "offset": 0, "next_offset": None}}


def test_catalogued_event_without_replay_is_visible_and_honestly_labelled(b2_client, b2_session):
    row = event(b2_session)
    response = b2_client.get("/api/v1/historical-events?data_mode=demo")
    assert response.status_code == 200
    HistoricalEventListResponse.model_validate(response.json())
    assert response.json() == json.loads((Path(__file__).parent / "fixtures/historical-events.json").read_text())
    body = response.json()["items"][0]
    assert body["event_id"] == row.event_id
    assert body["observed_coverage"] == row.observed_coverage
    assert body["coverage_start"] == "1998-01-01T00:00:00Z"
    assert body["source_urls"] == ["https://example.org/synthetic-event"]
    assert body["data_mode"] == "demo" and body["datasets"] == body["source_labels"] == []
    assert body["replay"]["available"] is False and body["replay"]["example"] is None
    assert b2_client.get(body["replay"]["scenarios_url"]).json()["items"] == []
    assert "quality_notes" not in response.text and "source_reference" not in response.text


def test_approved_replays_include_real_coverage_and_all_replays_are_linked(b2_client, scenario_factory):
    first = scenario_factory("b2-replay-a", historical_event_id="b2-test-event")
    scenario_factory("b2-replay-z", historical_event_id="b2-test-event")
    response = b2_client.get("/api/v1/historical-events")
    assert response.status_code == 200
    body = response.json()["items"][0]
    assert body["source_labels"] == ["demo"]
    assert body["datasets"][0]["checksum"] == first.datasets[0].checksum
    replay = body["replay"]
    assert replay["available"] is True
    assert replay["example"]["scenario_id"] == first.scenario_id
    assert replay["example"]["model_version"] == first.model_version
    assert replay["example"]["coverage_end"] == "2026-01-01T06:00:00Z"
    catalog = b2_client.get(replay["scenarios_url"])
    assert catalog.status_code == 200
    assert [row["scenario_id"] for row in catalog.json()["items"]] == ["b2-replay-a", "b2-replay-z"]
    for private in ("file:", "source_reference", "storage_uri", "manifest_json"):
        assert private not in response.text


@pytest.mark.parametrize("status", ["draft", "rejected", "revoked"])
def test_unpublished_replay_does_not_hide_event_or_claim_replay_availability(b2_client, scenario_factory, status):
    scenario_factory(status=status, historical_event_id="b2-test-event")
    body = b2_client.get("/api/v1/historical-events").json()["items"][0]
    assert body["replay"]["available"] is False
    assert body["replay"]["example"] is None


def test_replay_availability_changes_after_revocation(b2_client, b2_session, scenario_factory):
    item = scenario_factory(historical_event_id="b2-test-event")
    assert b2_client.get("/api/v1/historical-events").json()["items"][0]["replay"]["available"] is True
    PublishedScenarioRepository(b2_session).revoke(item.scenario_id, actor="b2-test-operator", reason="Test withdrawal")
    assert b2_client.get("/api/v1/historical-events").json()["items"][0]["replay"]["available"] is False


def test_event_modes_paging_and_time_overlap(b2_client, b2_session):
    event(b2_session, "b2-z", year=2006)
    event(b2_session, "b2-a", year=1998)
    event(b2_session, "b2-m", year=2003)
    event(b2_session, "b2-production-metadata", data_mode="production", year=2020)
    seen = []
    offset = 0
    for _ in range(3):
        response = b2_client.get("/api/v1/historical-events", params={"data_mode": "demo", "limit": 1, "offset": offset})
        assert response.status_code == 200
        body = response.json()
        seen.extend(row["event_id"] for row in body["items"])
        offset = body["pagination"]["next_offset"]
    assert seen == ["b2-a", "b2-m", "b2-z"] and offset is None
    production = b2_client.get("/api/v1/historical-events?data_mode=production").json()
    assert [row["event_id"] for row in production["items"]] == ["b2-production-metadata"]
    response = b2_client.get("/api/v1/historical-events", params={
        "start": "2003-01-02T05:30:00+05:30", "end": "2003-01-02T05:30:00+05:30", "limit": 999,
    })
    assert response.status_code == 200
    assert [row["event_id"] for row in response.json()["items"]] == ["b2-m"]


@pytest.mark.parametrize("query", [
    {"limit": 0}, {"limit": 1000}, {"offset": -1}, {"data_mode": "live"},
    {"start": "2003-01-01"}, {"start": "2003-01-01T00:00:00"},
    {"start": "2006-01-01T00:00:00Z", "end": "1998-01-01T00:00:00Z"},
])
def test_invalid_event_queries_use_safe_problem_envelopes(b2_client, query):
    response = b2_client.get("/api/v1/historical-events", params=query)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["instance"] == "/api/v1/historical-events"


def test_private_or_signed_event_urls_are_not_exposed(b2_client, b2_session):
    row = event(b2_session)
    row.source_urls = ["file:///D:/private/config", "https://user:private-secret@example.org/source",
        "https://example.org/source?token=private-secret", "http://127.0.0.1/internal",
        "https://example.org/public-source"]
    b2_session.flush()
    response = b2_client.get("/api/v1/historical-events")
    assert response.status_code == 200
    assert response.json()["items"][0]["source_urls"] == ["https://example.org/public-source"]
    assert "private-secret" not in response.text and "file:" not in response.text
