import { describe, expect, it } from "vitest";
import { arrivalPointCompatible, pointAssetPath, pointCell, pointDifference, pointRange, pointValue, readPoint, type PointGrid } from "./pointInspection";
import type { PrototypeDetail, PrototypeLayer, PrototypeLayers } from "./api";

const grid: PointGrid = { width: 2, height: 2, originX: 300000, originY: 2400000, pixelWidth: 10, pixelHeight: 10, crs: "EPSG:32643" };
const layer = { asset_type: "max_depth_cog", format: "cog", crs: "EPSG:32643", unit: "m", nodata: -9999,
  url: "/api/v1/prototypes/scenarios/fixture-h02/assets/max_depth_cog" } as PrototypeLayer;
const arrival = { arrival: { unit: "min", origin: "simulation_start", reference_timestamp: "2026-01-01T00:00:00Z", threshold_m: .1, temporal_resolution_minutes: 60 }, coverage_start: "2026-01-01T00:00:00Z" } as PrototypeDetail;
const options = { headers: { Range: "bytes=0-3" } };

describe("original-cell point semantics", () => {
  it("uses pixel area with west/north included and east/south excluded", () => {
    expect(pointCell(grid, [300000, 2400000])).toEqual({ row: 0, col: 0 });
    expect(pointCell(grid, [300019.9, 2399980.1])).toEqual({ row: 1, col: 1 });
    expect(pointCell(grid, [300020, 2399995])).toBeNull();
    expect(pointCell(grid, [300005, 2399980])).toBeNull();
    expect(pointCell(grid, [299999, 2400000])).toBeNull();
    expect(pointCell(grid, [NaN, 2400000])).toBeNull();
  });
  it.each([-9999, -9998, NaN, Infinity])("never turns missing/nonfinite %s into zero", v => expect(pointValue(v)).toMatchObject({ kind: "nodata", value: null }));
  it("preserves real zero and rejects invalid negative metric values", () => {
    expect(pointValue(0)).toEqual({ kind: "value", value: 0 });
    expect(pointValue(-.5).kind).toBe("unavailable");
  });
  it("computes candidate-minus-baseline only for the same grid cell", () => {
    const a = { ...pointValue(2), grid, row: 0, col: 1 }, b = { ...a, value: 5 };
    expect(pointDifference(a, b).value).toBe(3);
    expect(pointDifference(b, a).value).toBe(-3);
    expect(pointDifference(a, { ...b, col: 0 }).value).toBeNull();
    expect(pointDifference(a, { ...b, grid: { ...grid, originX: 300001 } }).value).toBeNull();
    expect(pointDifference(a, pointValue(-9999)).value).toBeNull();
    expect(pointDifference({ ...a, value: 0 }, { ...b, value: 0 }).value).toBe(0);
  });
  it("requires compatible elapsed arrival metadata, not equal calendar starts", () => {
    expect(arrivalPointCompatible(arrival, arrival)).toBe(true);
    const later = { ...arrival, coverage_start: "2026-01-02T00:00:00Z", arrival: { ...arrival.arrival, reference_timestamp: "2026-01-02T00:00:00Z" } };
    expect(arrivalPointCompatible(arrival, later)).toBe(true);
    expect(arrivalPointCompatible(arrival, { ...arrival, arrival: { ...arrival.arrival, unit: "h" } })).toBe(false);
    expect(arrivalPointCompatible(arrival, { ...arrival, arrival: { ...arrival.arrival, threshold_m: 1 } })).toBe(false);
    expect(arrivalPointCompatible(arrival, { ...arrival, coverage_start: "unknown" })).toBe(false);
  });
  it("restricts requests to the stored-raster namespace/role", () => {
    expect(pointAssetPath(layer)).toBe(layer.url);
    expect(pointAssetPath({ ...layer, url: "https://example.test" + layer.url })).toBe(layer.url);
    for (const url of ["//example.test/x", "/api/v1/candidates/jobs/x", "/api/v1/prototypes/scenarios/../assets/max_depth_cog", layer.url + "?x=y"])
      expect(() => pointAssetPath({ ...layer, url })).toThrow();
    expect(() => pointAssetPath({ ...layer, url: layer.url.replace("max_depth", "max_velocity") })).toThrow();
  });
});

describe("bounded range transport and availability", () => {
  const f = (body: Uint8Array, status = 206, range = "bytes 0-3/12", length = "4") => (async () => new Response(body as BodyInit, { status, headers: { "Content-Range": range, "Content-Length": length } })) as typeof fetch;
  it("accepts an exact 206 range", async () => {
    const result = await pointRange(layer.url, options, f(new Uint8Array([1, 2, 3, 4])));
    expect([...new Uint8Array(result.data)]).toEqual([1, 2, 3, 4]);
  });
  it("rejects whole-file fallback before consuming a 200 response", async () => {
    await expect(pointRange(layer.url, options, f(new Uint8Array(4), 200))).rejects.toThrow("whole-file fallback");
  });
  it.each(["bytes 1-4/12", "bytes 0-9/12", "bytes 0-3/3", "invalid"])("rejects bad Content-Range %s", async range => {
    await expect(pointRange(layer.url, options, f(new Uint8Array(4), 206, range))).rejects.toThrow("Content-Range");
  });
  it("rejects truncated, oversized and inconsistent bodies", async () => {
    await expect(pointRange(layer.url, options, f(new Uint8Array(3)))).rejects.toThrow("truncated");
    await expect(pointRange(layer.url, options, f(new Uint8Array(5)))).rejects.toThrow("exceeded");
    await expect(pointRange(layer.url, options, f(new Uint8Array(4), 206, "bytes 0-3/12", "8"))).rejects.toThrow("length");
  });
  it("rejects oversized/multi-range requests before fetching", async () => {
    const fail = (async () => { throw new Error("fetch must not be called"); }) as typeof fetch;
    await expect(pointRange(layer.url, { headers: { Range: "bytes=0-2000000" } }, fail)).rejects.toThrow("limit");
    await expect(pointRange(layer.url, { headers: { Range: "bytes=0-3,8-10" } }, fail)).rejects.toThrow("single bounded");
  });
  it("keeps absent assets and incompatible units unavailable without fetches", async () => {
    const data = { layers: [{ ...layer, unit: "ft" }] } as PrototypeLayers;
    const result = await readPoint(data, [300005, 2399995], undefined, (async () => { throw new Error("unexpected fetch"); }) as typeof fetch);
    expect(result.depth.kind).toBe("error");
    expect(result.depth.reason).toContain("Expected m");
    expect(result.arrival.kind).toBe("unavailable");
    expect(result.velocity.value).toBeNull();
  });
  it("honors cancellation before reading", async () => {
    const controller = new AbortController(); controller.abort();
    await expect(readPoint({ layers: [layer] } as PrototypeLayers, [300005, 2399995], controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  });
});
