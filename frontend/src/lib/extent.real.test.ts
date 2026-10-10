import { expect, it } from "vitest";
import { extentGeoJsonFormat } from "../map/projection";
import { lonLatToUtm43 } from "./utm";
const fsName = "node:fs";
const { readFileSync } = await import(/* @vite-ignore */ fsName);

it.each(["h01", "h02", "h03", "2006"])("%s real extent uses declared geographic CRS and lands in the actual UTM domain", (name) => {
  const folder = name === "h02" ? "part_a" : `receipts/${name}`;
  const manifest = JSON.parse(readFileSync(new URL(`../../../${folder}/prototype-manifest.json`, import.meta.url), "utf8"));
  const geo = JSON.parse(readFileSync(new URL(`../../../${folder}/assets/extent.geojson`, import.meta.url), "utf8"));
  expect(manifest.asset_metadata.extent_geojson.crs).toBe("EPSG:4326");
  const original = geo.features[0];
  const coordinates = original.geometry.type === "MultiPolygon" ? original.geometry.coordinates[0] : original.geometry.coordinates;
  const first = coordinates[0][0];
  expect(first[0]).toBeGreaterThan(72); expect(first[0]).toBeLessThan(78);
  const feature = extentGeoJsonFormat(manifest.asset_metadata.extent_geojson.crs).readFeatures({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates } }] })[0];
  const geometry = feature.getGeometry();
  if (!geometry) throw new Error("Extent geometry missing");
  const bounds = geometry.getExtent();
  expect(bounds[0]).toBeGreaterThan(250000); expect(bounds[2]).toBeLessThan(400000);
  expect(bounds[1]).toBeGreaterThan(2300000); expect(bounds[3]).toBeLessThan(2400000);
  const [east, north] = lonLatToUtm43(first);
  expect(east).toBeGreaterThanOrEqual(bounds[0] - 0.01); expect(east).toBeLessThanOrEqual(bounds[2] + 0.01);
  expect(north).toBeGreaterThanOrEqual(bounds[1] - 0.01); expect(north).toBeLessThanOrEqual(bounds[3] + 0.01);
});

it("keeps already-projected outlines in metres", () => {
  const feature = extentGeoJsonFormat("EPSG:32643").readFeatures({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [300000, 2350000] } }] })[0];
  expect(feature.getGeometry()?.getExtent()).toEqual([300000, 2350000, 300000, 2350000]);
});
it("refuses unknown CRS rather than guessing", () => {
  expect(() => extentGeoJsonFormat("EPSG:unknown")).toThrow(/unsupported/);
});
