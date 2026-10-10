// Same-origin client for the compute-v2 service. Only the fixed paths from contract.ts are ever requested; the caller supplies IDs that have
// already passed the identifier pattern, never URLs. Every body is parsed as JSON and handed to the strict validators by the controller.
import { assetPath, COMPUTE_PREFIX, isId, jobPath, resultPath, ROLES, type RequestV2, type Role } from "./contract";

export type ComputeErrorKind = "unavailable" | "http" | "parse" | "integrity" | "aborted";
export class ComputeError extends Error {
  readonly kind: ComputeErrorKind; readonly status: number | null; readonly code: string | null; readonly retryable: boolean;
  constructor(kind: ComputeErrorKind, message: string, opts: { status?: number | null; code?: string | null; retryable?: boolean } = {}) {
    super(message); this.name = "ComputeError"; this.kind = kind; this.status = opts.status ?? null; this.code = opts.code ?? null; this.retryable = opts.retryable ?? false;
  }
}
export const isAbortError = (e: unknown): boolean => (e instanceof DOMException && e.name === "AbortError") || (e instanceof ComputeError && e.kind === "aborted");

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const CODE_RE = /^[A-Za-z0-9_.:-]{1,80}$/;
/** Only short machine-style codes are ever shown from an error body; free text from the server is not echoed. */
export function safeCode(body: unknown): string | null {
  if (!isObj(body)) return null;
  for (const k of ["code", "error_code", "reason_code"]) { const v = body[k]; if (typeof v === "string" && CODE_RE.test(v)) return v; }
  if (isObj(body.detail)) return safeCode(body.detail);
  if (isObj(body.error)) return safeCode(body.error);
  if (typeof body.detail === "string" && CODE_RE.test(body.detail)) return body.detail;
  return null;
}
export const STATUS_TEXT_V2: Record<number, string> = {
  400: "The request was not valid.", 404: "The job or product was not found.", 409: "The request ID was already used for different input, the service is busy with another job, or the result is not ready.",
  413: "The request was too large.", 422: "The request was not in the supported format.", 429: "The service is rate limiting requests.", 503: "The service is temporarily unavailable.",
};
const CODE_TEXT: Record<string, string> = {
  request_conflict: "This request ID was already used with different input.", result_not_ready: "The result is not ready yet.", busy: "Another computation is already running; only one can run at a time.",
  job_active: "Another computation is already running; only one can run at a time.", compute_busy: "Another computation is already running; only one can run at a time.",
  interrupted: "The computation was interrupted before it finished.",
};
export const describeCode = (code: string | null): string | null => (code ? CODE_TEXT[code] ?? null : null);

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;
export interface ComputeClientOptions { base?: string; fetchImpl?: FetchLike }

export function createComputeClient(opts: ComputeClientOptions = {}) {
  const base = (opts.base ?? "").replace(/\/+$/, "");
  const f: FetchLike = opts.fetchImpl ?? ((input, init) => fetch(input, init));

  async function raw(path: string, init: RequestInit): Promise<Response> {
    if (!path.startsWith(`${COMPUTE_PREFIX}/`)) throw new ComputeError("integrity", "Refused to request a path outside the compute-v2 service.");
    try { return await f(`${base}${path}`, { cache: "no-store", credentials: "same-origin", redirect: "error", ...init }); }
    catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") throw e;
      throw new ComputeError("unavailable", "The computation service did not answer.", { retryable: true });
    }
  }
  async function json(path: string, init: RequestInit): Promise<{ body: unknown; status: number }> {
    const res = await raw(path, { ...init, headers: { Accept: "application/json", ...(init.body ? { "Content-Type": "application/json" } : {}) } });
    const text = await res.text().catch(() => "");
    let body: unknown = null;
    try { body = JSON.parse(text); } catch { /* not JSON */ }
    if (!res.ok) {
      const code = safeCode(body);
      const jsonError = body !== null;
      // a JSON error from a running service is a definite answer; a non-JSON or 5xx-without-JSON answer means the service/proxy is effectively down (retryable)
      const retryable = !jsonError ? res.status >= 500 || res.status === 0 : res.status === 503 || res.status === 429;
      throw new ComputeError(jsonError ? "http" : "unavailable", describeCode(code) ?? STATUS_TEXT_V2[res.status] ?? `The service answered HTTP ${res.status}.`, { status: res.status, code, retryable });
    }
    if (body === null) throw new ComputeError("parse", "The computation service returned a response that is not valid JSON.", { status: res.status });
    return { body, status: res.status };
  }

  return {
    base,
    getCapabilities: async (signal?: AbortSignal): Promise<unknown> => (await json(`${COMPUTE_PREFIX}/capabilities`, { method: "GET", signal })).body,
    /** 202 (queued/running) and 200 (saved terminal state) are both valid answers; the body is validated by the caller. */
    submit: async (req: RequestV2, signal?: AbortSignal): Promise<unknown> => (await json(`${COMPUTE_PREFIX}/jobs`, { method: "POST", body: JSON.stringify(req), signal })).body,
    getJob: async (jobId: string, signal?: AbortSignal): Promise<unknown> => {
      if (!isId(jobId)) throw new ComputeError("integrity", "Refused to poll a malformed job ID.");
      return (await json(jobPath(jobId), { method: "GET", signal })).body;
    },
    /** Fetch the checked Result. Call only after the job reported completed and its result_url equals this exact path. */
    getResult: async (jobId: string, signal?: AbortSignal): Promise<unknown> => {
      if (!isId(jobId)) throw new ComputeError("integrity", "Refused to read the result of a malformed job ID.");
      return (await json(resultPath(jobId), { method: "GET", signal })).body;
    },
    /** Download one registered product (bytes). The caller verifies length and SHA-256 against the Result. */
    getAssetBytes: async (jobId: string, role: Role, signal?: AbortSignal): Promise<ArrayBuffer> => {
      if (!isId(jobId) || !(ROLES as readonly string[]).includes(role)) throw new ComputeError("integrity", "Refused to download an unregistered product.");
      const res = await raw(assetPath(jobId, role), { method: "GET", signal, headers: { Accept: "*/*" } });
      if (!res.ok) { const code = safeCode(await res.json().catch(() => null)); throw new ComputeError("http", describeCode(code) ?? (res.status === 404 ? "The product is not available from the service." : STATUS_TEXT_V2[res.status] ?? `The service answered HTTP ${res.status}.`), { status: res.status, code, retryable: res.status >= 500 }); }
      return res.arrayBuffer();
    },
  };
}
export type ComputeClient = ReturnType<typeof createComputeClient>;

/** Lower-case hex SHA-256 as "sha256:<hex>". Refuses (rather than skips) when the platform cannot compute it. */
export async function sha256Of(buf: ArrayBuffer): Promise<string> {
  const subtle = (globalThis as { crypto?: { subtle?: SubtleCrypto } }).crypto?.subtle;
  if (!subtle) throw new ComputeError("integrity", "This browser context cannot verify checksums, so the product was not used.");
  const d = new Uint8Array(await subtle.digest("SHA-256", buf));
  let s = "sha256:";
  for (const b of d) s += b.toString(16).padStart(2, "0");
  return s;
}
