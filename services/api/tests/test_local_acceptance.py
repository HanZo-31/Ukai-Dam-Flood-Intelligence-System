"""Engineering flow only: four synthetic bundles, not scientific acceptance."""
import hashlib
from services.api.app.repositories.status_repository import StatusRepository


def test_one_replay_and_three_hypotheticals_roundtrip_across_b2(b2_client, b2_session, scenario_factory):
    items = [scenario_factory("b2-replay", historical_event_id="b2-synthetic-event", exports=True)]
    items += [scenario_factory(f"b2-hypothetical-{index}", exports=True) for index in range(1, 4)]
    scenario_factory("b2-hidden-draft", status="draft", exports=True)
    StatusRepository(b2_session).add(reading_time=items[0].time_coverage.start, data_mode="demo")
    assert b2_client.get("/api/v1/health").json()["status"] == "ok"
    collected = []
    offset = 0
    while True:
        page = b2_client.get("/api/v1/scenarios", params={"limit": 2, "offset": offset}).json()
        collected.extend(row["scenario_id"] for row in page["items"])
        offset = page["pagination"]["next_offset"]
        if offset is None:
            break
    assert collected == sorted(item.scenario_id for item in items)
    for item in items:
        base = f"/api/v1/scenarios/{item.scenario_id}"
        detail = b2_client.get(base).json()
        impact = b2_client.get(base + "/impact").json()
        assert detail["summary"] == {key: impact[key] for key in type(item.summary).model_fields}
        assert detail["data_mode"] == detail["data_kind"] == "demo"
        for layer in b2_client.get(detail["links"]["layers"]).json()["layers"]:
            download = b2_client.get(layer["url"])
            assert download.status_code == 200
            assert "sha256:" + hashlib.sha256(download.content).hexdigest() == layer["checksum"]
        export = b2_client.get(f"/api/v1/exports/{item.scenario_id}?format=geojson").json()
        download = b2_client.get(export["download_url"])
        assert "sha256:" + hashlib.sha256(download.content).hexdigest() == export["checksum"]
        assert b2_client.get(detail["assumptions"]["url"]).status_code == 200
    event = b2_client.get("/api/v1/historical-events").json()["items"][0]
    assert event["event_id"] == "b2-synthetic-event" and event["replay"]["available"] is True
    assert [row["scenario_id"] for row in b2_client.get(event["replay"]["scenarios_url"]).json()["items"]] == ["b2-replay"]
    status = b2_client.get("/api/v1/status/current").json()
    assert status["is_live"] is False and status["data_mode"] == "demo"
    assert status["timestamp"] == items[0].time_coverage.start.isoformat().replace("+00:00", "Z")
    assert b2_client.get("/api/v1/scenarios?data_mode=production").json()["items"] == []
