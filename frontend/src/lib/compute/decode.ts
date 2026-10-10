// Turns verified product bytes into grids the browser can compare and draw. Decoding uses the existing, inspected TIFF reader
// (lib/tiff.ts: classic little-endian TIFF, 256x256 tiles, float32, one band, Deflate, no predictor) and then adds the checks that reader
// does not make: georeferencing against the Result's derived grid, the projected CRS (GeoKeyDirectory), the exact nodata value, and sane
// physical values. An unsupported or inconsistent product is "unavailable" with a reason, never repaired, resampled or zero-filled.
import { readFloat32Tiff, type Inflate } from "../tiff";
import { lonLatToUtm43 } from "../utm";
import { NODATA, type ResultV2, type Role } from "./contract";

export interface GridGeo { originX: number; originY: number; pixelWidth: number; pixelHeight: number }
export interface ProductGrid {
  role: Role; width: number; height: number; geo: GridGeo; data: Float32Array;
  /** counts for the table fallback */
  valid: number; nodata: number; invalid: number; min: number | null; max: number | null;
}
export interface ExtentOutline {
  /** polygon rings in EPSG:4326 as delivered, plus the same rings in EPSG:32643 metres (transformed with lib/utm) */
  featureCount: number; ringCount: number; bboxUtm: [number, number, number, number]; geojson: unknown;
}
export interface Decoded {
  depth: ProductGrid | null; arrival: ProductGrid | null; velocity: ProductGrid | null; extent: ExtentOutline | null;
  /** per-role reason a product could not be used. Never empty for a missing/rejected role. */
  unavailable: Partial<Record<Role, string>>;
}

const T_GEOKEYS = 34735;
/** EPSG code from the GeoKeyDirectory (ProjectedCSTypeGeoKey 3072), or null when absent. Independent of the pixel reader. */
export function readEpsg(buf: ArrayBuffer): number | null {
  const dv = new DataView(buf);
  if (dv.byteLength < 8 || dv.getUint16(0, true) !== 0x4949 || dv.getUint16(2, true) !== 42) return null;
  const ifd = dv.getUint32(4, true);
  if (ifd + 2 > dv.byteLength) return null;
  const n = dv.getUint16(ifd, true);
  for (let i = 0; i < n; i++) {
    const e = ifd + 2 + i * 12;
    if (e + 12 > dv.byteLength) return null;
    if (dv.getUint16(e, true) !== T_GEOKEYS) continue;
    const type = dv.getUint16(e + 2, true), count = dv.getUint32(e + 4, true);
    if (type !== 3 || count < 4) return null;
    const off = count * 2 <= 4 ? e + 8 : dv.getUint32(e + 8, true);
    if (off + count * 2 > dv.byteLength) return null;
    const keys = dv.getUint16(off + 6, true);
    for (let k = 0; k < keys; k++) {
      const o = off + 8 + k * 8;
      if (o + 8 > dv.byteLength) return null;
      if (dv.getUint16(o, true) === 3072 && dv.getUint16(o + 2, true) === 0) return dv.getUint16(o + 6, true);
    }
    return null;
  }
  return null;
}

const nearly = (a: number, b: number): boolean => Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) <= 1e-7;

function gridFrom(role: Role, r: { width: number; height: number; data: Float32Array }, geo: GridGeo, validOf: (v: number) => boolean): ProductGrid {
  let valid = 0, nodata = 0, invalid = 0, min = Infinity, max = -Infinity;
  for (let i = 0; i < r.data.length; i++) {
    const v = r.data[i];
    if (v === NODATA) nodata++;
    else if (Number.isFinite(v) && validOf(v)) { valid++; if (v < min) min = v; if (v > max) max = v; }
    else invalid++;
  }
  return { role, width: r.width, height: r.height, geo, data: r.data, valid, nodata, invalid, min: valid ? min : null, max: valid ? max : null };
}

const VALID_NONNEG = (v: number) => v >= 0;
const VALID_ANY = () => true;

/** Decode one raster product against the Result's derived grid. Returns the grid or a human-readable reason (thrown as Error by callers is avoided). */
export async function decodeRaster(role: Role, buf: ArrayBuffer, result: Pick<ResultV2, "derived_grid" | "arrival_definition">, inflate: Inflate): Promise<ProductGrid | string> {
  let r;
  try { r = await readFloat32Tiff(buf, inflate); }
  catch (e) { return `This product is not in the supported raster format (${e instanceof Error ? e.message : "unreadable"}).`; }
  const g = result.derived_grid;
  if (r.width !== g.width || r.height !== g.height) return `The raster is ${r.width}×${r.height} but the Result declares ${g.width}×${g.height}.`;
  if (r.nodata !== NODATA) return `The raster nodata value is ${r.nodata === null ? "missing" : String(r.nodata)} but the contract requires -9999.`;
  const epsg = readEpsg(buf);
  if (epsg !== 32643) return epsg === null ? "The raster does not declare a projected coordinate system, so its position cannot be verified." : `The raster is in EPSG:${epsg}, not EPSG:32643.`;
  const [a, b, c, d, e, f] = g.transform;
  if (b !== 0 || d !== 0) return "The declared grid transform is rotated, which is not supported.";
  if (!nearly(r.pixelWidth, a) || !nearly(r.pixelHeight, -e) || !nearly(r.originX, c) || !nearly(r.originY, f))
    return "The raster's georeferencing differs from the Result's declared grid transform.";
  const geo: GridGeo = { originX: r.originX, originY: r.originY, pixelWidth: r.pixelWidth, pixelHeight: r.pixelHeight };
  const grid = gridFrom(role, r, geo, role === "max_velocity_cog" ? VALID_ANY : VALID_NONNEG);
  if (grid.invalid > 0) return `${grid.invalid} cell(s) hold values that are neither nodata (-9999) nor a valid ${role === "max_depth_cog" ? "depth" : "value"}; the product was not used.`;
  if (role === "arrival_time_cog") {
    // The documented transformation yields whole hours expressed in minutes. Anything else means the unit or transform is not what the contract says.
    let bad = 0;
    for (let i = 0; i < grid.data.length; i++) { const v = grid.data[i]; if (v !== NODATA && v % 60 !== 0) bad++; }
    if (bad > 0 && result.arrival_definition?.definition_compatible !== false) return `${bad} arrival value(s) are not whole hours (multiples of 60 minutes), which the declared hourly-ceiling transform cannot produce. Unit or transform is inconsistent; arrival was not used.`;
  }
  return grid;
}

function* positions(coords: unknown, depth: number): Generator<[number, number]> {
  if (!Array.isArray(coords)) return;
  if (depth === 0) { if (coords.length >= 2 && typeof coords[0] === "number" && typeof coords[1] === "number") yield [coords[0], coords[1]]; return; }
  for (const c of coords) yield* positions(c, depth - 1);
}

/** Validate the GeoJSON wet-extent outline (geographic coordinates) and project its bounds with the existing UTM transform. */
export function decodeExtent(text: string, grid: GridGeo & { width: number; height: number }): ExtentOutline | string {
  let doc: unknown;
  try { doc = JSON.parse(text); } catch { return "The extent outline is not valid JSON."; }
  const o = doc as { type?: unknown; features?: unknown };
  if (!o || o.type !== "FeatureCollection" || !Array.isArray(o.features)) return "The extent outline is not a GeoJSON FeatureCollection.";
  let rings = 0, minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const f of o.features as { type?: unknown; geometry?: { type?: unknown; coordinates?: unknown } | null }[]) {
    if (!f || f.type !== "Feature" || !f.geometry) return "The extent outline contains a feature without geometry.";
    const t = f.geometry.type;
    if (t !== "Polygon" && t !== "MultiPolygon") return `The extent outline contains a ${String(t)}; only polygons are supported.`;
    const level = t === "Polygon" ? 2 : 3;
    rings += t === "Polygon" ? (f.geometry.coordinates as unknown[]).length : (f.geometry.coordinates as unknown[][]).reduce((s, p) => s + p.length, 0);
    for (const [lon, lat] of positions(f.geometry.coordinates, level)) {
      if (!Number.isFinite(lon) || !Number.isFinite(lat) || Math.abs(lon) > 180 || Math.abs(lat) > 90) return "The outline has coordinates outside longitude/latitude ranges; it must be in geographic coordinates (EPSG:4326).";
      if (lon < 72 || lon > 78) return "The outline lies outside UTM zone 43, so it cannot be placed on this map.";
      const [x, y] = lonLatToUtm43([lon, lat]);
      if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
  }
  if (!rings || !Number.isFinite(minX)) return "The extent outline has no polygon rings.";
  const gx0 = grid.originX, gx1 = grid.originX + grid.width * grid.pixelWidth, gy1 = grid.originY, gy0 = grid.originY - grid.height * grid.pixelHeight;
  const slack = 2 * Math.max(grid.pixelWidth, grid.pixelHeight);
  if (minX < gx0 - slack || maxX > gx1 + slack || minY < gy0 - slack || maxY > gy1 + slack) return "The outline extends beyond the raster grid, so it does not belong to this result.";
  return { featureCount: o.features.length, ringCount: rings, bboxUtm: [minX, minY, maxX, maxY], geojson: doc };
}

export interface RawProducts { max_depth_cog?: ArrayBuffer; arrival_time_cog?: ArrayBuffer; max_velocity_cog?: ArrayBuffer; extent_geojson?: ArrayBuffer }

/** Decode every product that was successfully downloaded and verified. A role without bytes keeps whatever reason the caller already recorded. */
export async function decodeProducts(result: Pick<ResultV2, "derived_grid" | "arrival_definition">, bytes: RawProducts, inflate: Inflate, prior: Partial<Record<Role, string>> = {}): Promise<Decoded> {
  const out: Decoded = { depth: null, arrival: null, velocity: null, extent: null, unavailable: { ...prior } };
  const rasters: [Role, "depth" | "arrival" | "velocity"][] = [["max_depth_cog", "depth"], ["arrival_time_cog", "arrival"], ["max_velocity_cog", "velocity"]];
  for (const [role, slot] of rasters) {
    const b = bytes[role];
    if (!b) continue;
    const g = await decodeRaster(role, b, result, inflate);
    if (typeof g === "string") out.unavailable[role] = g; else out[slot] = g;
  }
  const eb = bytes.extent_geojson;
  if (eb) {
    const g = result.derived_grid, [a, , c, , e, f] = g.transform;
    const x = decodeExtent(new TextDecoder().decode(eb), { originX: c, originY: f, pixelWidth: a, pixelHeight: -e, width: g.width, height: g.height });
    if (typeof x === "string") out.unavailable.extent_geojson = x; else out.extent = x;
  }
  return out;
}
