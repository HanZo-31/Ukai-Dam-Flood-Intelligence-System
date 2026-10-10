"""Read-only local receipt preflight. DB integration lives in a lazy separate module."""
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from services.api.app.published_contract import PublishedScenarioManifest, resolve_reference
from services.api.app.prototype_context import MAX_CONTEXT_BYTES, ContextBindingError, PrototypeContext, validate_bound_context
from services.api.app.prototype_settings import regular_json

MAX_INVENTORY_BYTES = 2 * 1024 * 1024


class ReceiptError(ValueError):
    def __init__(self, reason, reference=None):
        super().__init__(reason)
        self.reason = reason
        self.reference = reference


def now():
    return datetime.now(ZoneInfo("Asia/Calcutta")).isoformat()


def raw_hash(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def relative_key(key):
    if (not isinstance(key, str) or not key or key.startswith("/") or "\\" in key or ":" in key or "%" in key
            or any(ord(c) < 32 or ord(c) == 127 for c in key) or str(PurePosixPath(key)) != key):
        raise ReceiptError("unsafe_transport_path")
    for part in key.split("/"):
        stem = part.split(".")[0].upper()
        if (part in {".", "..", ""} or part.endswith((".", " ")) or any(c in part for c in '<>"|?*')
                or stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", "CLOCK$"} or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", stem)
                or part.casefold() == ".env"):
            raise ReceiptError("unsafe_transport_path")
    return key


def regular_file(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or path.is_symlink()
            or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)):
        raise ReceiptError("regular_file_required")
    return info


def inventory(root):
    raw_path = root / "CHECKSUMS.sha256"
    info = regular_file(raw_path)
    if info.st_size > MAX_INVENTORY_BYTES:
        raise ReceiptError("inventory_oversize")
    entries = {}
    aliases = set()
    for line in raw_path.read_text(encoding="utf-8-sig").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if not match:
            raise ReceiptError("invalid_inventory_line")
        digest, key = match.groups()
        relative_key(key)
        if key == "CHECKSUMS.sha256" or key.casefold() in aliases:
            raise ReceiptError("duplicate_or_self_inventory_entry")
        aliases.add(key.casefold())
        entries[key] = digest
        if len(entries) > 10000:
            raise ReceiptError("inventory_entry_limit")
    actual = set()
    for key in entries:
        if any(str(parent).casefold() in aliases for parent in PurePosixPath(key).parents if str(parent) != "."):
            raise ReceiptError("file_directory_alias")
    for base, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            child = Path(base) / name
            meta = child.lstat()
            if child.is_symlink() or getattr(meta, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024):
                raise ReceiptError("linked_directory_rejected")
        for name in files:
            path = Path(base) / name
            regular_file(path)
            key = path.relative_to(root).as_posix()
            relative_key(key)
            if key != "CHECKSUMS.sha256":
                actual.add(key)
    if actual != set(entries):
        raise ReceiptError("missing_or_unexpected_transport_files")
    for key, expected in entries.items():
        if raw_hash(root / key) != expected:
            raise ReceiptError("transport_checksum_mismatch", key)
    return entries


def referenced(store, bundle_root, key, expected, entries, root):
    if urlsplit(key).scheme:
        raise ReceiptError("portable_reference_required")
    path = store.resolve_uri(resolve_reference(bundle_root, key))
    relative = path.relative_to(root).as_posix()
    if entries.get(relative) != expected.removeprefix("sha256:"):
        raise ReceiptError("reference_not_bound_to_transport_inventory")
    store.verify(path.as_uri(), expected)
    return path


def canonical_manifest_hash(manifest):
    raw = json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def arrival_conversion_check(original_path, derivative_path, depth_path):
    """Verify declared A2 hours-to-minutes math and coordinate-derived window."""
    import numpy as np
    import rasterio  # type: ignore[import-untyped]  # Runtime GIS library ships no typing marker.
    from rasterio.windows import from_bounds, Window  # type: ignore[import-untyped]
    with rasterio.open(original_path) as source, rasterio.open(derivative_path) as target, rasterio.open(depth_path) as depth:
        if (source.count != 1 or source.width * source.height > 20_000_000
                or source.crs != depth.crs or source.transform.b != 0 or source.transform.d != 0
                or source.transform.a <= 0 or source.transform.e >= 0
                or not np.allclose(source.res, depth.res, rtol=0, atol=1e-8)
                or target.transform != depth.transform or target.width != depth.width or target.height != depth.height):
            raise ReceiptError("arrival_grid_relationship_unsupported")
        window = from_bounds(*depth.bounds, transform=source.transform)
        values = (window.col_off, window.row_off, window.width, window.height)
        integers = tuple(round(value) for value in values)
        if any(abs(value - integer) > 1e-6 for value, integer in zip(values, integers)):
            raise ReceiptError("arrival_not_on_integer_source_lattice")
        col, row, width, height = integers
        if col < 0 or row < 0 or col + width > source.width or row + height > source.height:
            raise ReceiptError("arrival_window_outside_source")
        original = source.read(1, masked=True)
        valid = ~np.ma.getmaskarray(original)
        outside = valid.copy()
        outside[row:row + height, col:col + width] = False
        if outside.any():
            raise ReceiptError("valid_arrival_cells_outside_depth_window")
        portion = source.read(1, window=Window(col, row, width, height), masked=True)
        actual = target.read(1, masked=True)
        if not np.array_equal(np.ma.getmaskarray(portion), np.ma.getmaskarray(actual)):
            raise ReceiptError("arrival_nodata_mask_not_preserved")
        old = portion.compressed().astype("float64")
        new = actual.compressed().astype("float64")
        if not np.isfinite(old).all() or (old < 0).any():
            raise ReceiptError("invalid_original_arrival_cells")
        dtype = np.dtype(target.dtypes[0])
        epsilon = float(np.finfo(dtype).eps) if np.issubdtype(dtype, np.floating) else 0
        if not np.allclose(new, old * 60, rtol=8 * epsilon, atol=1e-6):
            raise ReceiptError("arrival_hour_to_minute_values_differ")
        if source.nodata != target.nodata:
            raise ReceiptError("arrival_nodata_value_changed")
        if source.units[0] not in {None, "h", "hour", "hours"}:
            raise ReceiptError("original_arrival_unit_conflicts_with_context")
        return {"column_offset": col, "row_offset": row, "width": width, "height": height,
                "valid_cells": int(old.size), "outside_valid_cells": 0, "conversion_factor": 60,
                "relative_dtype_tolerance": 8 * epsilon, "absolute_tolerance_minutes": 1e-6,
                "original_unit_tag": source.units[0],
                "unit_evidence_basis": "actual tag plus A2 context/QA" if source.units[0] else "A2 context/QA; original raster tag absent",
                "scientific_acceptance": False}


def pixel_edge_check(depth_path, extent_path, proof_path, manifest):
    """Numerical footprint check, not hydraulic calibration or scientific approval."""
    import numpy as np
    import rasterio
    from rasterio.features import shapes  # type: ignore[import-untyped]
    from pyproj import Transformer
    from shapely.geometry import shape  # type: ignore[import-untyped]
    from shapely.ops import transform, unary_union  # type: ignore[import-untyped]
    proof = regular_json(proof_path, 64 * 1024)
    expected_keys = {"schema_version", "method", "threshold_m", "comparison", "depth_checksum", "extent_checksum", "scenario_id", "run_id"}
    if (set(proof) != expected_keys or proof["schema_version"] != "1.0.0" or proof["method"] != "raster_pixel_edges"
            or proof["scenario_id"] != manifest.scenario_id or proof["run_id"] != manifest.run_id
            or proof["depth_checksum"] != manifest.asset_metadata["max_depth_cog"].checksum
            or proof["extent_checksum"] != manifest.asset_metadata["extent_geojson"].checksum
            or type(proof["threshold_m"]) not in {int, float} or not math.isfinite(proof["threshold_m"])
            or proof["threshold_m"] < 0 or proof["comparison"] not in {"greater_than", "greater_or_equal"}):
        raise ReceiptError("pixel_edge_evidence_invalid")
    payload = regular_json(extent_path, 20_000_000)
    for feature in payload["features"]:
        if feature["properties"].get("scenario_id") != manifest.scenario_id:
            raise ReceiptError("extent_derivative_identity_missing_or_wrong")
    with rasterio.open(depth_path) as source:
        if source.width * source.height > 20_000_000 or not source.crs.is_projected or source.crs.linear_units not in {"metre", "meter"}:
            raise ReceiptError("pixel_edge_grid_profile_unsupported")
        values = source.read(1, masked=True)
        valid = ~np.ma.getmaskarray(values)
        wet = valid & (values.data > proof["threshold_m"] if proof["comparison"] == "greater_than" else values.data >= proof["threshold_m"])
        geometries = []
        for geometry, value in shapes(wet.astype("uint8"), mask=wet, transform=source.transform, connectivity=4):
            if value:
                geometries.append(shape(geometry))
                if len(geometries) > 10000:
                    raise ReceiptError("pixel_edge_component_limit")
        if not geometries:
            raise ReceiptError("nonempty_extent_required")
        expected = unary_union(geometries)
        actual_wgs84 = unary_union([shape(item["geometry"]) for item in payload["features"]])
        actual = transform(Transformer.from_crs(4326, source.crs, always_xy=True).transform, actual_wgs84)
        tolerance = max(0.01, expected.area * 1e-8)
        if actual.symmetric_difference(expected).area > tolerance:
            raise ReceiptError("extent_not_authoritative_pixel_edge_geometry")
        return {"wet_pixels": int(wet.sum()), "native_area_m2": float(expected.area),
                "extent_area_m2": float(actual.area), "difference_tolerance_m2": tolerance,
                "scientific_acceptance": False}


def preflight(root, manifest_key, *, fixture=False):
    root = Path(root)
    if (not root.is_dir() or root.is_symlink()
            or getattr(root.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)):
        raise ReceiptError("receipt_root_unavailable_or_linked")
    root = root.resolve()
    relative_key(manifest_key)
    report = {"started_at": now(), "operation": "preflight", "evidence_kind": "synthetic_fixture" if fixture else "real_receipt",
              "scientific_acceptance": False, "database_connected": False, "data_imported": False,
              "steps": [], "root": str(root)}

    def step(name, callback, requirements):
        started = now()
        try:
            result = callback()
        except Exception as error:
            reason = error.reason if isinstance(error, ReceiptError) else type(error).__name__
            if isinstance(error, ContextBindingError):
                reason = "context_binding_mismatch:" + str(error)
            from pydantic import ValidationError
            if isinstance(error, ValidationError):
                known = set(PublishedScenarioManifest.model_fields) | set(PrototypeContext.model_fields)
                for schema in PrototypeContext.model_json_schema().get("$defs", {}).values():
                    known.update(schema.get("properties", {}))
                item = error.errors(include_input=False, include_url=False)[0]
                location = ".".join(str(part) if isinstance(part, int) or part in known else "<field>" for part in item["loc"])
                reason = "invalid_metadata:" + location + ":" + item["type"]
            report["steps"].append({"step": name, "requirements": requirements, "started_at": started,
                "finished_at": now(), "required": True, "performed": True, "exit_status": 1,
                "passed": False, "reason": reason,
                "failed_reference": error.reference if isinstance(error, ReceiptError) else None})
            raise
        report["steps"].append({"step": name, "requirements": requirements, "started_at": started,
            "finished_at": now(), "required": True, "performed": True, "exit_status": 0, "passed": True})
        return result

    try:
        entries = step("transport_inventory", lambda: inventory(root), ["A05", "A08"])
        manifest_path = root / manifest_key
        manifest = step("manifest_metadata", lambda: PublishedScenarioManifest.model_validate(regular_json(manifest_path, 1024 * 1024)), ["M01", "M02", "M03", "M13"])
        from services.api.app.storage import LocalObjectStore
        store = LocalObjectStore(root)
        bundle_root = manifest_path.parent.as_uri() + "/"

        def context_check():
            path = referenced(store, bundle_root, manifest.assumptions_url, manifest.assumptions_checksum, entries, root)
            context = PrototypeContext.model_validate(regular_json(path, MAX_CONTEXT_BYTES))
            return validate_bound_context(context, manifest, synthetic_example=fixture)

        context = step("context_binding", context_check, ["M09", "M11", "M13"])

        def provenance_check():
            referenced(store, bundle_root, manifest.quality.report_reference, manifest.quality.report_checksum, entries, root)
            for item in manifest.datasets:
                referenced(store, bundle_root, item.source_reference, item.checksum, entries, root)
            referenced(store, bundle_root, context.original.manifest_reference, context.original.manifest_checksum, entries, root)
            for key, digest in context.original.asset_checksums.items():
                referenced(store, bundle_root, key, digest, entries, root)
            references = [*context.forcing.provenance_references, *context.arrival.evidence_references,
                          *context.timing.evidence_references, *context.derivation.evidence_references]
            references.extend(key for operation in context.derivation.operations for key in operation.evidence_references)
            for key in set(references):
                path = store.resolve_uri(resolve_reference(bundle_root, key))
                if path.relative_to(root).as_posix() not in entries:
                    raise ReceiptError("required_evidence_reference_missing")

        step("provenance_and_evidence_bytes", provenance_check, ["M04", "M06", "M08", "M09", "M14"])

        def gis_check():
            from services.api.app.gis_validation import GISInspector
            inspector = GISInspector()
            paths = {}
            for role in sorted(manifest.assets, key=lambda key: (not key.endswith("_cog"), key)):
                metadata = manifest.asset_metadata[role]
                path = referenced(store, bundle_root, manifest.assets[role], metadata.checksum, entries, root)
                if path.stat().st_size > 512 * 1024 * 1024:
                    raise ReceiptError("delivered_asset_byte_limit")
                inspection = inspector(path, role, metadata)
                if not fixture and inspection.synthetic:
                    raise ReceiptError("synthetic_artifact_cannot_claim_real_receipt")
                paths[role] = path
            return paths

        paths = step("actual_gis_and_hashes", gis_check, ["A06", "R06", "R07", "R08", "R10", "R11", "R14"])
        original_arrival = store.resolve_uri(resolve_reference(bundle_root, context.arrival.original_reference))
        report["arrival_conversion"] = step("arrival_conversion_alignment", lambda: arrival_conversion_check(
            original_arrival, paths["arrival_time_cog"], paths["max_depth_cog"]), ["R01", "R02", "R03", "R04", "R05"])

        def footprint():
            references = [key for operation in context.derivation.operations for key in operation.evidence_references
                          if key.endswith("pixel-edge-extent-evidence.json")]
            if len(set(references)) != 1:
                raise ReceiptError("pixel_edge_evidence_reference_required")
            proof_path = store.resolve_uri(resolve_reference(bundle_root, references[0]))
            return pixel_edge_check(paths["max_depth_cog"], paths["extent_geojson"], proof_path, manifest)

        report["footprint"] = step("pixel_edge_authoritative_extent", footprint, ["R12", "R13", "R15", "RUN01"])
        step("second_hash_pass", lambda: inventory(root) == entries or (_ for _ in ()).throw(ReceiptError("receipt_changed_between_checks")), ["A08", "RUN07"])
        report.update(scenario_id=manifest.scenario_id, run_id=manifest.run_id,
                      canonical_manifest_checksum=canonical_manifest_hash(manifest),
                      manifest_raw_sha256=raw_hash(manifest_path), inventory_sha256=raw_hash(root / "CHECKSUMS.sha256"),
                      original_manifest_checksum=context.original.manifest_checksum, transport_files=len(entries),
                      second_review_passed=True, passed=True)
    except Exception:
        report["passed"] = False
        report["second_review_passed"] = False
        for name in ("manifest_metadata", "context_binding", "provenance_and_evidence_bytes", "actual_gis_and_hashes", "arrival_conversion_alignment", "pixel_edge_authoritative_extent", "second_hash_pass"):
            if not any(item["step"] == name for item in report["steps"]):
                report["steps"].append({"step": name, "required": True, "performed": False,
                                        "passed": False, "blocked": True, "reason": "prior_required_check_failed", "exit_status": None})
    report["finished_at"] = now()
    report["source_hashes"] = {name: raw_hash(Path(__file__).with_name(name)) for name in ("published_contract.py", "prototype_context.py", "gis_validation.py", "receiving.py")}
    project = Path(__file__).resolve().parents[3]
    report["schema_hashes"] = {name: raw_hash(project / "docs/contracts" / name) for name in ("published-scenario.schema.json", "prototype-context.schema.json")}
    return report


def write_evidence(report, output, *, resume=False):
    output = Path(output).resolve()
    root = Path(report["root"]).resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ReceiptError("evidence_must_be_outside_received_originals")
    if output.exists() and not resume:
        raise ReceiptError("fresh_evidence_directory_required")
    if output.exists():
        previous = json.loads((output / "report.json").read_text())
        if previous.get("root") != report.get("root") or previous.get("operation") not in {"preflight", "integrate", "verify-preview"}:
            raise ReceiptError("resume_evidence_ownership_mismatch")
        if previous.get("inventory_sha256") and previous["inventory_sha256"] != report.get("inventory_sha256"):
            report["passed"] = False
            report["expected_inventory_sha256"] = previous["inventory_sha256"]
            report["steps"].append({"step": "resume_receipt_identity", "required": True,
                "performed": True, "passed": False, "exit_status": 1, "reason": "resume_receipt_identity_changed"})
        index = 1
        while (output / f"report.previous-{index}.json").exists():
            index += 1
        (output / f"report.previous-{index}.json").write_bytes((output / "report.json").read_bytes())
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# Local receiver evidence", "", f"Operation: {report['operation']}; kind: {report['evidence_kind']}; passed: {report['passed']}",
             "Scientific approval is not established. Required unperformed/failed checks block completion.", "",
             "| Step | Performed | Passed | Reason |", "| --- | --- | --- | --- |"]
    for item in report["steps"]:
        lines.append(f"| {item['step']} | {item['performed']} | {item['passed']} | {item.get('reason', '')} |")
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    import csv
    with (output / "REQUIREMENT_RESULTS.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["requirement_id", "step", "performed", "passed", "evidence_kind", "scope"])
        for item in report["steps"]:
            for requirement in item.get("requirements", []):
                writer.writerow([requirement, item["step"], item["performed"], item["passed"], report["evidence_kind"], "individual check coverage; not whole work-order acceptance"])
    paths = sorted(path for path in output.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
    (output / "CHECKSUMS.sha256").write_text("".join(raw_hash(path) + "  " + path.name + "\n" for path in paths), encoding="utf-8")
