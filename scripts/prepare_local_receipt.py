"""Prepare honest draft metadata in the combined copy, without touching Team A."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "part_a"


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def inventory():
    files = sorted(p for p in RECEIPT.rglob("*") if p.is_file() and p.name not in {"CHECKSUMS.sha256", "FILE_INVENTORY.csv"})
    with (RECEIPT / "FILE_INVENTORY.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["path", "size_bytes", "sha256"])
        for p in files:
            writer.writerow([p.relative_to(RECEIPT).as_posix(), p.stat().st_size, digest(p)])
    files.append(RECEIPT / "FILE_INVENTORY.csv")
    (RECEIPT / "CHECKSUMS.sha256").write_text("".join(f"{digest(p)}  {p.relative_to(RECEIPT).as_posix()}\n" for p in sorted(files)), encoding="utf-8")


def main():
    path = RECEIPT / "prototype-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["schema_version"] = "1.1.0-local-draft"
    manifest["run_timestamp_unknown_reason"] = "Producing HEC-RAS file records 2026-10-07 08:34:11 without timezone. Historical Windows timezone cannot be confirmed. No UTC instant is asserted."
    for dataset in manifest["datasets"]:
        dataset["license"] = "UNKNOWN: no licence evidence supplied; no permission or redistribution licence asserted."
    import numpy as np
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union, transform
    from pyproj import Transformer
    extent_path = RECEIPT / manifest["assets"]["extent_geojson"]
    previous = RECEIPT / "reports/previous-derivative-extent.geojson"
    if not previous.exists():
        previous.write_bytes(extent_path.read_bytes())
    with rasterio.open(RECEIPT / manifest["assets"]["max_depth_cog"]) as src:
        values = src.read(1, masked=True)
        wet = ~np.ma.getmaskarray(values) & (values.data > 0.1)
        native = unary_union([shape(g) for g, v in shapes(wet.astype('uint8'), mask=wet, transform=src.transform) if v])
        geom = transform(Transformer.from_crs(src.crs, 4326, always_xy=True).transform, native)
    write(extent_path, {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": mapping(geom),
        "properties": {"scenario_id": manifest["scenario_id"], "run_id": manifest["run_id"], "threshold_m": 0.1}}]})
    manifest["asset_metadata"]["extent_geojson"]["checksum"] = "sha256:" + digest(extent_path)
    write(path, manifest)
    write(RECEIPT / "input-catalog.json", {"datasets": [
        {"dataset_id": item["dataset_id"], "name": item["dataset_id"],
         "description": item["quality_notes"], "data_mode": manifest["data_mode"]}
        for item in manifest["datasets"]], "events": []})
    proof = {"schema_version": "1.0.0", "method": "raster_pixel_edges", "threshold_m": 0.1,
             "comparison": "greater_than", "scenario_id": manifest["scenario_id"], "run_id": manifest["run_id"],
             "depth_checksum": manifest["asset_metadata"]["max_depth_cog"]["checksum"],
             "extent_checksum": manifest["asset_metadata"]["extent_geojson"]["checksum"]}
    # Threshold is copied from the verified extent build, checked again by receiver.
    write(RECEIPT / "reports" / "pixel-edge-extent-evidence.json", proof)
    context_path = RECEIPT / manifest["assumptions_url"]
    context = json.loads(context_path.read_text())
    operation = next(x for x in context["derivation"]["operations"] if x["name"] == "extent_geojson_normalization")
    operation["parameters_and_method"] = "Pixel-edge polygon rebuilt from unchanged maximum-depth raster, depth greater than 0.1 m, 4-connected components; all holes/components retained; full-precision EPSG:32643 to EPSG:4326 transform. Previous derivative retained in reports."
    reference = "reports/pixel-edge-extent-evidence.json"
    if reference not in operation["evidence_references"]:
        operation["evidence_references"].append(reference)
    write(context_path, context)
    manifest["assumptions_checksum"] = "sha256:" + digest(context_path)
    write(path, manifest)
    inventory()


if __name__ == "__main__":
    main()
