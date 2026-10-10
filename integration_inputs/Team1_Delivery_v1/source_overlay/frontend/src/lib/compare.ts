// Reference-scenario comparison on the shared stored grid. Direction is always "candidate minus baseline".
//
// Definitions (version "compare-v1"):
//  * Grid: both rasters must have identical size, pixel size and origin (the four stored references do).
//    Otherwise the comparison is unavailable; nothing is resampled or interpolated.
//  * valid(v)  = finite and v > -9000 (stored nodata is -9999). Nodata is never read as zero.
//  * wet(v)    = valid and maximum depth > 0.1 m.   (nodata and dry cells are both "not wet", as in the extent outline)
//  * common wet = wet in both; new wet = wet in candidate only; baseline-only (lost) wet = wet in baseline only.
//  * Coverage differences (cells valid in one raster and nodata in the other) are counted separately.
//  * Paired depth difference: cells wet in both; candidate depth minus baseline depth, metres.
//  * Paired arrival difference: cells with a valid arrival in both; (candidate - baseline) minutes / 60 = hours.
//    Negative means the candidate is reached earlier. Both rasters store whole hours (HEC-RAS), so differences are whole hours.
//  * Pixel area = |a*e - b*d| of the affine transform (a = pixel width, e = -pixel height, b = d = 0), m^2; km^2 = m^2 / 1e6.
//  * Maximum velocity is not compared: other engines define it differently.
import { MINUTES_PER_HOUR, NODATA_LIMIT } from "./timeline";

export const WET_THRESHOLD_M = 0.1;
export const COMPARE_VERSION = "compare-v1";

export interface GridGeo { originX: number; originY: number; pixelWidth: number; pixelHeight: number }
export interface Grid { width: number; height: number; geo: GridGeo; depth: Float32Array; arrival: Float32Array }

export const isValid = (v: number): boolean => Number.isFinite(v) && v > NODATA_LIMIT;
export const isWet = (v: number): boolean => isValid(v) && v > WET_THRESHOLD_M;

export function pixelAreaM2(g: GridGeo): number {
  const a = g.pixelWidth, e = -g.pixelHeight, b = 0, d = 0;
  return Math.abs(a * e - b * d);
}
export const m2ToKm2 = (m2: number): number => m2 / 1_000_000;

export function gridsAligned(a: Grid, b: Grid): string | null {
  if (a.width !== b.width || a.height !== b.height) return "The two rasters have different sizes.";
  const same = (x: number, y: number) => Math.abs(x - y) <= 1e-6;
  if (!same(a.geo.originX, b.geo.originX) || !same(a.geo.originY, b.geo.originY) || !same(a.geo.pixelWidth, b.geo.pixelWidth) || !same(a.geo.pixelHeight, b.geo.pixelHeight))
    return "The two rasters are not on the same grid.";
  if (a.depth.length !== a.width * a.height || a.arrival.length !== a.width * a.height || b.depth.length !== b.width * b.height || b.arrival.length !== b.width * b.height)
    return "A raster has the wrong number of values.";
  return null;
}

export const CLASS_NONE = 0, CLASS_COMMON = 1, CLASS_NEW = 2, CLASS_LOST = 3;

export interface DiffCounts {
  commonWet: number; newWet: number; lostWet: number; baselineWet: number; candidateWet: number;
  baselineValid: number; candidateValid: number; bothValid: number;
  baselineOnlyValid: number; candidateOnlyValid: number; // depth coverage: valid in one, nodata in the other
}
export interface DiffResult {
  version: string;
  pixelAreaM2: number;
  counts: DiffCounts;
  km2: { commonWet: number; newWet: number; lostWet: number; baselineWet: number; candidateWet: number; netChange: number };
  depth: { pairedCells: number; meanDiffM: number | null; meanAbsDiffM: number | null };
  arrival: { pairedCells: number; meanDiffH: number | null; medianDiffH: number | null; earlier: number; later: number; same: number;
    baselineOnlyValid: number; candidateOnlyValid: number };
  /** per-cell class (none/common/new/lost) for the difference map */
  classes: Uint8Array;
}

export function medianOfInts(sorted: Int32Array): number | null {
  const n = sorted.length; if (n === 0) return null;
  const m = n >> 1;
  return n % 2 ? sorted[m] : (sorted[m - 1] + sorted[m]) / 2;
}

/** Compare candidate against baseline. Returns the reason string when the pair cannot be compared. */
export function compareGrids(baseline: Grid, candidate: Grid): DiffResult | string {
  const why = gridsAligned(baseline, candidate);
  if (why) return why;
  const n = baseline.width * baseline.height;
  const classes = new Uint8Array(n);
  const c: DiffCounts = { commonWet: 0, newWet: 0, lostWet: 0, baselineWet: 0, candidateWet: 0, baselineValid: 0, candidateValid: 0, bothValid: 0, baselineOnlyValid: 0, candidateOnlyValid: 0 };
  let dN = 0, dSum = 0, dAbs = 0;
  let aN = 0, aSum = 0, aEarlier = 0, aLater = 0, aSame = 0, aBaseOnly = 0, aCandOnly = 0;
  const arrDiffs: number[] = [];
  for (let i = 0; i < n; i++) {
    const bd = baseline.depth[i], cd = candidate.depth[i];
    const bv = isValid(bd), cv = isValid(cd);
    if (bv) c.baselineValid++;
    if (cv) c.candidateValid++;
    if (bv && cv) c.bothValid++; else if (bv) c.baselineOnlyValid++; else if (cv) c.candidateOnlyValid++;
    const bw = bv && bd > WET_THRESHOLD_M, cw = cv && cd > WET_THRESHOLD_M;
    if (bw) c.baselineWet++;
    if (cw) c.candidateWet++;
    if (bw && cw) { c.commonWet++; classes[i] = CLASS_COMMON; const d = cd - bd; dN++; dSum += d; dAbs += Math.abs(d); }
    else if (cw) { c.newWet++; classes[i] = CLASS_NEW; }
    else if (bw) { c.lostWet++; classes[i] = CLASS_LOST; }
    const ba = baseline.arrival[i], ca = candidate.arrival[i];
    const bav = isValid(ba), cav = isValid(ca);
    if (bav && cav) {
      const diffMin = ca - ba; aN++; aSum += diffMin; arrDiffs.push(diffMin);
      if (diffMin < 0) aEarlier++; else if (diffMin > 0) aLater++; else aSame++;
    } else if (bav) aBaseOnly++; else if (cav) aCandOnly++;
  }
  const px = pixelAreaM2(baseline.geo);
  const km = (cells: number) => m2ToKm2(cells * px);
  const sortedDiffs = Int32Array.from(arrDiffs).sort();
  const med = medianOfInts(sortedDiffs);
  return {
    version: COMPARE_VERSION, pixelAreaM2: px, counts: c,
    km2: { commonWet: km(c.commonWet), newWet: km(c.newWet), lostWet: km(c.lostWet), baselineWet: km(c.baselineWet), candidateWet: km(c.candidateWet), netChange: km(c.candidateWet) - km(c.baselineWet) },
    depth: { pairedCells: dN, meanDiffM: dN ? dSum / dN : null, meanAbsDiffM: dN ? dAbs / dN : null },
    arrival: { pairedCells: aN, meanDiffH: aN ? aSum / aN / MINUTES_PER_HOUR : null, medianDiffH: med === null ? null : med / MINUTES_PER_HOUR,
      earlier: aEarlier, later: aLater, same: aSame, baselineOnlyValid: aBaseOnly, candidateOnlyValid: aCandOnly },
    classes,
  };
}

/** Paired arrival change classes for the arrival-difference map. d = (candidate - baseline) hours, whole hours for HEC-RAS. */
export const ARRIVAL_BIN_LABELS: readonly string[] = [
  "No paired arrival", "Candidate earlier by 24 h or more", "Candidate earlier by 6 to under 24 h", "Candidate earlier by under 6 h",
  "Same arrival hour", "Candidate later by under 6 h", "Candidate later by 6 to under 24 h", "Candidate later by 24 h or more",
];
export function arrivalBin(diffHours: number): number {
  if (diffHours <= -24) return 1;
  if (diffHours <= -6) return 2;
  if (diffHours < 0) return 3;
  if (diffHours === 0) return 4;
  if (diffHours < 6) return 5;
  if (diffHours < 24) return 6;
  return 7;
}
/** Per-cell bin (0 = not paired) and the number of cells in each bin. Cells without a valid arrival in both scenarios are never classed. */
export function arrivalChangeBins(baseline: Grid, candidate: Grid): { bins: Uint8Array; counts: number[] } | string {
  const why = gridsAligned(baseline, candidate);
  if (why) return why;
  const bins = new Uint8Array(baseline.width * baseline.height);
  const counts = new Array<number>(ARRIVAL_BIN_LABELS.length).fill(0);
  for (let i = 0; i < bins.length; i++) {
    const a = baseline.arrival[i], b = candidate.arrival[i];
    if (isValid(a) && isValid(b)) { const k = arrivalBin((b - a) / MINUTES_PER_HOUR); bins[i] = k; counts[k]++; }
  }
  counts[0] = bins.length - counts.slice(1).reduce((x, y) => x + y, 0);
  return { bins, counts };
}
