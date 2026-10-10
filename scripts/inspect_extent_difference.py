import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import shapes
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union, transform

root = Path(__file__).resolve().parents[1]
with rasterio.open(root / 'part_a/assets/max_depth.tif') as src:
    values = src.read(1, masked=True)
    wet = ~np.ma.getmaskarray(values) & (values.data > 0.1)
    expected = unary_union([shape(g) for g, v in shapes(wet.astype('uint8'), mask=wet, transform=src.transform) if v])
    payload = json.loads((root / 'part_a/assets/extent.geojson').read_text())
    actual = transform(Transformer.from_crs(4326, src.crs, always_xy=True).transform,
                       unary_union([shape(f['geometry']) for f in payload['features']]))
    report = dict(expected_area=expected.area, actual_area=actual.area,
                  symmetric_difference_m2=actual.symmetric_difference(expected).area,
                  tolerance_m2=max(0.01,expected.area*1e-8))
    print(json.dumps(report, indent=2))
    (root/'evidence/extent-difference.json').write_text(json.dumps(report,indent=2))
