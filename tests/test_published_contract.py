import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from services.api.app.published_contract import (
    PublishedScenarioManifest, published_json_schema, require_publishable, resolve_reference,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs/contracts/examples/published-scenario-demo.json"


@pytest.fixture
def payload():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_is_explicitly_synthetic_and_publishable(payload):
    manifest = PublishedScenarioManifest.model_validate(payload)
    assert require_publishable(manifest).data_kind == "demo"
    assert manifest.parameters.breach_width_m is None
    assert manifest.assets["max_depth_cog"].endswith(".tif")
    assert "quality" in manifest.model_dump()


def test_saved_schema_matches_executable_contract():
    saved = json.loads((ROOT / "docs/contracts/published-scenario.schema.json").read_text())
    assert saved == published_json_schema()
    assert saved["additionalProperties"] is False
    assert "status" in saved["properties"]
    assert "allOf" in saved


@pytest.mark.parametrize("field", ["schema_version", "run_timestamp", "parameter_units", "quality", "datasets", "assumptions_checksum"])
def test_required_metadata_cannot_be_omitted(payload, field):
    del payload[field]
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)


@pytest.mark.parametrize("field,value", [("approved_by", None), ("approved_by", " "), ("approved_at", None), ("validation_status", "fail")])
def test_approved_status_requires_quality_review(payload, field, value):
    payload["quality"][field] = value
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)


def test_draft_is_reviewable_but_cannot_be_published(payload):
    payload.update(status="draft")
    payload["quality"].update(validation_status="pending", approved_by=None, approved_at=None)
    manifest = PublishedScenarioManifest.model_validate(payload)
    with pytest.raises(ValueError, match="only approved"):
        require_publishable(manifest)


@pytest.mark.parametrize("value", ["2026-10-05T12:00:00", 1791201600, "1791201600"])
def test_run_timestamp_requires_iso_string_with_timezone(payload, value):
    payload["run_timestamp"] = value
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)


def test_time_ranges_and_approval_are_consistent(payload):
    payload["time_coverage"]["end"] = "2025-01-01T00:00:00Z"
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)
    fresh = json.loads(EXAMPLE.read_text())
    fresh["quality"]["approved_at"] = "2025-01-01T00:00:00Z"
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(fresh)


def test_publication_revalidates_mutated_metadata(payload):
    manifest = PublishedScenarioManifest.model_validate(payload)
    manifest.quality.approved_by = None
    with pytest.raises(ValueError):
        require_publishable(manifest)


def test_offset_timestamps_compare_by_instant(payload):
    payload["quality"]["approved_at"] = "2026-10-05T15:45:00+05:30"
    assert PublishedScenarioManifest.model_validate(payload).quality.approved_at.utcoffset().total_seconds() == 19800


@pytest.mark.parametrize("value", [-1, "12", float("nan"), float("inf")])
def test_invalid_scientific_values_are_not_defaulted(payload, value):
    payload["summary"]["max_depth_m"] = value
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)


def test_units_and_core_assets_are_required(payload):
    payload["asset_metadata"]["max_velocity_cog"]["unit"] = "km/h"
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)
    fresh = json.loads(EXAMPLE.read_text())
    del fresh["assets"]["max_depth_cog"]
    del fresh["asset_metadata"]["max_depth_cog"]
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(fresh)


def test_asset_metadata_roles_crs_and_coverage_match(payload):
    del payload["asset_metadata"]["max_depth_cog"]
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)
    fresh = json.loads(EXAMPLE.read_text())
    fresh["asset_metadata"]["max_depth_cog"]["crs"] = "EPSG:4326"
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(fresh)
    fresh = json.loads(EXAMPLE.read_text())
    fresh["asset_metadata"]["max_depth_cog"]["time_coverage"]["end"] = "2027-01-01T00:00:00Z"
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(fresh)


def test_production_cannot_relabel_demo_inputs(payload):
    payload.update(data_mode="production", data_kind="simulated")
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)


def test_dataset_provenance_and_historical_event_are_required(payload):
    payload.update(scenario_type="historical_replay")
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)
    payload["historical_event_id"] = "synthetic-event-001"
    manifest = PublishedScenarioManifest.model_validate(payload)
    assert manifest.historical_event_id == "synthetic-event-001"
    del payload["datasets"][0]["license"]
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)


def test_duplicate_provenance_and_asset_references_fail(payload):
    payload["datasets"].append(copy.deepcopy(payload["datasets"][0]))
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)
    fresh = json.loads(EXAMPLE.read_text())
    fresh["assets"]["max_velocity_cog"] = fresh["assets"]["max_depth_cog"]
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(fresh)


@pytest.mark.parametrize("ref", ["../outside.tif", "/outside.tif", "a/../b.tif", "a\\b.tif", "s3://bucket/key?secret=value", "results/%2e%2e/key", "results/%252e%252e/key", "file://server/share", "s3://bucket", "results/a\nb.tif"])
def test_unsafe_references_fail(payload, ref):
    payload["assets"]["max_depth_cog"] = ref
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload)


def test_bundle_root_resolution_is_explicit():
    assert resolve_reference("s3://test-bucket/bundles/v1/", "results/depth.tif") == "s3://test-bucket/bundles/v1/results/depth.tif"
    assert resolve_reference("file:///D:/bundles/v1/", "docs/assumptions.md") == "file:///D:/bundles/v1/docs/assumptions.md"
    with pytest.raises(ValueError):
        resolve_reference("https://example.com/", "results/depth.tif")


def test_validation_cli_is_metadata_only_and_redacts_payloads(payload, tmp_path):
    valid = subprocess.run([sys.executable, str(ROOT / "scripts/validate_published_manifest.py"), str(EXAMPLE)], capture_output=True, text=True)
    assert valid.returncode == 0
    assert "nothing registered" in valid.stdout
    payload["assets"]["max_depth_cog"] = "s3://user:secret@bucket/key"
    bad = tmp_path / "invalid.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    rejected = subprocess.run([sys.executable, str(ROOT / "scripts/validate_published_manifest.py"), str(bad)], capture_output=True, text=True)
    assert rejected.returncode == 1
    assert "secret" not in rejected.stderr
