import { describe, expect, it } from "vitest";
import { loadFixtures } from "../../testing/fixtureLoad";
import { createFixtureTransport } from "../../testing/computeFixtureTransport";
import { createComputeClient } from "./client";
import { ComputeController } from "./controller";
import { assetRows, classRgba, identityRows, rasterRgba, timingRows, TIMING_NOTE } from "./present";

async function accepted(b = {}) {
  const fx = await loadFixtures();
  const t = createFixtureTransport(fx.files, b);
  const c = new ComputeController({ client: createComputeClient({ fetchImpl: t.fetch }), inflate: fx.inflate, sleep: async () => {}, pollMs: 1, newRequestId: () => "req-1" });
  await c.run(25000);
  return c.getState().run.current!;
}
describe("result presentation", () => {
  it("shows identity honestly: computed, not validated, uncalibrated, run/job/config", async () => {
    const rows = identityRows(await accepted());
    const get = (l: string) => rows.find((r) => r.label === l)?.value;
    expect(get("Scientifically validated")).toBe("No");
    expect(get("Calibration")).toBe("uncalibrated");
    expect(get("Requested peak release")).toBe("25,000 m³/s");
    expect(get("Actual peak release")).toBe("25,000 m³/s");
    expect(get("Computed by the service")).toMatch(/^Yes/);
    expect(get("Served from cache")).toMatch(/^No/);
    expect(get("Run ID")).toMatch(/^synthetic-run-/);
    expect(get("Configuration")).toMatch(/^synthetic-config-v01 · sha256:/);
  });
  it("timing rows carry the declared scope and no target or SLA wording", async () => {
    const a = await accepted();
    const text = timingRows(a.result).map((r) => `${r.label} ${r.value} ${r.note ?? ""}`).join(" ") + TIMING_NOTE;
    expect(text).toMatch(/not_browser_ready/);
    expect(text).not.toMatch(/\bSLA\b|guarantee|within \d|target|fast enough|real-time/i);
  });
  it("lists every product with a status and a reason for each unavailable one", async () => {
    const rows = assetRows(await accepted());
    expect(rows.map((r) => r.role)).toEqual(["max_depth_cog", "arrival_time_cog", "max_velocity_cog", "extent_geojson"]);
    expect(rows.filter((r) => r.status === "received").length).toBe(3);
    const vel = rows.find((r) => r.role === "max_velocity_cog")!;
    expect(vel.status).toBe("unavailable");
    expect(vel.detail.length).toBeGreaterThan(5);
  });
  it("a corrupted product is unavailable with its reason, never silently drawn", async () => {
    const rows = assetRows(await accepted({ assets: "bad_checksum" }));
    expect(rows.find((r) => r.role === "max_depth_cog")!.status).toBe("unavailable");
  });
  it("drawing: dry is unshaded, wet is coloured, unknown (nodata) is a distinct grey", async () => {
    const a = await accepted();
    const rgba = rasterRgba(a.products.decoded!.depth!, "depth");
    const g = a.products.decoded!.depth!;
    for (let i = 0; i < g.data.length; i++) {
      const alpha = rgba[i * 4 + 3];
      if (g.data[i] === -9999) { expect(alpha).toBeGreaterThan(0); expect(rgba.slice(i * 4, i * 4 + 3)).toEqual(Uint8ClampedArray.from([120, 130, 140])); } // unknown: neutral grey, not dry, not a depth colour
      else if (g.data[i] <= Math.fround(0.1)) expect(alpha).toBe(0); else expect(alpha).toBeGreaterThan(0);
    }
    const cls = classRgba(Uint8Array.from([0, 1, 2, 3, 4, 5]));
    expect(cls[3]).toBe(0);
    for (let k = 1; k < 6; k++) expect(cls[k * 4 + 3]).toBeGreaterThan(0);
  });
});
