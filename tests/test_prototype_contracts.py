"""Stage 2 metadata tests only. All values/examples are synthetic; no DB or GIS."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]  # Existing runtime dependency has no bundled stubs.
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.api.app.published_contract import PublishedScenarioManifest
from services.api.app.prototype_context import (
    PrototypeContext, ContextBindingError, prototype_context_json_schema,
    validate_bound_context,
)


@pytest.fixture
def pair():
    manifest = json.loads((ROOT / "docs/contracts/examples/prototype-manifest.synthetic.json").read_text())
    context = json.loads((ROOT / "docs/contracts/examples/prototype-context.synthetic.json").read_text())
    return manifest, context


def bind(pair):
    manifest, context = pair
    return validate_bound_context(PrototypeContext.model_validate(context),
                                  PublishedScenarioManifest.model_validate(manifest),
                                  synthetic_example=True)


def test_synthetic_example_binds_but_is_not_real_preview(pair):
    assert bind(pair).prototype is True
    manifest, context = pair
    with pytest.raises(ContextBindingError, match="manifest.data_mode"):
        validate_bound_context(PrototypeContext.model_validate(context), PublishedScenarioManifest.model_validate(manifest))


def test_schema_matches_code_and_example(pair):
    stored = json.loads((ROOT / "docs/contracts/prototype-context.schema.json").read_text())
    assert stored == prototype_context_json_schema()
    Draft202012Validator.check_schema(stored)
    Draft202012Validator(stored).validate(pair[1])


@pytest.mark.parametrize("group,field,value", [
    (None, "prototype", 1), (None, "prototype", False),
    (None, "calibration_status", "calibrated"),
    (None, "scientific_validation_status", "pass"),
    ("arrival", "unit", "h"), ("arrival", "threshold_m", 0.2),
    ("arrival", "conversion_factor", 1), ("arrival", "conversion_factor", True),
    ("arrival", "temporal_resolution_minutes", float("nan")),
    ("timing", "result_output_interval_minutes", True),
    ("engine", "name", "<script>bad</script>"),
    ("engine", "build_unavailable_reason", None),
    ("original", "manifest_reference", "../source.json"),
    ("original", "manifest_reference", "file:///D:/private.json"),
    ("original", "manifest_reference", "https://example.org/source.json"),
])
def test_invalid_context_values_reject(pair, group, field, value):
    payload = pair[1]
    target = payload if group is None else payload[group]
    target[field] = value
    with pytest.raises(ValidationError):
        PrototypeContext.model_validate(payload)


@pytest.mark.parametrize("group", [None, "engine", "arrival", "timing", "original", "forcing", "derivation", "limitations"])
def test_unknown_fields_reject(pair, group):
    payload = pair[1]
    (payload if group is None else payload[group])["unexpected"] = "synthetic-sensitive-marker"
    with pytest.raises(ValidationError):
        PrototypeContext.model_validate(payload)


@pytest.mark.parametrize("group,field,value", [
    (None, "scenario_id", "different-scenario"),
    (None, "run_id", "different-run"),
    (None, "model_version", "different-model"),
    (None, "input_dataset_version", "different-inputs"),
    ("arrival", "reference_timestamp", "2026-01-01T01:00:00Z"),
    ("arrival", "original_checksum", "sha256:" + "9" * 64),
    ("timing", "result_output_interval_minutes", 30),
    ("timing", "coverage_clock_kind", "observed_event"),
    ("derivation", "derivative_run_id", "different-run"),
    ("derivation", "source_scenario_id", "different-source"),
    ("forcing", "kind", "reconstructed_historical"),
])
def test_cross_binding_mismatches_reject(pair, group, field, value):
    (pair[1] if group is None else pair[1][group])[field] = value
    with pytest.raises(ContextBindingError):
        bind(pair)


def test_unavailable_values_need_exact_reasons(pair):
    del pair[1]["unavailable_products"]["population_exposed"]
    with pytest.raises(ContextBindingError):
        bind(pair)


def test_forcing_link_and_duplicate_reject(pair):
    pair[1]["forcing"]["datasets"][0]["dataset_id"] = "unknown-input"
    with pytest.raises(ContextBindingError):
        bind(pair)
    pair[1]["forcing"]["datasets"].append(copy.deepcopy(pair[1]["forcing"]["datasets"][0]))
    with pytest.raises(ValidationError):
        PrototypeContext.model_validate(pair[1])


def test_missing_timing_reason_reject(pair):
    pair[1]["timing"]["unavailable_reasons"] = {}
    with pytest.raises(ValidationError):
        PrototypeContext.model_validate(pair[1])


def run_cli(tmp_path, pair, *, raw_context=None, update_hash=True, synthetic=True):
    manifest, context = copy.deepcopy(pair)
    raw = raw_context if raw_context is not None else json.dumps(context).encode()
    (tmp_path / "context.json").write_bytes(raw)
    if update_hash:
        manifest["assumptions_checksum"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    env = os.environ.copy()
    env["DATABASE_URL"] = "invalid-synthetic-sentinel-must-never-be-used"
    env["B2_ENV"] = "invalid-synthetic-sentinel"
    args = [sys.executable, "-I", "-B", str(ROOT / "scripts/check_prototype_metadata.py"),
            "--manifest", str(tmp_path / "manifest.json"), "--context", str(tmp_path / "context.json")]
    if synthetic:
        args.append("--synthetic-example")
    return subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)


def test_cli_ignores_invalid_db_env_and_declares_scope(tmp_path, pair):
    (tmp_path / ".env").write_text("DATABASE_URL=invalid-sensitive-sentinel", encoding="utf-8")
    result = run_cli(tmp_path, pair)
    assert result.returncode == 0
    assert "No database" in result.stdout and "Nothing imported" in result.stdout
    assert "invalid-sensitive-sentinel" not in result.stdout + result.stderr


def test_cli_rejects_demo_by_default(tmp_path, pair):
    result = run_cli(tmp_path, pair, synthetic=False)
    assert result.returncode == 1 and "manifest.data_mode" in result.stderr


@pytest.mark.parametrize("raw", [b'{"schema_version":"1.0.0","schema_version":"1.0.0"}', b'{"x":NaN}', b'{}' + b' ' * 65536, b'\xff'], ids=["duplicate", "nonfinite", "oversize", "encoding"])
def test_cli_invalid_bounded_json(tmp_path, pair, raw):
    result = run_cli(tmp_path, pair, raw_context=raw)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_cli_changed_context_bytes_reject(tmp_path, pair):
    result = run_cli(tmp_path, pair, update_hash=False)
    assert result.returncode == 1 and "assumptions_checksum" in result.stderr


def test_cli_error_omits_sensitive_values(tmp_path, pair):
    pair[1]["engine"]["name"] = "<synthetic-sensitive-marker>"
    result = run_cli(tmp_path, pair)
    assert result.returncode == 1
    assert "synthetic-sensitive-marker" not in result.stderr
    assert "context.engine.name" in result.stderr


def test_missing_required_core_role_reject(pair):
    del pair[0]["assets"]["arrival_time_cog"]
    del pair[0]["asset_metadata"]["arrival_time_cog"]
    with pytest.raises(ContextBindingError):
        bind(pair)


def test_preview_metadata_does_not_allow_kml(pair):
    key = "export_kml"
    pair[0]["assets"][key] = "results/example.kml"
    pair[0]["asset_metadata"][key] = dict(checksum="sha256:" + "9" * 64, format="kml", crs="EPSG:4326", unit="1", nodata=None, time_coverage=pair[0]["time_coverage"])
    with pytest.raises(ContextBindingError):
        bind(pair)
