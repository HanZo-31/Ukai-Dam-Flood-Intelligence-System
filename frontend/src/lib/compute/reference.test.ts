import { describe, expect, it } from "vitest";
import { loadFixtures } from "../../testing/fixtureLoad";
import { clearRasterCache } from "../rasterCache";
import type { PrototypeLayers } from "../api";
import { loadCandidateReference } from "./reference";

describe("optional reference arrival cannot hide usable depth", () => {
  const layers = (arrival = true, depthUnit = "m") => ({ layers: [
    { asset_type: "max_depth_cog", url: "/reference-depth", crs: "EPSG:32643", unit: depthUnit, nodata: -9999 },
    ...(arrival ? [{ asset_type: "arrival_time_cog", url: "/reference-arrival", crs: "EPSG:32643", unit: "min", nodata: -9999 }] : []),
  ] }) as unknown as PrototypeLayers;
  it("loads depth with null arrival when the optional role is absent", async () => {
    clearRasterCache(); const fx = await loadFixtures();
    const f = (async () => new Response(fx.ab(fx.f.baselineDepth))) as typeof fetch;
    const grid = await loadCandidateReference(layers(false), f, fx.inflate);
    expect(grid.depth.length).toBe(16); expect(grid.arrival).toBeNull();
  });
  it("a failed optional arrival download preserves depth", async () => {
    clearRasterCache(); const fx = await loadFixtures();
    const f = (async (url) => String(url).includes("arrival") ? new Response("Unavailable", { status: 503 }) : new Response(fx.ab(fx.f.baselineDepth))) as typeof fetch;
    const grid = await loadCandidateReference(layers(), f, fx.inflate);
    expect(grid.depth.length).toBe(16); expect(grid.arrival).toBeNull();
  });
  it("rejects incompatible depth units before any raster request", async () => {
    clearRasterCache(); const fx = await loadFixtures();
    const f = (async () => { throw new Error("must not request"); }) as typeof fetch;
    await expect(loadCandidateReference(layers(true, "ft"), f, fx.inflate)).rejects.toThrow(/metadata/);
  });
});
