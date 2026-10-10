# H02 facts verified from the actual files (read-only inspection)

Date: 2026-10-07 (timezone of this note not recorded). Scenario: `ukai-hyp-h02-release20000-v1` = HEC-RAS plan **p04 (HYP_H02, short ID HYPH02)**, flow file **u05**, geometry g01. (An earlier pass of this inspection read p05 by mistake; p05 is H03. The values below are from p04.)
Nothing in `v0.1`, the HEC-RAS project or the fast-solver folder was modified.

## Run and timing (plan file p04 + HEC-RAS result file p04.hdf)
| Item | Value | Where it comes from |
|---|---|---|
| Engine | HEC-RAS 7.0.1 June 2026, unsteady 2D | p04.hdf "Program Version" |
| Producing run window | 07 Oct 2026 07:47:27 to 08:34:11 (wall clock), total 00:46:45 | p04.hdf "Run Time Window", "Computation Time Total" |
| Wall-clock timezone | NOT STORED in the file. **Unverified.** File modification times were deliberately not used as evidence. | open; needs reliable evidence |
| Simulation window (model clock) | 06 Aug 2006 06:00 to 11 Aug 2006 00:00 (114 h) | p04 `Simulation Date=` |
| Model-clock meaning | A fixed anchor date reused from the 2006 event dates. For H02 it is a hypothetical anchor, not an observed event time | project decision, see QA report |
| Computation interval | 10 s | p04 |
| Hydrograph output interval | 15 min | p04 `Output Interval=15MIN` |
| Instantaneous interval | 1 h | p04 |
| Mapping interval | 1 h (this is why arrival times are whole hours) | p04 `Mapping Interval=1HOUR` |
| Forcing | 115 hourly values, peak 20,000 m3/s at hour 36 | u05 |
| Project path stored in the result file | `e:\Ukai\ukai-flood-intelligence\...` : the run was made from the E: copy, not C: | p04.hdf |
| Geometry file | g01; mesh spacing 100 m (hydraulic mesh) versus 28.999 m output pixels | earlier QA, not re-measured today |

## Source file hashes (sha256)
- g01: e6072375c5bd7a61e785dbbe980b02cdcadfbd89a783d9e0f1f44ed655defbbc
- p04: b58189476279a3a55595039fbc8287a683b6ead295e5e5d00b920d0d3fbd2273
- u05: b08b11972d91516d2c13a6582f70721541b88c80dfb5aaaa75016b4b0cc24689
- prj: 49cd169a3865b2655a295c048a99847bbf3f138a94cbc77b056ef9c421670596
- p04.hdf: 9cca16b3db46cc1de0157291e4c7a541f42d47f655e7920ec574f2b5dd68ce2f
- g01.hdf: bc901463fd88d698140255135888619951026b27540a32e9c7a4295275ac75a1
Full list (all four scenarios plus terrain and flow files): `HECRAS_SOURCE_HASHES.sha256`.
The project file currently names p08 as the current plan; p08 is the stopped sensitivity run and must not be used.

## Raster geometry (measured from the TIFF tags)
| Raster | Size (px) | Origin x | Origin y (top) | Pixel size | nodata |
|---|---|---|---|---|---|
| max_depth / max_velocity / max_wse | 3072 x 1024 | 268076.8810 | 2369001.5820 | 28.999033 m | -9999 |
| arrival_time | 3565 x 1189 | 260653.1285 | 2369001.5820 | 28.999033 m | -9999 |

- Offset between the two origins is **256.0000 px in x and 0.0000 px in y**. Same lattice, so the arrival raster can be cut to the depth grid without resampling.
- Cutting arrival to the depth window (rows 0-1023, columns 256-3327) keeps **all 426,586 valid arrival cells; 0 lie outside the window.**
- Arrival values: integer hours, minimum 1, maximum 113, no zeros. Whole-hour steps follow from the 1-hour mapping interval.
- Overlap with depth > 0.1 m: depth > 0.1 m cells 427,786; of these 2,094 have no arrival value; 894 arrival cells are not deeper than 0.1 m; 332 arrival cells fall where the depth raster is nodata. These counts are inherited from RAS Mapper; none was adjusted.
- All four rasters are tiled (256 x 256), deflate compressed, with 5 image levels. Whether they meet the strict COG layout is **not yet verified**.
- Extent GeoJSON: 1 MultiPolygon feature with 244 polygons, longitude 72.7690 to 73.5861, latitude 21.1521 to 21.3460, still carrying a top-level legacy `crs` member (CRS84) and the original `scenario_id` property.

## What this does and does not settle
- Settles: which plan made H02, run window and duration, plan intervals, the arrival-window geometry for H02 only (do not assume it for H01/H03/2006).
- Does not settle: wall-clock timezone, strict COG compliance, volume accounting error (stored inside a compressed text block of p04.hdf; reading it needs an HDF5 reader, not available in the cloud workspace), input licences, model-configuration and input-release labels.


## Raw run timestamps (as stored in p04.hdf, timezone unverified)
- Compute log: "Simulation started at: 07Oct2026 07:47:19 AM"; Date Processed 07-10-2026 07:47:25; Run Time Window 07OCT2026 07:47:27 to 07OCT2026 08:34:11; Computation Time Total 00:46:45; Unsteady Flow Computations 46:45; Complete Process 46:51.
- Reconciliation: 08:34:11 - 07:47:27 = 2804 s (46:44); reported total 46:45 = 2805 s. Difference 1 s: a ONE-SECOND DISCREPANCY between the stamp interval (2804 s) and the reported duration (2805 s). Rounding or truncation of whole-second stamps is a possible explanation, not confirmed. 07:47:19 to 08:34:11 = 2812 s vs Complete Process 46:51 = 2811 s: also 1 s (same possible explanation, also unconfirmed). No fractional seconds exist in any stored text attribute. The numeric "Compute Time (ms)" dataset was not read (needs h5py, not available).
- Plan/output times (model clock, not wall clock): 06Aug2006 06:00 to 11Aug2006 00:00; hourly stamps 3600 s apart.
