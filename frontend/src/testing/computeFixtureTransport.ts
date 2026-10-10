// TEST-ONLY transport for the compute-v2 contract. It answers like the future service would, but every value comes from the SYNTHETIC packet
// fixtures (hand-designed 4x4 grids). Nothing here ran a solver. It is imported by tests and by the explicit evidence harness only; the
// application never imports it (enforced by lib/compute/hygiene.v2.test.ts) and the production bundle contains none of it.
import { assetPath, COMPUTE_PREFIX, ROLES, resultPath, type Role } from "../lib/compute/contract";
import examples from "./fixtures_v2/examples.json";

export interface FixtureFiles { tif: { candidateDepth: Uint8Array; candidateArrival: Uint8Array }; extent: Uint8Array; sha256: (u: Uint8Array) => Promise<string> | string }
export type Outcome = "completed" | "failed" | "never";
export interface Behaviour {
  capabilities: "enabled" | "disabled" | "bad_version" | "malformed" | "http_error" | "outage" | "not_found" | "enabled_but_no_config";
  /** HTTP status/outcome of POST /jobs */
  submit: "accepted" | "terminal" | "busy" | "conflict" | "invalid" | "outage" | "outage_once";
  /** number of polls answered "queued" then "running" before the outcome (>= 0) */
  queuedPolls: number; runningPolls: number;
  outcome: Outcome;
  poll: "ok" | "outage" | "outage_once" | "not_found" | "wrong_job" | "wrong_config" | "wrong_request";
  result: "ok" | "malformed" | "wrong_config" | "wrong_checksum_config" | "wrong_job" | "wrong_request" | "peak_differs" | "not_computed" | "validated_true" | "foreign_asset_url" | "cross_job_asset_url" | "absolute_asset_url" | "query_asset_url" | "missing_required_asset" | "velocity_without_definition" | "http_409" | "outage" | "extra_field" | "wrong_unit";
  assets: "ok" | "bad_checksum" | "wrong_length" | "missing_arrival" | "missing_depth" | "outage" | "no_extent";
  /** extra bytes of delay are not simulated; tests control time through the injected sleep */
}
export const DEFAULT_BEHAVIOUR: Behaviour = { capabilities: "enabled", submit: "accepted", queuedPolls: 1, runningPolls: 1, outcome: "completed", poll: "ok", result: "ok", assets: "ok" };

type Ex = typeof examples;
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const json = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

export interface FixtureTransport {
  fetch: (input: string, init?: RequestInit) => Promise<Response>;
  /** every request that reached the transport, in order */
  calls: { method: string; path: string }[];
  behaviour: Behaviour;
  set: (b: Partial<Behaviour>) => void;
  jobId: (requestId: string) => string;
  /** the configuration the fixture advertises (SYNTHETIC) */
  config: { id: string; checksum: string };
}

export function createFixtureTransport(files: FixtureFiles, initial: Partial<Behaviour> = {}): FixtureTransport {
  const ex = examples as Ex;
  const behaviour: Behaviour = { ...DEFAULT_BEHAVIOUR, ...initial };
  const calls: { method: string; path: string }[] = [];
  const config = { id: ex.request.configuration_id, checksum: ex.request.configuration_checksum };
  const jobs = new Map<string, { request: Record<string, unknown>; polls: number; behaviourAtSubmit: Behaviour }>();
  let outageOnce = new Set<string>();
  const jobIdFor = (requestId: string) => `synthetic-job-${requestId}`.slice(0, 100);

  const jobBody = (jobId: string, status: string, req: Record<string, unknown>, b: Behaviour) => {
    const base: Record<string, unknown> = clone(ex.jobs[0]);
    Object.assign(base, { request_id: req.request_id, job_id: jobId, requested_peak_release_m3s: req.peak_release_m3s, configuration_id: req.configuration_id, configuration_checksum: req.configuration_checksum, status });
    base.result_url = status === "completed" ? resultPath(jobId) : null;
    base.error = status === "failed" ? { code: "interrupted", message: "Synthetic interruption fixture." } : null;
    if (b.poll === "wrong_job") base.job_id = "synthetic-job-someone-else";
    if (b.poll === "wrong_config") base.configuration_id = "synthetic-config-other";
    if (b.poll === "wrong_request") base.request_id = "someone-elses-request";
    return base;
  };

  async function resultBody(jobId: string, req: Record<string, unknown>, b: Behaviour): Promise<unknown> {
    const r: Record<string, unknown> = clone(ex.result);
    r.job_id = jobId; r.request_id = req.request_id; r.requested_peak_release_m3s = req.peak_release_m3s; r.actual_peak_release_m3s = req.peak_release_m3s;
    r.configuration_id = req.configuration_id; r.configuration_checksum = req.configuration_checksum;
    r.scenario_id = `synthetic-scenario-${jobId}`.slice(0, 100); r.run_id = `synthetic-run-${jobId}`.slice(0, 100);
    const assets = r.assets as Record<Role, Record<string, unknown> | null>;
    const bytesOf: Record<string, Uint8Array> = { max_depth_cog: files.tif.candidateDepth, arrival_time_cog: files.tif.candidateArrival, extent_geojson: files.extent };
    for (const role of ["max_depth_cog", "arrival_time_cog", "extent_geojson"] as Role[]) {
      assets[role] = { url: assetPath(jobId, role), sha256: await files.sha256(bytesOf[role]), bytes: bytesOf[role].byteLength, unit: (assets[role] as Record<string, unknown>).unit };
    }
    switch (b.result) {
      case "malformed": return { nonsense: true };
      case "wrong_config": r.configuration_id = "synthetic-config-other"; break;
      case "wrong_checksum_config": r.configuration_checksum = "sha256:" + "0".repeat(64); break;
      case "wrong_job": r.job_id = "synthetic-job-someone-else"; break;
      case "wrong_request": r.request_id = "someone-elses-request"; break;
      case "peak_differs": r.actual_peak_release_m3s = 20000; break;
      case "not_computed": r.computed = false; break;
      case "validated_true": r.scientifically_validated = true; break;
      case "foreign_asset_url": (assets.max_depth_cog as Record<string, unknown>).url = "https://example.invalid/depth.tif"; break;
      case "cross_job_asset_url": (assets.max_depth_cog as Record<string, unknown>).url = assetPath("synthetic-job-other", "max_depth_cog"); break;
      case "absolute_asset_url": (assets.max_depth_cog as Record<string, unknown>).url = `http://127.0.0.1:9${assetPath(jobId, "max_depth_cog")}`; break;
      case "query_asset_url": (assets.max_depth_cog as Record<string, unknown>).url = `${assetPath(jobId, "max_depth_cog")}?x=1`; break;
      case "missing_required_asset": assets.max_depth_cog = null; (r.unavailable_reasons as Record<string, unknown>).max_depth_cog = "Fixture says missing."; break;
      case "velocity_without_definition": assets.max_velocity_cog = { url: assetPath(jobId, "max_velocity_cog"), sha256: "sha256:" + "1".repeat(64), bytes: 10, unit: "m/s" }; (r.unavailable_reasons as Record<string, unknown>).max_velocity_cog = null; break;
      case "extra_field": r.surprise = 1; break;
      case "wrong_unit": (assets.max_depth_cog as Record<string, unknown>).unit = "ft"; break;
      default: break;
    }
    return r;
  }

  const route = async (input: string, init?: RequestInit): Promise<Response> => {
    const method = (init?.method ?? "GET").toUpperCase();
    const url = new URL(input, "http://127.0.0.1");
    const path = url.pathname;
    calls.push({ method, path: path + url.search });
    const b = behaviour;
    if (!path.startsWith(COMPUTE_PREFIX)) return json({ detail: "not found" }, 404);
    const rest = path.slice(COMPUTE_PREFIX.length);

    if (rest === "/capabilities" && method === "GET") {
      switch (b.capabilities) {
        case "outage": throw new TypeError("fetch failed");
        case "not_found": return json({ detail: "Not Found" }, 404);
        case "http_error": return new Response("Bad gateway", { status: 502 });
        case "malformed": return json({ enabled: "yes" });
        case "bad_version": return json({ ...clone(ex.capabilities_enabled), schema_version: "3.0.0" });
        case "disabled": return json(clone(ex.capabilities_disabled));
        case "enabled_but_no_config": return json({ ...clone(ex.capabilities_enabled), configuration_id: null, configuration_checksum: null });
        default: return json(clone(ex.capabilities_enabled));
      }
    }
    if (rest === "/jobs" && method === "POST") {
      const req = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
      const jobId = jobIdFor(String(req.request_id));
      if (b.submit === "outage") throw new TypeError("fetch failed");
      if (b.submit === "outage_once" && !outageOnce.has(String(req.request_id))) { outageOnce.add(String(req.request_id)); throw new TypeError("fetch failed"); }
      if (b.submit === "busy") return json({ detail: { code: "compute_busy", message: "Another job is active." } }, 409);
      if (b.submit === "conflict") return json({ detail: { code: "request_conflict", message: "Different payload." } }, 409);
      if (b.submit === "invalid") return json({ detail: [{ loc: ["body", "peak_release_m3s"], msg: "out of range", type: "value_error" }] }, 422);
      const allowed = ["schema_version", "input_family", "configuration_id", "configuration_checksum", "request_id", "peak_release_m3s"];
      if (Object.keys(req).some((k) => !allowed.includes(k))) return json({ detail: "extra fields" }, 422);
      jobs.set(jobId, { request: req, polls: 0, behaviourAtSubmit: { ...b } });
      if (b.submit === "terminal") return json(jobBody(jobId, b.outcome === "failed" ? "failed" : "completed", req, b), 200);
      return json(jobBody(jobId, "queued", req, b), 202);
    }
    const jm = /^\/jobs\/([^/]+)(\/result|\/assets\/([a-z_]+))?$/.exec(rest);
    if (jm) {
      const jobId = jm[1];
      const job = jobs.get(jobId);
      if (!job) return json({ detail: { code: "job_not_found", message: "unknown" } }, 404);
      const jb = behaviour;
      if (!jm[2] && method === "GET") {
        if (jb.poll === "outage") throw new TypeError("fetch failed");
        if (jb.poll === "outage_once" && !outageOnce.has(jobId + ":" + job.polls)) { outageOnce.add(jobId + ":" + job.polls); throw new TypeError("fetch failed"); }
        if (jb.poll === "not_found") return json({ detail: "Not Found" }, 404);
        job.polls++;
        const n = job.polls;
        let status: string;
        if (jb.outcome === "never") status = n <= jb.queuedPolls ? "queued" : "running";
        else if (n <= jb.queuedPolls) status = "queued";
        else if (n <= jb.queuedPolls + jb.runningPolls) status = "running";
        else status = jb.outcome === "failed" ? "failed" : "completed";
        return json(jobBody(jobId, status, job.request, jb));
      }
      if (jm[2] === "/result" && method === "GET") {
        if (jb.result === "outage") throw new TypeError("fetch failed");
        if (jb.result === "http_409") return json({ detail: { code: "result_not_ready", message: "not ready" } }, 409);
        return json(await resultBody(jobId, job.request, jb));
      }
      if (jm[2]?.startsWith("/assets/") && method === "GET") {
        const role = jm[3] as Role;
        if (!(ROLES as readonly string[]).includes(role)) return json({ detail: "unknown role" }, 404);
        if (jb.assets === "outage") throw new TypeError("fetch failed");
        if (role === "arrival_time_cog" && jb.assets === "missing_arrival") return json({ detail: { code: "asset_missing", message: "gone" } }, 404);
        if (role === "max_depth_cog" && jb.assets === "missing_depth") return json({ detail: { code: "asset_missing", message: "gone" } }, 404);
        if (role === "extent_geojson" && jb.assets === "no_extent") return json({ detail: { code: "asset_missing", message: "gone" } }, 404);
        const data = role === "max_depth_cog" ? files.tif.candidateDepth : role === "arrival_time_cog" ? files.tif.candidateArrival : role === "extent_geojson" ? files.extent : null;
        if (!data) return json({ detail: "not offered" }, 404);
        let out = data;
        if (jb.assets === "bad_checksum" && role === "max_depth_cog") { out = new Uint8Array(data); out[out.length - 1] ^= 0xff; }
        if (jb.assets === "wrong_length" && role === "max_depth_cog") out = data.subarray(0, data.length - 1);
        return new Response(out as BodyInit, { status: 200, headers: { "Content-Type": role === "extent_geojson" ? "application/geo+json" : "image/tiff", "Content-Length": String(out.length) } });
      }
    }
    return json({ detail: "Not Found" }, 404);
  };

  return {
    fetch: route, calls, behaviour,
    set: (b) => { Object.assign(behaviour, b); outageOnce = new Set(); },
    jobId: jobIdFor, config,
  };
}
