// Raster / outline decoding against the SYNTHETIC packet TIFFs (expected values = the packet's hand-authored arrays) and mutated TIFFs.
import { describe, expect, it } from "vitest";
import examples from "../../testing/fixtures_v2/examples.json";
import { loadFixtures, ORACLE } from "../../testing/fixtureLoad";
import { buildDeflateTiff } from "../../testing/tiffWriter";
import { decodeExtent, decodeProducts, decodeRaster, readEpsg } from "./decode";
import type { ResultV2 } from "./contract";

const result = examples.result as unknown as ResultV2;
const R = { derived_grid: result.derived_grid, arrival_definition: result.arrival_definition };
const flat = (a: number[][]) => a.flat();

async function mutated(over: Partial<Parameters<typeof buildDeflateTiff>[0]>, values?: number[]) {
  const { io, ab } = await loadFixtures();
  void ab;
  return buildDeflateTiff({ width: 4, height: 4, values: values ?? flat(ORACLE.candidate_depth), originX: 270000, originY: 2360000, pixelWidth: 100, pixelHeight: 100, deflate: io.deflate, ...over });
}

describe("packet TIFFs decode to the hand-authored arrays", () => {
  it("all four rasters, exactly (float32 values, nodata -9999 preserved)", async () => {
    const { f, ab, inflate } = await loadFixtures();
    const cases: [string, Uint8Array, number[][], "max_depth_cog" | "arrival_time_cog"][] = [
      ["baseline-depth", f.baselineDepth, ORACLE.baseline_depth, "max_depth_cog"],
      ["candidate-depth", f.candidateDepth, ORACLE.candidate_depth, "max_depth_cog"],
      ["baseline-arrival", f.baselineArrival, ORACLE.baseline_arrival_minutes, "arrival_time_cog"],
      ["candidate-arrival", f.candidateArrival, ORACLE.candidate_arrival_minutes, "arrival_time_cog"],
    ];
    for (const [name, bytes, want, role] of cases) {
      const g = await decodeRaster(role, ab(bytes), R, inflate);
      expect(typeof g, name).not.toBe("string");
      if (typeof g === "string") continue;
      expect(Array.from(g.data), name).toEqual(flat(want).map(Math.fround));
      expect(g.width).toBe(4); expect(g.height).toBe(4);
      expect(g.geo).toEqual({ originX: 270000, originY: 2360000, pixelWidth: 100, pixelHeight: 100 });
      expect(g.invalid).toBe(0);
      expect(g.valid + g.nodata).toBe(16);
    }
  });
  it("reports EPSG 32643 from the GeoKeyDirectory", async () => {
    const { f, ab } = await loadFixtures();
    expect(readEpsg(ab(f.candidateDepth))).toBe(32643);
  });
  it("decodeProducts returns rasters and the outline, bbox inside the grid", async () => {
    const { f, ab, inflate } = await loadFixtures();
    const d = await decodeProducts(R, { max_depth_cog: ab(f.candidateDepth), arrival_time_cog: ab(f.candidateArrival), extent_geojson: ab(f.extent) }, inflate);
    expect(d.depth).toBeTruthy(); expect(d.arrival).toBeTruthy(); expect(d.extent).toBeTruthy();
    expect(Object.keys(d.unavailable)).toEqual([]);
    const [x0, y0, x1, y1] = d.extent!.bboxUtm;
    expect(x0).toBeGreaterThan(269000); expect(x1).toBeLessThan(271000); expect(y0).toBeGreaterThan(2359000); expect(y1).toBeLessThan(2361000);
  });
});

describe("rasters that do not satisfy the contract are refused with a reason (never repaired)", () => {
  const dec = async (buf: ArrayBuffer, role: "max_depth_cog" | "arrival_time_cog" = "max_depth_cog") => decodeRaster(role, buf, R, (await loadFixtures()).inflate);
  it("wrong nodata value", async () => { expect(await dec(await mutated({ nodata: "-1" }))).toMatch(/nodata/); });
  it("missing nodata", async () => { expect(await dec(await mutated({ nodata: null }))).toMatch(/nodata/); });
  it("wrong CRS", async () => { expect(await dec(await mutated({ epsg: 4326 }))).toMatch(/EPSG:4326/); });
  it("missing CRS", async () => { expect(await dec(await mutated({ epsg: null }))).toMatch(/projected coordinate system/); });
  it("wrong size", async () => { expect(await dec(await mutated({ width: 5, height: 4 }, Array(20).fill(0)))).toMatch(/5×4/); });
  it("shifted origin", async () => { expect(await dec(await mutated({ originX: 270100 }))).toMatch(/georeferencing/); });
  it("sub-pixel projected northing shift", async () => { expect(await dec(await mutated({ originY: 2360000.5 }))).toMatch(/georeferencing/); });
  it("wrong pixel size", async () => { expect(await dec(await mutated({ pixelWidth: 90, pixelHeight: 90 }))).toMatch(/georeferencing/); });
  it("not float32", async () => { expect(await dec(await mutated({ bits: 64 }))).toMatch(/supported raster format/); });
  it("predictor", async () => { expect(await dec(await mutated({ predictor: 2 }))).toMatch(/supported raster format/); });
  it("not deflate", async () => { expect(await dec(await mutated({ compression: 1 }))).toMatch(/supported raster format/); });
  it("negative depth (not nodata)", async () => { const v = flat(ORACLE.candidate_depth); v[0] = -0.5; expect(await dec(await mutated({}, v))).toMatch(/neither nodata/); });
  it("NaN depth", async () => { const v = flat(ORACLE.candidate_depth); v[3] = Number.NaN; expect(await dec(await mutated({}, v))).toMatch(/neither nodata/); });
  it("arrival that is not whole hours (wrong unit or transform)", async () => {
    const v = flat(ORACLE.candidate_arrival_minutes); v[0] = 45;
    expect(await dec(await mutated({}, v), "arrival_time_cog")).toMatch(/not whole hours/);
  });
  it("not a TIFF at all", async () => { expect(await dec(new TextEncoder().encode("hello world, not a tiff").buffer as ArrayBuffer)).toMatch(/supported raster format/); });
  it("truncated TIFF", async () => {
    const full = await mutated({});
    expect(typeof (await dec(full.slice(0, 40)))).toBe("string");
  });
  it("a rejected raster leaves the others usable and records the reason", async () => {
    const { f, ab, inflate } = await loadFixtures();
    const d = await decodeProducts(R, { max_depth_cog: ab(f.candidateDepth), arrival_time_cog: await mutated({ epsg: 4326 }) }, inflate);
    expect(d.depth).toBeTruthy(); expect(d.arrival).toBeNull();
    expect(d.unavailable.arrival_time_cog).toMatch(/EPSG:4326/);
  });
});

describe("extent outline", () => {
  const grid = { originX: 270000, originY: 2360000, pixelWidth: 100, pixelHeight: 100, width: 4, height: 4 };
  it("accepts the packet outline", async () => { const { f } = await loadFixtures(); expect(typeof decodeExtent(new TextDecoder().decode(f.extent), grid)).toBe("object"); });
  it("refuses: invalid JSON, wrong type, point geometry, empty, swapped lon/lat, far away", () => {
    const fc = (g: unknown) => JSON.stringify({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: g }] });
    expect(decodeExtent("{nope", grid)).toMatch(/valid JSON/);
    expect(decodeExtent(JSON.stringify({ type: "Feature" }), grid)).toMatch(/FeatureCollection/);
    expect(decodeExtent(fc({ type: "Point", coordinates: [73, 21] }), grid)).toMatch(/only polygons/);
    expect(decodeExtent(JSON.stringify({ type: "FeatureCollection", features: [] }), grid)).toMatch(/no polygon rings/);
    expect(decodeExtent(fc({ type: "Polygon", coordinates: [[[21, 73], [21.1, 73], [21.1, 73.1], [21, 73]]] }), grid)).toMatch(/outside/);
    expect(decodeExtent(fc({ type: "Polygon", coordinates: [[[73.5, 21.2], [73.6, 21.2], [73.6, 21.3], [73.5, 21.2]]] }), grid)).toMatch(/beyond the raster grid/);
  });
});
