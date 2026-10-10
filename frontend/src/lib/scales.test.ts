import { describe, expect, it } from "vitest";
import { buildColorExpression, displayToRaw, hexToRgb, legendTicks, rawToDisplay, SCALES } from "./scales";

describe("scales", () => {
  it("arrival raw minutes show as hours; depth/velocity unchanged", () => {
    expect(rawToDisplay("arrival", 1440)).toBe(24);
    expect(displayToRaw("arrival", 24)).toBe(1440);
    expect(rawToDisplay("depth", 12.5)).toBe(12.5);
    expect(rawToDisplay("velocity", 3)).toBe(3);
  });
  it("same fixed domains for every scenario", () => {
    expect(SCALES.depth.stops.at(-1)![0]).toBe(40);
    expect(SCALES.velocity.stops.at(-1)![0]).toBe(12);
    expect(SCALES.arrival.stops.at(-1)![0]).toBe(140);
  });
  it("nodata is transparent in the style expression and arrival divides by 60 once", () => {
    const e = buildColorExpression("arrival") as unknown[];
    expect(e[0]).toBe("case");
    expect(e[2]).toEqual([0, 0, 0, 0]);
    expect(JSON.stringify(e[3])).toContain('["/",["band",1],60]');
    const d = buildColorExpression("depth") as unknown[];
    expect(JSON.stringify(d[3])).not.toContain('"/"');
  });
  it("hex parsing and ticks", () => {
    expect(hexToRgb("#1677EF")).toEqual([22, 119, 239]);
    expect(() => hexToRgb("blue")).toThrow();
    expect(legendTicks("depth").at(-1)).toEqual({ value: 40, pct: 100 });
  });
});
