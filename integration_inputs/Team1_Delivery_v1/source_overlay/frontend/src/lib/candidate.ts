// The only place that knows the Team 2 candidate-service contract (version 1.0.0). Pages use this adapter and nothing else.
// Reference resources are NOT fetched through here: their URLs belong to the reference prototype API (see lib/api.ts).
export const CANDIDATE_CONTRACT_VERSION = "1.0.0";
export const INPUT_FAMILY = "ukai-hyp-fixed-shape-v1";
export const MODE_STORED = "stored_reference";
export const MODE_ML = "experimental_ml";
export const PEAK_MIN = 15000;
export const PEAK_MAX = 30000;
export const DEFAULT_CANDIDATE_BASE = "/api/v1/candidates";
export const REFERENCE_PREFIX = "/api/v1/prototypes/scenarios/";

export interface CandidateRequest {
  schema_version: string; request_id: string; mode: string; input_family: string; peak_release_m3s: number; allow_nearest_stored: boolean;
}
export interface ReferenceResources { detail?: string; layers?: string; impact?: string; assumptions?: string; quality_report?: string; [k: string]: string | undefined }
export interface CandidateResult {
  schema_version: string; job_id: string; request_id: string; status: "queued" | "running" | "completed" | "failed"; mode: string; input_family: string;
  requested_peak_release_m3s: number; actual_peak_release_m3s: number; cache_hit: boolean; computed: boolean; engine: string;
  scientifically_validated: boolean; calibration_status: string; warnings: string[]; completed_at: string; elapsed_wall_seconds: number; timing_scope: string;
  source_scenario_id: string; source_run_id: string; reference_resources: ReferenceResources;
}
export interface ModeState { available: boolean; reason: string | null }
export interface Capabilities {
  /** false when the response could not be read as a capabilities document: nothing is then enabled */
  understood: boolean;
  storedReference: ModeState;
  experimentalMl: ModeState;
  storedPeaks: number[] | null;
  minPeak: number;
  maxPeak: number;
  validationStatus: string | null;
}

export type CandidateErrorKind = "unavailable" | "http" | "parse";
export class CandidateError extends Error {
  readonly kind: CandidateErrorKind; readonly status: number | null; readonly code: string | null;
  constructor(kind: CandidateErrorKind, message: string, status: number | null = null, code: string | null = null) { super(message); this.name = "CandidateError"; this.kind = kind; this.status = status; this.code = code; }
}

// same pattern as candidate-openapi-v1.json (CandidateRequest.request_id): must start with a letter or digit
export const ID_PATTERN_SOURCE = "^[a-z0-9][a-z0-9_-]{2,99}$";
const ID_RE = new RegExp(ID_PATTERN_SOURCE);
export const isValidId = (s: string): boolean => ID_RE.test(s);

/** Local checks that mirror the contract so obviously invalid input is never sent. The service remains the authority. */
export function validateRequestInput(peak: unknown, requestId: string): string | null {
  if (!isValidId(requestId)) return "The request ID must be 3–100 lowercase letters, digits, underscores or hyphens.";
  if (typeof peak !== "number" || !Number.isFinite(peak)) return "Enter a number for the peak release.";
  if (peak < PEAK_MIN || peak > PEAK_MAX) return `The peak release must be between ${PEAK_MIN.toLocaleString("en-US")} and ${PEAK_MAX.toLocaleString("en-US")} m³/s.`;
  return null;
}

export function buildRequest(requestId: string, peak: number, allowNearest: boolean): CandidateRequest {
  return { schema_version: CANDIDATE_CONTRACT_VERSION, request_id: requestId, mode: MODE_STORED, input_family: INPUT_FAMILY, peak_release_m3s: peak, allow_nearest_stored: allowNearest };
}

let seq = 0;
export function newRequestId(now: number = Date.now()): string { seq = (seq + 1) % 1_000_000; return `ui-${now.toString(36)}-${seq.toString(36)}`; }

/** Nearest stored peak; ties go to the lower peak (contract rule). */
export function nearestStoredPeak(requested: number, peaks: number[]): number | null {
  if (!peaks.length) return null;
  return [...peaks].sort((a, b) => a - b).reduce((best, p) => (Math.abs(p - requested) < Math.abs(best - requested) ? p : best));
}

// ---- capabilities ---------------------------------------------------------------------------------
// The real capabilities schema (candidate-openapi-v1.json, "Capabilities") uses supported_modes, stored_peaks_m3s, selection_range_m3s,
// experimental_ml_enabled and model_unavailable_reason. The reader still accepts the other plausible shapes used in tests and, when it
// cannot find a mode declared available, enables nothing. See docs/CANDIDATE_ADAPTER_NOTES.md.
const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const str = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v : null);
const REASON_KEYS = ["reason", "unavailable_reason", "reason_unavailable", "unavailability_reason", "disabled_reason", "message"];
const FLAG_KEYS = ["available", "enabled", "supported"];

function modeFrom(v: unknown): ModeState | null {
  if (typeof v === "boolean") return { available: v, reason: null };
  if (!isObj(v)) return null;
  let available: boolean | null = null;
  for (const k of FLAG_KEYS) if (typeof v[k] === "boolean") { available = v[k] as boolean; break; }
  if (available === null && typeof v.status === "string") available = ["available", "enabled", "supported"].includes(v.status);
  if (available === null) return null;
  let reason: string | null = null;
  for (const k of REASON_KEYS) { const r = str(v[k]); if (r) { reason = r; break; } }
  return { available, reason };
}

function findMode(raw: Record<string, unknown>, id: string): ModeState | null {
  const modes = raw.modes ?? raw.supported_modes ?? raw.capabilities;
  if (Array.isArray(modes)) {
    for (const m of modes) {
      if (typeof m === "string") { if (m === id) return { available: true, reason: null }; continue; }
      if (isObj(m) && (m.mode === id || m.id === id || m.name === id)) return modeFrom(m);
    }
  } else if (isObj(modes) && id in modes) {
    return modeFrom(modes[id]);
  }
  if (id in raw) return modeFrom(raw[id]);
  return null;
}

function numberList(v: unknown): number[] | null {
  if (!Array.isArray(v) || !v.length) return null;
  const out = v.map((x) => (typeof x === "number" ? x : isObj(x) && typeof x.peak_release_m3s === "number" ? x.peak_release_m3s : NaN));
  return out.every(Number.isFinite) ? [...out].sort((a, b) => a - b) : null;
}

export function parseCapabilities(raw: unknown): Capabilities {
  const none: Capabilities = { understood: false, storedReference: { available: false, reason: "The service's capability response could not be read, so nothing is enabled." },
    experimentalMl: { available: false, reason: null }, storedPeaks: null, minPeak: PEAK_MIN, maxPeak: PEAK_MAX, validationStatus: null };
  if (!isObj(raw)) return none;
  const stored = findMode(raw, MODE_STORED);
  let ml = findMode(raw, MODE_ML);
  // a separate reason field for the model, as described in the contract ("model unavailability reason")
  const mlReason = str(raw.model_unavailable_reason) ?? str(raw.model_unavailability_reason) ?? str(raw.ml_unavailable_reason) ?? str(raw.experimental_ml_reason);
  // the real service declares `experimental_ml_enabled` (contract examples); anything but an explicit true stays off
  if (!ml) ml = { available: raw.experimental_ml_enabled === true, reason: null };
  if (!ml.available && !ml.reason && mlReason) ml = { available: false, reason: mlReason };
  let peaks: number[] | null = null;
  for (const k of Object.keys(raw)) if (/peak/i.test(k) && (/available|stored|reference/i.test(k))) { peaks = numberList(raw[k]); if (peaks) break; }
  if (!peaks) peaks = numberList(raw.available_reference_peaks) ?? numberList(raw.stored_peaks_m3s);
  const family = isObj(raw.input_family) ? raw.input_family : null;
  const bounds = isObj(raw.peak_release_bounds_m3s) ? raw.peak_release_bounds_m3s : isObj(raw.bounds) ? raw.bounds : family;
  const range = Array.isArray(raw.selection_range_m3s) && raw.selection_range_m3s.length === 2 && raw.selection_range_m3s.every((x) => typeof x === "number" && Number.isFinite(x)) ? (raw.selection_range_m3s as number[]) : null;
  const lo = range ? range[0] : bounds && typeof bounds.min === "number" ? bounds.min : PEAK_MIN, hi = range ? range[1] : bounds && typeof bounds.max === "number" ? bounds.max : PEAK_MAX;
  const validation = str(raw.validation_status) ?? str(raw.calibration_status);
  if (!stored) return { ...none, experimentalMl: ml, storedPeaks: peaks, minPeak: lo, maxPeak: hi, validationStatus: validation,
    storedReference: { available: false, reason: "The service did not declare the stored_reference mode, so it is not enabled." } };
  return { understood: true, storedReference: stored, experimentalMl: ml, storedPeaks: peaks, minPeak: lo, maxPeak: hi, validationStatus: validation };
}

// ---- result validation ----------------------------------------------------------------------------
const REQUIRED = ["schema_version", "job_id", "request_id", "status", "mode", "input_family", "requested_peak_release_m3s", "actual_peak_release_m3s", "cache_hit", "computed",
  "engine", "scientifically_validated", "calibration_status", "warnings", "completed_at", "elapsed_wall_seconds", "timing_scope", "source_scenario_id", "source_run_id", "reference_resources"] as const;
export const RESOURCE_KEYS = ["detail", "layers", "impact", "assumptions", "quality_report"] as const;
const STATES = ["queued", "running", "completed", "failed"];

/** Returns the list of problems; an empty list means the result is acceptable for display. */
export function validateResult(raw: unknown, req: CandidateRequest, ctx: { knownScenarioIds: string[] | null; storedPeaks: number[] | null }): string[] {
  if (!isObj(raw)) return ["The service returned something that is not a result object."];
  const p: string[] = [];
  for (const k of REQUIRED) if (!(k in raw)) p.push(`Missing field: ${k}.`);
  if (p.length) return p;
  const r = raw as unknown as CandidateResult;
  if (r.schema_version !== CANDIDATE_CONTRACT_VERSION) p.push(`Unexpected schema version ${String(r.schema_version)} (expected ${CANDIDATE_CONTRACT_VERSION}).`);
  if (r.request_id !== req.request_id) p.push("The result belongs to a different request ID.");
  if (!STATES.includes(r.status)) p.push(`Unknown job status: ${String(r.status)}.`);
  if (r.mode !== req.mode) p.push("The result mode differs from the requested mode.");
  if (r.input_family !== req.input_family) p.push("The result input family differs from the request.");
  if (r.requested_peak_release_m3s !== req.peak_release_m3s) p.push("The result's requested peak differs from what was sent.");
  if (typeof r.actual_peak_release_m3s !== "number" || !Number.isFinite(r.actual_peak_release_m3s)) p.push("The actual returned peak is not a number.");
  else if (!req.allow_nearest_stored && r.actual_peak_release_m3s !== req.peak_release_m3s) p.push("An exact selection returned a different peak.");
  else if (req.allow_nearest_stored && ctx.storedPeaks) {
    const want = nearestStoredPeak(req.peak_release_m3s, ctx.storedPeaks);
    if (want !== null && r.actual_peak_release_m3s !== want) p.push("The returned peak is not the nearest stored peak.");
  }
  if (r.computed !== false) p.push("A stored lookup must report computed: false.");
  if (r.scientifically_validated !== false) p.push("The service reported scientific validation, which this prototype does not claim.");
  if (r.calibration_status !== "uncalibrated") p.push(`Unexpected calibration status: ${String(r.calibration_status)}.`);
  if (typeof r.engine !== "string" || !r.engine) p.push("The engine label is missing.");
  if (!Array.isArray(r.warnings)) p.push("Warnings must be a list.");
  if (typeof r.completed_at !== "string" || !r.completed_at) p.push("The completion time is missing.");
  if (typeof r.timing_scope !== "string" || !r.timing_scope) p.push("The timing scope is missing.");
  if (ctx.storedPeaks && typeof r.actual_peak_release_m3s === "number" && !ctx.storedPeaks.includes(r.actual_peak_release_m3s)) p.push("The returned peak is not one of the stored reference peaks.");
  if (typeof r.elapsed_wall_seconds !== "number" || !Number.isFinite(r.elapsed_wall_seconds) || r.elapsed_wall_seconds < 0) p.push("The lookup time is not a valid number.");
  if (r.status === "completed") {
    if (!r.source_scenario_id || !r.source_run_id) p.push("A completed result must name its source scenario and run.");
    if (ctx.knownScenarioIds && !ctx.knownScenarioIds.includes(r.source_scenario_id)) p.push("The source scenario is not one of the loaded reference scenarios.");
    if (!isObj(r.reference_resources)) p.push("Reference resources are missing.");
    else {
      for (const k of RESOURCE_KEYS) if (!(k in r.reference_resources)) p.push(`Reference resource “${k}” is missing.`);
      for (const [k, u] of Object.entries(r.reference_resources)) {
        if (typeof u !== "string" || !u.startsWith(`${REFERENCE_PREFIX}${r.source_scenario_id}`) || /^[a-z]+:\/\//i.test(u)) p.push(`Reference resource “${k}” does not point into the reference API for ${r.source_scenario_id}.`);
      }
    }
  }
  return p;
}

// ---- client ----------------------------------------------------------------------------------------
function safeCode(body: unknown): string | null {
  if (!isObj(body)) return null;
  for (const k of ["code", "reason_code", "reason", "error", "detail"]) { const v = body[k]; if (typeof v === "string" && /^[A-Za-z0-9_.:-]{1,80}$/.test(v)) return v; }
  if (isObj(body.detail)) return safeCode(body.detail);
  return null;
}
export const STATUS_TEXT: Record<number, string> = {
  400: "The selection was not valid.", 404: "The candidate service or job was not found.", 409: "That request ID was already used for different input, or the service is busy.",
  422: "The request was not in the supported format.", 503: "The service could not validate its stored reference data right now.",
};

export function createCandidateClient(opts: { base?: string; fetchImpl?: typeof fetch } = {}) {
  const base = (opts.base ?? DEFAULT_CANDIDATE_BASE).replace(/\/+$/, "");
  const f = opts.fetchImpl ?? ((...a: Parameters<typeof fetch>) => fetch(...a));
  async function call(path: string, init: RequestInit): Promise<unknown> {
    let res: Response;
    try { res = await f(`${base}${path}`, { ...init, headers: { Accept: "application/json", ...(init.body ? { "Content-Type": "application/json" } : {}) } }); }
    catch (e) { if (e instanceof DOMException && e.name === "AbortError") throw e; throw new CandidateError("unavailable", "The candidate service did not answer."); }
    const text = await res.text().catch(() => "");
    let body: unknown = null;
    try { body = JSON.parse(text); } catch { /* not JSON */ }
    if (!res.ok) {
      const code = safeCode(body);
      // a JSON error from a running service is an "http" error; a missing/non-JSON answer (or a 5xx other than 503) means it is effectively unavailable
      const reachable = body !== null && (res.status < 500 || res.status === 503);
      throw new CandidateError(reachable ? "http" : "unavailable", STATUS_TEXT[res.status] ?? `The service answered HTTP ${res.status}.`, res.status, code);
    }
    if (body === null) throw new CandidateError("parse", "The candidate service returned a response that is not valid JSON.", res.status);
    return body;
  }
  return {
    base,
    getCapabilities: async (signal?: AbortSignal): Promise<Capabilities> => parseCapabilities(await call("/capabilities", { method: "GET", signal })),
    submit: (req: CandidateRequest, signal?: AbortSignal): Promise<unknown> => call("/jobs", { method: "POST", body: JSON.stringify(req), signal }),
    getJob: (id: string, signal?: AbortSignal): Promise<unknown> => call(`/jobs/${encodeURIComponent(id)}`, { method: "GET", signal }),
  };
}
export type CandidateClient = ReturnType<typeof createCandidateClient>;
