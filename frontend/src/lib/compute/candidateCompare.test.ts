// Independent oracle: expected numbers come from the packet's hand-calculated oracle (SYNTHETIC arrays), not from running the code.
import { describe, expect, it } from "vitest";
import { ORACLE } from "../../testing/fixtureLoad";
import {
  alignmentProblem, arrivalValid, CLS_BASE_UNMATCHED, CLS_BOTH_WET, CLS_CAND_UNMATCHED, CLS_GAINED, CLS_LOST, compareCandidate, depthState, medianOf, S_DRY, S_INVALID, S_NODATA, S_WET,
  VELOCITY_REASON, WET_THRESHOLD_F32, type CompareGrid,
} from "./candidateCompare";

const geo = { originX: 270000, originY: 2360000, pixelWidth: 100, pixelHeight: 100 };
const mk = (depth: number[][], arrival: number[][] | null): CompareGrid => ({
  width: depth[0].length, height: depth.length, geo, crs: "EPSG:32643", depth: Float32Array.from(depth.flat()), arrival: arrival ? Float32Array.from(arrival.flat()) : null,
});
const base = mk(ORACLE.baseline_depth, ORACLE.baseline_arrival_minutes);
const cand = mk(ORACLE.candidate_depth, ORACLE.candidate_arrival_minutes);

describe("depth classification", () => {
  it("nodata is unknown, never dry; wet is strictly above float32 0.1", () => {
    expect(depthState(-9999)).toBe(S_NODATA);
    expect(depthState(Number.NaN)).toBe(S_INVALID);
    expect(depthState(-0.5)).toBe(S_INVALID);
    expect(depthState(0)).toBe(S_DRY);
    expect(depthState(0.05)).toBe(S_DRY);
    expect(depthState(WET_THRESHOLD_F32)).toBe(S_DRY);       // exactly 0.1 as stored in float32: dry
    expect(depthState(new Float32Array([0.1])[0])).toBe(S_DRY);
    expect(depthState(Math.fround(0.100001))).toBe(S_WET);
    expect(depthState(0.2)).toBe(S_WET);
  });
  it("arrival validity", () => {
    expect(arrivalValid(0)).toBe(true);
    expect(arrivalValid(60)).toBe(true);
    expect(arrivalValid(-9999)).toBe(false);
    expect(arrivalValid(Number.NaN)).toBe(false);
    expect(arrivalValid(-1)).toBe(false);
  });
  it("median", () => {
    expect(medianOf(Float64Array.from([]))).toBeNull();
    expect(medianOf(Float64Array.from([5]))).toBe(5);
    expect(medianOf(Float64Array.from([0, 30, 30, 60]))).toBe(30);
    expect(medianOf(Float64Array.from([0, 60]))).toBe(30);
  });
});

describe("packet oracle (4x4, SYNTHETIC)", () => {
  const r = compareCandidate(base, cand, null);
  it("returns a result", () => { expect(typeof r).not.toBe("string"); });
  const c = r as Exclude<typeof r, string>;
  it("validity counts", () => {
    expect(c.cells.baselineValid).toBe(ORACLE.oracle.baseline_valid_cells);
    expect(c.cells.candidateValid).toBe(ORACLE.oracle.candidate_valid_cells);
    expect(c.cells.bothValid).toBe(ORACLE.oracle.both_valid_cells);
    expect(c.cells.baselineOnlyValid).toBe(ORACLE.oracle.baseline_only_valid_cells);
    expect(c.cells.candidateOnlyValid).toBe(ORACLE.oracle.candidate_only_valid_cells);
  });
  it("wet counts, with recorded-only coverage kept separate", () => {
    expect(c.wet.bothWet).toBe(ORACLE.oracle.both_wet_cells);
    expect(c.wet.confirmedGained).toBe(3);
    expect(c.wet.confirmedLost).toBe(2);
    expect(c.wet.candidateOnlyRecordedWet).toBe(ORACLE.oracle.candidate_only_recorded_wet_cells);
    expect(c.wet.baselineOnlyRecordedWet).toBe(ORACLE.oracle.baseline_only_recorded_wet_cells);
    expect(c.wet.candidateWetUnknownBaseline).toBe(1);
    expect(c.wet.baselineWetUnknownCandidate).toBe(1);
    expect(c.km2.confirmedGained).toBeCloseTo(0.03, 12);
    expect(c.km2.confirmedLost).toBeCloseTo(0.02, 12);
    expect(c.km2.netRecordedChange).toBeCloseTo(0.01, 12);
  });
  it("paired arrival statistics (minutes; mean 15, median 30)", () => {
    expect(c.arrival.available).toBe(true);
    expect(c.arrival.pairedCells).toBe(4);
    expect(c.arrival.meanDiffMin).toBe(15);
    expect(c.arrival.medianDiffMin).toBe(30);
    expect(c.arrival.meanDiffH).toBe(0.25);
    expect(c.arrival.medianDiffH).toBe(0.5);
  });
  it("classes mark exactly the gained, lost, matched, and unmatched cells", () => {
    const n = (k: number) => Array.from(c.classes).filter((x) => x === k).length;
    expect(n(CLS_GAINED)).toBe(3);
    expect(n(CLS_LOST)).toBe(2);
    expect(n(CLS_BOTH_WET)).toBe(4);
    expect(n(CLS_CAND_UNMATCHED)).toBe(1);
    expect(n(CLS_BASE_UNMATCHED)).toBe(1);
  });
  it("velocity is never compared", () => { expect(c.velocity).toEqual({ available: false, reason: VELOCITY_REASON }); });
  it("depth differences are taken only over cells wet in both rasters (4 here), never over unknown or dry-vs-wet cells", () => { expect(c.depth.pairedCells).toBe(4); });
});

describe("arrival gating", () => {
  it("a block reason disables arrival but keeps wet counts", () => {
    const r = compareCandidate(base, cand, "Native threshold differs.");
    expect(typeof r).not.toBe("string");
    const c = r as Exclude<typeof r, string>;
    expect(c.arrival.available).toBe(false);
    expect(c.arrival.reason).toBe("Native threshold differs.");
    expect(c.arrival.meanDiffMin).toBeNull();
    expect(c.wet.confirmedGained).toBe(3);
  });
  it("missing arrival raster disables arrival", () => {
    const r = compareCandidate(base, mk(ORACLE.candidate_depth, null), null) as Exclude<ReturnType<typeof compareCandidate>, string>;
    expect(r.arrival.available).toBe(false);
  });
});

describe("grid alignment is mandatory", () => {
  it("refuses sub-pixel metric shifts despite large projected coordinates", () => {
    expect(alignmentProblem(base, { ...cand, geo: { ...geo, originY: geo.originY + 0.5 } })).toMatch(/same grid/);
    expect(alignmentProblem(base, { ...cand, geo: { ...geo, originX: geo.originX + 0.1 } })).toMatch(/same grid/);
  });
  it("refuses unequal size, geotransform, or CRS", () => {
    expect(alignmentProblem(base, cand)).toBeNull();
    expect(typeof compareCandidate(base, { ...cand, width: 3 }, null)).toBe("string");
    expect(typeof compareCandidate(base, { ...cand, geo: { ...geo, originX: geo.originX + 100 } }, null)).toBe("string");
    expect(typeof compareCandidate(base, { ...cand, geo: { ...geo, pixelWidth: 99.9 } }, null)).toBe("string");
    expect(typeof compareCandidate(base, { ...cand, crs: "EPSG:4326" }, null)).toBe("string");
  });
});
