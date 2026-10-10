from datetime import datetime, timezone
from fastapi.testclient import TestClient
from services.api.app.main import app
from services.api.app.api_schemas.scenario import OffsetPagination, ScenarioListResponse, ScenarioSummary
from services.api.app.services.scenario_service import get_scenario_service


class FakeScenarioService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def list_scenarios(self, **kwargs):
        self.calls.append(kwargs)
        return ScenarioListResponse(items=[ScenarioSummary(
            scenario_id="ukai-synthetic-hypothetical-v1", scenario_type="hypothetical",
            model_version="synthetic-contract-fixture-1.0.0", input_dataset_version="synthetic-input-release-1.0.0",
            crs="EPSG:32643", data_mode="demo", data_kind="demo",
            coverage_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            coverage_end=datetime(2026, 1, 1, 6, tzinfo=timezone.utc))],
            pagination=OffsetPagination(limit=kwargs["limit"], offset=kwargs["offset"]))


def test_scenarios_use_explicit_mode_and_return_public_schema() -> None:
    fake = FakeScenarioService()
    app.dependency_overrides[get_scenario_service] = lambda: fake
    try:
        response = TestClient(app).get("/api/v1/scenarios?data_mode=demo&limit=10&offset=3")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "approved"
    assert fake.calls[0]["data_mode"] == "demo"
    assert fake.calls[0]["limit"] == 10
    assert fake.calls[0]["offset"] == 3


def test_scenarios_reject_an_unknown_mode_before_a_repository_is_used() -> None:
    assert TestClient(app).get("/api/v1/scenarios?data_mode=unsafe").status_code == 422
