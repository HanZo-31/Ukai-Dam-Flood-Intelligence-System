// Arrival timeline: reveal cells whose stored arrival (minutes since simulation start) is
// <= elapsed model time. Hours -> minutes is converted in exactly one place (elapsedMinutes).
// Stored arrival values are never rescaled here; colour by arrival divides by 60 once, in scales.ts.
import { buildRamp, type RasterMode } from "./scales";

export const NODATA_LIMIT = -9000; // anything at or below this is nodata (stored value -9999)
export const MINUTES_PER_HOUR = 60;

export type TimelineColorBy = "arrival" | "depth" | "velocity";
export type CellState = "unavailable" | "unreached" | "reached";

/** The single hours -> minutes conversion. */
export function elapsedMinutes(hours: number): number {
  return hours * MINUTES_PER_HOUR;
}

/** Whole elapsed hours covered by the declared model-clock window; null if the window is unusable. */
export function timelineMaxHours(start: string | null | undefined, end: string | null | undefined): number | null {
  if (!start || !end) return null;
  const a = Date.parse(start), b = Date.parse(end);
  if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return null;
  const h = Math.floor((b - a) / 3_600_000);
  return h >= 1 ? h : null;
}

export function clampHours(h: number, max: number): number {
  if (!Number.isFinite(h)) return 0;
  return Math.min(Math.max(Math.round(h), 0), max);
}

/** unavailable = nodata / non-finite (no valid arrival); unreached = valid but later than elapsed; reached = valid and <= elapsed. */
export function cellState(arrivalMinutes: number, elapsedMin: number): CellState {
  if (!Number.isFinite(arrivalMinutes) || arrivalMinutes <= NODATA_LIMIT) return "unavailable";
  return arrivalMinutes <= elapsedMin ? "reached" : "unreached";
}

export function revealCounts(arrival: ArrayLike<number>, elapsedMin: number): { reached: number; unreached: number; unavailable: number } {
  const c = { reached: 0, unreached: 0, unavailable: 0 };
  for (let i = 0; i < arrival.length; i++) c[cellState(arrival[i], elapsedMin)]++;
  return c;
}

export const UNREACHED_RGBA = [120, 134, 150, 0.27] as const; // pale grey (alpha 0-1): valid arrival, not yet reached
export const REACHED_NO_VALUE_RGBA = [150, 150, 150, 1] as const; // reached, but the colour-by value is nodata

const RASTER_FOR: Record<TimelineColorBy, RasterMode> = { arrival: "arrival", depth: "depth", velocity: "velocity" };

/**
 * OpenLayers flat-style colour expression. Band 1 is always arrival (minutes). For depth/velocity the
 * second source is band 2 (same grid). Variable `elapsedMin` is updated without rebuilding the layer.
 */
export function buildTimelineExpression(colorBy: TimelineColorBy): unknown[] {
  const arrival: unknown[] = ["band", 1];
  const valueBand: unknown[] = colorBy === "arrival" ? arrival : ["band", 2];
  const reachedColour: unknown =
    colorBy === "arrival"
      ? buildRamp(RASTER_FOR[colorBy], arrival)
      : ["case", ["<=", valueBand, NODATA_LIMIT], [...REACHED_NO_VALUE_RGBA], buildRamp(RASTER_FOR[colorBy], valueBand)];
  return [
    "case",
    ["<=", arrival, NODATA_LIMIT], [0, 0, 0, 0],
    ["<=", arrival, ["var", "elapsedMin"]], reachedColour,
    [...UNREACHED_RGBA],
  ];
}

