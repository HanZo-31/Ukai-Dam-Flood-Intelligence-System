"""Derive a bounded, offline display backdrop. Never modify simulation inputs.

Contours are unlabelled intervals in source values, NOT verified metre elevations.
Relief uses normalized image gradients, NOT physically scaled metric hillshade.
Only bundled numpy/rasterio and the Python standard library are needed.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import zlib

import numpy as np
import rasterio
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'part_a/inputs/terrain.tif'
EXPECTED_SHA = 'c439396123c0414c41be4f4abb73fbb630cb24dfaf5b0a37d9471f8694fb7687'
OUTPUT = ROOT / 'frontend/src/map/terrain'


def backdrop(values, valid):
    """Return RGBA pixels; nodata never participates in contour/gradient edges."""
    valid = valid & np.isfinite(values)
    smooth = np.where(valid, values, 0).astype(np.float64)
    for _ in range(3):
        padded = np.pad(smooth, 1, mode='edge')
        mask = np.pad(valid.astype(float), 1, mode='edge')
        total = np.zeros_like(smooth)
        weight = np.zeros_like(smooth)
        for y in range(3):
            for x in range(3):
                total += padded[y:y + smooth.shape[0], x:x + smooth.shape[1]] * mask[y:y + smooth.shape[0], x:x + smooth.shape[1]]
                weight += mask[y:y + smooth.shape[0], x:x + smooth.shape[1]]
        smooth = np.divide(total, weight, out=np.zeros_like(total), where=weight > 0)
    # Exclude pixels neighbouring holes from relief/isolines (no nodata halos).
    interior = valid.copy()
    interior[1:] &= valid[:-1]
    interior[:-1] &= valid[1:]
    interior[:, 1:] &= valid[:, :-1]
    interior[:, :-1] &= valid[:, 1:]
    dy, dx = np.gradient(smooth)
    magnitude = np.hypot(dx, dy)[interior]
    scale = float(np.percentile(magnitude, 95)) if magnitude.size else 0
    directional = np.clip((dx - dy) / max(scale, 1e-9), -1, 1)
    shade = np.where(interior, directional * 12, 0)
    rgb = np.clip(np.array([238, 244, 237]) + shade[..., None], 0, 255)
    bins = np.floor(smooth / 10)  # display-only source-value isolines; no unit asserted
    lines = np.zeros_like(valid)
    lines[:, :-1] |= (bins[:, :-1] != bins[:, 1:]) & interior[:, :-1] & interior[:, 1:]
    lines[:-1] |= (bins[:-1] != bins[1:]) & interior[:-1] & interior[1:]
    rgb[lines] = rgb[lines] * .45 + np.array([190, 206, 188]) * .55
    rgba = np.zeros((*values.shape, 4), dtype=np.uint8)
    rgba[..., :3] = rgb.astype(np.uint8)
    rgba[..., 3] = valid.astype(np.uint8) * 255
    rgba[~valid] = 0
    return rgba


def png(rgba):
    """Encode a lossless RGBA PNG without a new imaging dependency."""
    height, width, channels = rgba.shape
    assert channels == 4 and rgba.dtype == np.uint8
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\x00' + row.tobytes() for row in rgba)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b'')


def main():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA, 'Terrain changed: inspect before regenerating.'
    with rasterio.open(SOURCE) as dem:
        assert dem.crs.to_string() == 'EPSG:32643' and dem.count == 1
        assert dem.transform.b == 0 and dem.transform.d == 0 and dem.transform.e < 0
        width, height = (dem.width + 1) // 2, (dem.height + 1) // 2
        sample = dem.read(1, masked=True, out_shape=(height, width), resampling=Resampling.bilinear)
        valid = ~np.ma.getmaskarray(sample) & np.isfinite(sample.data)
        rgba = backdrop(sample.data, valid)
        assert np.all(rgba[~valid] == 0)
        meta = {'generated_at': datetime.now().astimezone().isoformat(), 'source': 'part_a/inputs/terrain.tif',
                'source_sha256': digest, 'crs': dem.crs.to_string(), 'extent': list(dem.bounds),
                'source_size': [dem.width, dem.height], 'display_size': [width, height],
                'valid_display_pixels': int(valid.sum()), 'transparent_nodata_pixels': int((~valid).sum()),
                'elevation_units': dem.units[0], 'vertical_datum': None,
                'source_licence_verified': False, 'contour_interval_source_values': 10,
                'contours_labelled': False, 'purpose': 'Relative terrain context only; no elevation measurement or scientific approval.',
                'processing': 'Half-resolution bilinear display raster; three masked 3x3 smoothing passes; normalized directional gradients; unlabelled source-value isolines.',
                'coverage': 'Only supplied terrain footprint; nodata/outside remains plain grid.',
                'network': 'None. Bundled local derivative only.'}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    payload = png(rgba)
    (OUTPUT / 'light-terrain.png').write_bytes(payload)
    meta['display_png_sha256'] = hashlib.sha256(payload).hexdigest()
    (OUTPUT / 'provenance.json').write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    (OUTPUT / 'extent.ts').write_text('// Generated by scripts/build_local_terrain.py; EPSG:32643, not lon/lat.\nexport const TERRAIN_EXTENT: [number, number, number, number] = ' + json.dumps(meta['extent']) + ';\n', encoding='utf-8')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == digest
    print(json.dumps(meta | {'png_bytes': len(payload), 'input_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
