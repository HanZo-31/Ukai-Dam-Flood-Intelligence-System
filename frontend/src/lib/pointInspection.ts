// Original-resolution, one-cell reads. No interpolation, simulation or whole-file fallback.
import { BaseClient, BaseResponse, fromCustomClient, type GeoTIFFImage } from "geotiff";
import { layerFor, type PrototypeLayer, type PrototypeLayers, type PrototypeDetail } from "./api";
import type { RasterMode } from "./scales";
import { NODATA_LIMIT } from "./timeline";

export type MapPoint = [number, number];
export interface PointGrid { width: number; height: number; originX: number; originY: number; pixelWidth: number; pixelHeight: number; crs: string }
export interface PointValue { kind: "value" | "nodata" | "outside" | "unavailable" | "error"; value: number | null; reason?: string; grid?: PointGrid; row?: number; col?: number }
export type PointValues = Record<RasterMode, PointValue>;
export const POINT_FIELDS = [
  { key: "depth", role: "max_depth_cog", label: "Maximum depth", unit: "m" },
  { key: "arrival", role: "arrival_time_cog", label: "Arrival since simulation start", unit: "min" },
  { key: "velocity", role: "max_velocity_cog", label: "Maximum velocity (stored)", unit: "m/s" },
] as const;
const MAX_RANGE = 1024 * 1024;
const MAX_BYTES = 4 * MAX_RANGE; // per asset/click, metadata and one compressed tile included

export function pointAssetPath(layer: PrototypeLayer): string {
  let path = layer.url;
  if (/^https?:\/\//i.test(path)) { const u = new URL(path); path = u.pathname + u.search; }
  const expected = `/api/v1/prototypes/scenarios/`;
  if (!path.startsWith(expected) || !/^\/api\/v1\/prototypes\/scenarios\/[a-zA-Z0-9_-]+\/assets\/(max_depth_cog|arrival_time_cog|max_velocity_cog)$/.test(path)
      || !path.endsWith(`/assets/${layer.asset_type}`)) throw new Error("Unsupported asset path; only local stored-raster API reads are allowed.");
  return path;
}

/** Reject full-file responses, redirects, oversized/misaligned ranges and truncated bodies. */
export async function pointRange(url: string, options: RequestInit, f: typeof fetch): Promise<{ data: ArrayBuffer; response: Response }> {
  const match = /^bytes=(\d+)-(\d+)$/.exec(new Headers(options.headers).get("Range") ?? "");
  if (!match) throw new Error("A single bounded byte range is required.");
  const start = Number(match[1]), end = Number(match[2]);
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || end < start || end - start + 1 > MAX_RANGE)
    throw new Error("Raster range exceeds the point-read limit.");
  const response = await f(url, { ...options, credentials: "same-origin", redirect: "error" });
  const reject = async (message: string): Promise<never> => { await response.body?.cancel().catch(() => {}); throw new Error(message); };
  if (response.status !== 206) return reject(`Point read requires HTTP ranges (received ${response.status}); whole-file fallback is disabled.`);
  const range = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(response.headers.get("Content-Range") ?? "");
  if (!range || Number(range[1]) !== start || Number(range[2]) > end || Number(range[2]) < start || Number(range[3]) <= Number(range[2]))
    return reject("Invalid raster Content-Range.");
  const expected = Number(range[2]) - start + 1;
  const declared = response.headers.get("Content-Length");
  if (declared !== null && Number(declared) !== expected) return reject("Raster range length differs from its header.");
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Raster range has no readable body.");
  const chunks: Uint8Array[] = []; let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      length += value.byteLength;
      if (length > expected || length > MAX_RANGE) { await reader.cancel(); throw new Error("Raster range body exceeded its limit."); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  if (length !== expected) throw new Error("Raster range was truncated.");
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return { data: bytes.buffer, response };
}

class RangeResponse extends BaseResponse {
  constructor(private readonly result: { data: ArrayBuffer; response: Response }) { super(); }
  get ok() { return true; }
  get status() { return 206; }
  getHeader(name: string) { return this.result.response.headers.get(name) ?? undefined; }
  async getData() { return this.result.data; }
}
class RangeClient extends BaseClient {
  private used = 0;
  constructor(url: string, private readonly f: typeof fetch, private readonly signal: AbortSignal) { super(url); }
  async request(options: RequestInit = {}): Promise<BaseResponse> {
    const range = /^bytes=(\d+)-(\d+)$/.exec(new Headers(options.headers).get("Range") ?? "");
    if (!range) throw new Error("Missing raster byte range.");
    this.used += Number(range[2]) - Number(range[1]) + 1;
    if (this.used > MAX_BYTES) throw new Error("Point-read byte budget exceeded.");
    return new RangeResponse(await pointRange(this.url, { ...options, signal: this.signal }, this.f));
  }
}

export function pointGrid(image: GeoTIFFImage, layer: PrototypeLayer): PointGrid {
  const directory = image.getFileDirectory();
  const tie = directory.getValue("ModelTiepoint") as ArrayLike<number> | undefined;
  const origin = image.getOrigin(), res = image.getResolution();
  if (layer.format !== "cog" || layer.crs !== "EPSG:32643" || image.getGeoKeys()?.ProjectedCSTypeGeoKey !== 32643 || !image.pixelIsArea())
    throw new Error("Unsupported raster CRS or pixel interpretation; coordinates were not guessed.");
  if (directory.hasTag("ModelTransformation") || !tie || tie.length !== 6 || tie[0] !== 0 || tie[1] !== 0
      || ![origin[0], origin[1], res[0], res[1]].every(Number.isFinite) || res[0] <= 0 || res[1] >= 0)
    throw new Error("Unsupported raster grid; no rotation, resampling or origin adjustment is guessed.");
  if (image.getSamplesPerPixel() !== 1 || image.getBitsPerSample() !== 32 || image.getSampleFormat() !== 3
      || image.getTileWidth() * image.getTileHeight() * 4 > MAX_RANGE || image.getGDALNoData() !== layer.nodata || layer.nodata !== -9999)
    throw new Error("Unsupported band, tile size or nodata metadata.");
  const width = image.getWidth(), height = image.getHeight();
  if (![width, height].every(v => Number.isSafeInteger(v) && v > 0 && v <= 100000)) throw new Error("Invalid raster dimensions.");
  return { width, height, originX: origin[0], originY: origin[1], pixelWidth: res[0], pixelHeight: -res[1], crs: layer.crs };
}

export function pointCell(grid: PointGrid, point: MapPoint): { row: number; col: number } | null {
  if (!point.every(Number.isFinite)) return null;
  const col = Math.floor((point[0] - grid.originX) / grid.pixelWidth);
  const row = Math.floor((grid.originY - point[1]) / grid.pixelHeight);
  return col >= 0 && row >= 0 && col < grid.width && row < grid.height ? { row, col } : null;
}
export function pointValue(value: number): PointValue {
  if (!Number.isFinite(value) || value <= NODATA_LIMIT) return { kind: "nodata", value: null, reason: "No data in this raster cell." };
  if (value < 0) return { kind: "unavailable", value: null, reason: "Invalid negative metric value; not treated as zero." };
  return { kind: "value", value };
}

export async function samplePointImage(image: GeoTIFFImage, layer: PrototypeLayer, point: MapPoint, signal?: AbortSignal): Promise<PointValue> {
  const grid = pointGrid(image, layer), cell = pointCell(grid, point);
  if (!cell) return { kind: "outside", value: null, reason: "Outside this raster's coverage; not a safety statement.", grid };
  const values = await image.readRasters({ window: [cell.col, cell.row, cell.col + 1, cell.row + 1], samples: [0], interleave: true, signal });
  if (values.length !== 1) throw new Error("Unexpected point-read result size.");
  return { ...pointValue(values[0]), grid, ...cell };
}

export async function readPoint(layers: PrototypeLayers, point: MapPoint, signal?: AbortSignal, f: typeof fetch = fetch): Promise<PointValues> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (signal?.aborted) throw new DOMException("Point read cancelled", "AbortError");
  signal?.addEventListener("abort", cancel, { once: true });
  const timer = setTimeout(cancel, 15000);
  try {
    const fields = await Promise.all(POINT_FIELDS.map(async field => {
      const layer = layerFor(layers, field.role);
      if (!layer) return [field.key, { kind: "unavailable", value: null, reason: "This raster is not available." }] as const;
      try {
        if (layer.unit !== field.unit) throw new Error(`Expected ${field.unit}; no unit conversion was guessed.`);
        const tiff = await fromCustomClient(new RangeClient(pointAssetPath(layer), f, controller.signal),
          { allowFullFile: false, blockSize: 65536, cacheSize: 8, maxRanges: 0 }, controller.signal);
        const image = await tiff.getImage(0); // first image is the original resolution, never an overview
        return [field.key, await samplePointImage(image, layer, point, controller.signal)] as const;
      } catch (error) {
        if (signal?.aborted) throw new DOMException("Point read cancelled", "AbortError");
        return [field.key, { kind: "error", value: null, reason: controller.signal.aborted ? "Point read timed out. Retry when the local API is available." : error instanceof Error ? error.message : "Raster read failed." }] as const;
      }
    }));
    return Object.fromEntries(fields) as PointValues;
  } finally { clearTimeout(timer); signal?.removeEventListener("abort", cancel); }
}

export function pointDifference(a: PointValue, b: PointValue): { value: number | null; reason?: string } {
  if (a.kind !== "value" || b.kind !== "value" || a.value === null || b.value === null) return { value: null, reason: "Both cells need valid data; unknown is not zero." };
  const x = a.grid, y = b.grid;
  if (!x || !y || x.crs !== y.crs || x.width !== y.width || x.height !== y.height
      || !["originX", "originY", "pixelWidth", "pixelHeight"].every(k => Math.abs(x[k as keyof PointGrid] as number - (y[k as keyof PointGrid] as number)) <= 1e-6)
      || a.row !== b.row || a.col !== b.col) return { value: null, reason: "Different grids/cells: no point difference or resampling was guessed." };
  return { value: b.value - a.value };
}
export function arrivalPointCompatible(a: PrototypeDetail, b: PrototypeDetail): boolean {
  return [a, b].every(s => s.arrival?.unit === "min" && s.arrival.origin === "simulation_start"
    && s.arrival.reference_timestamp === s.coverage_start && Number.isFinite(s.arrival.threshold_m)
    && Number.isFinite(s.arrival.temporal_resolution_minutes) && s.arrival.temporal_resolution_minutes > 0)
    && a.arrival.threshold_m === b.arrival.threshold_m && a.arrival.temporal_resolution_minutes === b.arrival.temporal_resolution_minutes;
}
