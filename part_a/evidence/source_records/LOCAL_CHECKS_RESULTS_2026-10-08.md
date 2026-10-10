# GDAL / QGIS runner results, 2026-10-08 (read directly from the saved result files)

Runner: `local_checks/RUN_ALL_CANDIDATES.bat` -> `local_checks.py`, run by the user on the Team A laptop (QGIS 4.2.3 Python 3.12, GDAL 3.13.3, shapely 2.1.2, pyproj 3.8.0, numpy 2.4.6). Evidence folders: `local_checks/evidence_runs/run_20261008_003558` (H02-v2), `..._003608` (H01), `..._003611` (H03), `..._003616` (2006). Each has `run.log` and `local_checks_result.json`. The log timestamps are the laptop clock; timezone not asserted.
These are PRE-TAG candidates. Coverage tags will change bytes, so every step must be repeated after tags.

| Step | H02-v2 | H01 | H03 | 2006 |
|---|---|---|---|---|
| S00 tools present | PASS | PASS | PASS | PASS |
| S01 hashes vs pre-tag list (0 mismatches) | PASS (31 files) | PASS | PASS | PASS |
| S02 strict COG, GDAL validator full check, depth/velocity/arrival, no errors, no warnings | PASS | PASS | PASS | PASS |
| S03 1 band, float32, EPSG:32643, nodata -9999, units m / m/s / min, north-up finite transform, overviews 4, common size+transform | PASS | PASS | PASS | PASS |
| S04 GDAL-read values+nodata masks equal the originals; arrival = original x 60 on valid cells; window shift exact integer | PASS | PASS | PASS | PASS |
| S05 extent: no crs member, ID = derivative ID, every part valid in GEOS, whole MultiPolygon valid, native-CRS area equals wet px x px area, bounds inside raster, GDAL rasterisation == wet mask | PASS (0 differing px; rel area -6.3e-9) | PASS (0 px; -1.7e-8) | PASS (0 px; -1.6e-8) | PASS (0 px; -4.5e-9) |
| S06 display-outline informational | PASS (ratio 0.9221 of wet area) | SKIPPED | SKIPPED | SKIPPED |
| S07 sizes/counts (info only) | 1,999,529 B; 1,035 polygons; 4,016 rings; 77,154 vertices | 1,873,846 B; 1,223; 3,509; 72,287 | 1,859,561 B; 859; 4,261; 71,715 | 1,914,805 B; 817; 4,275; 73,851 |

Overall: H02 "ALL STEPS PASSED". H01/H03/2006 reported "NOT PASSED" only because S06 was SKIPPED. Cause checked: those candidates have no preserved display outline (their `preserved_optional/` holds only max_wse.tif), so S06 had nothing to examine. It is not a failure of any data check. The runner was then changed so that this case is reported as NOT_APPLICABLE and not counted as a failure (old copy kept as `local_checks_before_NA_change_2026-10-08.py`). The four saved runs are unchanged and were made with the old runner.

## What this now supports (and what it does not)
- Supported: the three registered rasters of all four candidates are strict COG by the GDAL validator (pre-tag); values/masks equal the originals when read through GDAL; extents are valid by GEOS and reproduce the wet mask under GDAL rasterisation. Words: "GIS-checked (pre-tag)".
- Not supported: anything about receiver acceptance, delivered/received/imported, receiver pixel/feature/byte limits (B-01), coverage tags, or scientific validity.
