import { describe, expect, it } from "vitest";
import { lonLatToUtm43, utm43ToLonLat } from "./utm";

describe("UTM zone 43 transform", () => {
  it("central meridian maps to easting 500000, equator to northing 0", () => {
    const [e, n] = lonLatToUtm43([75, 0]);
    expect(e).toBeCloseTo(500000, 3);
    expect(n).toBeCloseTo(0, 3);
  });
  it("known value: lon 75, lat 21 -> N ~ 2322 km", () => {
    const [e, n] = lonLatToUtm43([75, 21]);
    expect(e).toBeCloseTo(500000, 3);
    expect(n).toBeGreaterThan(2_318_000);
    expect(n).toBeLessThan(2_326_000);
  });
  it("round trip agrees to better than a centimetre", () => {
    for (const p of [[73.6, 21.2], [74.2, 21.9], [76.5, 20.1]] as const) {
      const [lon, lat] = utm43ToLonLat(lonLatToUtm43(p));
      expect(lon).toBeCloseTo(p[0], 7);
      expect(lat).toBeCloseTo(p[1], 7);
    }
  });
});
