"""Exercise approved details and usable layer links against B1's real fixture."""
import hashlib

import pytest
from sqlalchemy import select

from services.api.app.api_schemas.layer import ScenarioLayersResponse
from services.api.app.api_schemas.scenario import ScenarioDetail
from services.api.app.db.models import ProcessingRun, PublishedBundle, ResultAsset, Scenario
from services.api.app.repositories.published_repository import PublishedScenarioRepository


def assert_private_fields_absent(response):
    for private in ("file:", "storage_uri", "bundle_root_uri", "manifest_json",
                    "registered_by", "source_reference", "quality_report_uri", "log_uri"):
        assert private not in response.text


def test_detail_preserves_parameters_units_summary_and_run_provenance(b2_client, scenario_factory):
    item = scenario_factory()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}?data_mode=demo")
    assert response.status_code == 200
    body = response.json()
    ScenarioDetail.model_validate(body)
    assert body["parameters"] == item.parameters.model_dump()
    assert body["parameter_units"] == item.parameter_units.model_dump()
    assert body["summary"] == item.summary.model_dump()
    assert body["summary"]["population_exposed"] is None
    assert body["quality"]["validation_status"] == "pass"
    assert body["run_timestamp"] == "2026-10-05T10:00:00Z"
    assert body["run_id"] == item.run_id
    assert body["datasets"][0]["checksum"] == item.datasets[0].checksum
    assert body["datasets"][0]["source_label"] == "demo"
    assert body["assumptions"]["checksum"] == item.assumptions_checksum
    assert_private_fields_absent(response)
    for link in body["links"].values():
        assert link.startswith("/api/v1/scenarios/") and "data_mode=demo" in link
        assert b2_client.get(link).status_code == 200
    assumptions = b2_client.get(body["assumptions"]["url"])
    assert assumptions.status_code == 200
    assert "Synthetic GIS fixture" in assumptions.text
    assert "sha256:" + hashlib.sha256(assumptions.content).hexdigest() == item.assumptions_checksum
    assert assumptions.headers["content-type"].startswith("text/plain")


def test_layer_metadata_and_every_download_match_registered_bytes(b2_client, scenario_factory):
    item = scenario_factory()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}/layers")
    assert response.status_code == 200
    body = response.json()
    ScenarioLayersResponse.model_validate(body)
    assert body["model_version"] == item.model_version
    assert body["data_mode"] == body["data_kind"] == "demo"
    assert [layer["asset_type"] for layer in body["layers"]] == sorted(item.assets)
    assert_private_fields_absent(response)
    for layer in body["layers"]:
        expected = item.asset_metadata[layer["asset_type"]]
        assert layer["unit"] == expected.unit
        assert layer["format"] == expected.format
        assert layer["checksum"] == expected.checksum
        assert layer["coverage_start"].endswith("Z")
        download = b2_client.get(layer["url"])
        assert download.status_code == 200
        assert "sha256:" + hashlib.sha256(download.content).hexdigest() == layer["checksum"]
        assert download.headers["cache-control"] == "no-store"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert "file:" not in str(dict(download.headers))
        if layer["format"] == "geojson":
            assert download.headers["content-type"] == "application/geo+json"
            assert download.json()["synthetic"] is True
        else:
            assert download.headers["content-type"] == "image/tiff"


@pytest.mark.parametrize("status", ["draft", "rejected", "revoked"])
@pytest.mark.parametrize("suffix", ["", "/layers", "/assumptions", "/assets/max_depth_cog"])
def test_unpublished_records_are_hidden_on_all_new_routes(b2_client, scenario_factory, status, suffix):
    item = scenario_factory(status=status)
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}{suffix}")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == 404
    assert_private_fields_absent(response)


@pytest.mark.parametrize("suffix", ["", "/layers", "/assumptions", "/assets/max_depth_cog"])
def test_wrong_mode_and_unknown_id_return_same_not_found(b2_client, scenario_factory, suffix):
    item = scenario_factory()
    wrong = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}{suffix}?data_mode=production")
    missing = b2_client.get(f"/api/v1/scenarios/missing-scenario{suffix}")
    assert wrong.status_code == missing.status_code == 404
    assert wrong.json()["detail"] == missing.json()["detail"]


def test_previously_issued_links_stop_working_after_revocation(b2_client, b2_session, scenario_factory):
    item = scenario_factory()
    detail = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}").json()
    layer = b2_client.get(detail["links"]["layers"]).json()["layers"][0]
    assert b2_client.get(layer["url"]).status_code == 200
    PublishedScenarioRepository(b2_session).revoke(item.scenario_id, actor="b2-test-operator", reason="Test withdrawal")
    for url in (layer["url"], detail["assumptions"]["url"], detail["links"]["self"]):
        assert b2_client.get(url).status_code == 404
    assert b2_client.head(layer["url"]).status_code == 404


@pytest.mark.parametrize("mutation", ["run_failed", "bundle_missing", "summary_missing"])
def test_incomplete_registered_state_never_returns_detail(b2_client, b2_session, scenario_factory, mutation):
    from services.api.app.db.models import ImpactSummary
    item = scenario_factory()
    if mutation == "run_failed":
        row = b2_session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == item.run_id))
        row.status = "failed"
    elif mutation == "bundle_missing":
        b2_session.delete(b2_session.scalar(select(PublishedBundle)))
    else:
        b2_session.delete(b2_session.scalar(select(ImpactSummary)))
    b2_session.flush()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}")
    assert response.status_code == (503 if mutation == "summary_missing" else 404)
    assert_private_fields_absent(response)


def test_asset_lookup_is_scoped_to_scenario_and_role(b2_client, b2_session, scenario_factory):
    first = scenario_factory("b2-first")
    scenario_factory("b2-second")
    row = b2_session.scalar(select(ResultAsset).where(ResultAsset.scenario_id == first.scenario_id,
        ResultAsset.asset_type == "max_depth_cog"))
    # Simulate a mismatched asset mode without violating B1's spatial foreign keys.
    row.data_mode = "production"
    b2_session.flush()
    assert b2_client.get("/api/v1/scenarios/b2-first/assets/max_depth_cog").status_code == 404
    assert b2_client.get("/api/v1/scenarios/b2-second/assets/max_depth_cog").status_code == 200
    assert b2_client.get("/api/v1/scenarios/b2-second/assets/export_kml").status_code == 404


@pytest.mark.parametrize("target", ["asset", "assumptions"])
@pytest.mark.parametrize("mutation", ["missing", "checksum", "outside_root", "remote"])
def test_unavailable_or_unsafe_storage_is_never_served(b2_client, b2_session, scenario_factory, scenario_store, tmp_path, target, mutation):
    item = scenario_factory()
    if target == "asset":
        row = b2_session.scalar(select(ResultAsset).where(ResultAsset.asset_type == "max_depth_cog"))
        uri_field, checksum_field = "storage_uri", "checksum"
        suffix = "/assets/max_depth_cog"
    else:
        row = b2_session.scalar(select(Scenario))
        uri_field, checksum_field = "assumptions_url", "assumptions_checksum"
        suffix = "/assumptions"
    if mutation == "missing":
        setattr(row, uri_field, (scenario_store.root / "missing-object").as_uri())
    elif mutation == "checksum":
        setattr(row, checksum_field, "sha256:" + "0" * 64)
    elif mutation == "outside_root":
        setattr(row, uri_field, (tmp_path / "private-config.txt").as_uri())
    else:
        setattr(row, uri_field, "s3://private-bucket/internal-file")
    b2_session.flush()
    response = b2_client.get(f"/api/v1/scenarios/{item.scenario_id}{suffix}")
    assert response.status_code == 503
    assert_private_fields_absent(response)
    for private in ("private-config", "private-bucket", str(tmp_path)):
        assert private not in response.text


@pytest.mark.parametrize("range_header,expected", [
    ("bytes=0-15", (0, 16)), ("bytes=8-", (8, None)), ("bytes=-12", (-12, None)),
])
def test_cog_range_and_head_responses(b2_client, scenario_factory, range_header, expected):
    item = scenario_factory()
    url = f"/api/v1/scenarios/{item.scenario_id}/assets/max_depth_cog"
    full = b2_client.get(url)
    response = b2_client.get(url, headers={"Range": range_header})
    assert response.status_code == 206
    start, stop = expected
    assert response.content == full.content[start:stop]
    assert response.headers["content-range"].endswith("/" + str(len(full.content)))
    assert int(response.headers["content-length"]) == len(response.content)
    head = b2_client.head(url)
    assert head.status_code == 200 and head.content == b""
    assert int(head.headers["content-length"]) == len(full.content)
    assert head.headers["accept-ranges"] == "bytes"
    fallback = b2_client.get(url, headers={"Range": "bytes=0-15", "If-Range": '"old"'})
    assert fallback.status_code == 200 and fallback.content == full.content


@pytest.mark.parametrize("header", ["bytes=99999999-", "bytes=9-2", "bytes=-0", "bytes=", "bytes=0-1,4-5", "bytes=a-b"])
def test_invalid_or_multiple_ranges_return_safe_416(b2_client, scenario_factory, header):
    item = scenario_factory()
    url = f"/api/v1/scenarios/{item.scenario_id}/assets/max_depth_cog"
    response = b2_client.get(url, headers={"Range": header})
    assert response.status_code == 416
    assert response.headers["content-range"].startswith("bytes */")
    assert response.headers["content-type"] == "application/problem+json"


def test_openapi_describes_details_layers_and_problem_responses(b2_client):
    specification = b2_client.get("/openapi.json").json()
    paths = specification["paths"]
    assert paths["/api/v1/scenarios/{scenario_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/ScenarioDetail")
    assert paths["/api/v1/scenarios/{scenario_id}/layers"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/ScenarioLayersResponse")
    assert "application/problem+json" in paths["/api/v1/scenarios/{scenario_id}"]["get"]["responses"]["404"]["content"]
    operations = [operation["operationId"] for path in paths.values() for method, operation in path.items() if method in {"get", "head"}]
    assert len(operations) == len(set(operations))
