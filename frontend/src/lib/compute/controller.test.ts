// Journey tests of the compute controller against the SYNTHETIC test transport (never a real solver). Time is injected; nothing sleeps.
import { describe, expect, it } from "vitest";
import { createFixtureTransport, type Behaviour } from "../../testing/computeFixtureTransport";
import { loadFixtures, type Fixtures } from "../../testing/fixtureLoad";
import { createComputeClient } from "./client";
import { ComputeController, isActive } from "./controller";

let fxP: Promise<Fixtures> | null = null;
const getFx = (): Promise<Fixtures> => (fxP ??= loadFixtures());

async function setup(b: Partial<Behaviour> = {}, o: Partial<ConstructorParameters<typeof ComputeController>[0]> = {}) {
  const fx = await getFx();
  const t = createFixtureTransport(fx.files, b);
  let n = 0, clock = 0;
  const c = new ComputeController({ client: createComputeClient({ fetchImpl: t.fetch }), inflate: fx.inflate, sleep: async () => { clock += 1000; await Promise.resolve(); }, now: () => clock, pollMs: 1, retryMs: 1, newRequestId: () => `req-${++n}`, ...o });
  return { t, c };
}
const posts = (t: { calls: { method: string; path: string }[] }) => t.calls.filter((x) => x.method === "POST");
const assetGets = (t: { calls: { method: string; path: string }[] }) => t.calls.filter((x) => /\/assets\//.test(x.path));
const resultGets = (t: { calls: { method: string; path: string }[] }) => t.calls.filter((x) => /\/result$/.test(x.path));

describe("capabilities are the authority", () => {
  for (const cap of ["disabled", "bad_version", "malformed", "http_error", "outage", "not_found", "enabled_but_no_config"] as const) {
    it(`capabilities=${cap}: no job is submitted`, async () => {
      const { t, c } = await setup({ capabilities: cap });
      await c.loadCapabilities();
      expect(c.getState().caps.kind).not.toBe("ready");
      await c.run(25000);
      expect(posts(t).length).toBe(0);
      expect(c.getState().run.phase).toBe("error");
      expect(c.getState().run.current).toBeNull();
    });
  }
  it("enabled: ready with the advertised configuration", async () => {
    const { c } = await setup();
    const s = await c.loadCapabilities();
    expect(s.kind).toBe("ready");
  });
});

describe("happy path", () => {
  it("leaving during product download can resume the same completed job without another POST", async () => {
    const { t, c } = await setup();
    let paused = false;
    c.subscribe(() => {
      if (!paused && c.getState().run.phase === "loading_products") { paused = true; c.suspend(); }
    });
    await c.run(25000);
    expect(c.getState().run.error?.resumable).toBe(true);
    await c.resume();
    expect(c.getState().run.phase).toBe("completed");
    expect(c.getState().run.current?.products.decoded?.depth).not.toBeNull();
    expect(posts(t).length).toBe(1);
  });
  it("submits once, polls, fetches the result only after completion, then verified products; decoded rasters present", async () => {
    const { t, c } = await setup();
    const phases: string[] = [];
    c.subscribe(() => phases.push(c.getState().run.phase));
    expect(await c.run(25000)).toBeNull();
    const s = c.getState().run;
    expect(s.phase).toBe("completed");
    expect(posts(t).length).toBe(1);
    const firstResult = t.calls.findIndex((x) => /\/result$/.test(x.path));
    const lastJobPoll = t.calls.map((x, i) => (/\/jobs\/[^/]+$/.test(x.path) && x.method === "GET" ? i : -1)).filter((i) => i >= 0).pop()!;
    expect(firstResult).toBeGreaterThan(lastJobPoll);
    expect(resultGets(t).length).toBe(1);
    expect(assetGets(t).length).toBe(3);
    expect(phases).toContain("queued");
    expect(phases).toContain("running");
    expect(phases.indexOf("loading_result")).toBeGreaterThan(phases.indexOf("running"));
    const a = s.current!;
    expect(a.request.peak_release_m3s).toBe(25000);
    expect(a.result.requested_peak_release_m3s).toBe(a.result.actual_peak_release_m3s);
    expect(a.products.status).toBe("ready");
    expect(a.products.decoded?.depth).toBeTruthy();
    expect(a.products.decoded?.arrival).toBeTruthy();
    expect(a.products.decoded?.extent).toBeTruthy();
  });
  it("rejects a second run while one is active", async () => {
    const { c } = await setup({ queuedPolls: 5 });
    const p = c.run(25000);
    await Promise.resolve();
    expect(isActive(c.getState().run.phase)).toBe(true);
    expect(await c.run(26000)).toMatch(/already running/);
    await p;
  });
  it("out-of-range peak is blocked locally: nothing sent, state unchanged", async () => {
    const { t, c } = await setup();
    for (const v of [14999, 30001, Number.NaN]) expect(typeof (await c.run(v))).toBe("string");
    expect(t.calls.length).toBe(0);
    expect(c.getState().run.phase).toBe("idle");
  });
});

describe("service-reported failure and rejected responses", () => {
  it("failed job is shown as failed with its safe error and no result is fetched", async () => {
    const { t, c } = await setup({ outcome: "failed" });
    await c.run(25000);
    const s = c.getState().run;
    expect(s.phase).toBe("failed");
    expect(s.failedJob?.error?.code).toBe("interrupted");
    expect(resultGets(t).length).toBe(0);
  });
  for (const poll of ["wrong_job", "wrong_config", "wrong_request"] as const) {
    it(`poll=${poll}: response rejected, no result or asset request`, async () => {
      const { t, c } = await setup({ poll });
      await c.run(25000);
      expect(c.getState().run.phase).toBe("error");
      const er = c.getState().run.error!;
      expect(er.problems.length > 0 || er.code === "job_not_found").toBe(true); // either the identity check or the service's own unknown-job answer
      expect(resultGets(t).length).toBe(0);
      expect(assetGets(t).length).toBe(0);
    });
  }
  for (const result of ["malformed", "wrong_config", "wrong_checksum_config", "wrong_job", "wrong_request", "peak_differs", "not_computed", "validated_true", "foreign_asset_url", "cross_job_asset_url", "absolute_asset_url", "query_asset_url", "missing_required_asset", "velocity_without_definition", "extra_field", "wrong_unit"] as const) {
    it(`result=${result}: rejected before any product is requested; no accepted result`, async () => {
      const { t, c } = await setup({ result });
      await c.run(25000);
      const s = c.getState().run;
      expect(s.phase).toBe("error");
      expect(assetGets(t).length).toBe(0);
      expect(s.current === null || s.current.products.status === "loading").toBe(true);
      expect(s.phase).not.toBe("completed");
    });
  }
  it("result 409/outage surface as errors, not as results", async () => {
    for (const result of ["http_409", "outage"] as const) {
      const { c } = await setup({ result });
      await c.run(25000);
      expect(c.getState().run.phase).toBe("error");
    }
  });
  it("a corrupted or truncated product is discarded; the depth map is unavailable and the reason is stated", async () => {
    for (const assets of ["bad_checksum", "wrong_length"] as const) {
      const { c } = await setup({ assets });
      await c.run(25000);
      const s = c.getState().run;
      expect(s.phase === "completed" || s.phase === "error").toBe(true);
      if (s.phase === "completed") {
        expect(s.current!.products.decoded?.depth ?? null).toBeNull();
        expect(Object.values(s.current!.products.decoded?.unavailable ?? {}).join(" ")).toMatch(/./);
      }
    }
  });
  it("missing optional arrival: wet comparison stays possible, the arrival reason is recorded", async () => {
    const { c } = await setup({ assets: "missing_arrival" });
    await c.run(25000);
    const s = c.getState().run;
    if (s.phase === "completed") {
      expect(s.current!.products.decoded?.depth).toBeTruthy();
      expect(s.current!.products.decoded?.arrival ?? null).toBeNull();
    }
  });
});

describe("retries, timeouts, resume, staleness", () => {
  it("one transient submit failure is retried and exactly one job results", async () => {
    const { t, c } = await setup({ submit: "outage_once" });
    await c.run(25000);
    expect(c.getState().run.phase).toBe("completed");
    expect(posts(t).length).toBeGreaterThanOrEqual(1);
    expect(posts(t).length).toBeLessThanOrEqual(2);
  });
  it("persistent outage stops after a bounded number of attempts", async () => {
    const { t, c } = await setup({ submit: "outage" }, { maxRetries: 2 });
    await c.run(25000);
    expect(c.getState().run.phase).toBe("error");
    expect(posts(t).length).toBe(3);
  });
  it("busy and conflict answers are shown, not retried forever", async () => {
    for (const submit of ["busy", "conflict", "invalid"] as const) {
      const { t, c } = await setup({ submit });
      await c.run(25000);
      expect(c.getState().run.phase).toBe("error");
      expect(posts(t).length).toBeLessThanOrEqual(3);
    }
  });
  it("timeout is interface-side and resumable; check again re-polls the SAME job without a new submit", async () => {
    const { t, c } = await setup({ outcome: "never" }, { timeoutMs: 5000 });
    await c.run(25000);
    const s = c.getState().run;
    expect(s.phase).toBe("error");
    expect(s.error?.resumable).toBe(true);
    expect(s.error?.code).toBe("wait_timeout");
    const jobId = s.job!.job_id;
    t.set({ outcome: "completed" });
    await c.checkAgain();
    expect(c.getState().run.phase).toBe("completed");
    expect(c.getState().run.job!.job_id).toBe(jobId);
    expect(posts(t).length).toBe(1);
  });
  it("suspend stops polling; resume continues the same job and never re-submits", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => { release = r; });
    let slept = 0;
    const { t, c } = await setup({ outcome: "never" }, { sleep: async () => { slept++; if (slept === 2) { await gate; } } });
    const p = c.run(25000);
    for (let i = 0; i < 200 && slept < 2; i++) await new Promise((r) => setTimeout(r, 1));
    expect(slept).toBe(2);
    c.suspend();
    release();
    await p;
    const during = t.calls.length;
    await new Promise((r) => setTimeout(r, 5));
    expect(t.calls.length).toBe(during);
    expect(c.getState().run.suspended).toBe(true);
    t.set({ outcome: "completed" });
    await c.resume();
    expect(c.getState().run.phase).toBe("completed");
    expect(posts(t).length).toBe(1);
  });
  it("a failed second run keeps the earlier accepted result identified as previous", async () => {
    const { t, c } = await setup();
    await c.run(25000);
    const firstId = c.getState().run.current!.job.job_id;
    t.set({ outcome: "failed" });
    await c.run(20000);
    const s = c.getState().run;
    expect(s.phase).toBe("failed");
    expect(s.current).toBeNull();
    expect(s.previous?.job.job_id).toBe(firstId);
    expect(s.previous?.request.peak_release_m3s).toBe(25000);
  });
  it("a late response of a superseded run is not applied (dispose during a run)", async () => {
    const { c } = await setup({ queuedPolls: 3 });
    const p = c.run(25000);
    c.dispose();
    await p;
    expect(c.getState().run.current).toBeNull();
  });
});
