"""Approved derivative discovery and delivery, without generating exports."""
from datetime import datetime, timezone
import hashlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from services.api.app.api_schemas.export import ScenarioExportResponse
from services.api.app.db.models import ResultAsset
from services.api.app.main import app
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.services.scenario_service import ScenarioService, get_scenario_service
from services.api.app.storage import LocalObjectStore


def test_registered_geojson_export_has_a_working_verified_link(b2_client, scenario_factory):
    item = scenario_factory(exports=True)
    response = b2_client.get(f"/api/v1/exports/{item.scenario_id}?format=geojson")
    assert response.status_code == 200
    body = response.json()
    ScenarioExportResponse.model_validate(body)
    assert body["checksum"] == item.asset_metadata["export_geojson"].checksum
    assert body["model_version"] == item.model_version
    assert body["input_dataset_version"] == item.input_dataset_version
    assert body["data_mode"] == body["data_kind"] == "demo"
    assert body["crs"] == "EPSG:4326" and body["unit"] == "1"
    assert body["format"] == "geojson" and body["asset_type"] == "export_geojson"
    assert body["coverage_start"].endswith("Z") and body["coverage_end"].endswith("Z")
    assert body["download_url"].endswith("/assets/export_geojson?data_mode=demo")
    assert response.headers["cache-control"] == "no-store"
    for private in ("file:", "storage_uri", "manifest_json", "source_reference"):
        assert private not in response.text
    download = b2_client.get(body["download_url"])
    assert download.status_code == 200 and download.headers["content-type"] == "application/geo+json"
    assert "sha256:" + hashlib.sha256(download.content).hexdigest() == body["checksum"]
    assert download.json()["synthetic"] is True
    assert download.headers["content-disposition"] == 'attachment; filename="export_geojson.geojson"'
    partial = b2_client.get(body["download_url"], headers={"Range": "bytes=0-9"})
    assert partial.status_code == 206 and partial.content == download.content[:10]
    head = b2_client.head(body["download_url"])
    assert head.status_code == 200 and head.content == b""
    assert int(head.headers["content-length"]) == len(download.content)
    layers = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/layers").json()["layers"]
    assert "export_geojson" not in {layer["asset_type"] for layer in layers}


@pytest.mark.parametrize("format", ["geojson", "kml"])
def test_no_derivative_means_no_fabricated_link_or_extent_fallback(b2_client, scenario_factory, format):
    item = scenario_factory()
    response = b2_client.get(f"/api/v1/exports/{item.scenario_id}", params={"format": format})
    assert response.status_code == 404 and "download_url" not in response.text
    assert b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/assets/extent_geojson").status_code == 200


@pytest.mark.parametrize("status", ["draft", "rejected", "revoked"])
@pytest.mark.parametrize("format", ["geojson", "kml"])
def test_unpublished_scenarios_cannot_offer_exports(b2_client, scenario_factory, status, format):
    item = scenario_factory(status=status, exports=True)
    response = b2_client.get(f"/api/v1/exports/{item.scenario_id}", params={"format": format})
    assert response.status_code == 404


def test_mode_isolation_and_revocation_protect_previous_export_link(b2_client, b2_session, scenario_factory):
    item = scenario_factory(exports=True)
    base = f"/api/v1/exports/{item.scenario_id}"
    assert b2_client.get(base + "?format=geojson&data_mode=production").status_code == 404
    body = b2_client.get(base + "?format=geojson&data_mode=demo").json()
    assert b2_client.get(body["download_url"] + "&data_mode=production").status_code == 404
    PublishedScenarioRepository(b2_session).revoke(item.scenario_id, actor="b2-test", reason="Test withdrawal")
    assert b2_client.get(base + "?format=geojson").status_code == 404
    assert b2_client.get(body["download_url"]).status_code == 404


@pytest.mark.parametrize("fault", ["missing", "changed", "remote", "outside", "checksum", "format", "unit", "crs"])
def test_unavailable_or_invalid_exports_do_not_advertise_a_link(
    b2_client, b2_session, scenario_factory, scenario_store, tmp_path, fault,
):
    item = scenario_factory(exports=True)
    asset = b2_session.scalar(select(ResultAsset).where(ResultAsset.asset_type == "export_geojson"))
    if fault == "missing":
        scenario_store.resolve_uri(asset.storage_uri).unlink()
    elif fault == "changed":
        scenario_store.resolve_uri(asset.storage_uri).write_bytes(b"private-secret: changed bytes")
    elif fault == "remote":
        asset.storage_uri = "https://example.org/export?token=private-secret"
    elif fault == "outside":
        asset.storage_uri = (tmp_path / "private-secret.geojson").as_uri()
    elif fault == "checksum":
        asset.checksum = "private-secret"
    elif fault == "format":
        asset.format = "kml"
    elif fault == "unit":
        asset.unit = "m"
    else:
        asset.crs = "private-secret"
    b2_session.flush()
    response = b2_client.get(f"/api/v1/exports/{item.scenario_id}?format=geojson")
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert "private-secret" not in response.text and "download_url" not in response.text
    if fault in {"format", "unit"}:
        assert b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/assets/export_geojson").status_code == 503


@pytest.mark.parametrize("query", ["", "?format=csv", "?format=../private-secret", "?format=geojson&data_mode=live"])
def test_export_format_is_explicit_and_validated_before_repository_use(query):
    response = TestClient(app).get("/api/v1/exports/b2-approved-001" + query)
    assert response.status_code == 422 and "private-secret" not in response.text


def test_discovery_is_rechecked_when_source_changes(b2_client, scenario_factory, b2_session, scenario_store):
    item = scenario_factory(exports=True)
    body = b2_client.get(f"/api/v1/exports/{item.scenario_id}?format=geojson").json()
    asset = b2_session.scalar(select(ResultAsset).where(ResultAsset.asset_type == "export_geojson"))
    scenario_store.resolve_uri(asset.storage_uri).write_bytes(b"Changed after discovery")
    assert b2_client.get(body["download_url"]).status_code == 503


def test_kml_delivery_adapter_preserves_bytes_but_does_not_claim_gis_acceptance(tmp_path):
    # Unit adapter test only: B1's current GISInspector cannot approve KML.
    # No KML bundle/approval is registered in any database by this test.
    store = LocalObjectStore(tmp_path / "objects")
    content = b'<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Synthetic transport fixture only</name></Document></kml>'
    uri, checksum = store.put("exports/synthetic.kml", content)
    time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = SimpleNamespace(scenario_id="b2-kml-unit", model_version="synthetic-1",
                          input_dataset_version="synthetic-1", data_mode="demo", data_kind="demo")
    asset = SimpleNamespace(format="kml", crs="EPSG:4326", unit="1", checksum=checksum,
                            coverage_start=time, coverage_end=time, storage_uri=uri)

    class StubApprovedRepository:
        def get(self, scenario_id, *, data_mode):
            assert scenario_id == row.scenario_id and data_mode == "demo"
            return row

        def assets(self, scenario_id, *, data_mode, asset_type, limit):
            assert data_mode == "demo" and asset_type == "export_kml" and limit == 1
            return [asset]

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_scenario_service] = lambda: ScenarioService(StubApprovedRepository(), store)
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/exports/b2-kml-unit?format=kml")
            assert response.status_code == 200
            body = response.json()
            assert body["format"] == "kml" and body["checksum"] == checksum
            download = client.get(body["download_url"])
            assert download.status_code == 200 and download.content == content
            assert download.headers["content-type"] == "application/vnd.google-earth.kml+xml"
            assert download.headers["content-disposition"] == 'attachment; filename="export_kml.kml"'
            assert download.headers["x-content-type-options"] == "nosniff"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
