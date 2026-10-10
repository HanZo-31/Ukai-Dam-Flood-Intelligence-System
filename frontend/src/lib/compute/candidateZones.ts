// Candidate review zones, rule "candidate-zone-v2". Same fixed 5 km squares of EPSG:32643 and the same cell-centre assignment as the reference
// zones (lib/zones.ts, "zone-rule-v1", unchanged), so each cell belongs to exactly one zone and zone totals add back to the comparison totals.
//
// Order (a coordinate "priority for review", not an evacuation order, not a recommended release, not calibrated):
//   1. confirmed gained wet area, descending (cells where BOTH rasters have a known depth, candidate wet and baseline dry);
//   2. eligible paired median arrival advance (baseline minus candidate, minutes), descending;
//   3. zone ID, ascending (deterministic tie-break).
//   A zone is flagged when it has confirmed gained wet area > 0, or an eligible median advance > 0.
//   Timing is eligible only with >= 50 paired cells AND paired >= 50% of cells with a valid arrival in EITHER raster (engineering reuse of the
//   reference thresholds; not calibrated safety limits). Otherwise it is "unavailable" with a reason, never zero.
//   Unmatched wet coverage (wet over a nodata cell of the other raster) is reported beside, NOT in, the ranking quantity.
import { MINUTES_PER_HOUR } from "../timeline";
import { pixelAreaM2, m2ToKm2 } from "../compare";
import { zoneId, ZONE_SIZE_M, MIN_PAIRED_CELLS, MIN_PAIRED_FRACTION } from "../zones";
import { alignmentProblem, arrivalValid, depthState, medianOf, S_DRY, S_WET, type CandidateCompareResult, type CompareGrid } from "./candidateCompare";

export const CANDIDATE_ZONE_RULE_VERSION = "candidate-zone-v2";
export type CandidatePriorityReason = "confirmed_gained_wet_area" | "earlier_paired_arrival";
export interface CandidateZoneRow {
  id: string; bounds: [number, number, number, number]; cells: number; rasterCoverage: number;
  counts: { gained: number; lost: number; bothWet: number; candidateWetUnknownBaseline: number; baselineWetUnknownCandidate: number };
  confirmedGainedKm2: number; confirmedLostKm2: number; bothWetKm2: number;
  unmatchedCandidateWetKm2: number; unmatchedBaselineWetKm2: number;
  pairedArrivalCells: number; eitherArrivalCells: number; pairedArrivalFraction: number | null;
  /** baseline minus candidate, minutes; positive = candidate reached earlier. null = not eligible/unavailable (see reason) */
  medianAdvanceMin: number | null; medianAdvanceH: number | null; timingUnavailableReason: string | null;
  priority: { rank: number; reason: CandidatePriorityReason } | null;
}
export interface CandidateZoneResult {
  version: string; zoneSizeM: number; pixelAreaM2: number; minPairedCells: number; minPairedFraction: number;
  arrivalAvailable: boolean; arrivalReason: string | null;
  zones: CandidateZoneRow[]; ranked: CandidateZoneRow[];
  totals: { cells: number; gained: number; lost: number; bothWet: number; candidateWetUnknownBaseline: number; baselineWetUnknownCandidate: number };
}
interface Acc { ix: number; iy: number; cells: number; gained: number; lost: number; both: number; cu: number; bu: number; either: number; diffs: number[] }

export function computeCandidateZones(baseline: CompareGrid, candidate: CompareGrid, arrivalBlock: string | null, size = ZONE_SIZE_M): CandidateZoneResult | string {
  const why = alignmentProblem(baseline, candidate);
  if (why) return why;
  const { width, height, geo } = baseline;
  const arrAvail = !arrivalBlock && !!baseline.arrival && !!candidate.arrival;
  const colZone = new Int32Array(width);
  for (let c = 0; c < width; c++) colZone[c] = Math.floor((geo.originX + (c + 0.5) * geo.pixelWidth) / size);
  const accs = new Map<string, Acc>();
  for (let r = 0; r < height; r++) {
    const iy = Math.floor((geo.originY - (r + 0.5) * geo.pixelHeight) / size);
    for (let c = 0; c < width; c++) {
      const ix = colZone[c], key = `${ix}:${iy}`;
      let a = accs.get(key);
      if (!a) { a = { ix, iy, cells: 0, gained: 0, lost: 0, both: 0, cu: 0, bu: 0, either: 0, diffs: [] }; accs.set(key, a); }
      const i = r * width + c;
      a.cells++;
      const bs = depthState(baseline.depth[i]), cs = depthState(candidate.depth[i]);
      const bw = bs === S_WET, cw = cs === S_WET, bv = bs >= S_DRY, cv = cs >= S_DRY;
      if (bw && cw) a.both++;
      else if (cw && bs === S_DRY) a.gained++;
      else if (bw && cs === S_DRY) a.lost++;
      else if (cw && !bv) a.cu++;
      else if (bw && !cv) a.bu++;
      if (arrAvail) {
        const ba = baseline.arrival![i], ca = candidate.arrival![i];
        const bav = arrivalValid(ba), cav = arrivalValid(ca);
        if (bav || cav) a.either++;
        if (bav && cav) a.diffs.push(ba - ca);
      }
    }
  }
  const px = pixelAreaM2(geo);
  const fullCells = (size * size) / px;
  const zones: CandidateZoneRow[] = [];
  for (const a of accs.values()) {
    const paired = a.diffs.length;
    const frac = a.either > 0 ? paired / a.either : null;
    let median: number | null = null, reason: string | null = null;
    if (!arrAvail) reason = arrivalBlock ?? "Arrival is not available for this comparison.";
    else if (paired === 0) reason = "No cell has a valid arrival time in both rasters.";
    else if (paired < MIN_PAIRED_CELLS) reason = `Only ${paired} paired cells (minimum ${MIN_PAIRED_CELLS}).`;
    else if (frac !== null && frac < MIN_PAIRED_FRACTION) reason = `Paired cells cover ${(frac * 100).toFixed(0)}% of cells with an arrival time in either raster (minimum ${MIN_PAIRED_FRACTION * 100}%).`;
    else median = medianOf(Float64Array.from(a.diffs).sort());
    const km = (n: number) => m2ToKm2(n * px);
    zones.push({
      id: zoneId(a.ix, a.iy, size), bounds: [a.ix * size, a.iy * size, (a.ix + 1) * size, (a.iy + 1) * size], cells: a.cells, rasterCoverage: Math.min(1, a.cells / fullCells),
      counts: { gained: a.gained, lost: a.lost, bothWet: a.both, candidateWetUnknownBaseline: a.cu, baselineWetUnknownCandidate: a.bu },
      confirmedGainedKm2: km(a.gained), confirmedLostKm2: km(a.lost), bothWetKm2: km(a.both), unmatchedCandidateWetKm2: km(a.cu), unmatchedBaselineWetKm2: km(a.bu),
      pairedArrivalCells: paired, eitherArrivalCells: a.either, pairedArrivalFraction: frac,
      medianAdvanceMin: median, medianAdvanceH: median === null ? null : median / MINUTES_PER_HOUR, timingUnavailableReason: reason, priority: null,
    });
  }
  zones.sort((x, y) => (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
  const flagged = zones.filter((z) => z.counts.gained > 0 || (z.medianAdvanceMin !== null && z.medianAdvanceMin > 0));
  flagged.sort((x, y) =>
    y.counts.gained - x.counts.gained ||
    (y.medianAdvanceMin ?? -Infinity) - (x.medianAdvanceMin ?? -Infinity) ||
    (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
  flagged.forEach((z, k) => { z.priority = { rank: k + 1, reason: z.counts.gained > 0 ? "confirmed_gained_wet_area" : "earlier_paired_arrival" }; });
  const sum = (f: (z: CandidateZoneRow) => number) => zones.reduce((s, z) => s + f(z), 0);
  return {
    version: CANDIDATE_ZONE_RULE_VERSION, zoneSizeM: size, pixelAreaM2: px, minPairedCells: MIN_PAIRED_CELLS, minPairedFraction: MIN_PAIRED_FRACTION,
    arrivalAvailable: arrAvail, arrivalReason: arrAvail ? null : arrivalBlock ?? "Arrival is not available for this comparison.",
    zones, ranked: flagged,
    totals: { cells: sum((z) => z.cells), gained: sum((z) => z.counts.gained), lost: sum((z) => z.counts.lost), bothWet: sum((z) => z.counts.bothWet),
      candidateWetUnknownBaseline: sum((z) => z.counts.candidateWetUnknownBaseline), baselineWetUnknownCandidate: sum((z) => z.counts.baselineWetUnknownCandidate) },
  };
}

/** Zone partition must add back to the comparison exactly (integer counts). Returns the list of mismatches; empty = reconciled. */
export function reconcileZones(z: CandidateZoneResult, c: CandidateCompareResult): string[] {
  const p: string[] = [];
  const chk = (name: string, a: number, b: number) => { if (a !== b) p.push(`${name}: zones ${a} vs comparison ${b}`); };
  chk("cells", z.totals.cells, c.cells.total);
  chk("confirmed gained", z.totals.gained, c.wet.confirmedGained);
  chk("confirmed lost", z.totals.lost, c.wet.confirmedLost);
  chk("wet in both", z.totals.bothWet, c.wet.bothWet);
  chk("candidate wet over unknown baseline", z.totals.candidateWetUnknownBaseline, c.wet.candidateWetUnknownBaseline);
  chk("baseline wet over unknown candidate", z.totals.baselineWetUnknownCandidate, c.wet.baselineWetUnknownCandidate);
  return p;
}

export function explainCandidateZone(z: CandidateZoneRow): string {
  if (!z.priority) return "No confirmed change or eligible earlier arrival is flagged in this zone.";
  const parts: string[] = [];
  if (z.counts.gained > 0) parts.push(`${z.confirmedGainedKm2 < 0.005 ? "<0.01" : z.confirmedGainedKm2.toFixed(2)} km² is confirmed newly wet (known depth in both rasters, depth above 0.1 m only in the new run)`);
  if (z.medianAdvanceH !== null) parts.push(z.medianAdvanceH > 0 ? `the new run reaches paired cells a median ${z.medianAdvanceH.toFixed(1)} h earlier` : z.medianAdvanceH < 0 ? `the new run reaches paired cells a median ${Math.abs(z.medianAdvanceH).toFixed(1)} h later` : "paired arrival is unchanged at the median");
  else if (z.timingUnavailableReason) parts.push(`timing is unavailable: ${z.timingUnavailableReason.replace(/\.$/, "")}`);
  const um = z.unmatchedCandidateWetKm2;
  return `Priority for review: ${parts.join("; ")}.${um > 0 ? ` A further ${um.toFixed(2)} km² of the new run is wet over cells where the reference has no data (unmatched coverage, shown separately, not a confirmed change).` : ""} Zone coverage of the raster: ${(z.rasterCoverage * 100).toFixed(0)}%.`;
}
