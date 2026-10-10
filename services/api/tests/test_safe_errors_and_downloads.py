"""Security failures return problem responses; verified snapshots resist drift."""
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from services.api.app.main import app
from services.api.app.services.asset_service import verified_download
from services.api.app.services.scenario_service import get_scenario_service
from services.api.app.storage import LocalObjectStore


@pytest.mark.parametrize("error,status", [
    (OperationalError("SELECT private_table", {}, RuntimeError("password=private-secret")), 503),
    (RuntimeError("D:/private-config/private-secret"), 500),
])
def test_internal_failures_never_echo_private_details(error, status):
    class BrokenService:
        def list_scenarios(self, **kwargs):
            raise error

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_scenario_service] = lambda: BrokenService()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/scenarios?model_version=private-secret")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["instance"] == "/api/v1/scenarios"
    assert "private" not in response.text and "SELECT" not in response.text


def test_download_reads_verified_snapshot_after_source_changes(tmp_path):
    store = LocalObjectStore(tmp_path / "objects")
    content = b"Approved original bytes"
    uri, checksum = store.put("results/original.geojson", content)
    download = verified_download(store, uri, checksum,
        media_type="application/geo+json", filename="extent.geojson")
    # Test-only drift after verification cannot change bytes sent to the client.
    store.resolve_uri(uri).write_bytes(b"Changed private bytes")
    assert b"".join(download.chunks(0, download.size)) == content
    assert download.handle.closed
    assert download.checksum == "sha256:" + hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize("suffix", ["/assets/not-a-registered-role", "/assets/private-config.txt"])
def test_download_role_cannot_select_an_arbitrary_path(b2_client, scenario_factory, suffix):
    item = scenario_factory()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}{suffix}")
    assert response.status_code == 422
    assert response.json()["detail"] == "The request parameters are invalid."


def test_range_end_is_clipped_and_if_range_etag_is_respected(b2_client, scenario_factory):
    item = scenario_factory()
    url = f"/api/v1/scenarios/{item.scenario_id}/assets/max_depth_cog"
    full = b2_client.get(url)
    clipped = b2_client.get(url, headers={"Range": "bytes=0-99999999"})
    assert clipped.status_code == 206 and clipped.content == full.content
    partial = b2_client.get(url, headers={"Range": "bytes=0-3", "If-Range": full.headers["etag"]})
    assert partial.status_code == 206 and partial.content == full.content[:4]
