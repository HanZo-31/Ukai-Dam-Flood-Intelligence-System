import { fromArrayBuffer } from "geotiff";
import { describe, expect, it } from "vitest";
import expected from "./fixtures/point_samples.json";
import { pointCell, samplePointImage, pointGrid, type MapPoint } from "./pointInspection";
import type { PrototypeLayer } from "./api";

const root = new URL("../../../", import.meta.url);
const fields = [
  { key: "depth", file: "max_depth.tif", role: "max_depth_cog", unit: "m" },
  { key: "arrival", file: "arrival_time.tif", role: "arrival_time_cog", unit: "min" },
  { key: "velocity", file: "max_velocity.tif", role: "max_velocity_cog", unit: "m/s" },
] as const;

describe("single-cell reader against independent rasterio values", () => {
  for (const [name, fixture] of Object.entries(expected.scenarios)) {
    it(`${name}: actual depth, arrival, velocity and nodata at original resolution`, async () => {
      const fsName = "node:fs", urlName = "node:url";
      const fs = await import(/* @vite-ignore */ fsName), url = await import(/* @vite-ignore */ urlName);
      for (const field of fields) {
        const bytes = fs.readFileSync(url.fileURLToPath(new URL(`${fixture.folder}/assets/${field.file}`, root)));
        const tiff = await fromArrayBuffer(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer);
        const image = await tiff.getImage(0);
        const layer = { asset_type: field.role, unit: field.unit, format: "cog", crs: "EPSG:32643", nodata: -9999 } as PrototypeLayer;
        const grid = pointGrid(image, layer);
        expect(grid.width).toBe(3072); expect(grid.height).toBe(1024);
        for (const point of fixture.points) {
          expect(pointCell(grid, point.coordinate as MapPoint)).toEqual({ row: point.row, col: point.col });
          const value = await samplePointImage(image, layer, point.coordinate as MapPoint);
          const independent = point.values[field.key];
          if (independent <= -9000 || !Number.isFinite(independent)) expect(value).toMatchObject({ kind: "nodata", value: null });
          else { expect(value.kind).toBe("value"); expect(value.value).toBeCloseTo(independent, 6); }
        }
        expect((await samplePointImage(image, layer, [grid.originX - 1, grid.originY])).kind).toBe("outside");
        await expect(samplePointImage(image, { ...layer, crs: "EPSG:4326" }, fixture.points[0].coordinate as MapPoint)).rejects.toThrow("CRS");
        await expect(samplePointImage(image, { ...layer, nodata: 0 }, fixture.points[0].coordinate as MapPoint)).rejects.toThrow("nodata");
      }
    }, 120000);
  }
});
