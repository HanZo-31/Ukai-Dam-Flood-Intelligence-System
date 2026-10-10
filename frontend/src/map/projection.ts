import { addCoordinateTransforms, addProjection, get as getProjection } from "ol/proj";
import Projection from "ol/proj/Projection";
import GeoJSON from "ol/format/GeoJSON";
import { lonLatToUtm43, utm43ToLonLat } from "../lib/utm";

export const UTM43 = "EPSG:32643";
export const UTM43_PROJ4 = "+proj=utm +zone=43 +datum=WGS84 +units=m +no_defs";

/** Register EPSG:32643 (with a built-in lon/lat transform) once. No network, no proj4 package. */
export function registerUtm43(): Projection {
  const existing = getProjection(UTM43);
  if (existing && (existing as Projection).getUnits() === "m" && (existing as Projection).getExtent()) return existing as Projection;
  const p = new Projection({ code: UTM43, units: "m", extent: [166021, 0, 833978, 9329005], worldExtent: [72, 0, 78, 84] });
  addProjection(p);
  addCoordinateTransforms("EPSG:4326", p, (c) => lonLatToUtm43(c), (c) => utm43ToLonLat(c));
  return p;
}

/** GeoJSON outlines are delivered in lon/lat; never reinterpret degrees as UTM metres. */
export function extentGeoJsonFormat(crs: string): GeoJSON {
  if (crs !== "EPSG:4326" && crs !== UTM43) throw new Error("The extent CRS is unsupported; no coordinate interpretation was guessed.");
  registerUtm43();
  return new GeoJSON({ dataProjection: crs, featureProjection: UTM43 });
}
