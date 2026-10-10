"""Independent rasterio single-cell expectations, no source-raster writes."""
from datetime import datetime
import json
from pathlib import Path
import rasterio
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[2]
FOLDERS = {'h01': 'receipts/h01', 'h02': 'part_a', 'h03': 'receipts/h03', '2006': 'receipts/2006'}
ROLES = {'depth': 'max_depth', 'arrival': 'arrival_time', 'velocity': 'max_velocity'}


def main():
    existing = json.loads((ROOT / 'frontend/src/lib/fixtures/arrival_samples.json').read_text())
    result = {'checked_at': datetime.now().astimezone().isoformat(), 'method': 'rasterio full-resolution 1x1 windows; existing independent arrival fixture pixel locations', 'scenarios': {}}
    for name, folder in FOLDERS.items():
        fixture = existing['scenarios'][name]
        cells = fixture['samples180'][:2] + fixture['nodataSamples'][:1]
        rows = []
        with rasterio.open(ROOT / folder / 'assets/max_depth.tif') as depth:
            for cell in cells:
                row, col = cell['row'], cell['col']
                x, y = depth.xy(row, col)
                values = {}
                for key, filename in ROLES.items():
                    with rasterio.open(ROOT / folder / 'assets' / (filename + '.tif')) as raster:
                        values[key] = float(raster.read(1, window=Window(col, row, 1, 1))[0, 0])
                rows.append({'row': row, 'col': col, 'coordinate': [x, y], 'values': values})
        result['scenarios'][name] = {'folder': folder, 'points': rows}
    (ROOT / 'frontend/src/lib/fixtures/point_samples.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('Independent point fixtures recorded for all four scenarios.')


if __name__ == '__main__':
    main()
