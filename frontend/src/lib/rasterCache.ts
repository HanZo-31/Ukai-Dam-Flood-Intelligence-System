// Loads the stored depth + arrival rasters of a scenario for the browser-side comparison.
// Rasters are read through the same reference API paths the map uses (never directly from disk) and cached by URL.
import { layerFor, type PrototypeLayers } from "./api";
import { sameOriginPath } from "./assets";
import type { Grid } from "./compare";
import { browserInflate, readFloat32Tiff, type Inflate, type Raster } from "./tiff";

const cache = new Map<string, Promise<Raster>>();
export const clearRasterCache = (): void => cache.clear();

async function fetchRaster(url: string, f: typeof fetch, inflate: Inflate): Promise<Raster> {
  let res: Response;
  try { res = await f(url); } catch { throw new Error("The raster could not be downloaded. Is the Ukai backend running?"); }
  if (!res.ok) throw new Error(`The raster request failed (HTTP ${res.status}).`);
  return readFloat32Tiff(await res.arrayBuffer(), inflate);
}

/** Cached per URL. A failed load is not cached, so a retry fetches again. Callers ignore results of stale requests. */
export function loadRaster(url: string, f: typeof fetch = fetch, inflate: Inflate = browserInflate): Promise<Raster> {
  const key = sameOriginPath(url);
  let p = cache.get(key);
  if (!p) {
    p = fetchRaster(key, f, inflate);
    cache.set(key, p);
    p.catch(() => { if (cache.get(key) === p) cache.delete(key); });
  }
  return p;
}

/** Depth (maximum depth, m) and arrival (minutes) of one scenario. Rejects with a readable reason when unavailable. */
export async function loadGrid(layers: PrototypeLayers, f: typeof fetch = fetch, inflate: Inflate = browserInflate): Promise<Grid> {
  const d = layerFor(layers, "max_depth_cog"), a = layerFor(layers, "arrival_time_cog");
  if (!d) throw new Error("The maximum-depth raster is not available for this scenario.");
  if (!a) throw new Error("The arrival-time raster is not available for this scenario.");
  if (inflate === browserInflate && typeof DecompressionStream === "undefined") throw new Error("This browser cannot decompress the rasters needed for comparison.");
  const [dr, ar] = await Promise.all([loadRaster(d.url, f, inflate), loadRaster(a.url, f, inflate)]);
  if (dr.width !== ar.width || dr.height !== ar.height || dr.originX !== ar.originX || dr.originY !== ar.originY || dr.pixelWidth !== ar.pixelWidth || dr.pixelHeight !== ar.pixelHeight)
    throw new Error("The depth and arrival rasters of this scenario are not on the same grid.");
  return { width: dr.width, height: dr.height, geo: { originX: dr.originX, originY: dr.originY, pixelWidth: dr.pixelWidth, pixelHeight: dr.pixelHeight }, depth: dr.data, arrival: ar.data };
}
