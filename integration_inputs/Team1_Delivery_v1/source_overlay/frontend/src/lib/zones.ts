// Coordinate review zones and "priority for review" ordering (rule version "zone-rule-v1").
// These are fixed squares in the projected CRS (EPSG:32643), labelled "coordinate review zones".
// They are not administrative areas: no village names, population, buildings or roads are implied.
//
// Zone assignment: each raster cell belongs to exactly one zone, the one that contains the cell CENTRE.
// Zones therefore form a complete, non-overlapping partition of the raster and zone totals add up exactly.
// Partial zones at the raster edge simply contain fewer cells; their raster coverage is reported.
//
// Order ("priority for review", not an evacuation order and not an optimal release decision):
//   1. zones with newly flooded area (candidate wet, baseline not wet): descending new area, ties by zone id;
//   2. other zones whose paired arrival timing is eligible and where the candidate is reached EARLIER
//      (median of baseline - candidate > 0): descending median advance, ties by zone id.
//   Timing is eligible only with >= MIN_PAIRED_CELLS paired cells AND paired cells >= MIN_PAIRED_FRACTION of the
//   cells that have a valid arrival in either scenario inside the zone. Otherwise timing is "unavailable", never zero.
import { Grid, WET_THRESHOLD_M, isValid, m2ToKm2, medianOfInts, pixelAreaM2, gridsAligned } from "./compare";
import { MINUTES_PER_HOUR } from "./timeline";

export const ZONE_RULE_VERSION = "zone-rule-v1";
export const ZONE_SIZE_M = 5000;
export const MIN_PAIRED_CELLS = 50;
export const MIN_PAIRED_FRACTION = 0.5;

export type PriorityReason = "new_flooded_area" | "earlier_arrival";
export interface ZoneRow {
  id: string; bounds: [number, number, number, number]; // minX, minY, maxX, maxY in metres
  cells: number; rasterCoverage: number; // cells in raster / cells of a full zone
  newWetKm2: number; lostWetKm2: number; commonWetKm2: number; baselineWetKm2: number; candidateWetKm2: number;
  pairedArrivalCells: number; pairedArrivalFraction: number | null;
  medianAdvanceH: number | null; // (baseline - candidate) in hours; positive = candidate reached earlier
  timingUnavailableReason: string | null;
  priority: { rank: number; reason: PriorityReason } | null;
}
export interface ZoneResult {
  version: string; zoneSizeM: number; pixelAreaM2: number; minPairedCells: number; minPairedFraction: number;
  zones: ZoneRow[]; // every zone that contains raster cells, sorted by id
  ranked: ZoneRow[];
  totals: { newWetKm2: number; lostWetKm2: number; commonWetKm2: number; cells: number };
}

const km = (n: number) => String(Math.floor(n / 1000)).padStart(4, "0");
export function zoneId(ix: number, iy: number, size = ZONE_SIZE_M): string { return `Z-E${km(ix * size)}-N${km(iy * size)}`; }

interface Acc { ix: number; iy: number; cells: number; newC: number; lostC: number; commonC: number; baseW: number; candW: number; baseArr: number; candArr: number; either: number; diffs: number[] }

export function computeZones(baseline: Grid, candidate: Grid, size = ZONE_SIZE_M): ZoneResult | string {
  const why = gridsAligned(baseline, candidate);
  if (why) return why;
  const { width, height, geo } = baseline;
  const colZone = new Int32Array(width);
  for (let c = 0; c < width; c++) colZone[c] = Math.floor((geo.originX + (c + 0.5) * geo.pixelWidth) / size);
  const accs = new Map<string, Acc>();
  for (let r = 0; r < height; r++) {
    const iy = Math.floor((geo.originY - (r + 0.5) * geo.pixelHeight) / size);
    for (let c = 0; c < width; c++) {
      const ix = colZone[c];
      const key = `${ix}:${iy}`;
      let a = accs.get(key);
      if (!a) { a = { ix, iy, cells: 0, newC: 0, lostC: 0, commonC: 0, baseW: 0, candW: 0, baseArr: 0, candArr: 0, either: 0, diffs: [] }; accs.set(key, a); }
      const i = r * width + c;
      a.cells++;
      const bd = baseline.depth[i], cd = candidate.depth[i];
      const bw = isValid(bd) && bd > WET_THRESHOLD_M, cw = isValid(cd) && cd > WET_THRESHOLD_M;
      if (bw) a.baseW++;
      if (cw) a.candW++;
      if (bw && cw) a.commonC++; else if (cw) a.newC++; else if (bw) a.lostC++;
      const ba = baseline.arrival[i], ca = candidate.arrival[i];
      const bv = isValid(ba), cv = isValid(ca);
      if (bv) a.baseArr++;
      if (cv) a.candArr++;
      if (bv || cv) a.either++;
      if (bv && cv) a.diffs.push(ba - ca); // baseline - candidate, minutes (positive = candidate earlier)
    }
  }
  const px = pixelAreaM2(geo);
  const fullCells = (size * size) / px;
  const zones: ZoneRow[] = [];
  for (const a of accs.values()) {
    const sorted = Int32Array.from(a.diffs).sort();
    const paired = sorted.length;
    const frac = a.either > 0 ? paired / a.either : null;
    let median: number | null = null, reason: string | null = null;
    if (paired === 0) reason = "No cell has a valid arrival time in both scenarios.";
    else if (paired < MIN_PAIRED_CELLS) reason = `Only ${paired} paired cells (minimum ${MIN_PAIRED_CELLS}).`;
    else if (frac !== null && frac < MIN_PAIRED_FRACTION) reason = `Paired cells cover ${(frac * 100).toFixed(0)}% of cells with an arrival time in either scenario (minimum ${MIN_PAIRED_FRACTION * 100}%).`;
    else { const m = medianOfInts(sorted); median = m === null ? null : m / MINUTES_PER_HOUR; }
    zones.push({
      id: zoneId(a.ix, a.iy, size), bounds: [a.ix * size, a.iy * size, (a.ix + 1) * size, (a.iy + 1) * size],
      cells: a.cells, rasterCoverage: Math.min(1, a.cells / fullCells), // edge cells of the pixel grid can slightly exceed a nominal zone; never report above 100%
      newWetKm2: m2ToKm2(a.newC * px), lostWetKm2: m2ToKm2(a.lostC * px), commonWetKm2: m2ToKm2(a.commonC * px),
      baselineWetKm2: m2ToKm2(a.baseW * px), candidateWetKm2: m2ToKm2(a.candW * px),
      pairedArrivalCells: paired, pairedArrivalFraction: frac, medianAdvanceH: median, timingUnavailableReason: reason, priority: null,
    });
  }
  zones.sort((x, y) => (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
  const group1 = zones.filter((z) => z.newWetKm2 > 0).sort((x, y) => y.newWetKm2 - x.newWetKm2 || (x.id < y.id ? -1 : 1));
  const g1 = new Set(group1.map((z) => z.id));
  const group2 = zones.filter((z) => !g1.has(z.id) && z.medianAdvanceH !== null && z.medianAdvanceH > 0)
    .sort((x, y) => (y.medianAdvanceH as number) - (x.medianAdvanceH as number) || (x.id < y.id ? -1 : 1));
  const ranked: ZoneRow[] = [];
  group1.forEach((z) => { z.priority = { rank: ranked.length + 1, reason: "new_flooded_area" }; ranked.push(z); });
  group2.forEach((z) => { z.priority = { rank: ranked.length + 1, reason: "earlier_arrival" }; ranked.push(z); });
  const sum = (f: (z: ZoneRow) => number) => zones.reduce((s, z) => s + f(z), 0);
  return { version: ZONE_RULE_VERSION, zoneSizeM: size, pixelAreaM2: px, minPairedCells: MIN_PAIRED_CELLS, minPairedFraction: MIN_PAIRED_FRACTION, zones, ranked,
    totals: { newWetKm2: sum((z) => z.newWetKm2), lostWetKm2: sum((z) => z.lostWetKm2), commonWetKm2: sum((z) => z.commonWetKm2), cells: sum((z) => z.cells) } };
}

export function explainZone(z: ZoneRow): string {
  if (!z.priority) return "No change flagged for review in this zone.";
  const parts: string[] = [];
  if (z.priority.reason === "new_flooded_area") parts.push(`${z.newWetKm2.toFixed(2)} km² is flooded (depth > ${WET_THRESHOLD_M} m) in the candidate but not in the baseline`);
  if (z.medianAdvanceH !== null) parts.push(z.medianAdvanceH > 0 ? `the candidate reaches paired cells a median ${z.medianAdvanceH.toFixed(1)} h earlier` : z.medianAdvanceH < 0 ? `the candidate reaches paired cells a median ${Math.abs(z.medianAdvanceH).toFixed(1)} h later` : "paired arrival times are unchanged at the median");
  else if (z.timingUnavailableReason) parts.push(`timing is unavailable: ${z.timingUnavailableReason.replace(/\.$/, "")}`);
  return `Priority for review: ${parts.join("; ")}. Zone coverage of the raster: ${(z.rasterCoverage * 100).toFixed(0)}%.`;
}
