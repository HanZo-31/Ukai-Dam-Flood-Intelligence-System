// Display colour scales. Fixed per layer so the same colour means the same value in every
// scenario. Classes are display choices, not validated hazard categories.
export type RasterMode = "depth" | "velocity" | "arrival";
export type ViewMode = "extent" | "timeline" | RasterMode;

export interface ScaleDef {
  mode: RasterMode;
  role: "max_depth_cog" | "max_velocity_cog" | "arrival_time_cog";
  title: string;
  unit: string; // display unit
  /** raw stored value / divisor = displayed value. Arrival is stored in minutes, shown in hours. */
  divisor: number;
  stops: readonly (readonly [number, string])[]; // [display value, hex]
  note: string;
}

export const SCALES: Record<RasterMode, ScaleDef> = {
  depth: {
    mode: "depth", role: "max_depth_cog", title: "Maximum depth", unit: "m", divisor: 1,
    stops: [[0, "#d6e6fb"], [0.5, "#a9cdf6"], [2, "#6fa8ee"], [5, "#3b82e0"], [10, "#1f5cc0"], [20, "#163f8a"], [40, "#0b1f4d"]],
    note: "Fixed 0–40 m scale for every scenario. Values above 40 m would use the darkest colour.",
  },
  velocity: {
    mode: "velocity", role: "max_velocity_cog", title: "Maximum velocity", unit: "m/s", divisor: 1,
    stops: [[0, "#fff3c4"], [1, "#fdd37a"], [2, "#f7a44a"], [4, "#e4682e"], [6, "#b8332a"], [9, "#7a1a46"], [12, "#3b0f5c"]],
    note: "Fixed 0–12 m/s scale for every scenario. Values above 12 m/s would use the darkest colour.",
  },
  arrival: {
    mode: "arrival", role: "arrival_time_cog", title: "Arrival time (from simulation start)", unit: "h", divisor: 60,
    stops: [[0, "#440154"], [6, "#472d7b"], [12, "#3b528b"], [24, "#21908d"], [48, "#27ad81"], [96, "#85d54a"], [140, "#fde725"]],
    note: "Stored in minutes, shown in hours. Fixed 0–140 h scale; first depth > 0.1 m. Later values would use the lightest colour.",
  },
};

export function hexToRgb(hex: string): [number, number, number] {
  const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (!m) throw new Error(`bad colour ${hex}`);
  return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
}

/** Value shown to the user for a raw stored value (arrival: minutes -> hours; once). */
export function rawToDisplay(mode: RasterMode, raw: number): number {
  return raw / SCALES[mode].divisor;
}

/** Displayed value -> raw stored value (inverse of rawToDisplay). */
export function displayToRaw(mode: RasterMode, shown: number): number {
  return shown * SCALES[mode].divisor;
}

export const ROLE_FOR_MODE: Record<RasterMode, ScaleDef["role"]> = {
  depth: "max_depth_cog", velocity: "max_velocity_cog", arrival: "arrival_time_cog",
};

/**
 * OpenLayers flat-style colour expression. nodata (-9999 or any value below -9000) is fully
 * transparent: never drawn as zero or as safe land. Bands are read unnormalised.
 */
export function buildRamp(mode: RasterMode, raw: unknown): unknown[] {
  const s = SCALES[mode];
  const shown: unknown = s.divisor === 1 ? raw : ["/", raw, s.divisor];
  const ramp: unknown[] = ["interpolate", ["linear"], shown];
  for (const [v, hex] of s.stops) ramp.push(v, hexToRgb(hex));
  return ramp;
}

export function buildColorExpression(mode: RasterMode, nodata = -9999): unknown[] {
  const raw: unknown[] = ["band", 1];
  return ["case", ["<=", raw, nodata + 1], [0, 0, 0, 0], buildRamp(mode, raw)];
}

export function legendGradientCss(mode: RasterMode): string {
  const s = SCALES[mode];
  const lo = s.stops[0][0], hi = s.stops[s.stops.length - 1][0];
  const parts = s.stops.map(([v, c]) => `${c} ${(((v - lo) / (hi - lo)) * 100).toFixed(1)}%`);
  return `linear-gradient(90deg, ${parts.join(", ")})`;
}

export function legendTicks(mode: RasterMode): { value: number; pct: number }[] {
  const s = SCALES[mode];
  const lo = s.stops[0][0], hi = s.stops[s.stops.length - 1][0];
  const pick = mode === "arrival" ? [0, 24, 48, 96, 140] : mode === "depth" ? [0, 5, 10, 20, 40] : [0, 2, 4, 6, 9, 12];
  return pick.map((value) => ({ value, pct: ((value - lo) / (hi - lo)) * 100 }));
}
