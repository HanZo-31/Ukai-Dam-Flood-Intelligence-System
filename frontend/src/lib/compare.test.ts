import { describe, expect, it } from "vitest";
import { arrivalBin, arrivalChangeBins, ARRIVAL_BIN_LABELS, CLASS_COMMON, CLASS_LOST, CLASS_NEW, compareGrids, pixelAreaM2, type Grid } from "./compare";
import { computeZones, explainZone, zoneId } from "./zones";

const NODATA = -9999;
function grid(w: number, h: number, depth: (x: number, y: number) => number, arrival: (x: number, y: number) => number, px = 10): Grid {
  const d = new Float32Array(w * h), a = new Float32Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { d[y * w + x] = depth(x, y); a[y * w + x] = arrival(x, y); }
  return { width: w, height: h, geo: { originX: 0, originY: h * px, pixelWidth: px, pixelHeight: px }, depth: d, arrival: a };
}

describe("compare-v1 on a small grid", () => {
  // 4x2 grid. baseline wet: x=0,1 ; candidate wet: x=1,2 ; x=3 nodata in baseline, 5 m in candidate? (candidate-only valid, wet)
  const base = grid(4, 2, (x) => (x < 2 ? 2 : x === 2 ? 0.05 : NODATA), (x) => (x < 2 ? 120 : NODATA));
  const cand = grid(4, 2, (x) => (x === 0 ? 0 : x < 3 ? 3 : 4), (x) => (x === 0 ? NODATA : x < 3 ? 60 + 60 * x : 600));
  const r = compareGrids(base, cand);
  it("classifies new, common and baseline-only wet cells; nodata is not wet", () => {
    if (typeof r === "string") throw new Error(r);
    expect(r.counts.commonWet).toBe(2);       // x=1 (2 rows)
    expect(r.counts.lostWet).toBe(2);         // x=0 (2 rows): baseline wet, candidate depth 0
    expect(r.counts.newWet).toBe(4);          // x=2 (baseline 0.05 m) and x=3 (baseline nodata)
    expect(r.classes[1]).toBe(CLASS_COMMON); expect(r.classes[0]).toBe(CLASS_LOST); expect(r.classes[2]).toBe(CLASS_NEW); expect(r.classes[3]).toBe(CLASS_NEW);
  });
  it("keeps coverage differences separate", () => {
    if (typeof r === "string") throw new Error(r);
    expect(r.counts.candidateOnlyValid).toBe(2); expect(r.counts.baselineOnlyValid).toBe(0); expect(r.counts.bothValid).toBe(6);
    expect(r.arrival.candidateOnlyValid).toBe(4); // x=2,3 valid arrival in candidate only
    expect(r.arrival.baselineOnlyValid).toBe(2);  // x=0 valid in baseline only
  });
  it("area is count x |a*e - b*d|, in km2", () => {
    if (typeof r === "string") throw new Error(r);
    expect(pixelAreaM2(base.geo)).toBe(100);
    expect(r.km2.newWet).toBeCloseTo((4 * 100) / 1e6, 12);
  });
  it("paired differences are candidate minus baseline; arrival converted to hours once", () => {
    if (typeof r === "string") throw new Error(r);
    expect(r.depth.pairedCells).toBe(2); expect(r.depth.meanDiffM).toBeCloseTo(1, 6); // 3 - 2
    expect(r.arrival.pairedCells).toBe(2);   // x=1 only: baseline 120, candidate 120
    expect(r.arrival.meanDiffH).toBe(0);
  });
  it("swapping reverses the signs and swaps new/lost", () => {
    const s = compareGrids(cand, base);
    if (typeof r === "string" || typeof s === "string") throw new Error("compare failed");
    expect(s.counts.newWet).toBe(r.counts.lostWet + 0 === 2 ? s.counts.newWet : -1);
    expect(s.counts.newWet).toBe(r.counts.lostWet); expect(s.counts.lostWet).toBe(r.counts.newWet);
    expect(s.depth.meanDiffM).toBeCloseTo(-(r.depth.meanDiffM as number), 9);
  });
  it("same scenario gives zero change", () => {
    const z = compareGrids(base, base);
    if (typeof z === "string") throw new Error(z);
    expect(z.counts.newWet).toBe(0); expect(z.counts.lostWet).toBe(0); expect(z.depth.meanDiffM).toBe(0); expect(z.arrival.meanDiffH).toBe(0);
  });
  it("an unaligned pair is unavailable with a reason, not compared", () => {
    const other = grid(4, 3, () => 1, () => 60);
    expect(typeof compareGrids(base, other)).toBe("string");
    const shifted: Grid = { ...cand, geo: { ...cand.geo, originX: 5 } };
    expect(compareGrids(base, shifted)).toMatch(/same grid/);
  });
});

describe("zone-rule-v1 on a synthetic partition", () => {
  // 20x10 cells of 500 m => two 5 km zones (10x10 cells). Zone 0 gains new flooding; zone 1 only arrives earlier.
  const W = 20, H = 10, PX = 500; // 500 m cells: each 10x10 block is one 5 km zone
  const base = grid(W, H, (x) => (x < 5 ? 2 : NODATA), () => 600, PX);
  const cand = grid(W, H, (x, y) => (x < 8 && y < 5 ? 2 : x >= 10 ? 2 : NODATA), (x) => (x >= 10 ? 540 : 600), PX);
  const baseTimed = grid(W, H, (x) => (x < 5 || x >= 10 ? 2 : NODATA), () => 600, PX);
  it("every cell is in exactly one zone and totals reconcile with the whole-grid comparison", () => {
    const z = computeZones(baseTimed, cand, 5000);
    const c = compareGrids(baseTimed, cand);
    if (typeof z === "string" || typeof c === "string") throw new Error("failed");
    expect(z.zones.length).toBe(2);
    expect(z.totals.cells).toBe(W * H);
    expect(z.totals.newWetKm2).toBeCloseTo(c.km2.newWet, 12);
    expect(z.totals.lostWetKm2).toBeCloseTo(c.km2.lostWet, 12);
    expect(z.totals.commonWetKm2).toBeCloseTo(c.km2.commonWet, 12);
  });
  it("orders new flooded area first, then earlier arrival; ids break ties", () => {
    const z = computeZones(baseTimed, cand, 5000);
    if (typeof z === "string") throw new Error(z);
    expect(z.ranked.map((r) => r.priority?.reason)).toEqual(["new_flooded_area", "earlier_arrival"]);
    expect(z.ranked[0].medianAdvanceH).toBe(0); // timing equal in this zone: reported as 0 h, not hidden
    expect(z.ranked[1].medianAdvanceH).toBeCloseTo(1, 9); // 600 -> 540 minutes: one hour earlier
    expect(explainZone(z.ranked[1])).toMatch(/earlier/);
    expect(computeZones(baseTimed, cand, 5000)).toEqual(z); // deterministic
  });
  it("same-scenario comparison yields no priority", () => {
    const z = computeZones(base, base, 5000);
    if (typeof z === "string") throw new Error(z);
    expect(z.ranked.length).toBe(0);
  });
  it("timing is unavailable (not zero) without enough paired cells", () => {
    const sparse = grid(W, H, () => 2, (x, y) => (x === 0 && y === 0 ? 600 : NODATA), PX);
    const z = computeZones(sparse, sparse, 5000);
    if (typeof z === "string") throw new Error(z);
    expect(z.zones[0].medianAdvanceH).toBeNull();
    expect(z.zones[0].timingUnavailableReason).toMatch(/Only 1 paired/);
    expect(z.zones[1].timingUnavailableReason).toMatch(/No cell/);
  });
  it("coverage never exceeds 100% and explanations have no doubled full stops", () => {
    const big = grid(21, 10, () => 2, () => NODATA, 500); // 21 columns of 500 m: the last zone is partial
    const z = computeZones(big, big, 5000);
    if (typeof z === "string") throw new Error(z);
    expect(z.zones.every((r) => r.rasterCoverage <= 1)).toBe(true);
    const row = { ...z.zones[0], priority: { rank: 1, reason: "new_flooded_area" as const }, newWetKm2: 1, medianAdvanceH: null, timingUnavailableReason: "Only 3 paired cells (minimum 50)." };
    expect(explainZone(row).includes("..")).toBe(false);
  });
  it("zone ids come from kilometre corners", () => { expect(zoneId(53, 473)).toBe("Z-E0265-N2365"); });
});

describe("arrival change bins", () => {
  it("bins are symmetric around zero and cover every difference", () => {
    expect([-48, -24, -23, -6, -5, -1, 0, 1, 5, 6, 23, 24, 48].map(arrivalBin)).toEqual([1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6, 7, 7]);
    expect(ARRIVAL_BIN_LABELS.length).toBe(8);
  });
  it("classes only cells with a valid arrival in both, in candidate-minus-baseline hours", () => {
    const base = grid(4, 1, () => 1, (x) => [600, 600, NODATA, 600][x]);
    const cand = grid(4, 1, () => 1, (x) => [540, 600, 600, 600 + 60 * 30][x]);
    const r = arrivalChangeBins(base, cand);
    if (typeof r === "string") throw new Error(r);
    expect(Array.from(r.bins)).toEqual([3, 4, 0, 7]);        // 1 h earlier, same, unpaired, 30 h later
    expect(r.counts).toEqual([1, 0, 0, 1, 1, 0, 0, 1]);
    expect(r.counts.reduce((a, b) => a + b, 0)).toBe(4);       // partition of all cells
  });
  it("same scenario: every paired cell is 'same'; swap mirrors the bins", () => {
    const g = grid(3, 1, () => 1, (x) => 120 + x * 60);
    const h = grid(3, 1, () => 1, (x) => 120 + x * 60 + 600);
    const same = arrivalChangeBins(g, g), ab = arrivalChangeBins(g, h), ba = arrivalChangeBins(h, g);
    if (typeof same === "string" || typeof ab === "string" || typeof ba === "string") throw new Error("failed");
    expect(same.counts[4]).toBe(3);
    expect(Array.from(ab.bins)).toEqual([6, 6, 6]); expect(Array.from(ba.bins)).toEqual([2, 2, 2]); // 10 h later vs 10 h earlier
  });
  it("misaligned grids are unavailable", () => { expect(typeof arrivalChangeBins(grid(2, 1, () => 1, () => 60), grid(3, 1, () => 1, () => 60))).toBe("string"); });
});
