// Framework-free state machine for one computed-candidate job at a time. React only subscribes to it (hooks/useCompute.ts).
//
// Rules implemented here (CLAUDE_ANALYSIS_FRONTEND_JOB C02/C03):
//  * The capability document is the authority. Unknown/malformed/disabled => new computation is blocked; nothing else is touched.
//  * One submission => one request ID => one job. The advertised configuration ID/checksum are sent back unchanged. No nearest lookup exists.
//  * Every response (job, result, product) is validated before use. Identity, version, configuration and URL mismatches are rejected BEFORE any
//    follow-up request or map fetch. The Result is fetched only after a validated "completed" job. Products only after a validated Result.
//  * Polling stops on: terminal state, new run, suspend() (page left), dispose(), timeout, or too many consecutive failures.
//  * Responses of superseded requests are dropped by a token check (LatestGuard) and aborted.
//  * The last fully accepted Result stays identified (and visible) while a new run loads or fails.
import { LatestGuard } from "../latest";
import type { Inflate } from "../tiff";
import { ComputeError, isAbortError, type ComputeClient } from "./client";
import {
  buildComputeRequest, newComputeRequestId, parseCapabilitiesV2, validateJob, validatePeak, validateResult,
  type CapabilitiesV2, type JobV2, type RequestV2, type ResultV2, type Role,
} from "./contract";
import { decodeProducts, type Decoded, type RawProducts } from "./decode";
import { fetchProducts, type ProductEntry } from "./products";

export type CapState =
  | { kind: "loading" }
  | { kind: "unavailable"; message: string }
  | { kind: "invalid"; problems: string[] }
  | { kind: "disabled"; reason: string; caps: CapabilitiesV2 }
  | { kind: "ready"; caps: CapabilitiesV2 };

export type Phase = "idle" | "submitting" | "queued" | "running" | "loading_result" | "loading_products" | "completed" | "failed" | "error";
export interface RunError { message: string; problems: string[]; code: string | null; /** the job may still be running on the service and can be checked again */ resumable: boolean }
export interface ProductsState {
  status: "loading" | "ready";
  entries: Partial<Record<Role, ProductEntry>>;
  decoded: Decoded | null;
}
export interface Accepted { request: RequestV2; job: JobV2; result: ResultV2; products: ProductsState }
export interface RunState {
  phase: Phase;
  request: RequestV2 | null;
  job: JobV2 | null;
  error: RunError | null;
  /** failed job reported by the service (kept separately from `error`, which is for interface-side problems) */
  failedJob: JobV2 | null;
  suspended: boolean;
  /** number of status polls made for the current job, and whether the interface is retrying a failed poll */
  polls: number;
  retrying: boolean;
  current: Accepted | null;
  /** last fully accepted result of an EARLIER run, kept identified while a newer run is loading or has failed */
  previous: Accepted | null;
}
export interface ControllerState { caps: CapState; run: RunState }

export interface ControllerOptions {
  client: ComputeClient;
  inflate: Inflate;
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
  now?: () => number;
  pollMs?: number;
  /** interface-side limit on waiting for one job; the job itself is not cancelled and can be checked again */
  timeoutMs?: number;
  /** bounded retry for transient network/5xx failures; submit retries are safe because the request ID is idempotent */
  maxRetries?: number;
  retryMs?: number;
  /** consecutive failed polls tolerated before the interface stops and offers "check again" */
  maxPollFailures?: number;
  newRequestId?: () => string;
}

export const defaultSleep = (ms: number, signal?: AbortSignal): Promise<void> => new Promise<void>((res, rej) => {
  if (signal?.aborted) { rej(new DOMException("Aborted", "AbortError")); return; }
  const t = setTimeout(() => { signal?.removeEventListener("abort", onAbort); res(); }, ms);
  const onAbort = () => { clearTimeout(t); rej(new DOMException("Aborted", "AbortError")); };
  signal?.addEventListener("abort", onAbort, { once: true });
});

const IDLE_RUN: RunState = { phase: "idle", request: null, job: null, error: null, failedJob: null, suspended: false, polls: 0, retrying: false, current: null, previous: null };
const ACTIVE: Phase[] = ["submitting", "queued", "running", "loading_result", "loading_products"];
export const isActive = (p: Phase): boolean => ACTIVE.includes(p);

class Reject extends Error { problems: string[]; code: string | null; resumable: boolean; constructor(message: string, problems: string[] = [], code: string | null = null, resumable = false) { super(message); this.problems = problems; this.code = code; this.resumable = resumable; } }

export class ComputeController {
  private state: ControllerState = { caps: { kind: "loading" }, run: IDLE_RUN };
  private listeners = new Set<() => void>();
  private runGuard = new LatestGuard();
  private capGuard = new LatestGuard();
  private abort: AbortController | null = null;
  private capAbort: AbortController | null = null;
  private disposed = false;
  private readonly o: Required<Omit<ControllerOptions, "client" | "inflate">> & Pick<ControllerOptions, "client" | "inflate">;

  constructor(opts: ControllerOptions) {
    this.o = {
      client: opts.client, inflate: opts.inflate, sleep: opts.sleep ?? defaultSleep, now: opts.now ?? (() => Date.now()), pollMs: opts.pollMs ?? 1500,
      timeoutMs: opts.timeoutMs ?? 20 * 60_000, maxRetries: opts.maxRetries ?? 2, retryMs: opts.retryMs ?? 600, maxPollFailures: opts.maxPollFailures ?? 3,
      newRequestId: opts.newRequestId ?? (() => newComputeRequestId(Date.now())),
    };
  }

  // ---- store -------------------------------------------------------------------------------------------------------
  getState = (): ControllerState => this.state;
  subscribe = (fn: () => void): (() => void) => { this.listeners.add(fn); return () => { this.listeners.delete(fn); }; };
  private set(patch: { caps?: CapState; run?: Partial<RunState> }): void {
    if (this.disposed) return;
    this.state = { caps: patch.caps ?? this.state.caps, run: patch.run ? { ...this.state.run, ...patch.run } : this.state.run };
    for (const l of [...this.listeners]) l();
  }

  // ---- capabilities ------------------------------------------------------------------------------------------------
  /** Reads and strictly validates the capability document. Failure here disables only new computation. */
  async loadCapabilities(): Promise<CapState> {
    this.capAbort?.abort();
    const ac = new AbortController(); this.capAbort = ac;
    const token = this.capGuard.begin();
    this.set({ caps: { kind: "loading" } });
    let next: CapState;
    try {
      const raw = await this.o.client.getCapabilities(ac.signal);
      const parsed = parseCapabilitiesV2(raw);
      next = !parsed.ok ? { kind: "invalid", problems: parsed.problems }
        : parsed.caps.enabled ? { kind: "ready", caps: parsed.caps } : { kind: "disabled", reason: parsed.caps.reason ?? "Computation is disabled.", caps: parsed.caps };
    } catch (e) {
      if (isAbortError(e)) return this.state.caps;
      next = e instanceof ComputeError && e.kind === "http" && (e.status === 404 || e.status === 405)
        ? { kind: "unavailable", message: "This service does not offer the computed-candidate contract 2.0.0." }
        : { kind: "unavailable", message: e instanceof ComputeError ? e.message : "The computation service could not be reached." };
    }
    if (!this.capGuard.isCurrent(token) || this.disposed) return this.state.caps;
    this.set({ caps: next });
    return next;
  }

  // ---- run ---------------------------------------------------------------------------------------------------------
  /** Validates, re-reads capabilities (the authority), then submits exactly one job. Returns the reason when nothing was started. */
  async run(peak: number): Promise<string | null> {
    if (this.disposed) return "closed";
    if (isActive(this.state.run.phase)) return "A computation is already running in this window; wait for it to finish.";
    const bad = validatePeak(peak);
    if (bad) return bad; // blocked locally: nothing is sent and the visible state is unchanged
    const token = this.runGuard.begin();
    this.abort?.abort();
    const ac = new AbortController(); this.abort = ac;
    const prev = this.state.run.current ?? this.state.run.previous;
    this.set({ run: { ...IDLE_RUN, phase: "submitting", previous: prev, current: null } });
    try {
      const caps = await this.loadCapabilities();
      if (!this.runGuard.isCurrent(token)) return null;
      if (caps.kind !== "ready") throw new Reject(caps.kind === "disabled" ? `Computation is not available: ${caps.reason}` : caps.kind === "invalid" ? "The service's capability document is not valid, so computation is disabled." : "The computation service is not available.", caps.kind === "invalid" ? caps.problems : []);
      const req = buildComputeRequest(this.o.newRequestId(), peak, caps.caps);
      if (typeof req === "string") throw new Reject(req);
      this.set({ run: { request: req } });
      await this.execute(req, token, ac.signal, null);
    } catch (e) {
      this.fail(e, token);
    }
    return null;
  }

  /** Check a job again after a timeout or lost contact. Uses the same job; never submits a new one. */
  async checkAgain(): Promise<void> {
    const r = this.state.run;
    if (this.disposed || !r.request || !r.job || isActive(r.phase) || !r.error?.resumable) return;
    const token = this.runGuard.begin();
    this.abort?.abort();
    const ac = new AbortController(); this.abort = ac;
    this.set({ run: { phase: r.job.status === "queued" ? "queued" : "running", error: null, suspended: false, polls: 0, retrying: false } });
    try { await this.execute(r.request, token, ac.signal, r.job); } catch (e) { this.fail(e, token); }
  }

  /** Page left: stop all polling/requests. State and the job identity are kept so `resume()` can continue. */
  suspend(): void {
    if (this.disposed) return;
    const r = this.state.run;
    this.capAbort?.abort();
    if (!isActive(r.phase)) return;
    this.runGuard.invalidate(); this.abort?.abort();
    if (r.job && r.request) {
      this.set({ run: { suspended: true, polls: 0, retrying: false, error: { message: "Status checks paused while this page was closed. The job may still be running on the service.", problems: [], code: null, resumable: !!r.job }, phase: "error" } });
    } else this.set({ run: { suspended: true, phase: r.current ? "completed" : "idle", error: null } });
  }
  /** Page opened again: continue checking a job that was left running. Never re-submits. */
  async resume(): Promise<void> {
    const r = this.state.run;
    if (this.disposed || !r.suspended) return;
    this.set({ run: { suspended: false } });
    if (r.job && r.request && r.error?.resumable && r.phase === "error") await this.checkAgain();
  }
  cancelWaiting(): void { this.suspend(); }
  dispose(): void { this.disposed = true; this.runGuard.invalidate(); this.capGuard.invalidate(); this.abort?.abort(); this.capAbort?.abort(); this.listeners.clear(); }

  // ---- internals ---------------------------------------------------------------------------------------------------
  private async retry<T>(fn: () => Promise<T>, signal: AbortSignal, onRetry?: (n: number) => void): Promise<T> {
    let attempt = 0;
    for (;;) {
      try { return await fn(); }
      catch (e) {
        if (isAbortError(e) || !(e instanceof ComputeError) || !e.retryable || attempt >= this.o.maxRetries) throw e;
        attempt++; onRetry?.(attempt);
        await this.o.sleep(this.o.retryMs * attempt, signal);
      }
    }
  }

  private async execute(req: RequestV2, token: number, signal: AbortSignal, resumeJob: JobV2 | null): Promise<void> {
    const live = () => this.runGuard.isCurrent(token) && !signal.aborted && !this.disposed;
    const started = this.o.now();
    const retrying = (n: number) => { if (live()) this.set({ run: { retrying: n > 0 } }); };
    let job: unknown = resumeJob ? resumeJob : await this.retry(() => this.o.client.submit(req, signal), signal, retrying);
    let failures = 0, polls = 0, jobId: string | undefined = resumeJob?.job_id;
    for (;;) {
      if (!live()) return;
      const problems = validateJob(job, { request: req, jobId });
      if (problems.length) throw new Reject("The service's job response does not match the request that was sent, so it was not used.", problems);
      const j = job as JobV2;
      jobId = j.job_id;
      if (!live()) return;
      if (j.status === "failed") { this.set({ run: { phase: "failed", job: j, failedJob: j, error: null, retrying: false } }); return; }
      if (j.status === "completed") { this.set({ run: { phase: "loading_result", job: j, retrying: false } }); await this.finish(req, j, token, signal); return; }
      this.set({ run: { phase: j.status, job: j, polls, retrying: false } });
      if (this.o.now() - started > this.o.timeoutMs) throw new Reject(`Stopped waiting after ${Math.round(this.o.timeoutMs / 60000)} minutes. The job may still be running on the service; you can check it again.`, [], "wait_timeout", true);
      await this.o.sleep(this.o.pollMs, signal);
      if (!live()) return;
      try {
        job = await this.retry(() => this.o.client.getJob(j.job_id, signal), signal, retrying);
        failures = 0; polls++;
      } catch (e) {
        if (isAbortError(e)) return;
        failures++;
        if (e instanceof ComputeError && e.status === 404) throw new Reject("The service no longer knows this job (it may have restarted). Start a new run.", [], "job_not_found");
        if (!(e instanceof ComputeError) || !e.retryable || failures >= this.o.maxPollFailures) throw new Reject("Lost contact with the computation service. The job may still be running; you can check it again.", [], e instanceof ComputeError ? e.code : null, e instanceof ComputeError ? e.retryable || e.kind === "unavailable" : false);
        job = j; // transient: poll again with the last known state
      }
    }
  }

  private async finish(req: RequestV2, j: JobV2, token: number, signal: AbortSignal): Promise<void> {
    const live = () => this.runGuard.isCurrent(token) && !signal.aborted && !this.disposed;
    // C03: the Result is read only after a validated completed job whose result_url equals this job's own result path (validateJob checked that).
    const raw = await this.retry(() => this.o.client.getResult(j.job_id, signal), signal);
    if (!live()) return;
    const problems = validateResult(raw, { request: req, jobId: j.job_id });
    if (problems.length) throw new Reject("The result was rejected before any map data was requested.", problems);
    const result = raw as ResultV2;
    const accepted: Accepted = { request: req, job: j, result, products: { status: "loading", entries: {}, decoded: null } };
    this.set({ run: { phase: "loading_products", current: accepted } });
    const entries = await fetchProducts(this.o.client, result, signal);
    if (!live()) return;
    const bytes: RawProducts = {}; const prior: Partial<Record<Role, string>> = {};
    for (const e of Object.values(entries)) {
      if (e.status === "ok") bytes[e.role] = e.buffer;
      else prior[e.role] = e.status === "not_offered" ? e.reason : e.message;
    }
    let decoded: Decoded;
    try { decoded = await decodeProducts(result, bytes, this.o.inflate, prior); }
    catch (e) { if (isAbortError(e)) return; decoded = { depth: null, arrival: null, velocity: null, extent: null, unavailable: { ...prior, max_depth_cog: "The products could not be decoded." } }; }
    if (!live()) return;
    const done: Accepted = { ...accepted, products: { status: "ready", entries, decoded } };
    this.set({ run: { phase: "completed", current: done, error: null, failedJob: null, previous: null } });
  }

  private fail(e: unknown, token: number): void {
    if (!this.runGuard.isCurrent(token) || this.disposed || isAbortError(e)) return;
    let err: RunError;
    if (e instanceof Reject) err = { message: e.message, problems: e.problems, code: e.code, resumable: e.resumable };
    else if (e instanceof ComputeError) err = { message: e.message, problems: [], code: e.code, resumable: false };
    else err = { message: "The request failed unexpectedly.", problems: [], code: null, resumable: false };
    this.set({ run: { phase: "error", error: err, retrying: false } });
  }
}
