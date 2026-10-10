// Zone oracle. 4x4 packet case: timing must be ineligible (4 pairs < 50). Large case: 100x100 grid of 100 m cells -> four 5 km zones, every
// number below was counted by hand from the construction in buildLarge().
import { describe, expect, it } from "vitest";
import { ORACLE } from "../../testing/fixtureLoad";
import { compareCandidate, type CompareGrid } from "./candidateCompare";
import { CANDIDATE_ZONE_RULE_VERSION, computeCandidateZones, explainCandidateZone, reconcileZones } from "./candidateZones";

const geo = { originX: 270000, originY: 2360000, pixelWidth: 100, pixelHeight: 100 };
const mk4 = (depth: number[][], arrival: number[][]): CompareGrid => ({ width: 4, height: 4, geo, crs: "EPSG:32643", depth: Float32Array.from(depth.flat()), arrival: Float32Array.from(arrival.flat()) });

describe("packet 4x4", () => {
  const b = mk4(ORACLE.baseline_depth, ORACLE.baseline_arrival_minutes), c = mk4(ORACLE.candidate_depth, ORACLE.candidate_arrival_minutes);
  it("has 3 gained, flagged by wet area, with timing unavailable (4 < 50 pairs)", () => {
    const z = computeCandidateZones(b, c, null);
    expect(typeof z).not.toBe("string");
    const r = z as Exclude<typeof z, string>;
    expect(r.version).toBe(CANDIDATE_ZONE_RULE_VERSION);
    expect(r.zones.length).toBe(1);
    const z0 = r.zones[0];
    expect(z0.counts.gained).toBe(3);
    expect(z0.counts.lost).toBe(2);
    expect(z0.pairedArrivalCells).toBe(4);
    expect(z0.medianAdvanceMin).toBeNull();
    expect(z0.timingUnavailableReason).toMatch(/Only 4 paired cells \(minimum 50\)/);
    expect(z0.priority).toEqual({ rank: 1, reason: "confirmed_gained_wet_area" });
    expect(explainCandidateZone(z0)).toMatch(/timing is unavailable/);
  });
  it("reconciles with the comparison", () => {
    const z = computeCandidateZones(b, c, null) as Exclude<ReturnType<typeof computeCandidateZones>, string>;
    const cmp = compareCandidate(b, c, null) as Exclude<ReturnType<typeof compareCandidate>, string>;
    expect(reconcileZones(z, cmp)).toEqual([]);
    expect(reconcileZones({ ...z, totals: { ...z.totals, gained: 99 } }, cmp).length).toBe(1);
  });
  it("blocked arrival keeps wet ranking and gives the block as reason", () => {
    const z = computeCandidateZones(b, c, "Different definition.") as Exclude<ReturnType<typeof computeCandidateZones>, string>;
    expect(z.arrivalAvailable).toBe(false);
    expect(z.zones[0].timingUnavailableReason).toBe("Different definition.");
    expect(z.zones[0].priority?.rank).toBe(1);
  });
});

function buildLarge() {
  const W = 100, H = 100, N = W * H;
  const bd = new Float32Array(N), cd = new Float32Array(N), ba = new Float32Array(N).fill(-9999), ca = new Float32Array(N).fill(-9999);
  const at = (r: number, c: number) => r * W + c;
  const g = { originX: 0, originY: 10000, pixelWidth: 100, pixelHeight: 100 };
  // Zone A (ix0,iy1 = rows 0-49, cols 0-49): 100 gained (rows0-9 x cols0-9); 60 both wet (row20-21 x cols0-29) arrival base 180 / cand 120 -> advance 60
  for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) cd[at(r, c)] = 0.5;
  for (let r = 20; r < 22; r++) for (let c = 0; c < 30; c++) { bd[at(r, c)] = 1; cd[at(r, c)] = 1; ba[at(r, c)] = 180; ca[at(r, c)] = 120; }
  // Zone B (ix1,iy1 = rows 0-49, cols 50-99): 20 gained (row0 x cols50-69); 5 paired arrivals (row 30 x cols 50-54), equal -> diff 0
  for (let c = 50; c < 70; c++) cd[at(0, c)] = 0.5;
  for (let c = 50; c < 55; c++) { ba[at(30, c)] = 60; ca[at(30, c)] = 60; }
  // Zone C (ix0,iy0 = rows 50-99, cols 0-49): 55 both wet (row60 x 50 cols + row61 x cols0-4), base 180 / cand 60 -> advance 120
  for (let c = 0; c < 50; c++) { bd[at(60, c)] = 1; cd[at(60, c)] = 1; ba[at(60, c)] = 180; ca[at(60, c)] = 60; }
  for (let c = 0; c < 5; c++) { bd[at(61, c)] = 1; cd[at(61, c)] = 1; ba[at(61, c)] = 180; ca[at(61, c)] = 60; }
  // Zone D (ix1,iy0 = rows 50-99, cols 50-99): 7 lost (row90 x cols50-56); 60 paired (row70 x 50 + row71 x cols50-59) diff 0;
  // 200 baseline-only arrivals (rows72-75 x 50 cols) -> paired 60 / either 260 = 23% < 50% -> ineligible by fraction
  for (let c = 50; c < 57; c++) bd[at(90, c)] = 1;
  for (let c = 50; c < 100; c++) { ba[at(70, c)] = 60; ca[at(70, c)] = 60; }
  for (let c = 50; c < 60; c++) { ba[at(71, c)] = 60; ca[at(71, c)] = 60; }
  for (let r = 72; r < 76; r++) for (let c = 50; c < 100; c++) ba[at(r, c)] = 120;
  const base: CompareGrid = { width: W, height: H, geo: g, crs: "EPSG:32643", depth: bd, arrival: ba };
  const cand: CompareGrid = { width: W, height: H, geo: g, crs: "EPSG:32643", depth: cd, arrival: ca };
  return { base, cand };
}

describe("large synthetic case (>=50 paired cells per eligible zone)", () => {
  const { base, cand } = buildLarge();
  const z = computeCandidateZones(base, cand, null) as Exclude<ReturnType<typeof computeCandidateZones>, string>;
  const byCounts = (g: number) => z.zones.find((q) => q.counts.gained === g)!;
  it("partitions into four 5 km zones covering all 10,000 cells", () => {
    expect(z.zones.length).toBe(4);
    expect(z.zones.map((q) => q.cells)).toEqual([2500, 2500, 2500, 2500]);
    expect(z.totals).toEqual({ cells: 10000, gained: 120, lost: 7, bothWet: 115, candidateWetUnknownBaseline: 0, baselineWetUnknownCandidate: 0 });
    expect(z.zones.every((q) => q.rasterCoverage === 1)).toBe(true);
  });
  it("zone A: 100 gained, 60 pairs, median advance 60 min = 1 h", () => {
    const a = byCounts(100);
    expect(a.pairedArrivalCells).toBe(60);
    expect(a.eitherArrivalCells).toBe(60);
    expect(a.medianAdvanceMin).toBe(60);
    expect(a.medianAdvanceH).toBe(1);
    expect(a.confirmedGainedKm2).toBeCloseTo(1, 12);
    expect(a.priority).toEqual({ rank: 1, reason: "confirmed_gained_wet_area" });
  });
  it("zone B: 20 gained, only 5 pairs -> timing ineligible", () => {
    const b = byCounts(20);
    expect(b.pairedArrivalCells).toBe(5);
    expect(b.medianAdvanceMin).toBeNull();
    expect(b.timingUnavailableReason).toMatch(/Only 5 paired cells/);
    expect(b.priority).toEqual({ rank: 2, reason: "confirmed_gained_wet_area" });
  });
  it("zone C: nothing gained but 55 pairs advance 120 min -> ranked 3 by earlier arrival", () => {
    const c = z.zones.find((q) => q.counts.bothWet === 55)!;
    expect(c.counts.gained).toBe(0);
    expect(c.pairedArrivalCells).toBe(55);
    expect(c.pairedArrivalFraction).toBe(1);
    expect(c.medianAdvanceMin).toBe(120);
    expect(c.priority).toEqual({ rank: 3, reason: "earlier_paired_arrival" });
  });
  it("zone D: 7 lost, 60 pairs but only 60/260 in either -> ineligible by fraction, not flagged", () => {
    const d = z.zones.find((q) => q.counts.lost === 7)!;
    expect(d.pairedArrivalCells).toBe(60);
    expect(d.eitherArrivalCells).toBe(260);
    expect(d.medianAdvanceMin).toBeNull();
    expect(d.timingUnavailableReason).toMatch(/23%.*minimum 50%/);
    expect(d.priority).toBeNull();
    expect(explainCandidateZone(d)).toMatch(/No confirmed change/);
  });
  it("ranked list order is gained desc, then median advance desc, then id", () => {
    expect(z.ranked.map((q) => q.counts.gained)).toEqual([100, 20, 0]);
    expect(z.ranked.map((q) => q.priority?.rank)).toEqual([1, 2, 3]);
  });
  it("overall comparison agrees: paired 180, mean -10200/180, median -60 (candidate minus baseline), earlier 115, same 65", () => {
    const c = compareCandidate(base, cand, null) as Exclude<ReturnType<typeof compareCandidate>, string>;
    expect(reconcileZones(z, c)).toEqual([]);
    expect(c.arrival.pairedCells).toBe(180);
    expect(c.arrival.meanDiffMin).toBeCloseTo(-10200 / 180, 9); // candidate minus baseline: negative = candidate earlier
    expect(c.arrival.medianDiffMin).toBe(-60);
    expect(c.arrival.earlier).toBe(115);
    expect(c.arrival.same).toBe(65);
    expect(c.arrival.later).toBe(0);
    expect(c.arrival.baselineOnlyValid).toBe(200);
  });
  it("is deterministic across runs", () => { expect(JSON.stringify(computeCandidateZones(base, cand, null))).toBe(JSON.stringify(z)); });
  it("a tiny real positive area is not explained as 0.00 km²", () => {
    const tiny = { ...z.ranked[0], confirmedGainedKm2: 0.000841 };
    expect(explainCandidateZone(tiny)).toContain("<0.01 km²");
  });
});
