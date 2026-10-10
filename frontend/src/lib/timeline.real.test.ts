// Uses numbers read independently (numpy/tifffile) from the stored rasters; see fixtures/arrival_samples.json.
import { describe, expect, it } from "vitest";
import data from "./fixtures/arrival_samples.json";
import { cellState, elapsedMinutes, revealCounts, timelineMaxHours } from "./timeline";

type Cell = { row: number; col: number; arrival: number; depth: number };
type Scn = typeof data.scenarios.h02;
const scenarios = Object.entries(data.scenarios) as [string, Scn][];

function expand(hist: Record<string, number>): number[] {
  const out: number[] = [];
  for (const [v, c] of Object.entries(hist)) for (let i = 0; i < c; i++) out.push(Number(v));
  return out;
}

describe.each(scenarios)("stored arrival grid %s", (_name: string, s: Scn) => {
  const arrivals = expand(s.histogram);
  it("arrival values are whole hours stored as minutes (no further rescaling)", () => {
    expect(Object.keys(s.histogram).every((k) => Number(k) % 60 === 0 && Number(k) >= 60)).toBe(true);
  });
  it("reveal counts equal the independent per-hour counts", () => {
    for (const [h, n] of Object.entries(s.reachedByHour)) expect(revealCounts(arrivals, elapsedMinutes(Number(h))).reached).toBe(n);
  });
  it("nothing is reached at 0 h and reveal never decreases", () => {
    expect(revealCounts(arrivals, 0).reached).toBe(0);
    let prev = 0;
    for (let h = 0; h <= s.maxHours; h++) { const r = revealCounts(arrivals, elapsedMinutes(h)).reached; expect(r >= prev).toBe(true); prev = r; }
  });
  it("final hour of the window reveals exactly the valid-arrival footprint", () => {
    const r = revealCounts(arrivals, elapsedMinutes(s.maxHours));
    expect(r.reached).toBe(s.validArrival);
    expect(r.unreached).toBe(0);
  });
  it("sampled 180-minute cells are absent at 2 h and present at 3 h", () => {
    expect(s.samples180.length).toBeGreaterThan(0);
    for (const c of s.samples180 as Cell[]) {
      expect(c.arrival).toBe(180);
      expect(cellState(c.arrival, elapsedMinutes(2))).toBe("unreached");
      expect(cellState(c.arrival, elapsedMinutes(3))).toBe("reached");
    }
  });
  it("sampled nodata cells are unavailable at every hour", () => {
    for (const c of s.nodataSamples as Cell[]) { expect(c.arrival).toBe(-9999); for (const h of [0, 3, s.maxHours]) expect(cellState(c.arrival, elapsedMinutes(h))).toBe("unavailable"); }
  });
});

describe("window from the stored model-clock coverage", () => {
  it("matches the hours used for the fixtures", () => {
    expect(timelineMaxHours("2006-08-06T06:00:00Z", "2006-08-11T00:00:00Z")).toBe(data.scenarios.h01.maxHours);
    expect(timelineMaxHours("2006-08-06T00:00:00Z", "2006-08-11T18:00:00Z")).toBe(data.scenarios["2006"].maxHours);
  });
});
