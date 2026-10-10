import type { MapRole, PrototypeLayer } from "./api";

/** Keep downloads/map requests same-origin (through the dev proxy) even if the API returns an absolute URL. */
export function sameOriginPath(url: string): string {
  try {
    if (/^https?:\/\//i.test(url)) { const u = new URL(url); return u.pathname + u.search; }
  } catch { /* fall through */ }
  return url;
}

export const ROLE_LABEL: Record<MapRole, string> = {
  max_depth_cog: "Maximum depth (m)",
  max_velocity_cog: "Maximum velocity (m/s)",
  arrival_time_cog: "Arrival time (stored in minutes)",
  extent_geojson: "Flood extent outline",
  duration_cog: "Duration",
  hazard_cog: "Hazard",
  exposure_geojson: "Exposure",
};

export function fileHint(l: PrototypeLayer): string {
  return l.format === "cog" ? "GeoTIFF (COG)" : "GeoJSON";
}
