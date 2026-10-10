"""Step 16: specification conformance, reproducible export and real examples."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from sqlalchemy import select

from services.api.app.api_schemas.export import ScenarioExportResponse
from services.api.app.api_schemas.health import HealthResponse
from services.api.app.api_schemas.historical_event import HistoricalEventListResponse
from services.api.app.api_schemas.impact import ScenarioImpactResponse
from services.api.app.api_schemas.layer import ScenarioLayersResponse
from services.api.app.api_schemas.problem import Problem
from services.api.app.api_schemas.scenario import ScenarioDetail, ScenarioListResponse
from services.api.app.api_schemas.status import CurrentStatusResponse
from services.api.app.catalog_schemas import HistoricalEventCreate
from services.api.app.db.models import ResultAsset
from services.api.app.main import app
from services.api.app.openapi import ASSET_PATH, ASSUMPTIONS_PATH, JSON_ENDPOINTS, load_examples
from services.api.app.repositories.catalog_repository import HistoricalEventRepository
from services.api.app.repositories.status_repository import StatusRepository
from services.api.app.services.scenario_service import get_scenario_service

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "docs/contracts/b2-openapi-v1.json"
MODELS = {"health": HealthResponse, "scenario_list": ScenarioListResponse,
          "scenario_detail": ScenarioDetail, "layers": ScenarioLayersResponse,
          "impact": ScenarioImpactResponse, "historical_events": HistoricalEventListResponse,
          "current_status": CurrentStatusResponse, "export": ScenarioExportResponse}
NOTICE = "Synthetic HTTP examples only; not predictions, observations, or scientific approval."


def platform_fixture_expected(actual, documented):
    """Adapt only native COG fixture hashes/sizes, never API/scientific fields.

    Native GDAL wheels encode different TIFF bytes across platforms. Actual byte
    hashes/ranges/HEAD remain verified; stored examples are never overwritten.
    """
    expected = deepcopy(documented)
    expected_layers = expected["responses"]["layers"]["layers"]
    actual_layers = actual["responses"]["layers"]["layers"]
    assert len(expected_layers) == len(actual_layers)
    for left, right in zip(expected_layers, actual_layers):
        assert left["asset_type"] == right["asset_type"]
        if left["asset_type"] in {"max_depth_cog", "max_velocity_cog", "arrival_time_cog"}:
            left["checksum"] = right["checksum"]
    depth = next(layer for layer in actual_layers if layer["asset_type"] == "max_depth_cog")
    cog = actual["downloads"]["cog"]
    assert cog["headers"]["etag"] == cog["partial_headers"]["etag"] == '"' + depth["checksum"] + '"'
    size = int(cog["headers"]["content-length"])
    assert size >= 16 and cog["partial_headers"]["content-range"] == f"bytes 0-15/{size}"
    expected_cog = expected["downloads"]["cog"]
    expected_cog["headers"]["etag"] = cog["headers"]["etag"]
    expected_cog["headers"]["content-length"] = cog["headers"]["content-length"]
    expected_cog["partial_headers"]["etag"] = cog["partial_headers"]["etag"]
    expected_cog["partial_headers"]["content-range"] = cog["partial_headers"]["content-range"]
    return expected


def test_native_cog_fixture_metadata_can_vary_without_changing_contract():
    documented = load_examples()
    actual = deepcopy(documented)
    for layer in actual["responses"]["layers"]["layers"]:
        if layer["asset_type"].endswith("_cog"):
            layer["checksum"] = "sha256:" + "a" * 64
    cog = actual["downloads"]["cog"]
    cog["headers"].update(etag='"sha256:' + "a" * 64 + '"', **{"content-length": "3000"})
    cog["partial_headers"].update(etag=cog["headers"]["etag"], **{"content-range": "bytes 0-15/3000"})
    assert actual == platform_fixture_expected(actual, documented)
    assert documented == load_examples()


def test_platform_fixture_comparison_does_not_mask_impact_drift():
    actual = deepcopy(load_examples())
    actual["responses"]["impact"]["max_depth_m"] = 999
    assert actual != platform_fixture_expected(actual, load_examples())


def test_platform_fixture_comparison_rejects_unmatched_etag():
    actual = deepcopy(load_examples())
    actual["downloads"]["cog"]["headers"]["etag"] = '"sha256:' + "b" * 64 + '"'
    with pytest.raises(AssertionError):
        platform_fixture_expected(actual, load_examples())


def test_platform_fixture_comparison_preserves_layer_role_order():
    actual = deepcopy(load_examples())
    actual["responses"]["layers"]["layers"].reverse()
    with pytest.raises(AssertionError):
        platform_fixture_expected(actual, load_examples())


@pytest.fixture
def specification():
    previous = app.openapi_schema
    app.openapi_schema = None
    try:
        yield app.openapi()
    finally:
        app.openapi_schema = previous


def test_documented_examples_match_real_isolated_http_responses(
    b2_client, b2_session, scenario_factory, request,
):
    item = scenario_factory(exports=True)
    HistoricalEventRepository(b2_session).register(HistoricalEventCreate(
        event_id="b2-catalog-event", name="Synthetic event metadata for HTTP testing",
        time_coverage={"start": "1998-01-01T00:00:00Z", "end": "1998-01-02T00:00:00Z"},
        observed_coverage="Synthetic fixture; no observed historical data claimed",
        quality_notes="Internal test note", source_urls=["https://example.org/synthetic-event"],
        data_mode="demo",
    ))
    StatusRepository(b2_session).add(reading_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        reservoir_level_m=101.25, inflow_m3s=20.0, release_m3s=15.0, data_mode="demo")
    responses = {}
    for path, name in JSON_ENDPOINTS.items():
        url = path.replace("{scenario_id}", item.scenario_id)
        if name == "export":
            url += "?format=geojson&data_mode=demo"
        response = b2_client.get(url)
        assert response.status_code == 200
        responses[name] = response.json()
        MODELS[name].model_validate(responses[name])
    downloads = {}
    base = f"/api/v1/scenarios/{item.scenario_id}"
    for name, suffix, checksum in (
        ("cog", "/assets/max_depth_cog?data_mode=demo", item.asset_metadata["max_depth_cog"].checksum),
        ("geojson", "/assets/export_geojson?data_mode=demo", item.asset_metadata["export_geojson"].checksum),
        ("assumptions", "/assumptions?data_mode=demo", item.assumptions_checksum),
    ):
        url = base + suffix
        response = b2_client.get(url)
        assert response.status_code == 200
        assert "sha256:" + hashlib.sha256(response.content).hexdigest() == checksum
        assert response.headers["etag"] == '"' + checksum + '"'
        assert int(response.headers["content-length"]) == len(response.content)
        entry = {"url": url, "media_type": response.headers["content-type"],
                 "headers": {key: response.headers[key] for key in (
                     "content-length", "etag", "content-disposition", "accept-ranges",
                     "cache-control", "x-content-type-options")}}
        if name == "assumptions":
            entry["text"] = response.text
        if name == "geojson":
            entry["geojson"] = response.json()
        partial = b2_client.get(url, headers={"Range": "bytes=0-15"})
        assert partial.status_code == 206 and partial.content == response.content[:16]
        assert partial.headers["content-range"] == f"bytes 0-15/{len(response.content)}"
        entry["partial_headers"] = {key: partial.headers[key] for key in ("content-length", "content-range", "etag")}
        head = b2_client.head(url)
        assert head.status_code == 200 and head.content == b""
        assert head.headers["content-length"] == response.headers["content-length"]
        downloads[name] = entry
    problems = {}
    cases = {
        "not_found": ("get", "/api/v1/scenarios/b2-missing", 404),
        "method_not_allowed": ("post", "/api/v1/health", 405),
        "invalid_request": ("get", "/api/v1/scenarios?limit=0", 422),
    }
    for name, (method, url, status) in cases.items():
        response = getattr(b2_client, method)(url)
        assert response.status_code == status
        problems[name] = response.json()
    response = b2_client.get(base + "/assets/max_depth_cog", headers={"Range": "bytes=9-2"})
    assert response.status_code == 416
    problems["range"] = response.json()
    asset = b2_session.scalar(select(ResultAsset).where(ResultAsset.asset_type == "export_geojson"))
    original_uri = asset.storage_uri
    try:
        asset.storage_uri = "s3://unavailable-test-only/export.geojson"
        b2_session.flush()
        response = b2_client.get(base + "/assets/export_geojson")
        assert response.status_code == 503
        problems["unavailable"] = response.json()
    finally:
        asset.storage_uri = original_uri
        b2_session.flush()
    previous = app.dependency_overrides.copy()
    class BrokenService:
        def list_scenarios(self, **kwargs):
            raise RuntimeError("Internal synthetic error, not public")
    try:
        app.dependency_overrides[get_scenario_service] = lambda: BrokenService()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/scenarios")
        assert response.status_code == 500
        problems["unexpected"] = response.json()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    # A missing stored status is a distinct 404, not a missing scenario.
    from services.api.app.services.status_service import get_status_service, StatusService
    class EmptyStatusRepository:
        def latest(self, *, data_mode):
            assert data_mode == "demo"
            return None
    try:
        app.dependency_overrides[get_status_service] = lambda: StatusService(EmptyStatusRepository())
        response = b2_client.get("/api/v1/status/current")
        assert response.status_code == 404
        problems["status_not_found"] = response.json()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    actual = {"notice": NOTICE, "responses": responses, "problems": problems, "downloads": downloads}
    for value in problems.values():
        Problem.model_validate(value)
    output = request.config.getoption("--b2-examples-output")
    if output:
        # Generated artifact only, and only when the operator explicitly asks.
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(actual, indent=2, sort_keys=True, allow_nan=False) + "\n",
                          encoding="utf-8", newline="\n")
        assert json.loads(target.read_text(encoding="utf-8")) == actual
    else:
        expected = platform_fixture_expected(actual, load_examples())
        if actual != expected:
            def drift(left, right, path=""):
                if isinstance(left, dict) and isinstance(right, dict):
                    for key in left.keys() | right.keys():
                        if key not in left or key not in right:
                            yield path + "/" + key
                        else:
                            yield from drift(left[key], right[key], path + "/" + key)
                elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
                    for index, (a, b) in enumerate(zip(left, right)):
                        yield from drift(a, b, path + "/" + str(index))
                elif left != right:
                    yield path
            assert actual == expected, "HTTP example drift paths: " + ", ".join(drift(actual, expected))
    assert b2_client.get("/api/v1/scenarios?model_version=absent-example").json() == {
        "items": [], "pagination": {"limit": 20, "offset": 0, "next_offset": None}}
    assert b2_client.get("/api/v1/historical-events?end=1900-01-01T00:00:00Z").json() == {
        "items": [], "pagination": {"limit": 20, "offset": 0, "next_offset": None}}


def test_openapi_is_valid_31_and_export_equals_live_document(specification):
    validate(specification)
    assert specification["openapi"] == "3.1.0"
    exported = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    def differences(left, right, path=""):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in left.keys() | right.keys():
                if key not in left or key not in right:
                    yield path + "/" + key, "missing key"
                else:
                    yield from differences(left[key], right[key], path + "/" + key)
        elif isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                yield path, (len(left), len(right))
            for index, (first, second) in enumerate(zip(left, right)):
                yield from differences(first, second, path + "/" + str(index))
        elif left != right:
            yield path, (left, right)
    assert exported == specification, list(differences(exported, specification))[:10]
    assert TestClient(app).get("/openapi.json").json() == specification


@pytest.mark.parametrize("name,model", MODELS.items())
def test_each_json_example_matches_its_public_pydantic_model(name, model):
    model.model_validate(load_examples()["responses"][name])


def test_every_embedded_example_validates_against_the_exported_schema(specification):
    count = 0
    for methods in specification["paths"].values():
        for operation in methods.values():
            for response in operation["responses"].values():
                for media in response.get("content", {}).values():
                    schema = deepcopy(media["schema"])
                    schema["components"] = specification["components"]
                    validator = Draft202012Validator(schema, format_checker=FormatChecker())
                    for example in media.get("examples", {}).values():
                        validator.validate(example["value"])
                        count += 1
    assert count >= 10  # Eight successful JSON responses plus both empty catalogs.


def test_all_routes_are_documented_with_unique_operation_ids(specification):
    from fastapi.routing import APIRoute
    from services.api.tests.route_inventory import route_contexts
    actual = {(route.path, method.lower()) for route in route_contexts(app) if isinstance(route.route, APIRoute)
              and route.path.startswith("/api/v1") for method in route.methods}
    documented = {(path, method) for path, methods in specification["paths"].items() for method in methods}
    assert documented == actual
    assert len(documented) == 12  # Eight JSON GETs, two artifact GETs and their HEADs.
    ids = [operation["operationId"] for methods in specification["paths"].values() for operation in methods.values()]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("path,media", [(ASSET_PATH, {"image/tiff", "application/geo+json", "application/vnd.google-earth.kml+xml"}),
                                       (ASSUMPTIONS_PATH, {"text/plain"})])
def test_download_documentation_matches_media_ranges_headers_and_head(specification, path, media):
    get = specification["paths"][path]["get"]
    assert {parameter["name"] for parameter in get["parameters"] if parameter["in"] == "header"} == {"Range", "If-Range"}
    for code in ("200", "206"):
        assert set(get["responses"][code]["content"]) == media
        assert {"ETag", "Content-Length", "Accept-Ranges", "Content-Disposition", "Cache-Control", "X-Content-Type-Options"} <= set(get["responses"][code]["headers"])
    assert "Content-Range" in get["responses"]["206"]["headers"]
    assert "Content-Range" in get["responses"]["416"]["headers"]
    head = specification["paths"][path]["head"]
    assert all("content" not in response for response in head["responses"].values())
    assert not {"Range", "If-Range"} & {parameter["name"] for parameter in head["parameters"]}
    sample = load_examples()["downloads"]["assumptions" if path == ASSUMPTIONS_PATH else "cog"]
    for name, value in sample["headers"].items():
        documented = next(header for key, header in get["responses"]["200"]["headers"].items() if key.lower() == name)
        assert documented["example"] == value
    assert get["responses"]["206"]["headers"]["Content-Range"]["example"] == sample["partial_headers"]["content-range"]


def test_query_constraints_and_examples_remain_explicit(specification):
    catalog = {p["name"]: p for p in specification["paths"]["/api/v1/scenarios"]["get"]["parameters"]}
    assert catalog["limit"]["schema"]["minimum"] == 1
    assert catalog["limit"]["schema"]["maximum"] == 999
    assert catalog["offset"]["schema"]["minimum"] == 0
    assert catalog["data_mode"]["schema"]["enum"] == ["demo", "production"]
    status_mode = next(p for p in specification["paths"]["/api/v1/status/current"]["get"]["parameters"] if p["name"] == "data_mode")
    assert status_mode["schema"]["const"] == "demo"
    format_query = next(p for p in specification["paths"]["/api/v1/exports/{scenario_id}"]["get"]["parameters"] if p["name"] == "format")
    assert format_query["required"] is True and format_query["schema"]["enum"] == ["geojson", "kml"]
    source = load_examples()["responses"]["scenario_detail"]["datasets"][0]
    assert catalog["dataset_version"]["example"] == source["version"]
    for p in catalog.values():
        assert p["description"] and "example" in p
    units = specification["components"]["schemas"]["ParameterUnits"]
    assert set(units["properties"]) <= set(units["required"])
    assert all(prop["type"] == "string" and "not nullable" in prop["description"] for prop in units["properties"].values())


def test_usage_guide_covers_routes_and_links_to_existing_artifacts():
    guide = ROOT / "docs/runbooks/b2-api-usage.md"
    content = guide.read_text(encoding="utf-8")
    assert all(path.removeprefix("/api/v1") in content for path in JSON_ENDPOINTS)
    assert all(phrase in content for phrase in ("127.0.0.1", "--check", "--b2-examples-output", "is_live", "KML", "Git/CI", "temporary-disk", "scientific"))
    import re
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if not target.startswith("https://"):
            assert (guide.parent / target).is_file()


def test_specification_generation_never_opens_a_database_session(monkeypatch):
    from services.api.app.db import session
    def forbidden(*args, **kwargs):
        raise AssertionError("Documentation attempted a database query")
    monkeypatch.setattr(session.engine, "connect", forbidden)
    monkeypatch.setattr(session, "SessionLocal", forbidden)
    previous = app.openapi_schema
    app.openapi_schema = None
    try:
        assert app.openapi()["openapi"] == "3.1.0"
        assert TestClient(app).get("/docs").status_code == 200
        assert TestClient(app).get("/redoc").status_code == 200
    finally:
        app.openapi_schema = previous


def test_export_check_detects_drift_without_changing_the_file(tmp_path):
    command = [sys.executable, str(ROOT / "scripts/export_b2_openapi.py")]
    success = subprocess.run(command + ["--check"], cwd=ROOT, capture_output=True, text=True)
    assert success.returncode == 0, success.stderr
    stale = tmp_path / "stale.json"
    stale.write_text("{}\n", encoding="utf-8")
    failed = subprocess.run(command + ["--check", "--output", str(stale)], cwd=ROOT, capture_output=True, text=True)
    assert failed.returncode == 1 and "stale" in failed.stderr
    assert stale.read_text(encoding="utf-8") == "{}\n"


def test_document_has_no_internal_fields_or_claimed_production_security(specification):
    serialized = json.dumps(specification, allow_nan=False)
    for private in ("storage_uri", "source_reference", "manifest_json", "bundle_root_uri", "quality_report_uri", "DATABASE_URL", "file://"):
        assert private not in serialized
    assert "security" not in specification
    assert "scientific/production acceptance" in specification["info"]["description"]
    assert "Synthetic" in specification["info"]["x-example-notice"]
