import { describe, expect, it } from "vitest";
import { buildTimelineExpression, cellState, clampHours, elapsedMinutes, revealCounts, timelineMaxHours } from "./timeline";

// Minimal evaluator for the flat-style subset used by buildTimelineExpression, so the real
// expression (not a re-implementation of its rules) is exercised on sample cell values.
type Ctx = { bands: number[]; vars: Record<string, number> };
function ev(e: unknown, c: Ctx): any {
  if (!Array.isArray(e)) return e;
  const [op, ...a] = e as [string, ...unknown[]];
  switch (op) {
    case "band": return c.bands[(a[0] as number) - 1];
    case "var": return c.vars[a[0] as string];
    case "/": return ev(a[0], c) / ev(a[1], c);
    case "<=": return ev(a[0], c) <= ev(a[1], c);
    case "case": for (let i = 0; i + 1 < a.length; i += 2) if (ev(a[i], c)) return ev(a[i + 1], c); return ev(a[a.length - 1], c);
    case "interpolate": {
      const x = ev(a[1], c) as number; const st = a.slice(2) as [number, number[]][] | unknown[];
      const pts: [number, number[]][] = []; for (let i = 0; i < st.length; i += 2) pts.push([st[i] as number, st[i + 1] as number[]]);
      if (x <= pts[0][0]) return pts[0][1]; if (x >= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
      for (let i = 0; i < pts.length - 1; i++) if (x <= pts[i + 1][0]) { const t = (x - pts[i][0]) / (pts[i + 1][0] - pts[i][0]); return pts[i][1].map((v, k) => v + t * (pts[i + 1][1][k] - v)); }
      throw new Error("interp");
    }
    default:
      if (Array.isArray(e) && typeof e[0] === "number") return e; // colour literal handled by caller
      throw new Error("op " + op);
  }
}
const run = (colorBy: "arrival" | "depth" | "velocity", arrival: number, depth: number, hours: number) =>
  ev(buildTimelineExpression(colorBy), { bands: [arrival, depth], vars: { elapsedMin: elapsedMinutes(hours) } }) as number[];

describe("timeline arithmetic", () => {
  it("converts hours to minutes once", () => { expect(elapsedMinutes(3)).toBe(180); expect(elapsedMinutes(0)).toBe(0); });
  it("limits come from the declared model-clock window", () => {
    expect(timelineMaxHours("2006-08-06T06:00:00Z", "2006-08-11T00:00:00Z")).toBe(114);
    expect(timelineMaxHours("2006-08-06T00:00:00Z", "2006-08-11T18:00:00Z")).toBe(138);
    expect(timelineMaxHours(null, "2006-08-11T18:00:00Z")).toBeNull();
    expect(timelineMaxHours("2006-08-11T18:00:00Z", "2006-08-06T00:00:00Z")).toBeNull();
    expect(timelineMaxHours("garbage", "x")).toBeNull();
  });
  it("clamps", () => { expect(clampHours(500, 114)).toBe(114); expect(clampHours(-3, 114)).toBe(0); expect(clampHours(NaN, 114)).toBe(0); });
});

describe("cell states", () => {
  it("distinguishes unavailable, unreached and reached; boundary is inclusive", () => {
    expect(cellState(-9999, 600)).toBe("unavailable");
    expect(cellState(NaN, 600)).toBe("unavailable");
    expect(cellState(180, elapsedMinutes(2))).toBe("unreached");
    expect(cellState(180, elapsedMinutes(3))).toBe("reached");
    expect(cellState(180, elapsedMinutes(4))).toBe("reached");
    expect(cellState(60, 0)).toBe("unreached");
  });
  it("reveal is monotonic and counts add up", () => {
    const a = [-9999, 60, 120, 180, 180, 240, 6840];
    let prev = -1;
    for (let h = 0; h <= 114; h++) { const c = revealCounts(a, elapsedMinutes(h)); expect(c.reached + c.unreached + c.unavailable).toBe(a.length); expect(c.reached >= prev).toBe(true); prev = c.reached; }
    expect(revealCounts(a, elapsedMinutes(114)).reached).toBe(6);
    expect(revealCounts(a, 0).reached).toBe(0);
  });
});

describe("style expression behaviour on sample cells", () => {
  it("a 180-minute cell is absent at 2 h and present at 3 h", () => {
    expect(run("arrival", 180, 5, 2)).toEqual([120, 134, 150, 0.27]);
    const shown = run("arrival", 180, 5, 3);
    expect(shown.length).toBe(3);
  });
  it("nodata is fully transparent at every time; it never becomes a colour", () => {
    for (const h of [0, 3, 114]) { expect(run("arrival", -9999, -9999, h)).toEqual([0, 0, 0, 0]); expect(run("depth", -9999, 5, h)).toEqual([0, 0, 0, 0]); }
  });
  it("reached cell with nodata depth gets the neutral 'no value' colour, never a depth colour", () => {
    expect(run("depth", 120, -9999, 5)).toEqual([150, 150, 150, 1]);
    expect(run("velocity", 120, -9999, 5)).toEqual([150, 150, 150, 1]);
  });
  it("unreached cells keep the same pale tint whichever value is coloured", () => {
    expect(run("depth", 600, 12, 2)).toEqual([120, 134, 150, 0.27]);
    expect(run("velocity", 600, 3, 2)).toEqual([120, 134, 150, 0.27]);
  });
});
