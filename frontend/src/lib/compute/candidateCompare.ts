// Computed-candidate comparison, version "candidate-compare-v2". A SEPARATE module from the reference comparison (lib/compare.ts, "compare-v1"),
// which is unchanged. Direction is always candidate minus baseline.
//
//  * Aligned grids only (same size, CRS, pixel size, origin); otherwise the comparison is rejected. Nothing is resampled here.
//  * Cell states, per raster: NODATA (exactly -9999 = unknown, NEVER dry), INVALID (non-finite or negative = unknown, counted and reported),
//    DRY (valid, depth <= 0.1 m), WET (valid, depth > 0.1 m). The threshold is applied to float32 storage as Math.fround(0.1), so a stored
//    depth that is exactly 0.1 m is dry and the next representable float32 above it is wet.
//  * CONFIRMED changes need a known (valid) depth in BOTH rasters: gained = candidate wet & baseline dry, lost = baseline wet & candidate dry.
//  * RECORDED-ONLY footprints are reported separately and are never called confirmed changes: wet in one raster while the other is nodata
//    ("unmatched coverage"). candidate-only recorded wet = confirmed gained + candidate wet over unknown baseline (and symmetrically).
//  * Paired depth difference: cells wet in both. Mean/mean-absolute/extremes of candidate minus baseline, metres.
//  * Paired arrival difference: only when BOTH arrival grids exist and both definitions are equivalent (first depth > 0.1 m since simulation start,
//    candidate converted ONCE by the documented hourly ceiling, so values are whole hours in minutes). Differences stay in minutes; the hour value is
//    minutes / 60 computed once. Otherwise unavailable with a reason, never guessed.
//  * Maximum velocity is never subtracted: the candidate's velocity may be a face-normal component while the reference is a different quantity.
import { MINUTES_PER_HOUR } from "../timeline";
import { pixelAreaM2, m2ToKm2 } from "../compare";
import { NODATA } from "./contract";
import type { GridGeo } from "./decode";

export const CANDIDATE_COMPARE_VERSION = "candidate-compare-v2";
export const WET_THRESHOLD_M = 0.1;
/** The threshold as it exists in float32 storage; see header. */
export const WET_THRESHOLD_F32 = Math.fround(WET_THRESHOLD_M);

export interface CompareGrid {
  width: number; height: number; geo: GridGeo; crs: string;
  depth: Float32Array;
  /** minutes since simulation start; null when the product does not exist */
  arrival: Float32Array | null;
}
export const VELOCITY_REASON = "Maximum velocity is not compared: the new run's velocity may be a face-normal component while the reference value is defined differently, and a cross-engine difference would be misleading.";

export type DepthState = 0 | 1 | 2 | 3; // 0 nodata, 1 invalid, 2 dry, 3 wet
export const S_NODATA = 0, S_INVALID = 1, S_DRY = 2, S_WET = 3;
export function depthState(v: number): DepthState {
  if (v === NODATA) return S_NODATA;
  if (!Number.isFinite(v) || v < 0) return S_INVALID;
  return v > WET_THRESHOLD_F32 ? S_WET : S_DRY;
}
export const arrivalValid = (v: number): boolean => Number.isFinite(v) && v !== NODATA && v >= 0;

export const CLS_NONE = 0, CLS_BOTH_WET = 1, CLS_GAINED = 2, CLS_LOST = 3, CLS_CAND_UNMATCHED = 4, CLS_BASE_UNMATCHED = 5;
export const CLASS_LABELS = ["Not flooded or not comparable", "Wet in both (confirmed)", "Confirmed gained wet (candidate wet, baseline known dry)", "Confirmed lost wet (baseline wet, candidate known dry)",
  "Candidate wet where baseline is nodata (unmatched coverage, not a confirmed change)", "Baseline wet where candidate is nodata (unmatched coverage, not a confirmed change)"] as const;

export function alignmentProblem(a: CompareGrid, b: CompareGrid): string | null {
  if (a.crs !== b.crs) return `The rasters use different coordinate systems (${a.crs} and ${b.crs}).`;
  if (a.width !== b.width || a.height !== b.height) return "The rasters have different sizes.";
  // Absolute metric tolerance: relative tolerance on a northing of ~2.3e6
  // would silently accept metre-scale shifts of the supposedly exact grid.
  const same = (x: number, y: number) => Number.isFinite(x) && Number.isFinite(y) && Math.abs(x - y) <= 1e-7;
  if (!same(a.geo.originX, b.geo.originX) || !same(a.geo.originY, b.geo.originY) || !same(a.geo.pixelWidth, b.geo.pixelWidth) || !same(a.geo.pixelHeight, b.geo.pixelHeight)) return "The rasters are not on the same grid.";
  const n = a.width * a.height;
  if (a.depth.length !== n || b.depth.length !== n || (a.arrival && a.arrival.length !== n) || (b.arrival && b.arrival.length !== n)) return "A raster has the wrong number of values.";
  return null;
}

export interface WetCounts {
  bothWet: number; confirmedGained: number; confirmedLost: number; confirmedDryBoth: number;
  baselineRecordedWet: number; candidateRecordedWet: number;
  candidateOnlyRecordedWet: number; baselineOnlyRecordedWet: number;
  candidateWetUnknownBaseline: number; baselineWetUnknownCandidate: number;
}
export interface CellCounts { total: number; baselineValid: number; candidateValid: number; bothValid: number; baselineOnlyValid: number; candidateOnlyValid: number; neitherValid: number; baselineInvalid: number; candidateInvalid: number }
export interface ArrivalSummary {
  available: boolean; reason: string | null;
  pairedCells: number; baselineOnlyValid: number; candidateOnlyValid: number;
  meanDiffMin: number | null; medianDiffMin: number | null; meanDiffH: number | null; medianDiffH: number | null;
  earlier: number; later: number; same: number;
}
export interface CandidateCompareResult {
  version: string; width: number; height: number; pixelAreaM2: number;
  cells: CellCounts; wet: WetCounts; km2: Record<keyof WetCounts, number> & { netRecordedChange: number };
  depth: { pairedCells: number; meanDiffM: number | null; meanAbsDiffM: number | null; maxIncreaseM: number | null; maxDecreaseM: number | null };
  arrival: ArrivalSummary;
  velocity: { available: false; reason: string };
  /** per-cell class for the difference map (see CLS_* / CLASS_LABELS) */
  classes: Uint8Array;
}

export function medianOf(sorted: Float64Array): number | null {
  const n = sorted.length; if (n === 0) return null;
  const m = n >> 1;
  return n % 2 ? sorted[m] : (sorted[m - 1] + sorted[m]) / 2;
}

/** `arrivalBlock` is the reason arrival must not be compared (null = definitions are equivalent). Returns a string when the pair cannot be compared at all. */
export function compareCandidate(baseline: CompareGrid, candidate: CompareGrid, arrivalBlock: string | null): CandidateCompareResult | string {
  const why = alignmentProblem(baseline, candidate);
  if (why) return why;
  const n = baseline.width * baseline.height;
  const classes = new Uint8Array(n);
  const cells: CellCounts = { total: n, baselineValid: 0, candidateValid: 0, bothValid: 0, baselineOnlyValid: 0, candidateOnlyValid: 0, neitherValid: 0, baselineInvalid: 0, candidateInvalid: 0 };
  const w: WetCounts = { bothWet: 0, confirmedGained: 0, confirmedLost: 0, confirmedDryBoth: 0, baselineRecordedWet: 0, candidateRecordedWet: 0, candidateOnlyRecordedWet: 0, baselineOnlyRecordedWet: 0, candidateWetUnknownBaseline: 0, baselineWetUnknownCandidate: 0 };
  let dN = 0, dSum = 0, dAbs = 0, dMax = -Infinity, dMin = Infinity;
  const arrAvail = !arrivalBlock && !!baseline.arrival && !!candidate.arrival;
  let aN = 0, aSum = 0, aEarlier = 0, aLater = 0, aSame = 0, aBaseOnly = 0, aCandOnly = 0;
  const diffs: number[] = [];
  for (let i = 0; i < n; i++) {
    const bs = depthState(baseline.depth[i]), cs = depthState(candidate.depth[i]);
    const bv = bs >= S_DRY, cv = cs >= S_DRY;
    if (bs === S_INVALID) cells.baselineInvalid++;
    if (cs === S_INVALID) cells.candidateInvalid++;
    if (bv) cells.baselineValid++;
    if (cv) cells.candidateValid++;
    if (bv && cv) cells.bothValid++; else if (bv) cells.baselineOnlyValid++; else if (cv) cells.candidateOnlyValid++; else cells.neitherValid++;
    const bw = bs === S_WET, cw = cs === S_WET;
    if (bw) w.baselineRecordedWet++;
    if (cw) w.candidateRecordedWet++;
    if (bw && cw) {
      w.bothWet++; classes[i] = CLS_BOTH_WET;
      const d = candidate.depth[i] - baseline.depth[i]; dN++; dSum += d; dAbs += Math.abs(d); if (d > dMax) dMax = d; if (d < dMin) dMin = d;
    } else if (cw && bs === S_DRY) { w.confirmedGained++; classes[i] = CLS_GAINED; }
    else if (bw && cs === S_DRY) { w.confirmedLost++; classes[i] = CLS_LOST; }
    else if (cw && !bv) { w.candidateWetUnknownBaseline++; classes[i] = CLS_CAND_UNMATCHED; }
    else if (bw && !cv) { w.baselineWetUnknownCandidate++; classes[i] = CLS_BASE_UNMATCHED; }
    else if (bs === S_DRY && cs === S_DRY) w.confirmedDryBoth++;
    if (arrAvail) {
      const ba = baseline.arrival![i], ca = candidate.arrival![i];
      const bav = arrivalValid(ba), cav = arrivalValid(ca);
      if (bav && cav) { const d = ca - ba; aN++; aSum += d; diffs.push(d); if (d < 0) aEarlier++; else if (d > 0) aLater++; else aSame++; }
      else if (bav) aBaseOnly++; else if (cav) aCandOnly++;
    }
  }
  w.candidateOnlyRecordedWet = w.confirmedGained + w.candidateWetUnknownBaseline;
  w.baselineOnlyRecordedWet = w.confirmedLost + w.baselineWetUnknownCandidate;
  const px = pixelAreaM2(baseline.geo);
  const km = (c: number) => m2ToKm2(c * px);
  const km2 = Object.fromEntries((Object.keys(w) as (keyof WetCounts)[]).map((k) => [k, km(w[k])])) as Record<keyof WetCounts, number>;
  const sorted = Float64Array.from(diffs).sort();
  const med = medianOf(sorted);
  const arrival: ArrivalSummary = {
    available: arrAvail, reason: arrAvail ? null : arrivalBlock ?? "The new run or the reference has no arrival-time product.",
    pairedCells: aN, baselineOnlyValid: aBaseOnly, candidateOnlyValid: aCandOnly,
    meanDiffMin: aN ? aSum / aN : null, medianDiffMin: med,
    meanDiffH: aN ? aSum / aN / MINUTES_PER_HOUR : null, medianDiffH: med === null ? null : med / MINUTES_PER_HOUR,
    earlier: aEarlier, later: aLater, same: aSame,
  };
  return {
    version: CANDIDATE_COMPARE_VERSION, width: baseline.width, height: baseline.height, pixelAreaM2: px, cells, wet: w,
    km2: { ...km2, netRecordedChange: km(w.candidateRecordedWet) - km(w.baselineRecordedWet) },
    depth: { pairedCells: dN, meanDiffM: dN ? dSum / dN : null, meanAbsDiffM: dN ? dAbs / dN : null, maxIncreaseM: dN ? dMax : null, maxDecreaseM: dN ? dMin : null },
    arrival, velocity: { available: false, reason: VELOCITY_REASON }, classes,
  };
}

/** Difference-map palette (index = CLS_*). Distinct hue AND lightness so the unmatched classes are not mistaken for confirmed changes. */
export const CANDIDATE_CLASS_COLOURS: readonly (readonly number[])[] = [
  [0, 0, 0, 0], [120, 144, 170, 150], [214, 40, 40, 235], [22, 119, 239, 235], [255, 193, 7, 215], [130, 90, 200, 215],
];
