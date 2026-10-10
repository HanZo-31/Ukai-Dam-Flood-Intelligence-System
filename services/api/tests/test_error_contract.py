"""Cross-endpoint failure contracts, safe details, and dependency cleanup."""
import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from services.api.app.api_schemas.scenario import OffsetPagination
from services.api.app.main import app
from services.api.app.services.historical_event_service import get_historical_event_service
from services.api.app.services.scenario_service import get_scenario_service
from services.api.app.services.status_service import get_status_service

ROUTES = [
    ("/api/v1/scenarios", get_scenario_service),
    ("/api/v1/scenarios/b2-approved-001", get_scenario_service),
    ("/api/v1/scenarios/b2-approved-001/layers", get_scenario_service),
    ("/api/v1/scenarios/b2-approved-001/impact", get_scenario_service),
    ("/api/v1/scenarios/b2-approved-001/assets/export_geojson", get_scenario_service),
    ("/api/v1/scenarios/b2-approved-001/assumptions", get_scenario_service),
    ("/api/v1/exports/b2-approved-001?format=geojson", get_scenario_service),
    ("/api/v1/historical-events", get_historical_event_service),
    ("/api/v1/status/current", get_status_service),
]


@pytest.mark.parametrize("path,dependency", ROUTES)
@pytest.mark.parametrize("failure,status", [("database", 503), ("validation", 503), ("unexpected", 500)])
def test_failures_have_consistent_private_safe_envelopes(path, dependency, failure, status):
    class BrokenService:
        def __getattr__(self, method):
            def fail(*args, **kwargs):
                if failure == "database":
                    raise OperationalError("SELECT private-secret", {}, RuntimeError("password=private-secret"))
                if failure == "validation":
                    OffsetPagination(limit="private-secret", offset=0)
                raise RuntimeError("file:///private-secret")
            return fail

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[dependency] = lambda: BrokenService()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(path + ("&" if "?" in path else "?") + "ignored=private-secret")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    body = response.json()
    assert body["status"] == status and body["type"] == "about:blank"
    assert body["instance"] == path.split("?")[0]
    assert set(body) == {"type", "title", "status", "detail", "instance"}
    assert "private-secret" not in response.text and "SELECT" not in response.text


@pytest.mark.parametrize("path,dependency", [ROUTES[0], ROUTES[1], ROUTES[2], ROUTES[3], ROUTES[6], ROUTES[7], ROUTES[8]])
def test_invalid_service_response_is_unavailable_not_invalid_client_input(path, dependency):
    class InvalidResponseService:
        def __getattr__(self, method):
            return lambda *args, **kwargs: {"private": "private-secret"}

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[dependency] = lambda: InvalidResponseService()
    try:
        with TestClient(app) as client:
            response = client.get(path)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    assert response.status_code == 503 and "private-secret" not in response.text


@pytest.mark.parametrize("path", ["/api/v1/scenarios", "/api/v1/historical-events"])
def test_bad_time_window_remains_a_client_error(path):
    response = TestClient(app).get(path, params={
        "start": "2026-01-02T00:00:00Z", "end": "2026-01-01T00:00:00Z",
    })
    assert response.status_code == 422 and response.json()["status"] == 422


def test_dataset_version_requires_dataset_identity_before_repository_use():
    response = TestClient(app).get("/api/v1/scenarios?dataset_version=private-secret")
    assert response.status_code == 422 and "private-secret" not in response.text


def test_unknown_route_and_disallowed_method_use_problem_contract():
    with TestClient(app) as client:
        missing = client.get("/api/v1/does-not-exist?token=private-secret")
        method = client.post("/api/v1/health", json={"private": "private-secret"})
    assert missing.status_code == 404 and method.status_code == 405
    assert "GET" in method.headers["allow"]
    for response in (missing, method):
        assert response.headers["content-type"] == "application/problem+json"
        assert "private-secret" not in response.text


@pytest.mark.parametrize("module_name,function_name", [
    ("scenario_service", "get_scenario_service"),
    ("historical_event_service", "get_historical_event_service"),
    ("status_service", "get_status_service"),
])
@pytest.mark.parametrize("exceptional", [False, True])
def test_request_session_is_closed_on_success_and_failure(monkeypatch, module_name, function_name, exceptional):
    module = importlib.import_module("services.api.app.services." + module_name)
    session = type("TrackedSession", (), {"closed": False, "close": lambda self: setattr(self, "closed", True)})()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)
    dependency = getattr(module, function_name)()
    next(dependency)
    if exceptional:
        with pytest.raises(RuntimeError):
            dependency.throw(RuntimeError("Synthetic request failure"))
    else:
        dependency.close()
    assert session.closed


def test_each_data_endpoint_documents_safe_server_error_responses():
    spec = TestClient(app).get("/openapi.json").json()
    for path, methods in spec["paths"].items():
        if path == "/api/v1/health":
            continue
        for code in ("500", "503"):
            assert "application/problem+json" in methods["get"]["responses"][code]["content"]
    export = spec["paths"]["/api/v1/exports/{scenario_id}"]["get"]
    assert export["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/ScenarioExportResponse")
    assert next(query for query in export["parameters"] if query["name"] == "format")["required"] is True
