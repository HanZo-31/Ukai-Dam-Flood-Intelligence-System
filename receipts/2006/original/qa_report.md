# QA report — ukai-2006-historical-v2 (OBS_2006 run)

Date 2026-10-07. Status: **uncalibrated technical candidate. Not scientifically validated.**

## What was checked (files in `assets/`, from the OBS2006 RAS Mapper exports)

| Check | Result |
|---|---|
| CRS | EPSG:32643 in the GeoTIFF GeoKeys (ProjectedCSTypeGeoKey 32643) and the VRT sidecars |
| Pixel size | 28.999 m (square) for all four rasters |
| Nodata | -9999 declared; no NaN values; no negative values outside nodata |
| Layout | tiled, DEFLATE, 5 overview levels. Strict COG layout (IFD ordering) not verified |
| Depth, velocity, WSE | same grid (1024 x 3072, origin x 268076.88, y 2369001.58), same valid-cell footprint (503,289 cells) |
| Arrival time | **different grid** (1189 x 3565, origin x 260653.13). Same pixel lattice, offset 256 columns, same top edge. Needs windowing before overlay. Not resampled in this bundle |
| Arrival-time units | integer hours since 2006-08-06 00:00 at 0.1 m depth threshold, range 1 to 138 (hourly mapping output, so 1 h resolution only) |
| Layer consistency | 495,702 cells deeper than 0.1 m; 2,122 of them have no arrival value and 857 arrival cells are not deeper than 0.1 m (threshold/timing edge effect, 0.4%) |
| Extent | `extent.geojson`: max depth > 0.1 m, 182 polygons, CRS84 lon/lat, simplified (0.7 px), parts under 4 px dropped. Total wet area 416.9 km2 |
| Physical ranges | depth 0.001-38.86 m, velocity 0-11.58 m/s, WSE 9.4-71.1 m |

## Flags — read before using

1. **Depths look too deep for a floodplain.** Of the wet area, 29% (123 km2) is deeper than 5 m, 12% deeper than 10 m, 4.5% deeper than 15 m. With no channel bathymetry, a 100 m mesh and a 29 m DEM that cannot resolve the river, water is probably stored in terrain pits and the channel is not represented. Treat depth and extent as indicative only. Surat-city studies report 4-5 m in the west zone (abstract level), but that is city scale and not directly comparable.
2. **Maximum velocity 11.6 m/s** is high for a floodplain; likely local artefacts at the dam end or steep cells. Not investigated.
3. **Vertical datum unknown.** WSE values cannot be compared with gauge levels.
4. **Mesh spacing 100 m** is from the original setup; not confirmed in this audit.
5. **Numerical run evidence only:** completed, volume error 0.0004%, runtime 1 h 05 min (read from the HEC-RAS window). Small volume error is not evidence of historical accuracy.
6. **Forcing** is reconstructed (see `provenance/`). Cross-check against the published 12-hourly release table (E01) gives agreement within about 4% at 5 of 8 comparable times and up to about 24% on the rising limb.
7. **Not computed:** duration, exposure (population, buildings, roads), hazard classification. Manifest fields kept null.
8. Run warnings/messages beyond the final summary were not captured (no saved log file).

## Eligibility (separate concepts)
- Numerical run completion: yes.
- Asset/metadata QA: partial (above).
- Technical integration eligibility: unknown until the real Part B validator is available.
- Scientific calibration/validation: **not done**.
