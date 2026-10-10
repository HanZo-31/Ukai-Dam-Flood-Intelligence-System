import { describe, expect, it } from "vitest";
import provenanceJson from "./terrain/provenance.json?raw";
import { createLocalTerrain, TERRAIN_LIMITATION } from "./localTerrain";
import { TERRAIN_EXTENT } from "./terrain/extent";

describe("offline display-only terrain", () => {
  it("is below flood layers, uses the exact projected extent, and never changes the view", () => {
    const layer = createLocalTerrain(() => {});
    expect(layer.getZIndex()).toBe(-20);
    expect(layer.getSource()!.getProjection()!.getCode()).toBe("EPSG:32643");
    expect(layer.getSource()!.getImageExtent()).toEqual(TERRAIN_EXTENT);
    expect(TERRAIN_EXTENT).toEqual([260653.128487587, 2334521.7312866333, 364034.6824212541, 2369001.58195343]);
    expect(layer.getSource()!.getUrl()).not.toMatch(/^https?:|\/\/|api\//);
    layer.dispose();
  });
  it("can be hidden without touching flood opacity or map status", () => {
    let failed = false;
    const layer = createLocalTerrain(() => { failed = true; });
    layer.setVisible(false);
    expect(layer.getVisible()).toBe(false);
    layer.getSource()!.dispatchEvent("imageloaderror");
    expect(failed).toBe(true);
    expect(layer.getOpacity()).toBe(1);
    layer.dispose();
  });
  it("does not invent elevation units, calibration or an outside-footprint basemap", () => {
    expect(TERRAIN_LIMITATION).toContain("elevation units, vertical datum and source licence remain unverified");
    const provenance = JSON.parse(provenanceJson);
    expect(provenance.elevation_units).toBeNull();
    expect(provenance.vertical_datum).toBeNull();
    expect(provenance.contours_labelled).toBe(false);
    expect(provenance.transparent_nodata_pixels).toBeGreaterThan(0);
  });
});
