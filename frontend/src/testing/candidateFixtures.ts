// TEST FIXTURES ONLY. Nothing in the application imports this file; it is never part of the production build.
// Fixture results are not outputs of the real candidate service and must never be presented as such.
import { buildRequest, CANDIDATE_CONTRACT_VERSION, INPUT_FAMILY, REFERENCE_PREFIX, type CandidateRequest, type CandidateResult } from "../lib/candidate";

export const FIXTURE_NOTICE = "FIXTURE — not a real candidate-service result";
// scenario IDs as published by the reference API / candidate-examples.json
export const KNOWN_IDS = ["ukai-hyp-h01-release15000-combined-v1", "ukai-hyp-h02-release20000-hr-int-v1", "ukai-hyp-h03-release30000-combined-v1", "ukai-2006-historical-combined-v1"];
export const SOURCE_FOR_PEAK: Record<number, string> = { 15000: KNOWN_IDS[0], 20000: KNOWN_IDS[1], 30000: KNOWN_IDS[2] };

export const capabilitiesShapeA = {
  schema_version: "1.0.0",
  modes: [{ mode: "stored_reference", available: true }, { mode: "experimental_ml", available: false, reason: "Acceptance gate closed: only one intermediate holdout exists." }],
  available_reference_peaks_m3s: [30000, 15000, 20000],
  validation_status: "uncalibrated",
};
export const capabilitiesShapeB = { modes: { stored_reference: { enabled: true }, experimental_ml: { enabled: false, unavailable_reason: "No accepted surrogate." } }, stored_peaks_m3s: [15000, 20000, 30000] };
export const capabilitiesShapeC = { supported_modes: ["stored_reference"], model_unavailable_reason: "Experimental ML is disabled by the acceptance gate." };

export function fixtureResult(req: CandidateRequest, over: Partial<CandidateResult> = {}): CandidateResult {
  const peaks = [15000, 20000, 30000];
  const actual = req.allow_nearest_stored ? peaks.reduce((b, p) => (Math.abs(p - req.peak_release_m3s) < Math.abs(b - req.peak_release_m3s) ? p : b)) : req.peak_release_m3s;
  const src = SOURCE_FOR_PEAK[actual] ?? KNOWN_IDS[1];
  return {
    schema_version: CANDIDATE_CONTRACT_VERSION, job_id: `job-${req.request_id}`, request_id: req.request_id, status: "completed", mode: req.mode, input_family: INPUT_FAMILY,
    requested_peak_release_m3s: req.peak_release_m3s, actual_peak_release_m3s: actual, cache_hit: false, computed: false, engine: "HEC-RAS stored reference",
    scientifically_validated: false, calibration_status: "uncalibrated", warnings: [FIXTURE_NOTICE], completed_at: "2026-01-01T00:00:00Z", elapsed_wall_seconds: 0.012, timing_scope: "FIXTURE timing scope", source_scenario_id: src, source_run_id: `run-${src}`,
    reference_resources: {
      detail: `${REFERENCE_PREFIX}${src}`, layers: `${REFERENCE_PREFIX}${src}/layers`, impact: `${REFERENCE_PREFIX}${src}/impact`,
      assumptions: `${REFERENCE_PREFIX}${src}/assumptions`, quality_report: `${REFERENCE_PREFIX}${src}/quality-report`,
    },
    ...over,
  };
}
export const req20k = (id = "demo-request-001", nearest = false, peak = 20000): CandidateRequest => buildRequest(id, peak, nearest);

export type Handler = (url: string, init?: RequestInit) => Response | Promise<Response> | "throw";
/** A fetch stand-in that records calls. Unknown routes answer 404 with a non-JSON body (like a proxy with no route). */
export function fakeFetch(handler: Handler): { f: typeof fetch; calls: { url: string; init?: RequestInit }[] } {
  const calls: { url: string; init?: RequestInit }[] = [];
  const f = (async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    const r = await handler(url, init);
    if (r === "throw") throw new TypeError("network down");
    return r;
  }) as unknown as typeof fetch;
  return { f, calls };
}
export const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
