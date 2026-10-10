from fastapi.testclient import TestClient
from services.api.app.main import app


def test_health_reports_versioned_service_identity() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ukai-flood-api", "api_version": "v1"}
