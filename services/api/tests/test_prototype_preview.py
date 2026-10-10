"""Mock eligibility/transport tests only; NOT real production GIS ingestion."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as Row

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException
import pytest

from services.api.app.api.v1.router import router as approved_router
from services.api.app.main import http_error, invalid_request
from services.api.app.published_contract import PublishedScenarioManifest
from services.api.app.prototype_settings import Admission, PrototypeSettings, prototype_settings
from services.api.app.prototype_runtime import install_preview, build_preview_openapi
from services.api.app.services.prototype_service import PrototypeService, canonical_checksum, get_prototype_service, safe_public
from services.api.app.storage import LocalObjectStore

ROOT = Path(__file__).resolve().parents[3]
BASE = "/api/v1/prototypes/scenarios"


class MockRepository:
    """No DB writes or scientific claims; shapes match admitted metadata only."""
    def __init__(self, row, assets, summary, datasets):
        self.row, self.asset_rows, self.impact, self.input_rows = row, assets, summary, datasets

    def get(self, identity, *, entries):
        scenario, bundle, _ = self.row
        if identity == scenario.scenario_id and any((item.scenario_id, item.run_id, item.manifest_checksum) == (identity, bundle.run_id, bundle.manifest_checksum) for item in entries):
            return self.row
        return None

    def list(self, *, entries, limit, offset):
        return ([self.row] if self.get(self.row[0].scenario_id, entries=entries) else [])[offset:offset + limit]

    def assets(self, scenario_id, run_id):
        return self.asset_rows

    def summary(self, scenario_id):
        return self.impact

    def datasets(self, scenario_id):
        return self.input_rows


@pytest.fixture
def mocked(tmp_path, monkeypatch):
    store = LocalObjectStore(tmp_path / "objects")
    store.root.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    payload = json.loads((ROOT / "docs/contracts/examples/prototype-manifest.synthetic.json").read_text())
    context = json.loads((ROOT / "docs/contracts/examples/prototype-context.synthetic.json").read_text())
    # Production-shaped metadata ONLY behind a test double. Bytes and engine
    # remain explicitly synthetic; no actual production import is attempted.
    payload.update(data_mode="production", data_kind="simulated")
    payload["datasets"][0]["source_label"] = "assumed"
    for role, reference in payload["assets"].items():
        _, checksum = store.put(reference, ("Synthetic transport bytes; not GIS: " + role).encode())
        payload["asset_metadata"][role]["checksum"] = checksum
    _, payload["quality"]["report_checksum"] = store.put(payload["quality"]["report_reference"], b'{"synthetic":true,"scientific_approval":false}')
    _, payload["datasets"][0]["checksum"] = store.put(payload["datasets"][0]["source_reference"], b"synthetic,not_observed\n1,2\n")
    context["engine"]["name"] = "Mock transport metadata; no actual engine"
    raw = json.dumps(context).encode()
    _, payload["assumptions_checksum"] = store.put(payload["assumptions_url"], raw)
    manifest = PublishedScenarioManifest.model_validate(payload)
    uri = store.root.as_uri() + "/"
    scenario = Row(**{key: getattr(manifest, key) for key in ("scenario_id", "scenario_type", "model_version", "input_dataset_version", "data_mode", "data_kind", "crs", "time_step_minutes")},
                   status="completed", publication_status="draft", coverage_start=manifest.time_coverage.start,
                   coverage_end=manifest.time_coverage.end, parameters=manifest.parameters.model_dump(),
                   parameter_units=manifest.parameter_units.model_dump(), assumptions_url=uri + manifest.assumptions_url,
                   assumptions_checksum=manifest.assumptions_checksum)
    bundle = Row(run_id=manifest.run_id, manifest_json=manifest.model_dump(mode="json"), manifest_checksum=canonical_checksum(manifest), bundle_root_uri=uri)
    run = Row(run_id=manifest.run_id, scenario_id=manifest.scenario_id, run_timestamp=manifest.run_timestamp,
              model_version=manifest.model_version, input_dataset_version=manifest.input_dataset_version,
              status="completed", validation_status="pending", approved_by=None, approved_at=None,
              quality_report_uri=uri + manifest.quality.report_reference, quality_report_checksum=manifest.quality.report_checksum)
    assets = []
    for index, (role, metadata) in enumerate(manifest.asset_metadata.items()):
        asset = Row(id=index + 1, scenario_id=manifest.scenario_id, run_id=manifest.run_id,
                    asset_type=role, data_mode="production", storage_uri=uri + manifest.assets[role],
                    coverage_start=metadata.time_coverage.start, coverage_end=metadata.time_coverage.end,
                    **metadata.model_dump(exclude={"time_coverage"}))
        # Mock inspection shape, never persisted or claimed as actual GIS QA.
        spatial = Row(asset_id=asset.id, source_checksum=metadata.checksum,
                      details=dict(inspector_version="mock-only", native_crs=metadata.crs,
                                   cog_valid=True, width=4, height=4, valid_cells=16, feature_count=1))
        assets.append((asset, spatial))
    datasets = [Row(**item.model_dump(exclude={"time_coverage"}),
                    coverage_start=item.time_coverage.start if item.time_coverage else None,
                    coverage_end=item.time_coverage.end if item.time_coverage else None) for item in manifest.datasets]
    repo = MockRepository((scenario, bundle, run), assets, Row(**manifest.summary.model_dump()), datasets)
    admission = tmp_path / "admission.json"

    def admit(entries=None):
        entry = dict(scenario_id=manifest.scenario_id, run_id=manifest.run_id, manifest_checksum=bundle.manifest_checksum)
        admission.write_text(json.dumps({"schema_version": "1.0.0", "entries": [entry] if entries is None else entries}), encoding="utf-8")

    admit()
    settings = PrototypeSettings(admission)
    service = PrototypeService(repo, store, settings)
    return Row(manifest=manifest, context=context, repo=repo, store=store, settings=settings,
               service=service, admit=admit, admission=admission, tmp_path=tmp_path)


def make_client(mocked, *, enabled=True, peer="127.0.0.1"):
    app = FastAPI(title="Preview test only", version="1.0.0", description="Synthetic mock transport")
    app.include_router(approved_router)
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    install_preview(app, mocked.settings if enabled else None)
    app.dependency_overrides[get_prototype_service] = lambda: mocked.service
    if enabled:
        setattr(app, "openapi", lambda: build_preview_openapi(app))
    return TestClient(app, client=(peer, 12345)), app


def test_mock_preview_has_explicit_warning_and_nulls(mocked):
    client, _ = make_client(mocked)
    identity = mocked.manifest.scenario_id
    for suffix in ("", "/layers", "/impact"):
        result = client.get(BASE + "/" + identity + suffix)
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["status"] == "draft" and body["validation_status"] == "pending"
        assert body["prototype"] is True and body["scientifically_validated"] is False
        assert body["approved_by"] is None and body["label"] == "Uncalibrated prototype — simulated"
        assert "file://" not in result.text
    detail = client.get(BASE + "/" + identity).json()
    assert detail["summary"]["population_exposed"] is None
    assert detail["engine"]["name"].startswith("Mock")
    assert all(value.startswith(BASE + "/") for value in detail["links"].values())
    assert client.get(BASE).json()["items"][0]["scenario_id"] == identity


@pytest.mark.parametrize("suffix", ["", "/layers", "/impact", "/assumptions", "/quality-report", "/assets/max_depth_cog"])
def test_disabled_and_removed_admission_hide_every_resource(mocked, suffix):
    disabled, app = make_client(mocked, enabled=False)
    path = BASE + "/" + mocked.manifest.scenario_id + suffix
    assert disabled.get(path).status_code == 404
    assert not any("/prototypes/" in path for path in app.openapi()["paths"])
    client, _ = make_client(mocked)
    mocked.admit([])
    assert client.get(path).status_code == 404
    assert client.get(BASE).json()["items"] == []


@pytest.mark.parametrize("peer", ["10.0.0.1", "192.168.1.5", "testclient"])
def test_nonloopback_and_forwarded_headers_cannot_bypass(mocked, peer):
    client, _ = make_client(mocked, peer=peer)
    assert client.get(BASE, headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 404


@pytest.mark.parametrize("query", ["?limit=101", "?offset=-1", "?include_drafts=true", "?data_mode=demo", "?limit=1&limit=2"])
def test_bounded_and_explicit_query_validation(mocked, query):
    client, _ = make_client(mocked)
    assert client.get(BASE + query).status_code == 422


def test_malformed_admission_fails_closed(mocked):
    client, _ = make_client(mocked)
    mocked.admission.write_text('{"schema_version":"1.0.0","entries":[],"wildcard":true}')
    assert client.get(BASE).status_code == 503


@pytest.mark.parametrize("change", ["manifest", "context_bytes", "spatial_hash", "wrong_asset_run", "wrong_asset_uri", "impact", "dataset", "private_context"])
def test_corrupt_registered_state_fails_without_private_values(mocked, change):
    if change == "manifest":
        mocked.repo.row[1].manifest_json["model_version"] = "broken"
    elif change == "context_bytes":
        mocked.store.resolve_uri(mocked.repo.row[0].assumptions_url).write_bytes(b"corrupt")
    elif change == "spatial_hash":
        mocked.repo.asset_rows[0][1].source_checksum = "sha256:" + "0" * 64
    elif change == "wrong_asset_run":
        mocked.repo.asset_rows[0][0].run_id = "different-run"
    elif change == "wrong_asset_uri":
        mocked.repo.asset_rows[0][0].storage_uri = mocked.store.root.as_uri() + "/other.tif"
    elif change == "impact":
        mocked.repo.impact.population_exposed = 0
    elif change == "dataset":
        mocked.repo.input_rows[0].license = "different"
    else:
        context = copy.deepcopy(mocked.context)
        context["engine"]["name"] = r"C:\private\sensitive-file"
        raw = json.dumps(context).encode()
        mocked.store.resolve_uri(mocked.repo.row[0].assumptions_url).write_bytes(raw)
        manifest = mocked.manifest.model_copy(deep=True)
        manifest.assumptions_checksum = "sha256:" + hashlib.sha256(raw).hexdigest()
        mocked.repo.row[0].assumptions_checksum = manifest.assumptions_checksum
        mocked.repo.row[1].manifest_json = manifest.model_dump(mode="json")
        mocked.repo.row[1].manifest_checksum = canonical_checksum(manifest)
        mocked.admit()
    client, _ = make_client(mocked)
    result = client.get(BASE + "/" + mocked.manifest.scenario_id)
    assert result.status_code == 503
    assert "sensitive-file" not in result.text and "file://" not in result.text


def test_downloads_preserve_full_head_range_and_warning_headers(mocked):
    client, _ = make_client(mocked)
    path = BASE + "/" + mocked.manifest.scenario_id + "/assets/max_depth_cog"
    full = client.get(path)
    assert full.status_code == 200 and full.content.startswith(b"Synthetic transport")
    assert full.headers["X-Ukai-Scientific-Validation"] == "not_validated"
    assert full.headers["Cache-Control"] == "no-store"
    head = client.head(path, headers={"Range": "bytes=0-3"})
    assert head.status_code == 200 and not head.content
    partial = client.get(path, headers={"Range": "bytes=0-3", "If-Range": full.headers["ETag"]})
    assert partial.status_code == 206 and partial.content == full.content[:4]
    assert client.get(path, headers={"Range": "bytes=0-3", "If-Range": '"different"'}).content == full.content
    assert client.get(path, headers={"Range": "bytes=999999-"}).status_code == 416
    for suffix in ("assumptions", "quality-report"):
        response = client.get(BASE + "/" + mocked.manifest.scenario_id + "/" + suffix)
        assert response.status_code == 200
        assert response.headers["X-Ukai-Prototype"] == "true"
    mocked.store.resolve_uri(mocked.repo.asset_rows[0][0].storage_uri).unlink()
    assert client.get(path).status_code == 503


def test_openapi_is_stable_and_advertises_no_kml_or_wse(mocked):
    _, app = make_client(mocked)
    first, second = app.openapi(), app.openapi()
    assert first == second
    assert len([path for path in first["paths"] if path.startswith(BASE)]) == 7
    role = first["components"]["schemas"]["PrototypeLayer"]["properties"]["asset_type"]["enum"]
    assert "export_kml" not in role and "max_wse_cog" not in role


def test_config_requires_local_profile_and_launcher_marker(mocked):
    valid = {"B2_ENABLE_PROTOTYPE_PREVIEW": "true", "B2_ENV": "local",
             "B2_PROTOTYPE_ADMISSION_FILE": str(mocked.admission), "B2_PROTOTYPE_LAUNCH_BOUND": "127.0.0.1"}
    assert prototype_settings(valid) is not None
    for override in ({"B2_ENV": "production"}, {"B2_PROTOTYPE_LAUNCH_BOUND": "0.0.0.0"}, {"B2_ENABLE_PROTOTYPE_PREVIEW": "yes"}):
        with pytest.raises(ValueError):
            prototype_settings(valid | override)
    assert prototype_settings({}) is None


@pytest.mark.parametrize("entries", [
    [{"scenario_id": "*", "run_id": "run-001", "manifest_checksum": "sha256:" + "1" * 64}],
    [{"scenario_id": "scenario-001", "run_id": "run-001", "manifest_checksum": "bad"}],
    [{"scenario_id": "scenario-001", "run_id": "run-001", "manifest_checksum": "sha256:" + "1" * 64}] * 2,
])
def test_admission_identity_constraints(entries):
    with pytest.raises(ValueError):
        Admission.model_validate({"schema_version": "1.0.0", "entries": entries})


def test_public_license_url_is_not_a_windows_drive():
    safe_public("https://example.org/license")
    with pytest.raises(ValueError):
        safe_public(r"C:\private\file")


@pytest.mark.parametrize("change", ["wrong_run", "wrong_hash", "oversize", "missing_file"])
def test_admission_changes_fail_closed(mocked, change):
    client, _ = make_client(mocked)
    if change in {"wrong_run", "wrong_hash"}:
        entry = dict(scenario_id=mocked.manifest.scenario_id, run_id=mocked.manifest.run_id,
                     manifest_checksum=canonical_checksum(mocked.manifest))
        entry["run_id" if change == "wrong_run" else "manifest_checksum"] = "other-run-001" if change == "wrong_run" else "sha256:" + "0" * 64
        mocked.admit([entry])
    elif change == "oversize":
        mocked.admission.write_bytes(b" " * (1024 * 1024 + 1))
    else:
        mocked.admission.unlink()
    result = client.get(BASE + "/" + mocked.manifest.scenario_id)
    assert result.status_code == (404 if change in {"wrong_run", "wrong_hash"} else 503)


def test_preview_budget_and_admission_race_close_handles(mocked, monkeypatch):
    from services.api.app.services import prototype_service, download_policy
    from fastapi import HTTPException
    real = prototype_service.verified_download
    handles = []
    def tracked(*args, **kwargs):
        result = real(*args, **kwargs)
        handles.append(result.handle)
        # The first is context verification. Revoke only after asset snapshot.
        if len(handles) == 2:
            mocked.admit([])
        return result
    monkeypatch.setattr(prototype_service, "verified_download", tracked)
    with pytest.raises(HTTPException) as error:
        mocked.service.download(mocked.manifest.scenario_id, "max_depth_cog")
    assert error.value.status_code == 404 and handles and all(handle.closed for handle in handles)
    assert not download_policy._pending
    mocked.admit()
    monkeypatch.setattr(download_policy.shutil, "disk_usage", lambda _: Row(free=0))
    client, _ = make_client(mocked)
    result = client.get(BASE + "/" + mocked.manifest.scenario_id + "/assets/max_depth_cog")
    assert result.status_code == 503 and not download_policy._pending


def test_preview_interrupted_asgi_send_releases_snapshot(mocked):
    import asyncio
    from starlette.requests import Request, ClientDisconnect
    from services.api.app.api.v1.scenarios import download_response
    from services.api.app.services import download_policy
    download = mocked.service.download(mocked.manifest.scenario_id, "max_depth_cog")
    scope = {"type": "http", "asgi": {"spec_version": "2.4"}, "method": "GET", "path": "/", "headers": []}
    response = download_response(download, Request(scope))
    async def receive():
        return {"type": "http.disconnect"}
    async def send(message):
        raise OSError("Synthetic interrupted send")
    with pytest.raises(ClientDisconnect):
        asyncio.run(response(scope, receive, send))
    assert download.handle.closed and not download_policy._pending


def test_receiving_http_against_mock_preview_and_removal(mocked, monkeypatch):
    """Runner HTTP behavior with actual route serialization, mock eligibility only."""
    from services.api.app import receiving_http
    client, _ = make_client(mocked)
    key = "mock-transport-manifest.json"
    (mocked.store.root / key).write_text(mocked.manifest.model_dump_json())
    files = sorted(path for path in mocked.store.root.rglob("*") if path.is_file())
    (mocked.store.root / "CHECKSUMS.sha256").write_text("".join(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.relative_to(mocked.store.root).as_posix() + "\n" for path in files))
    def request(base, path, *, method="GET", headers=None, max_bytes=1024 * 1024, checksum=None):
        response = client.request(method, path, headers=headers or {})
        raw = response.content
        assert len(raw) <= max_bytes
        actual = "sha256:" + hashlib.sha256(raw).hexdigest()
        if checksum is not None and response.status_code == 200:
            assert actual == checksum
        return dict(status=response.status_code, headers=dict(response.headers), body=raw, bytes=len(raw), checksum=actual)
    monkeypatch.setattr(receiving_http, "request", request)
    report = dict(root=str(mocked.store.root), passed=True, evidence_kind="mocked_eligibility_transport",
                  steps=[], source_hashes={})
    result = receiving_http.verify_preview(copy.deepcopy(report), key, base_url="http://127.0.0.1:8000")
    assert result["passed"], result
    assert len(result["download_results"]) == 6 and not result["real_api_roundtrip_verified"]
    mocked.admit([])
    result = receiving_http.verify_preview(copy.deepcopy(report), key, base_url="http://127.0.0.1:8000", expect_unadmitted=True)
    assert result["passed"] and not result["real_api_roundtrip_verified"]
