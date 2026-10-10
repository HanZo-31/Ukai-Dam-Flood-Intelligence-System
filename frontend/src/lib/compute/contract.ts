// Computed-candidate contract 2.0.0 (nested prefix /api/v1/candidates/compute-v2): types and STRICT validators.
// This is the only module that knows the v2 wire shapes. The v1 stored-reference adapter (lib/candidate.ts) is not touched
// and is never used for v2 traffic. Every validator returns a list of problems; an empty list means "acceptable".
// Nothing here fabricates values: unknown or malformed input is rejected, never repaired.
export const COMPUTE_SCHEMA_VERSION = "2.0.0";
export const COMPUTE_PREFIX = "/api/v1/candidates/compute-v2";
export const COMPUTE_INPUT_FAMILY = "ukai-hyp-fixed-shape-v1";
export const COMPUTE_PEAK_MIN = 15000;
export const COMPUTE_PEAK_MAX = 30000;
export const COMPUTE_ENGINE = "experimental_fast_solver";
export const TIMING_SCOPE = "request_to_checked_asset_availability_not_browser_ready";
export const ARRIVAL_TRANSFORM = "ceil(native_seconds/3600)*60";
export const NODATA = -9999;
export const ID_SOURCE = "^[a-z0-9][a-z0-9_-]{2,99}$";
const ID_RE = new RegExp(ID_SOURCE);
const SHA_RE = /^sha256:[a-f0-9]{64}$/;
export const isId = (v: unknown): v is string => typeof v === "string" && ID_RE.test(v);
export const isSha = (v: unknown): v is string => typeof v === "string" && SHA_RE.test(v);

export type Role = "max_depth_cog" | "arrival_time_cog" | "max_velocity_cog" | "extent_geojson";
export const ROLES: readonly Role[] = ["max_depth_cog", "arrival_time_cog", "max_velocity_cog", "extent_geojson"];
export const REQUIRED_ROLES: readonly Role[] = ["max_depth_cog", "extent_geojson"];
export const ROLE_UNIT: Record<Role, string> = { max_depth_cog: "m", arrival_time_cog: "min", max_velocity_cog: "m/s", extent_geojson: "geographic_coordinates" };
export const ROLE_LABEL_V2: Record<Role, string> = {
  max_depth_cog: "Maximum depth (m)", arrival_time_cog: "Arrival time (min, hourly resolution)", max_velocity_cog: "Maximum velocity (m/s)", extent_geojson: "Wet extent outline (lon/lat)",
};
export type JobStatus = "queued" | "running" | "completed" | "failed";
export const JOB_STATUSES: readonly JobStatus[] = ["queued", "running", "completed", "failed"];

export interface CapabilitiesV2 {
  schema_version: string; input_family: string; configuration_id: string | null; configuration_checksum: string | null; enabled: boolean; reason: string | null;
  peak_range_m3s: [number, number]; available_roles: Role[]; scientifically_validated: false;
}
export interface RequestV2 {
  schema_version: "2.0.0"; input_family: typeof COMPUTE_INPUT_FAMILY; configuration_id: string; configuration_checksum: string; request_id: string; peak_release_m3s: number;
}
export interface ErrorV2 { code: string; message: string }
export interface JobV2 {
  schema_version: string; input_family: string; configuration_id: string; configuration_checksum: string; request_id: string; job_id: string;
  requested_peak_release_m3s: number; status: JobStatus; created_at: string; updated_at: string; elapsed_wall_seconds: number; cache_hit: boolean;
  result_url: string | null; error: ErrorV2 | null;
}
export interface AssetV2 { url: string; sha256: string; bytes: number; unit: string }
export interface ArrivalDefinitionV2 {
  threshold_m: number; origin: string; native_unit: string; comparison_transform: string; definition_compatible: boolean; unavailable_reason: string | null;
}
export interface DerivedGridV2 {
  crs: string; width: number; height: number; transform: number[]; nodata: number; mapping: string; target_reference_scenario_id: string;
}
export interface TimingsV2 {
  prepare_seconds: number; solver_seconds: number; package_check_seconds: number; availability_seconds: number; request_to_assets_seconds: number; scope: string;
}
export interface ResultV2 {
  schema_version: string; input_family: string; configuration_id: string; configuration_checksum: string; job_id: string; request_id: string;
  scenario_id: string; run_id: string; requested_peak_release_m3s: number; actual_peak_release_m3s: number; engine: string; engine_version: string;
  computed: true; cache_hit: boolean; scientifically_validated: false; calibration_status: string; input_checksums: Record<string, string>;
  warnings: string[]; limitations: string[]; timings: TimingsV2; numerical_diagnostics_checksum: string; native_results_checksum: string;
  arrival_definition: ArrivalDefinitionV2 | null; velocity_definition: string | null; derived_grid: DerivedGridV2;
  assets: Record<Role, AssetV2 | null>; unavailable_reasons: Record<Role, string | null>;
}

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const fin = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const nonEmpty = (v: unknown): v is string => typeof v === "string" && v.trim().length > 0;
/** RFC 3339 date-time with an explicit offset (Z or ±hh:mm): no timezone is ever assumed. */
const RFC3339 = /^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$/;
export const isDateTime = (v: unknown): v is string => typeof v === "string" && RFC3339.test(v) && Number.isFinite(Date.parse(v));

function noExtraKeys(o: Record<string, unknown>, allowed: readonly string[], what: string, p: string[]): void {
  const extra = Object.keys(o).filter((k) => !allowed.includes(k));
  if (extra.length) p.push(`${what} has unknown field(s): ${extra.slice(0, 5).join(", ")}.`);
  const missing = allowed.filter((k) => !(k in o));
  if (missing.length) p.push(`${what} is missing: ${missing.slice(0, 8).join(", ")}.`);
}

/** URL of one job's own sub-resource. Exact string; no query, fragment, traversal, encoding tricks or other host. */
export const jobPath = (jobId: string): string => `${COMPUTE_PREFIX}/jobs/${jobId}`;
export const resultPath = (jobId: string): string => `${jobPath(jobId)}/result`;
export const assetPath = (jobId: string, role: Role): string => `${jobPath(jobId)}/assets/${role}`;

// ---- capabilities --------------------------------------------------------------------------------------------------
const CAP_KEYS = ["schema_version", "input_family", "configuration_id", "configuration_checksum", "enabled", "reason", "peak_range_m3s", "available_roles", "scientifically_validated"] as const;
export type CapabilitiesParse = { ok: true; caps: CapabilitiesV2 } | { ok: false; problems: string[] };
/** A capability document is authoritative only when it is entirely well-formed. Anything else disables new computation (and nothing else). */
export function parseCapabilitiesV2(raw: unknown): CapabilitiesParse {
  if (!isObj(raw)) return { ok: false, problems: ["The capability response is not an object."] };
  const p: string[] = [];
  noExtraKeys(raw, CAP_KEYS, "The capability response", p);
  if (raw.schema_version !== COMPUTE_SCHEMA_VERSION) p.push(`Unsupported contract version ${JSON.stringify(raw.schema_version)} (this interface supports ${COMPUTE_SCHEMA_VERSION}).`);
  if (raw.input_family !== COMPUTE_INPUT_FAMILY) p.push("The input family is not the supported fixed-shape family.");
  if (typeof raw.enabled !== "boolean") p.push("The enabled flag must be true or false.");
  const idOk = raw.configuration_id === null || isId(raw.configuration_id), shaOk = raw.configuration_checksum === null || isSha(raw.configuration_checksum);
  if (!idOk) p.push("The configuration ID is not a valid identifier.");
  if (!shaOk) p.push("The configuration checksum is not a valid sha256 value.");
  const r = raw.peak_range_m3s;
  if (!Array.isArray(r) || r.length !== 2 || r[0] !== COMPUTE_PEAK_MIN || r[1] !== COMPUTE_PEAK_MAX) p.push(`The peak range must be exactly ${COMPUTE_PEAK_MIN}–${COMPUTE_PEAK_MAX} m³/s.`);
  const roles = raw.available_roles;
  if (!Array.isArray(roles) || !roles.every((x) => typeof x === "string" && (ROLES as readonly string[]).includes(x)) || new Set(roles).size !== roles.length) p.push("The list of available roles is invalid.");
  if (raw.scientifically_validated !== false) p.push("The service must declare scientifically_validated: false.");
  if (raw.reason !== null && !nonEmpty(raw.reason)) p.push("The reason must be text or null.");
  if (raw.enabled === true) {
    if (!isId(raw.configuration_id) || !isSha(raw.configuration_checksum)) p.push("An enabled service must advertise a verified configuration ID and checksum.");
    if (raw.reason !== null) p.push("An enabled service must not carry a disabling reason.");
    if (Array.isArray(roles) && !(REQUIRED_ROLES.every((x) => (roles as unknown[]).includes(x)))) p.push("An enabled service must offer the maximum-depth raster and the extent outline.");
  } else if (raw.enabled === false && !nonEmpty(raw.reason)) p.push("A disabled service must say why.");
  if (p.length) return { ok: false, problems: p };
  return { ok: true, caps: raw as unknown as CapabilitiesV2 };
}

// ---- request ------------------------------------------------------------------------------------------------------
export function validatePeak(peak: unknown): string | null {
  if (typeof peak !== "number" || !Number.isFinite(peak)) return "Enter a finite number for the peak release.";
  if (peak < COMPUTE_PEAK_MIN || peak > COMPUTE_PEAK_MAX) return `The peak release must be between ${COMPUTE_PEAK_MIN.toLocaleString("en-US")} and ${COMPUTE_PEAK_MAX.toLocaleString("en-US")} m³/s.`;
  return null;
}
let seq = 0;
export function newComputeRequestId(now: number = Date.now()): string { seq = (seq + 1) % 1_000_000; return `run2-${now.toString(36)}-${seq.toString(36)}`; }
/** Only the advertised configuration is ever sent; there is no field for nearest selection, paths, options or hydrographs. */
export function buildComputeRequest(requestId: string, peak: number, caps: Pick<CapabilitiesV2, "configuration_id" | "configuration_checksum">): RequestV2 | string {
  const bad = validatePeak(peak);
  if (bad) return bad;
  if (!isId(requestId)) return "The request ID is not a valid identifier.";
  if (!isId(caps.configuration_id) || !isSha(caps.configuration_checksum)) return "The service has not advertised a verified configuration.";
  return { schema_version: COMPUTE_SCHEMA_VERSION, input_family: COMPUTE_INPUT_FAMILY, configuration_id: caps.configuration_id, configuration_checksum: caps.configuration_checksum, request_id: requestId, peak_release_m3s: peak };
}

// ---- job ----------------------------------------------------------------------------------------------------------
const JOB_KEYS = ["schema_version", "input_family", "configuration_id", "configuration_checksum", "request_id", "job_id", "requested_peak_release_m3s", "status", "created_at", "updated_at", "elapsed_wall_seconds", "cache_hit", "result_url", "error"] as const;
export interface Expectation { request: RequestV2; jobId?: string }
export function validateJob(raw: unknown, ex: Expectation): string[] {
  if (!isObj(raw)) return ["The job response is not an object."];
  const p: string[] = [];
  noExtraKeys(raw, JOB_KEYS, "The job response", p);
  if (p.length) return p;
  if (raw.schema_version !== COMPUTE_SCHEMA_VERSION) p.push(`Unexpected contract version ${JSON.stringify(raw.schema_version)}.`);
  if (raw.input_family !== COMPUTE_INPUT_FAMILY) p.push("The job's input family differs.");
  if (raw.configuration_id !== ex.request.configuration_id) p.push("The job reports a different configuration ID than the one submitted.");
  if (raw.configuration_checksum !== ex.request.configuration_checksum) p.push("The job reports a different configuration checksum than the one submitted.");
  if (raw.request_id !== ex.request.request_id) p.push("The job belongs to a different request ID.");
  if (!isId(raw.job_id)) p.push("The job ID is not a valid identifier.");
  else if (ex.jobId !== undefined && raw.job_id !== ex.jobId) p.push("The job ID changed between responses.");
  if (raw.requested_peak_release_m3s !== ex.request.peak_release_m3s) p.push("The job's requested peak differs from what was sent.");
  if (typeof raw.status !== "string" || !(JOB_STATUSES as readonly string[]).includes(raw.status)) p.push(`Unknown job status ${JSON.stringify(raw.status)}.`);
  if (!isDateTime(raw.created_at) || !isDateTime(raw.updated_at)) p.push("Job times must be date-times with an explicit time-zone offset.");
  if (!fin(raw.elapsed_wall_seconds) || raw.elapsed_wall_seconds < 0) p.push("The job's elapsed time must be a non-negative number.");
  if (typeof raw.cache_hit !== "boolean") p.push("The cache-hit flag must be true or false.");
  const st = raw.status;
  if (st === "completed") {
    if (isId(raw.job_id) && raw.result_url !== resultPath(raw.job_id)) p.push("A completed job must point to exactly its own result.");
    if (raw.error !== null) p.push("A completed job must not carry an error.");
  } else {
    if (raw.result_url !== null) p.push("Only a completed job may carry a result URL.");
    if (st === "failed") {
      const e = raw.error;
      if (!isObj(e) || !isId(e.code) || !nonEmpty(e.message) || Object.keys(e).length !== 2) p.push("A failed job must carry a safe error with a code and a message.");
    } else if (raw.error !== null) p.push("Only a failed job may carry an error.");
  }
  return p;
}

// ---- result -------------------------------------------------------------------------------------------------------
const RESULT_KEYS = ["schema_version", "input_family", "configuration_id", "configuration_checksum", "job_id", "request_id", "scenario_id", "run_id", "requested_peak_release_m3s", "actual_peak_release_m3s",
  "engine", "engine_version", "computed", "cache_hit", "scientifically_validated", "calibration_status", "input_checksums", "warnings", "limitations", "timings", "numerical_diagnostics_checksum",
  "native_results_checksum", "arrival_definition", "velocity_definition", "derived_grid", "assets", "unavailable_reasons"] as const;
const TIMING_KEYS = ["prepare_seconds", "solver_seconds", "package_check_seconds", "availability_seconds", "request_to_assets_seconds", "scope"] as const;
const GRID_KEYS = ["crs", "width", "height", "transform", "nodata", "mapping", "target_reference_scenario_id"] as const;
const ARRIVAL_KEYS = ["threshold_m", "origin", "native_unit", "comparison_transform", "definition_compatible", "unavailable_reason"] as const;

/** Validates the checked Result against the schema AND the identities the interface itself submitted. Called before any asset is fetched. */
export function validateResult(raw: unknown, ex: Expectation & { jobId: string }): string[] {
  if (!isObj(raw)) return ["The result is not an object."];
  const p: string[] = [];
  noExtraKeys(raw, RESULT_KEYS, "The result", p);
  if (p.length) return p;
  if (raw.schema_version !== COMPUTE_SCHEMA_VERSION) p.push(`Unexpected contract version ${JSON.stringify(raw.schema_version)}.`);
  if (raw.input_family !== COMPUTE_INPUT_FAMILY) p.push("The result's input family differs.");
  if (raw.configuration_id !== ex.request.configuration_id) p.push("The result's configuration ID differs from the one submitted.");
  if (raw.configuration_checksum !== ex.request.configuration_checksum) p.push("The result's configuration checksum differs from the one submitted.");
  if (raw.job_id !== ex.jobId) p.push("The result belongs to a different job.");
  if (raw.request_id !== ex.request.request_id) p.push("The result belongs to a different request.");
  if (!isId(raw.scenario_id)) p.push("The new scenario ID is not a valid identifier.");
  if (!isId(raw.run_id)) p.push("The new run ID is not a valid identifier.");
  if (raw.requested_peak_release_m3s !== ex.request.peak_release_m3s) p.push("The result's requested peak differs from what was sent.");
  if (raw.actual_peak_release_m3s !== ex.request.peak_release_m3s) p.push("The actual peak differs from the request; a computed run must use exactly the requested peak.");
  if (raw.engine !== COMPUTE_ENGINE) p.push("The engine is not the experimental fast solver.");
  if (!nonEmpty(raw.engine_version)) p.push("The engine version is missing.");
  if (raw.computed !== true) p.push("A computed result must declare computed: true.");
  if (typeof raw.cache_hit !== "boolean") p.push("The cache-hit flag must be true or false.");
  if (raw.scientifically_validated !== false) p.push("The result must declare scientifically_validated: false.");
  if (raw.calibration_status !== "uncalibrated") p.push("The calibration status must be uncalibrated.");
  const ic = raw.input_checksums;
  if (!isObj(ic) || Object.keys(ic).length < 1 || !Object.values(ic).every(isSha)) p.push("The input checksums are missing or malformed.");
  if (!Array.isArray(raw.warnings) || !raw.warnings.every(nonEmpty)) p.push("Warnings must be a list of non-empty text.");
  if (!Array.isArray(raw.limitations) || raw.limitations.length < 1 || !raw.limitations.every(nonEmpty)) p.push("Limitations must be a non-empty list of text.");
  if (!isSha(raw.numerical_diagnostics_checksum) || !isSha(raw.native_results_checksum)) p.push("The diagnostics or native-results checksum is malformed.");
  const t = raw.timings;
  if (!isObj(t)) p.push("Timings are missing.");
  else {
    noExtraKeys(t, TIMING_KEYS, "Timings", p);
    for (const k of TIMING_KEYS) if (k !== "scope" && !(fin(t[k]) && (t[k] as number) >= 0)) p.push(`Timing “${k}” must be a non-negative number.`);
    if (t.scope !== TIMING_SCOPE) p.push("The timing scope is not the declared service-side scope.");
  }
  // arrival definition
  const ad = raw.arrival_definition;
  if (ad !== null) {
    if (!isObj(ad)) p.push("The arrival definition is malformed.");
    else {
      noExtraKeys(ad, ARRIVAL_KEYS, "The arrival definition", p);
      if (ad.threshold_m !== 0.1) p.push("The arrival threshold is not 0.1 m.");
      if (ad.origin !== "elapsed_simulation_start") p.push("The arrival origin is not the simulation start.");
      if (ad.native_unit !== "s") p.push("The native arrival unit is not seconds.");
      if (ad.comparison_transform !== ARRIVAL_TRANSFORM) p.push("The arrival comparison transform is not the documented hourly ceiling.");
      if (typeof ad.definition_compatible !== "boolean") p.push("definition_compatible must be true or false.");
      if (ad.unavailable_reason !== null && !nonEmpty(ad.unavailable_reason)) p.push("The arrival unavailable reason must be text or null.");
      if (ad.definition_compatible === false && !nonEmpty(ad.unavailable_reason)) p.push("An incompatible arrival definition must say why.");
    }
  }
  if (raw.velocity_definition !== null && !nonEmpty(raw.velocity_definition)) p.push("The velocity definition must be text or null.");
  // derived grid
  const g = raw.derived_grid;
  if (!isObj(g)) p.push("The derived grid is missing.");
  else {
    noExtraKeys(g, GRID_KEYS, "The derived grid", p);
    if (g.crs !== "EPSG:32643") p.push("The derived grid is not in EPSG:32643.");
    if (!Number.isInteger(g.width) || (g.width as number) < 1 || !Number.isInteger(g.height) || (g.height as number) < 1) p.push("The derived grid size is invalid.");
    if (!Array.isArray(g.transform) || g.transform.length !== 6 || !g.transform.every(fin)) p.push("The derived grid transform is invalid.");
    else {
      const tr = g.transform as number[];
      if (!(tr[0] > 0) || tr[1] !== 0 || tr[3] !== 0 || !(tr[4] < 0)) p.push("The derived grid transform must be north-up with positive pixel width and negative pixel height.");
    }
    if (g.nodata !== NODATA) p.push("The derived grid nodata must be -9999.");
    if (g.mapping !== "nearest_neighbour_with_validity_mask") p.push("The derived-grid mapping is not the documented nearest-neighbour mapping with a validity mask.");
    if (!isId(g.target_reference_scenario_id)) p.push("The target reference scenario ID is invalid.");
  }
  // assets and reasons
  const a = raw.assets, ur = raw.unavailable_reasons;
  if (!isObj(a)) p.push("The asset list is missing.");
  if (!isObj(ur)) p.push("The unavailable-reason list is missing.");
  if (isObj(a) && isObj(ur)) {
    noExtraKeys(a, ROLES, "The asset list", p);
    noExtraKeys(ur, ROLES, "The unavailable-reason list", p);
    for (const role of ROLES) {
      const asset = a[role], reason = ur[role];
      if (asset === null || asset === undefined) {
        if (REQUIRED_ROLES.includes(role)) p.push(`The required product “${role}” must not be missing from a completed result.`);
        if (!nonEmpty(reason)) p.push(`The unavailable product “${role}” has no stated reason.`);
        continue;
      }
      if (reason !== null) p.push(`The product “${role}” is present but also has an unavailable reason.`);
      if (!isObj(asset)) { p.push(`The asset “${role}” is malformed.`); continue; }
      noExtraKeys(asset, ["url", "sha256", "bytes", "unit"], `Asset “${role}”`, p);
      if (asset.url !== assetPath(ex.jobId, role)) p.push(`Asset “${role}” does not point to this job's own asset path.`);
      if (!isSha(asset.sha256)) p.push(`Asset “${role}” has a malformed checksum.`);
      if (!Number.isInteger(asset.bytes) || (asset.bytes as number) < 1) p.push(`Asset “${role}” has an invalid byte count.`);
      if (asset.unit !== ROLE_UNIT[role]) p.push(`Asset “${role}” declares the unit ${JSON.stringify(asset.unit)} instead of ${ROLE_UNIT[role]}.`);
    }
    if (isObj(a.max_velocity_cog) && !nonEmpty(raw.velocity_definition)) p.push("A velocity product requires a stated velocity definition.");
    if (isObj(a.arrival_time_cog) && ad === null) { /* allowed: arrival is shown, but comparison is unavailable without a definition */ }
  }
  return p;
}

/** Arrival may be compared with the reference scenarios only when the service declares a compatible definition. null = comparable. */
export function arrivalComparisonBlock(res: Pick<ResultV2, "assets" | "arrival_definition">): string | null {
  if (!res.assets.arrival_time_cog) return "The new run has no arrival-time product.";
  const d = res.arrival_definition;
  if (!d) return "The service did not declare how arrival is defined, so it is not compared.";
  if (!d.definition_compatible) return d.unavailable_reason ?? "The service marked the arrival definition as not comparable.";
  return null;
}

/** Reference arrival (HEC-RAS stored scenario) must use the same threshold and resolution as the candidate's hourly-ceiling transform. null = equivalent. */
export function referenceArrivalBlock(ref: { unit?: string; origin?: string; threshold_m?: number; temporal_resolution_minutes?: number } | null | undefined): string | null {
  if (!ref) return "The reference scenario does not declare its arrival definition.";
  if (ref.unit !== "min") return "The reference arrival is not stored in minutes.";
  if (ref.threshold_m !== 0.1) return "The reference arrival threshold is not 0.1 m.";
  if (ref.temporal_resolution_minutes !== 60) return "The reference arrival is not at hourly resolution.";
  if (ref.origin !== "simulation_start") return "The reference arrival origin is not the simulation start.";
  return null;
}

/** The single native-seconds -> comparison-minutes conversion (documented hourly ceiling). Used by tests and by diagnostics; rasters arrive already converted. */
export function hourlyCeilingMinutes(nativeSeconds: number): number { return Math.ceil(nativeSeconds / 3600) * 60; }
