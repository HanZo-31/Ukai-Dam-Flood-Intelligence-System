import pytest
from sqlalchemy.exc import OperationalError

from services.api.app.repositories.catalog_repository import HistoricalEventRepository
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.repositories.status_repository import StatusRepository


@pytest.mark.parametrize("path,repository,method", [
    ("/api/v1/historical-events", HistoricalEventRepository, "list"),
    ("/api/v1/status/current", StatusRepository, "latest"),
    ("/api/v1/scenarios/b2-approved-001/impact", PublishedScenarioRepository, "summary"),
])
def test_database_failure_is_safe_on_every_new_endpoint(b2_client, scenario_factory, monkeypatch, path, repository, method):
    scenario_factory()
    def fail(*args, **kwargs):
        raise OperationalError("SELECT private_table", {}, RuntimeError("password=private-secret"))
    monkeypatch.setattr(repository, method, fail)
    response = b2_client.get(path)
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert "private" not in response.text and "SELECT" not in response.text


def test_new_response_models_and_problem_media_types_are_in_openapi(b2_client):
    spec = b2_client.get("/openapi.json").json()
    expected = {
        "/api/v1/scenarios/{scenario_id}/impact": "ScenarioImpactResponse",
        "/api/v1/historical-events": "HistoricalEventListResponse",
        "/api/v1/status/current": "CurrentStatusResponse",
    }
    for path, schema in expected.items():
        responses = spec["paths"][path]["get"]["responses"]
        assert responses["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/" + schema)
        assert "application/problem+json" in responses["503"]["content"]
