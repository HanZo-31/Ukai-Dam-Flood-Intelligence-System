"""Bounded local GIS integrity checks, not scientific calibration or approval."""
from dataclasses import dataclass
from datetime import datetime
import json
import math
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rio_cogeo.cogeo import cog_validate
from shapely.geometry import shape, box, mapping, MultiPolygon
from shapely.ops import unary_union
from shapely.errors import ShapelyError


@dataclass(frozen=True)
class GISInspection:
    geometry: dict
    details: dict
    synthetic: bool = False


def polygon_geometry(geometry):
    if geometry.geom_type == "Polygon":
        geometry = MultiPolygon([geometry])
    if geometry.geom_type != "MultiPolygon" or geometry.is_empty or not geometry.is_valid:
        raise ValueError("footprint must be a valid nonempty polygon")
    west, south, east, north = geometry.bounds
    if not all(math.isfinite(v) for v in geometry.bounds) or not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("footprint requires finite WGS84 bounds; dateline wrapping is unsupported")
    return geometry


class GISInspector:
    """Create a fresh inspector per bundle. Local limits are configurable."""
    def __init__(self, *, max_pixels=20_000_000, max_vector_bytes=20_000_000, max_features=10_000):
        self.max_pixels, self.max_vector_bytes, self.max_features = max_pixels, max_vector_bytes, max_features
        self.grid = None
        self.raster_bounds = None

    def reset(self):
        self.grid = None
        self.raster_bounds = None

    def __call__(self, path, role, metadata):
        try:
            if metadata.format == "cog":
                return self.raster(path, role, metadata)
            if metadata.format == "geojson":
                return self.vector(path, role, metadata)
            raise ValueError("local GIS verifier does not support KML yet")
        except (rasterio.errors.RasterioError, ShapelyError, TypeError, KeyError, OverflowError, AttributeError) as exc:
            raise ValueError("invalid GIS content") from exc

    def raster(self, path, role, metadata):
        valid, _, _ = cog_validate(str(path), strict=True, quiet=True)
        if not valid:
            raise ValueError("invalid COG structure")
        with rasterio.open(path) as source:
            if source.driver != "GTiff" or source.count != 1 or source.width * source.height > self.max_pixels:
                raise ValueError("raster must be a bounded single-band GeoTIFF")
            if source.crs is None or source.crs != rasterio.crs.CRS.from_string(metadata.crs):
                raise ValueError("raster CRS differs from metadata")
            if source.units[0] != metadata.unit:
                raise ValueError("raster unit differs from metadata")
            if source.nodata != metadata.nodata:
                raise ValueError("raster nodata differs from metadata")
            transform = source.transform
            if not all(math.isfinite(v) for v in transform) or transform.b != 0 or transform.d != 0 or transform.a <= 0 or transform.e >= 0:
                raise ValueError("raster requires a finite north-up grid")
            tags = source.tags()
            for key, expected in (("coverage_start", metadata.time_coverage.start), ("coverage_end", metadata.time_coverage.end)):
                value = datetime.fromisoformat(tags.get(key, "").replace("Z", "+00:00"))
                if value.tzinfo is None or value != expected:
                    raise ValueError("raster coverage tags differ from metadata")
            grid = (source.crs.to_string(), source.width, source.height, tuple(transform))
            if self.grid is not None and grid != self.grid:
                raise ValueError("raster grids are not aligned")
            count, minimum, maximum = 0, math.inf, -math.inf
            for _, window in source.block_windows(1):
                values = source.read(1, window=window, masked=True).compressed()
                if values.size:
                    if not np.isfinite(values).all() or (values < 0).any():
                        raise ValueError("raster valid cells must be finite and nonnegative")
                    if role == "hazard_cog" and not np.equal(values, np.floor(values)).all():
                        raise ValueError("hazard classes must be integral")
                    count += int(values.size)
                    minimum, maximum = min(minimum, float(values.min())), max(maximum, float(values.max()))
            if not count:
                raise ValueError("raster contains no valid cells")
            geometry = polygon_geometry(box(*transform_bounds(source.crs, "EPSG:4326", *source.bounds, densify_pts=21)))
            self.grid, self.raster_bounds = grid, geometry
            return GISInspection(mapping(geometry), dict(width=source.width, height=source.height,
                native_crs=source.crs.to_string(), transform=list(transform), resolution=list(source.res),
                dtype=source.dtypes[0], valid_cells=count, minimum=minimum, maximum=maximum,
                cog_valid=True, footprint_kind="raster_bounds", inspector_version="1.0.0"), tags.get("synthetic") == "true")

    def vector(self, path, role, metadata):
        if metadata.crs != "EPSG:4326" or path.stat().st_size > self.max_vector_bytes:
            raise ValueError("GeoJSON requires EPSG:4326 and the configured size limit")
        def bad_constant(value):
            raise ValueError("nonfinite JSON value")
        payload = json.loads(path.read_text(encoding="utf-8"), parse_constant=bad_constant)
        if payload.get("type") != "FeatureCollection" or "crs" in payload:
            raise ValueError("GeoJSON requires a FeatureCollection without CRS override")
        features = payload.get("features")
        if not isinstance(features, list) or not 1 <= len(features) <= self.max_features:
            raise ValueError("GeoJSON needs a bounded nonempty feature list")
        geometries = []
        synthetic = payload.get("synthetic") is True
        for feature in features:
            if feature.get("type") != "Feature" or not isinstance(feature.get("properties"), dict):
                raise ValueError("invalid GeoJSON feature")
            synthetic = synthetic or feature.get("synthetic") is True or feature["properties"].get("synthetic") is True
            geometry = shape(feature["geometry"])
            if geometry.is_empty or not geometry.is_valid or geometry.has_z:
                raise ValueError("invalid or unsupported GeoJSON geometry")
            if role == "extent_geojson" and geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                raise ValueError("extent requires polygon geometry")
            west, south, east, north = geometry.bounds
            if not all(math.isfinite(v) for v in geometry.bounds) or not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
                raise ValueError("GeoJSON requires finite WGS84 coordinates")
            geometries.append(geometry)
        merged = unary_union(geometries)
        footprint = polygon_geometry(merged if role == "extent_geojson" else box(*merged.bounds))
        if role == "extent_geojson" and self.raster_bounds is not None and not self.raster_bounds.buffer(1e-8).covers(footprint):
            raise ValueError("vector extent lies outside raster coverage")
        return GISInspection(mapping(footprint), dict(feature_count=len(features), native_crs="EPSG:4326",
            footprint_kind="flood_extent" if role == "extent_geojson" else "vector_bounds", inspector_version="1.0.0"), synthetic)
