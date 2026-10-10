import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import Experimental from "../../pages/Experimental";
import { setComputeControllerForTests } from "../../hooks/useCompute";
import { loadFixtures } from "../../testing/fixtureLoad";
import { createFixtureTransport } from "../../testing/computeFixtureTransport";
import { ComputeController } from "./controller";
import { createComputeClient } from "./client";
import { rasterRgba } from "./present";

async function controller() {
  const fx = await loadFixtures(); const t = createFixtureTransport(fx.files);
  let seq = 0;
  const c = new ComputeController({ client: createComputeClient({ fetchImpl: t.fetch }), inflate: fx.inflate,
    sleep: async () => {}, pollMs: 1, newRequestId: () => `view-${++seq}` });
  await c.run(25000);
  return c;
}

describe("computed view integration guards", () => {
  it("shows actual pixel dimensions, scientific limits, component definition and a display legend", async () => {
    const c = await controller(); setComputeControllerForTests(c);
    try {
      const html = renderToStaticMarkup(createElement(Experimental, { views: [], active: false, onOpenWhatIf: () => {} }));
      expect(html).toContain("Displayed grid pixels");
      expect(html).toContain("100.000 × 100.000 m");
      expect(html).toContain("Velocity definition");
      expect(html).toContain("Velocity component");
      expect(html).toContain("Display colours");
      expect(html).toContain("not validated hazard classes");
      expect(html).toContain("Download Maximum depth");
      expect(html).toContain("aria-describedby=");
    } finally { setComputeControllerForTests(null); }
  });
  it("shows the identified previous result while new product downloads are paused", async () => {
    const c = await controller();
    let paused = false;
    c.subscribe(() => { if (!paused && c.getState().run.phase === "loading_products") { paused = true; c.suspend(); } });
    await c.run(25000); setComputeControllerForTests(c);
    try {
      const html = renderToStaticMarkup(createElement(Experimental, { views: [], active: false, onOpenWhatIf: () => {} }));
      expect(html).toContain("Previous computed result (not the latest run)");
      expect(html).toContain(c.getState().run.previous!.result.run_id);
      expect(html).toContain("Maximum depth");
    } finally { setComputeControllerForTests(null); }
  });
  it("colours the delivered absolute velocity component without an arrival-unit conversion", async () => {
    const c = await controller();
    const depth = c.getState().run.current!.products.decoded!.depth!;
    const grid = { ...depth, width: 2, height: 1, data: Float32Array.from([2, -9999]) };
    expect(rasterRgba(grid, "velocity").slice(0, 4)).toEqual(Uint8ClampedArray.from([247, 164, 74, 225]));
    expect(rasterRgba(grid, "velocity").slice(4)).toEqual(Uint8ClampedArray.from([120, 130, 140, 150]));
    c.dispose();
  });
});
