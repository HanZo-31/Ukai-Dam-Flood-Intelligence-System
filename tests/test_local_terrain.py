"""Display generation checks; no solver, imports, database or mutable data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest
import zlib

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('terrain_builder', ROOT / 'scripts/build_local_terrain.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class LocalTerrainTests(unittest.TestCase):
    def test_nodata_transparent_no_contour_halo(self):
        values = np.full((9, 9), 15.)
        values[4, 4] = -9999
        valid = values != -9999
        image = builder.backdrop(values, valid)
        self.assertEqual(image[4, 4].tolist(), [0, 0, 0, 0])
        self.assertTrue(np.all(image[valid, :3] == [238, 244, 237]))
        self.assertTrue(np.all(image[valid, 3] == 255))

    def test_empty_is_transparent_and_finite(self):
        image = builder.backdrop(np.full((5, 5), np.nan), np.zeros((5, 5), dtype=bool))
        self.assertTrue(np.all(image == 0))

    def test_png_lossless_scanlines_and_checksum(self):
        rgba = np.arange(48, dtype=np.uint8).reshape((3, 4, 4))
        payload = builder.png(rgba)
        self.assertEqual(payload[:8], b'\x89PNG\r\n\x1a\n')
        offset, compressed = 8, b''
        while offset < len(payload):
            size = struct.unpack('>I', payload[offset:offset + 4])[0]
            kind = payload[offset + 4:offset + 8]
            data = payload[offset + 8:offset + 8 + size]
            crc = struct.unpack('>I', payload[offset + 8 + size:offset + 12 + size])[0]
            self.assertEqual(crc, zlib.crc32(kind + data) & 0xffffffff)
            if kind == b'IDAT':
                compressed += data
            offset += 12 + size
        self.assertEqual(zlib.decompress(compressed), b''.join(b'\0' + row.tobytes() for row in rgba))

    def test_real_derivative_crs_bounds_mask_and_original_hash(self):
        output = ROOT / 'frontend/src/map/terrain'
        meta = json.loads((output / 'provenance.json').read_text())
        self.assertEqual(hashlib.sha256(builder.SOURCE.read_bytes()).hexdigest(), builder.EXPECTED_SHA)
        self.assertEqual(hashlib.sha256((output / 'light-terrain.png').read_bytes()).hexdigest(), meta['display_png_sha256'])
        with rasterio.open(builder.SOURCE) as source, rasterio.open(output / 'light-terrain.png') as png:
            self.assertEqual(list(source.bounds), meta['extent'])
            self.assertEqual(source.crs.to_string(), meta['crs'])
            self.assertEqual([png.width, png.height], meta['display_size'])
            alpha = png.read(4)
            self.assertEqual(int((alpha == 0).sum()), meta['transparent_nodata_pixels'])
            self.assertEqual(int((alpha == 255).sum()), meta['valid_display_pixels'])

    def test_original_flood_swap_clock_and_selection_code_unchanged(self):
        old = (ROOT / 'simulation_polish_evidence/FloodMap.before-terrain.txt').read_text()
        new = (ROOT / 'frontend/src/map/FloodMap.tsx').read_text()
        start, end = '  // swap the data layer', '  return ('
        self.assertEqual(old.split(start)[1].split(end)[0], new.split(start)[1].split(end)[0])


if __name__ == '__main__':
    unittest.main()
