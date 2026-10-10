"""Read-only terrain metadata/sample inspection; no contours or input edits."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import rasterio
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[2]
PATHS = ['part_a/inputs/terrain.tif',
    'solver_inputs_v01/terrain/Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif']


def main():
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'read_only': True,
        'contours_generated': False, 'background_changed': False, 'files': {},
        'limitations': ['Terrain inspection is not calibration or scientific approval.',
            'Source licences and vertical datum remain unverified in inherited project evidence.',
            'The reference screenshot is not georeferenced terrain data.']}
    with rasterio.open(ROOT / 'part_a/assets/max_depth.tif') as flood:
        flood_crs, flood_bounds = flood.crs, flood.bounds
    for relative in PATHS:
        path = ROOT / relative
        with path.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        with rasterio.open(path) as dem:
            sample = dem.read(1, masked=True, out_shape=(min(256, dem.height), min(256, dem.width)),
                              resampling=Resampling.nearest)
            values = sample.compressed()
            same_crs = dem.crs == flood_crs
            bounds = dem.bounds
            report['files'][relative] = {'sha256': digest, 'bytes': path.stat().st_size,
                'driver': dem.driver, 'bands': dem.count, 'dimensions': [dem.width, dem.height],
                'crs': dem.crs.to_string() if dem.crs else None, 'transform': list(dem.transform)[:6],
                'resolution': list(dem.res), 'bounds': list(bounds), 'dtype': dem.dtypes[0],
                'nodata': dem.nodata, 'band_units': list(dem.units), 'tags': dem.tags(),
                'sample_valid_pixels': int(values.size), 'sample_total_pixels': int(sample.size),
                'sample_elevation_range_not_full_grid': [float(values.min()), float(values.max())] if values.size else None,
                'same_crs_as_h02': same_crs,
                'bounds_enclose_h02_grid_not_a_valid_coverage_guarantee': same_crs and
                    bounds.left <= flood_bounds.left and bounds.bottom <= flood_bounds.bottom and
                    bounds.right >= flood_bounds.right and bounds.top >= flood_bounds.top,
                'technical_contour_candidate': bool(dem.crs and values.size and dem.count == 1)}
    (ROOT / 'navigation_legend_evidence/TERRAIN_INSPECTION.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
