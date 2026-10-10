// Small typed client for the read-only prototype namespace. Same-origin relative URLs only
// (the Vite proxy forwards /api to the backend on 127.0.0.1:8765).
export type MapRole =
  | "max_depth_cog" | "max_velocity_cog" | "arrival_time_cog" | "extent_geojson"
  | "duration_cog" | "hazard_cog" | "exposure_geojson";

export interface PrototypeSummary {
  scenario_id: string;
  run_id: string;
  scenario_type: "historical_replay" | "hypothetical";
  model_version: string;
  input_dataset_version: string;
  status: string;
  validation_status: string;
  data_mode: string;
  data_kind: string;
  calibration_status: string;
  prototype: boolean;
  scientifically_validated: boolean;
  label: string;
  warnings: string[];
}
export interface Pagination { limit: number; offset: number; next_offset: number | null }
export interface PrototypeList { items: PrototypeSummary[]; pagination: Pagination }

export interface ImpactFields {
  max_depth_m: number | null;
  flooded_area_km2: number | null;
  population_exposed: number | null;
  buildings_exposed: number | null;
  roads_affected_km: number | null;
  critical_facilities_exposed: number | null;
}
export interface PrototypeImpact extends PrototypeSummary, ImpactFields { unavailable_reasons: Record<string, string> }

export interface EngineInfo {
  name: string;
  software_version: string;
  build: string | null;
  build_unavailable_reason: string | null;
  source_checksum: string | null;
  source_checksum_unavailable_reason: string | null;
}
export interface TimingInfo {
  time_step_meaning: string;
  result_output_interval_minutes: number;
  computation_step_seconds: number | null;
  forcing_interval_minutes: number | null;
  mapping_interval_minutes: number | null;
  unavailable_reasons: Record<string, string>;
  coverage_clock_kind: string;
  timezone_convention: string;
}
export interface ArrivalInfo {
  unit: string;
  origin: string;
  reference_timestamp: string;
  threshold_m: number;
  temporal_resolution_minutes: number;
  original_unit: string;
  conversion_factor: number;
}
export interface DatasetInfo {
  dataset_id: string;
  version: string;
  source_label: string;
  license: string;
  checksum: string;
  crs: string | null;
  coverage_start: string | null;
  coverage_end: string | null;
}
export interface PrototypeDetail extends PrototypeSummary {
  crs: string;
  historical_event_id: string | null;
  run_timestamp: string | null;
  run_timestamp_unknown_reason?: string | null;
  coverage_start: string;
  coverage_end: string;
  time_step_minutes: number;
  parameters: {
    reservoir_level_m: number | null; peak_inflow_m3s: number | null; peak_release_m3s: number | null;
    breach_width_m: number | null; breach_formation_minutes: number | null;
  };
  parameter_units: Record<string, string>;
  summary: ImpactFields;
  engine: EngineInfo;
  provenance: {
    source_scenario_id: string; source_manifest_checksum: string; scenario_family: string;
    derivation_processor: string; derivation_version: string;
  };
  timing: TimingInfo;
  arrival: ArrivalInfo;
  datasets: DatasetInfo[];
  limitations: string[];
  assumptions: string[];
  unavailable_reasons: Record<string, string>;
  links: { self: string; layers: string; impact: string; assumptions: string; quality_report: string };
}
export interface PrototypeLayer {
  asset_type: MapRole;
  format: "cog" | "geojson";
  crs: string;
  unit: string;
  nodata: number | null;
  checksum: string;
  coverage_start: string;
  coverage_end: string;
  url: string;
}
export interface PrototypeLayers extends PrototypeSummary { layers: PrototypeLayer[] }

export type ApiErrorKind = "network" | "http" | "parse";
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly url: string;
  constructor(kind: ApiErrorKind, url: string, message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.url = url;
  }
}

export const API_BASE = "/api/v1";

export function isAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === "AbortError";
}

function problemText(body: unknown): string | null {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    for (const k of ["detail", "title", "message"]) if (typeof b[k] === "string") return b[k] as string;
  }
  return null;
}

/** Fetch JSON. Network failure, HTTP error and bad JSON are distinct, actionable ApiErrors. */
export async function getJson<T>(path: string, signal?: AbortSignal, fetchImpl: typeof fetch = fetch): Promise<T> {
  let res: Response;
  try {
    res = await fetchImpl(path, { headers: { Accept: "application/json" }, signal });
  } catch (e) {
    if (isAbort(e)) throw e;
    throw new ApiError("network", path, "The API did not answer. Is the Ukai backend running?");
  }
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    // Vite's proxy answers 500/502/504 with an empty body when the backend is not listening.
    let detail: string | null = null;
    try { detail = problemText(JSON.parse(text)); } catch { /* not JSON */ }
    const unreachable = res.status >= 500 && !detail;
    throw new ApiError("http", path,
      unreachable ? "The API did not answer. Is the Ukai backend running?" : (detail ?? `HTTP ${res.status}`), res.status);
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError("parse", path, "The API returned a response that is not valid JSON.", res.status);
  }
}

export const listScenarios = async (signal?: AbortSignal, f?: typeof fetch): Promise<PrototypeSummary[]> => {
  const all: PrototypeSummary[] = [];
  let offset = 0;
  for (let guard = 0; guard < 20; guard++) {
    const page = await getJson<PrototypeList>(`${API_BASE}/prototypes/scenarios?limit=20&offset=${offset}`, signal, f);
    all.push(...page.items);
    if (page.pagination.next_offset == null) break;
    offset = page.pagination.next_offset;
  }
  return all;
};
const enc = encodeURIComponent;
export const getDetail = (id: string, s?: AbortSignal, f?: typeof fetch) => getJson<PrototypeDetail>(`${API_BASE}/prototypes/scenarios/${enc(id)}`, s, f);
export const getLayers = (id: string, s?: AbortSignal, f?: typeof fetch) => getJson<PrototypeLayers>(`${API_BASE}/prototypes/scenarios/${enc(id)}/layers`, s, f);
export const getImpact = (id: string, s?: AbortSignal, f?: typeof fetch) => getJson<PrototypeImpact>(`${API_BASE}/prototypes/scenarios/${enc(id)}/impact`, s, f);
export const getHealth = (s?: AbortSignal, f?: typeof fetch) => getJson<unknown>(`${API_BASE}/health`, s, f);

/** Stored JSON documents (assumptions / quality report) for the evidence preview. */
export const getStoredJson = (url: string, s?: AbortSignal, f?: typeof fetch) => getJson<Record<string, unknown>>(url, s, f);

export function layerFor(layers: PrototypeLayers | undefined, role: MapRole): PrototypeLayer | undefined {
  return layers?.layers.find((l) => l.asset_type === role);
}

export interface ScenarioRecord { summary: PrototypeSummary; detail: PrototypeDetail; impact: PrototypeImpact }

/** Load every scenario's detail and impact (small JSON). Layers and rasters are loaded on demand. */
export async function loadAllScenarios(signal?: AbortSignal, f?: typeof fetch): Promise<ScenarioRecord[]> {
  const list = await listScenarios(signal, f);
  return Promise.all(list.map(async (summary) => {
    const [detail, impact] = await Promise.all([getDetail(summary.scenario_id, signal, f), getImpact(summary.scenario_id, signal, f)]);
    return { summary, detail, impact };
  }));
}

export function describeApiError(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Unexpected error.";
}
