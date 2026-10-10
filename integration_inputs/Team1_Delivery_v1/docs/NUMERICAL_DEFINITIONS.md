# Numerical definitions (compare-v1, zone-rule-v1, timeline)

**Grid.** All four stored references share one grid: 3072 × 1024 cells, 28.999033361477533 m, origin (268076.8810281253, 2369001.58195343), EPSG:32643. Comparison requires an identical grid and otherwise reports "unavailable"; nothing is resampled.

**Valid.** finite and > −9000 (stored nodata is −9999). Nodata is never treated as zero or dry.

**Wet.** valid and maximum depth > 0.1 m. New wet = wet in candidate only; common = both; baseline-only = baseline only. Always candidate minus baseline.

**Coverage differences.** Cells valid in one raster and nodata in the other are counted separately and excluded from paired statistics.

**Paired depth.** cells wet in both; mean of (candidate − baseline), metres.

**Paired arrival.** cells with a valid arrival in both; (candidate − baseline) minutes ÷ 60 = hours (negative = candidate earlier). Median and mean reported; counts earlier / later / same.

**Arrival-change classes.** d = (candidate − baseline) hours over cells with a valid arrival in both: d ≤ −24; −24 < d ≤ −6; −6 < d < 0; d = 0; 0 < d < 6; 6 ≤ d < 24; d ≥ 24. Other cells are unclassed. Counts match independent numpy counts for four pairs.

**Pixel area.** |a·e − b·d| of the affine transform (a = pixel width, e = −pixel height, b = d = 0); km² = cells × area ÷ 1,000,000. Velocity is not compared (definitions can differ between engines).

**Timeline.** reached ⇔ arrival valid and arrival_minutes ≤ elapsed_hours × 60 (inclusive). Hours→minutes converted once; arrival colours convert back once. Unreached cells are pale grey; no-arrival cells are transparent.

**Zones.** 5,000 m squares of the projected grid; each cell belongs to the zone containing its centre (complete, non-overlapping partition; edge zones are partial and show raster coverage). Zone ID `Z-E{km}-N{km}` of the lower-left corner (4-digit kilometres). Rank group 1: zones with new wet area > 0, by descending new area. Group 2: other zones with eligible timing and median advance (baseline − candidate, hours) > 0, by descending advance. Ties by zone ID. Timing is eligible only with ≥ 50 paired cells and paired ≥ 50% of cells with a valid arrival in either scenario.

**Checks.** See `WORK_EVIDENCE.md` E6, E8, E14.
