"""Receiver fixtures are explicitly synthetic demo data, never real A acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from test_b1_integration import isolated_database  # noqa: F401 -- existing disposable-schema fixture

from scripts.gis_fixture import build_fixture, cog_bytes
from services.api.app.receiving import preflight, inventory, relative_key, ReceiptError, write_evidence
from services.api.app.storage import LocalObjectStore

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root):
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (root / "CHECKSUMS.sha256").write_text("".join(digest(path) + "  " + path.relative_to(root).as_posix() + "\n" for path in paths), encoding="utf-8")


@pytest.fixture
def receipt(tmp_path):
    root = tmp_path / "receipt"
    store = LocalObjectStore(root)
    manifest, _, _ = build_fixture(store, prefix="bundle/")
    payload = manifest.model_dump(mode="json")
    payload.update(scenario_id="synthetic-receiver-hr-int-v1", run_id="synthetic-receiver-run-v1")
    context = json.loads((ROOT / "docs/contracts/examples/prototype-context.synthetic.json").read_text())
    context.update(scenario_id=payload["scenario_id"], run_id=payload["run_id"], model_version=payload["model_version"], input_dataset_version=payload["input_dataset_version"], time_coverage=payload["time_coverage"])
    context["forcing"]["datasets"] = [{"dataset_id": payload["datasets"][0]["dataset_id"], "version": payload["datasets"][0]["version"]}]
    original = {"scenario_id": "synthetic-receiver-source-v1", "status": "draft", "validation_status": "not_validated", "synthetic": True}
    _, checksum = store.put("bundle/original/scenario_manifest.json", json.dumps(original).encode())
    context["original"].update(scenario_id=original["scenario_id"], manifest_reference="original/scenario_manifest.json", manifest_checksum=checksum)
    context["original"]["asset_checksums"] = {}
    original_arrival = "original/arrival_time.tif"
    _, checksum = store.put("bundle/" + original_arrival, cog_bytes(0.25, "h", payload["time_coverage"]))
    context["original"]["asset_checksums"][original_arrival] = checksum
    context["arrival"].update(original_reference=original_arrival, original_checksum=checksum, reference_timestamp=payload["time_coverage"]["start"])
    extent = json.loads(store.resolve_uri(root.as_uri() + "/bundle/" + payload["assets"]["extent_geojson"]).read_text())
    for feature in extent["features"]:
        feature["properties"]["scenario_id"] = payload["scenario_id"]
    reference = "results/pixel-edge-extent.geojson"
    _, checksum = store.put("bundle/" + reference, json.dumps(extent).encode())
    payload["assets"]["extent_geojson"] = reference
    payload["asset_metadata"]["extent_geojson"]["checksum"] = checksum
    proof = {"schema_version": "1.0.0", "method": "raster_pixel_edges", "threshold_m": 0.1,
             "comparison": "greater_than", "depth_checksum": payload["asset_metadata"]["max_depth_cog"]["checksum"],
             "extent_checksum": checksum, "scenario_id": payload["scenario_id"], "run_id": payload["run_id"]}
    proof_ref = "evidence/pixel-edge-extent-evidence.json"
    store.put("bundle/" + proof_ref, json.dumps(proof).encode())
    context["derivation"].update(source_scenario_id=original["scenario_id"], derivative_scenario_id=payload["scenario_id"], derivative_run_id=payload["run_id"])
    context["derivation"]["operations"].append({"name": "extent_geojson_normalization", "parameters_and_method": "Synthetic pixel-edge fixture only", "evidence_references": [proof_ref]})
    for refs in (context["forcing"]["provenance_references"], context["arrival"]["evidence_references"],
                 context["timing"]["evidence_references"], context["derivation"]["evidence_references"]):
        for key in refs:
            store.put("bundle/" + key, b"Synthetic fixture evidence, not actual science.\n")
    for operation in context["derivation"]["operations"]:
        for key in operation["evidence_references"]:
            if key != proof_ref:
                store.put("bundle/" + key, b"Synthetic fixture evidence, not actual science.\n")
    _, payload["assumptions_checksum"] = store.put("bundle/prototype-context.json", json.dumps(context).encode())
    payload["assumptions_url"] = "prototype-context.json"
    path = root / "bundle/derivative-manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    catalog = {"datasets": [{"dataset_id": payload["datasets"][0]["dataset_id"], "name": "Synthetic receiver dataset",
                            "description": "Synthetic test input; no observations", "data_mode": "demo"}], "events": []}
    (root / "input-catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    hashes(root)
    return root, "bundle/derivative-manifest.json"


def test_complete_fixture_preflight_is_readonly_and_pixel_edge_verified(receipt):
    root, manifest = receipt
    before = inventory(root)
    result = preflight(root, manifest, fixture=True)
    assert result["passed"], result
    assert result["evidence_kind"] == "synthetic_fixture" and not result["database_connected"]
    assert not result["scientific_acceptance"] and not result["data_imported"]
    assert result["arrival_conversion"]["conversion_factor"] == 60
    assert result["footprint"]["wet_pixels"] == 192 * 192
    assert inventory(root) == before


def test_fixture_cannot_be_treated_as_real(receipt):
    result = preflight(*receipt)
    assert not result["passed"]
    assert not result["database_connected"]
    assert any(item.get("blocked") for item in result["steps"])


@pytest.mark.parametrize("path", ["../x", "a/../b", "a\\b", "file:///x", "CON.txt", "a/LPT¹.txt", "a. /b", ".env", "a//b", "a%2fb"])
def test_transport_path_constraints(path):
    with pytest.raises(ReceiptError):
        relative_key(path)


def test_drift_and_unexpected_files_block(receipt):
    root, manifest = receipt
    (root / "bundle/results/max_depth.tif").write_bytes(b"corrupt")
    report = preflight(root, manifest, fixture=True)
    assert not report["passed"]
    assert report["steps"][0]["reason"] == "transport_checksum_mismatch"
    assert report["steps"][0]["failed_reference"] == "bundle/results/max_depth.tif"


def test_unknown_transport_file_rejected(receipt):
    root, _ = receipt
    (root / "unexpected.txt").write_text("unexpected")
    with pytest.raises(ReceiptError, match="missing_or_unexpected"):
        inventory(root)


def test_resume_preserves_previous_and_refuses_silent_drift(receipt, tmp_path):
    root, manifest = receipt
    report = preflight(root, manifest, fixture=True)
    output = tmp_path / "evidence"
    write_evidence(report, output)
    with pytest.raises(ReceiptError):
        write_evidence(report, output)
    drift = copy.deepcopy(report)
    drift["inventory_sha256"] = "different"
    write_evidence(drift, output, resume=True)
    assert (output / "report.previous-1.json").exists()
    saved = json.loads((output / "report.json").read_text())
    assert not saved["passed"] and saved["expected_inventory_sha256"] == report["inventory_sha256"]


def test_pixel_centre_outline_is_not_accepted_as_authoritative(receipt):
    import shapely.geometry  # type: ignore[import-untyped]
    import shapely.affinity  # type: ignore[import-untyped]
    root, manifest = receipt
    path = root / "bundle/results/pixel-edge-extent.geojson"
    payload = json.loads(path.read_text())
    geometry = shapely.geometry.shape(payload["features"][0]["geometry"])
    payload["features"][0]["geometry"] = shapely.geometry.mapping(shapely.affinity.scale(geometry, xfact=0.98, yfact=0.98))
    path.write_text(json.dumps(payload))
    metadata = json.loads((root / manifest).read_text())
    new_hash = "sha256:" + digest(path)
    metadata["asset_metadata"]["extent_geojson"]["checksum"] = new_hash
    (root / manifest).write_text(json.dumps(metadata))
    proof_path = root / "bundle/evidence/pixel-edge-extent-evidence.json"
    proof = json.loads(proof_path.read_text())
    proof["extent_checksum"] = new_hash
    proof_path.write_text(json.dumps(proof))
    hashes(root)
    result = preflight(root, manifest, fixture=True)
    assert not result["passed"]
    assert any(item.get("reason") == "extent_not_authoritative_pixel_edge_geometry" for item in result["steps"])


def test_default_cli_never_loads_private_configuration(receipt, tmp_path):
    root, manifest = receipt
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/receive_part_a.py"),
        "--receipt", str(root), "--manifest", manifest, "--fixture", "--output", str(tmp_path / "cli-report")],
        cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "cli-report/report.json").read_text())
    assert not report["database_connected"] and not report["data_imported"]


def test_wrong_or_unowned_database_marker_rejected_without_connection(tmp_path):
    from services.api.app.receiving_db import owned_target
    marker = tmp_path / "owner.json"
    marker.write_text(json.dumps({"database": "ukai", "state": "created"}))
    with pytest.raises(ReceiptError, match="verified_isolated_target"):
        owned_target(marker, "ukai", tmp_path)


def test_explicit_integration_cannot_follow_failed_preflight():
    from services.api.app.receiving_db import integrate
    with pytest.raises(ReceiptError, match="preflight_must_pass"):
        integrate({"passed": False}, "manifest.json", marker=None, expected_database="ukai", object_root=None,
                  delivery_id="fixture", registered_by="fixture", fixture=True)


@pytest.mark.parametrize("value", ["https://127.0.0.1:8000", "http://localhost:8000", "http://10.0.0.1:8000",
    "http://127.0.0.1:8000/api", "http://name:secret@127.0.0.1:8000", "http://127.0.0.1:8000?x=1", "http://127.0.0.1"])
def test_http_verification_requires_literal_local_url(value):
    from services.api.app.receiving_http import local_base
    with pytest.raises(ReceiptError):
        local_base(value)


def test_http_verification_is_explicit_and_failure_blocks_gate(receipt, monkeypatch):
    from services.api.app import receiving_http
    def deny(*args, **kwargs):
        return {"status": 200, "headers": {}, "body": b"{}", "bytes": 2}
    monkeypatch.setattr(receiving_http, "request", deny)
    result = receiving_http.verify_preview(preflight(*receipt, fixture=True), receipt[1],
        base_url="http://127.0.0.1:8000", expect_unadmitted=True)
    assert not result["passed"] and not result["real_api_roundtrip_verified"]
    assert result["steps"][-1]["reason"] == "draft_visible_in_approved_namespace"


def test_preflight_forbids_private_and_database_module_imports(receipt, monkeypatch):
    import builtins
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.startswith(("dotenv", "sqlalchemy", "psycopg", "services.api.app.db.session", "fastapi")):
            raise AssertionError("Read-only preflight imported a forbidden module")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    result = preflight(*receipt, fixture=True)
    assert result["passed"], result


@pytest.mark.parametrize("change", ["half_pixel", "outside_valid", "mask", "nodata", "wrong_value"])
def test_actual_arrival_grid_mask_and_conversion_negatives(tmp_path, change):
    import numpy as np
    import rasterio  # type: ignore[import-untyped]
    from rasterio.transform import from_origin  # type: ignore[import-untyped]
    from services.api.app.receiving import arrival_conversion_check
    depth = tmp_path / "depth.tif"
    source = tmp_path / "hours.tif"
    target = tmp_path / "minutes.tif"
    transform = from_origin(300000, 2350000, 10, 10)
    def write(path, values, grid, nodata=-9999):
        with rasterio.open(path, "w", driver="GTiff", width=values.shape[1], height=values.shape[0],
            count=1, dtype="float32", crs="EPSG:32643", transform=grid, nodata=nodata) as dataset:
            dataset.write(values.astype("float32"), 1)
    original = np.full((2, 4), -9999, dtype="float32")
    original[:, 1:3] = 0.5
    minutes = np.full((2, 2), 30, dtype="float32")
    source_grid = from_origin(299990, 2350000, 10, 10)
    if change == "half_pixel":
        source_grid = from_origin(299995, 2350000, 10, 10)
    elif change == "outside_valid":
        original[0, 0] = 0.5
    elif change == "mask":
        minutes[0, 0] = -9999
    elif change == "wrong_value":
        minutes[0, 0] = 0.5
    write(depth, np.ones((2, 2)), transform)
    write(source, original, source_grid)
    write(target, minutes, transform, -9998 if change == "nodata" else -9999)
    with pytest.raises(ReceiptError):
        arrival_conversion_check(source, target, depth)


def test_coordinate_window_and_nodata_preservation_positive(tmp_path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from services.api.app.receiving import arrival_conversion_check
    paths = [tmp_path / name for name in ("depth.tif", "hours.tif", "minutes.tif")]
    grids = [from_origin(300000, 2350000, 10, 10), from_origin(299980, 2350000, 10, 10), from_origin(300000, 2350000, 10, 10)]
    original = np.full((2, 5), -9999, dtype="float32")
    original[:, 2:4] = [[0.5, -9999], [0.25, 1.0]]
    minute = original[:, 2:4].copy()
    minute[minute != -9999] *= 60
    for path, values, grid in zip(paths, [np.ones((2, 2), dtype="float32"), original, minute], grids):
        with rasterio.open(path, "w", driver="GTiff", width=values.shape[1], height=values.shape[0], count=1,
            dtype="float32", crs="EPSG:32643", transform=grid, nodata=-9999) as dataset:
            dataset.write(values, 1)
    result = arrival_conversion_check(paths[1], paths[2], paths[0])
    assert result["column_offset"] == 2 and result["valid_cells"] == 3 and result["outside_valid_cells"] == 0


def test_demo_database_import_resume_and_late_failure_are_atomic(receipt, tmp_path, monkeypatch, isolated_database):  # noqa: F811 -- pytest fixture parameter
    """Actual PostGIS demo import; target-selection boundary doubled, never genuine A acceptance."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from services.api.app import receiving_db
    from services.api.app.db.models import Scenario, PublishedBundle, Dataset, DatasetVersion
    from services.api.app.repositories.prototype_repository import PrototypeRepository
    from services.api.app.repositories.published_repository import PublishedScenarioRepository
    from services.api.app.prototype_settings import AdmissionEntry
    engine, _ = isolated_database
    objects = tmp_path / "owned-objects"
    objects.mkdir()
    monkeypatch.setattr(receiving_db, "owned_target", lambda *args: (engine, objects))
    root, key = receipt
    options = dict(marker=tmp_path / "unused-marker", expected_database="test-schema-boundary",
        object_root=objects, delivery_id="synthetic-receiver", registered_by="synthetic-test-operator",
        catalog=root / "input-catalog.json", fixture=True)
    actual_register = receiving_db.__dict__.get("register_published_bundle")
    from services.api.app import published_registry
    original_register = published_registry.register_published_bundle
    def fail_late(*args, **kwargs):
        original_register(*args, **kwargs)
        raise ValueError("Synthetic late failure after registry flush")
    monkeypatch.setattr(published_registry, "register_published_bundle", fail_late)
    with pytest.raises(ValueError, match="Synthetic late failure"):
        receiving_db.integrate(preflight(root, key, fixture=True), key, **options)
    with Session(engine) as session:
        assert session.scalars(select(Scenario)).all() == []
        assert session.scalars(select(PublishedBundle)).all() == []
        assert session.scalars(select(Dataset)).all() == []
        assert session.scalars(select(DatasetVersion)).all() == []
    assert list((objects / "received/synthetic-receiver").rglob("*.tif"))  # Staging retained, not DB success.
    monkeypatch.setattr(published_registry, "register_published_bundle", original_register)
    result = receiving_db.integrate(preflight(root, key, fixture=True), key, **options)
    assert result["integration_result"] == "registered_new_draft"
    assert not result["preview_admission_granted"] and not result["real_api_roundtrip_verified"]
    resumed = receiving_db.integrate(preflight(root, key, fixture=True), key, **options)
    assert resumed["integration_result"] == "verified_existing_identity" and not resumed["data_imported"]
    with Session(engine) as session:
        entry = AdmissionEntry(scenario_id=result["stored_scenario_id"], run_id=result["stored_run_id"],
                               manifest_checksum=result["stored_canonical_checksum"])
        assert PrototypeRepository(session).get(entry.scenario_id, entries=[entry]) is None
        for mode in ("demo", "production"):
            assert PublishedScenarioRepository(session).get(entry.scenario_id, data_mode=mode) is None
        row = session.scalar(select(Scenario))
        assert row is not None
        row.model_version = "corrupt-synthetic-version"
        session.commit()
    with pytest.raises(ReceiptError, match="resume_scenario_or_run_metadata_conflict"):
        receiving_db.integrate(preflight(root, key, fixture=True), key, **options)
    assert actual_register is None  # Registration is a local import, not hidden preflight startup.
