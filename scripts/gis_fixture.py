"""Generate actual synthetic COG/GeoJSON assets, without registering approval."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from pyproj import Transformer
from rasterio.io import MemoryFile
from rasterio.shutil import copy as copy_raster
from rasterio.transform import from_origin
from shapely.geometry import box, mapping
from shapely.ops import transform as transform_geometry
from services.api.app.published_contract import PublishedScenarioManifest, ROLE_UNITS
from services.api.app.storage import LocalObjectStore, default_store

GRID = from_origin(300000, 2300000, 10, 10)
SIZE = 256
SCENARIO_ID = "synthetic-gis-local-003"


def cog_bytes(value, unit, coverage, *, transform=GRID, crs="EPSG:32643", nodata=-9999.0):
    values = np.full((SIZE, SIZE), nodata, dtype="float32")
    values[32:-32, 32:-32] = value
    with MemoryFile() as source:
        with source.open(driver="GTiff", width=SIZE, height=SIZE, count=1, dtype="float32", crs=crs, transform=transform, nodata=nodata) as dataset:
            dataset.write(values, 1)
            dataset.set_band_unit(1, unit)
            dataset.update_tags(synthetic="true", coverage_start=coverage["start"], coverage_end=coverage["end"])
        with source.open() as dataset, MemoryFile() as output:
            copy_raster(dataset, output.name, driver="COG", BLOCKSIZE=128, COMPRESS="DEFLATE", RESAMPLING="NEAREST")
            output.seek(0)
            return output.read()


def build_fixture(store, *, prefix=None):
    prefix = prefix or f"scenarios/{SCENARIO_ID}/"
    if not prefix.endswith("/"):
        raise ValueError("fixture prefix must end in /")
    payload = json.loads((ROOT / "docs/contracts/examples/published-scenario-demo.json").read_text(encoding="utf-8"))
    payload.update(scenario_id=SCENARIO_ID, run_id="synthetic-gis-run-003", status="draft")
    payload["model_version"] = "synthetic-gis-fixture-1.0.0"
    payload["input_dataset_version"] = "synthetic-gis-input-release-1.0.0"
    payload["quality"].update(validation_status="pending", approved_by=None, approved_at=None)
    for role, value in (("max_depth_cog", 0.5), ("max_velocity_cog", 0.2), ("arrival_time_cog", 15.0)):
        reference = payload["assets"][role]
        _, checksum = store.put(prefix + reference, cog_bytes(value, ROLE_UNITS[role], payload["time_coverage"]))
        payload["asset_metadata"][role]["checksum"] = checksum
    geometry = transform_geometry(Transformer.from_crs(32643, 4326, always_xy=True).transform,
                                  box(300320, 2297760, 302240, 2299680))
    extent = {"type": "FeatureCollection", "synthetic": True, "features": [{"type": "Feature", "properties": {"synthetic": True, "not_a_prediction": True}, "geometry": mapping(geometry)}]}
    _, payload["asset_metadata"]["extent_geojson"]["checksum"] = store.put(prefix + payload["assets"]["extent_geojson"], json.dumps(extent, allow_nan=False).encode())
    item = payload["datasets"][0]
    item.update(dataset_id="synthetic-gis-input", crs=None, quality_notes="Synthetic time series for GIS contract testing only; not an observation.")
    _, item["checksum"] = store.put(prefix + item["source_reference"], b"time,value\n0,1\n1,2\n")
    _, payload["assumptions_checksum"] = store.put(prefix + payload["assumptions_url"], b"Synthetic GIS fixture, not a flood prediction or observed historical event. No scientific approval is claimed.\n")
    _, payload["quality"]["report_checksum"] = store.put(prefix + payload["quality"]["report_reference"], b'{"synthetic":true,"scientific_approval":false,"purpose":"local GIS integrity testing"}')
    payload["summary"].update(max_depth_m=0.5, flooded_area_km2=3.6864, population_exposed=None, buildings_exposed=None)
    manifest = PublishedScenarioManifest.model_validate(payload)
    manifest_uri, _ = store.put(prefix + "manifest.json", manifest.model_dump_json(indent=2).encode())
    return manifest, store.root.as_uri() + "/" + prefix, manifest_uri


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path)
    args = parser.parse_args()
    store = LocalObjectStore(args.storage_root) if args.storage_root else default_store()
    manifest, _, uri = build_fixture(store)
    print(f"synthetic GIS fixture ready: {manifest.scenario_id}; publication=draft; no DB rows written; {uri}")


if __name__ == "__main__":
    main()
