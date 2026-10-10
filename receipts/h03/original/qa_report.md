# QA report: ukai-hyp-h03-release30000-v1

Status: **draft, uncalibrated prototype, hypothetical scenario**. Not an observed or reproduced event.

## What this is
A HEC-RAS 2D run of the Ukai to Surat reach driven by an assumed dam-release hydrograph with a peak of 30,000 m3/s (plan p05, flow file u06, 06 Aug 2006 06:00 to 11 Aug 2006 00:00, 115 h). The shape of the hydrograph is a scaled test shape, not a reservoir-routing result. No breach is modelled.

## Run
Runtime 51:09; volume accounting error 0.000607%. Solver diffusion wave. Terrain SRTM-derived with no channel bathymetry; mesh 100 m; Manning n 0.04 uniform; datum unresolved.

## Results (max over the run)
- Flooded area (depth > 0.1 m): 450.4 km2
- Max depth: 39.28 m; max velocity: 10.25 m/s
- Area deeper than 1 m: 386.0 km2; deeper than 5 m: 138.6 km2; deeper than 10 m: 53.4 km2

## Checks done
Rasters share the 1024 x 3072 grid with the 2006 bundle; no NaN; no negative values apart from the -9999 nodata; velocity and depth have identical valid cells: True. Extent outline made from depth > 0.1 m (188 polygons, simplified 0.7 px).

## Not done / limits
- Arrival-time raster is in hours from simulation start (06 Aug 2006 06:00), threshold 0.1 m. Its grid is offset 256 columns from the depth grid (same pixel lattice).
- Rasters are RAS Mapper exports of the default max layers (tiled GeoTIFF); strict COG layout not verified.
- No exposure statistics (no building/road/population layers available): left null.
- Near-channel depths unreliable (no bathymetry, 100 m mesh). Do not quote as a forecast.
