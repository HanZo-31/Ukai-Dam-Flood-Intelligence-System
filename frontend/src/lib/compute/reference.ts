// Candidate comparisons may still use depth when optional reference arrival is
// missing. Never assume units/CRS or change the existing reference-v1 loader.
import { layerFor, type PrototypeLayers } from "../api";
import { loadRaster } from "../rasterCache";
import { browserInflate, type Inflate } from "../tiff";
import { alignmentProblem, type CompareGrid } from "./candidateCompare";

export async function loadCandidateReference(layers: PrototypeLayers, fetchImpl: typeof fetch = fetch, inflate: Inflate = browserInflate): Promise<CompareGrid> {
  const depth = layerFor(layers, "max_depth_cog");
  if (!depth || depth.unit !== "m" || depth.crs !== "EPSG:32643" || depth.nodata !== -9999)
    throw new Error("The reference depth metadata must declare metres, EPSG:32643 and nodata -9999.");
  const dr = await loadRaster(depth.url, fetchImpl, inflate);
  if (dr.nodata !== -9999) throw new Error("The reference depth raster has incompatible nodata.");
  const grid: CompareGrid = { width: dr.width, height: dr.height, crs: depth.crs,
    geo: { originX: dr.originX, originY: dr.originY, pixelWidth: dr.pixelWidth, pixelHeight: dr.pixelHeight }, depth: dr.data, arrival: null };
  const arrival = layerFor(layers, "arrival_time_cog");
  if (arrival && arrival.unit === "min" && arrival.crs === depth.crs && arrival.nodata === -9999) {
    // An unavailable optional arrival must not suppress the usable depth comparison.
    try {
      const ar = await loadRaster(arrival.url, fetchImpl, inflate);
      const other = { ...grid, width: ar.width, height: ar.height,
        geo: { originX: ar.originX, originY: ar.originY, pixelWidth: ar.pixelWidth, pixelHeight: ar.pixelHeight }, depth: ar.data };
      if (ar.nodata === -9999 && !alignmentProblem(grid, other)) grid.arrival = ar.data;
    } catch { /* null preserves unavailability; no fabricated arrival values */ }
  }
  return grid;
}
