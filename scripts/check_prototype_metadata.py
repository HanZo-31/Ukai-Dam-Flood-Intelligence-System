"""Standalone metadata/context checker. No DB/session, .env, GIS or app startup."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError
from services.api.app.published_contract import PublishedScenarioManifest
from services.api.app.prototype_context import (
    MAX_CONTEXT_BYTES, ContextBindingError, PrototypeContext, validate_bound_context,
)

MAX_MANIFEST_BYTES = 1024 * 1024
SAFE_NAMES = {
    "schema_version", "scenario_id", "run_id", "model_version", "input_dataset_version",
    "status", "quality", "validation_status", "approved_by", "approved_at", "datasets",
    "assets", "asset_metadata", "crs", "time_step_minutes", "time_coverage", "start", "end",
    "engine", "software_version", "name", "build", "build_unavailable_reason",
    "source_checksum", "source_checksum_unavailable_reason", "scenario_family", "original",
    "forcing", "arrival", "timing", "limitations", "assumptions", "derivation", "prototype",
    "calibration_status", "scientific_validation_status", "unavailable_products", "preserved_wse",
    "reference_timestamp", "unit", "origin", "threshold_m", "conversion_factor",
    "temporal_resolution_minutes", "result_output_interval_minutes", "checksum",
    "max_depth_cog", "max_velocity_cog", "arrival_time_cog", "extent_geojson",
}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError("nonfinite_json_value")


def read_json(path, maximum):
    with path.open("rb") as handle:
        raw = handle.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("metadata_too_large")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_bad_constant)
    return data, raw


def diagnostic(scope, error):
    for item in error.errors(include_input=False, include_url=False)[:25]:
        pieces = [str(v) if isinstance(v, int) or v in SAFE_NAMES else "<field>" for v in item["loc"]]
        location = ".".join(pieces) or "metadata"
        print(f"invalid: {scope}.{location} ({item['type']})", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--synthetic-example", action="store_true", help="Metadata-only demo example; never eligible for real preview")
    args = parser.parse_args()
    scope = "manifest"
    try:
        payload, _ = read_json(args.manifest, MAX_MANIFEST_BYTES)
        manifest = PublishedScenarioManifest.model_validate(payload)
        scope = "context"
        payload, raw_context = read_json(args.context, MAX_CONTEXT_BYTES)
        context = PrototypeContext.model_validate(payload)
        if "sha256:" + hashlib.sha256(raw_context).hexdigest() != manifest.assumptions_checksum:
            raise ContextBindingError("manifest.assumptions_checksum")
        validate_bound_context(context, manifest, synthetic_example=args.synthetic_example)
    except ValidationError as error:
        diagnostic(scope, error)
        return 1
    except ContextBindingError as error:
        print(f"invalid: {error} (binding_mismatch)", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError, RecursionError, TypeError):
        print(f"invalid: {scope}.metadata (unreadable_invalid_or_oversize)", file=sys.stderr)
        return 1
    forbidden = {"dotenv", "sqlalchemy", "psycopg", "fastapi", "rasterio", "services.api.app.db.session", "services.api.app.main"}
    if forbidden.intersection(sys.modules):
        print("invalid: checker.import_boundary (unexpected_runtime_dependency)", file=sys.stderr)
        return 1
    profile = "synthetic demo metadata example" if args.synthetic_example else "production/simulated draft metadata"
    print(f"Metadata and context binding valid: {profile}.")
    print("No database, GIS/input/asset bytes or scientific approval checked. Nothing imported; preview admission not granted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
