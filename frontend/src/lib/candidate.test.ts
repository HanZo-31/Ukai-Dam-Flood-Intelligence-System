import { describe, expect, it } from "vitest";
import { buildRequest, CandidateError, createCandidateClient, isValidId, nearestStoredPeak, newRequestId, parseCapabilities, validateRequestInput, validateResult } from "./candidate";
import { CandidateInvalid, runLookup } from "./candidateRun";
import { capabilitiesShapeA, capabilitiesShapeB, capabilitiesShapeC, fakeFetch, fixtureResult, json, KNOWN_IDS, req20k } from "../testing/candidateFixtures";

const ctx = { knownScenarioIds: KNOWN_IDS, storedPeaks: [15000, 20000, 30000] };

describe("request checks (mirror the contract)", () => {
  it("accepts releases 15000..30000 only and valid IDs only", () => {
    expect(validateRequestInput(20000, "demo-request-001")).toBeNull();
    expect(validateRequestInput(14999, "demo-request-001")).toMatch(/between/);
    expect(validateRequestInput(30001, "demo-request-001")).toMatch(/between/);
    expect(validateRequestInput(Number.NaN, "demo-request-001")).toMatch(/number/);
    expect(validateRequestInput(20000, "AB")).toMatch(/request ID/);
    expect(isValidId("a_b-9")).toBe(true); expect(isValidId("Upper-case")).toBe(false); expect(isValidId("x".repeat(101))).toBe(false);
  });
  it("generates valid distinct request IDs", () => {
    const a = newRequestId(1_800_000_000_000), b = newRequestId(1_800_000_000_000);
    expect(isValidId(a)).toBe(true); expect(a === b).toBe(false);
  });
  it("builds exactly the contract fields", () => {
    expect(buildRequest("demo-request-001", 20000, false)).toEqual({ schema_version: "1.0.0", request_id: "demo-request-001", mode: "stored_reference", input_family: "ukai-hyp-fixed-shape-v1", peak_release_m3s: 20000, allow_nearest_stored: false });
  });
  it("nearest stored peak: ties go to the lower peak", () => {
    const p = [15000, 20000, 30000];
    expect(nearestStoredPeak(17500, p)).toBe(15000); expect(nearestStoredPeak(25000, p)).toBe(20000); expect(nearestStoredPeak(26000, p)).toBe(30000); expect(nearestStoredPeak(1, [])).toBeNull();
  });
});

describe("capabilities are read, not assumed", () => {
  it("reads three plausible shapes", () => {
    for (const raw of [capabilitiesShapeA, capabilitiesShapeB, capabilitiesShapeC]) {
      const c = parseCapabilities(raw);
      expect(c.understood).toBe(true); expect(c.storedReference.available).toBe(true); expect(c.experimentalMl.available).toBe(false);
    }
    expect(parseCapabilities(capabilitiesShapeA).storedPeaks).toEqual([15000, 20000, 30000]);
    expect(parseCapabilities(capabilitiesShapeA).experimentalMl.reason).toMatch(/holdout/);
    expect(parseCapabilities(capabilitiesShapeC).experimentalMl.reason).toMatch(/acceptance gate/);
  });
  it("enables nothing when a mode is not declared or the document is unreadable", () => {
    expect(parseCapabilities({ modes: [] }).storedReference.available).toBe(false);
    expect(parseCapabilities("nope").storedReference.available).toBe(false);
    expect(parseCapabilities(null).understood).toBe(false);
    expect(parseCapabilities({ modes: [{ mode: "stored_reference", available: false, reason: "sources failed checks" }] }).storedReference.reason).toBe("sources failed checks");
  });
  it("never reports ML available unless the service says so explicitly", () => { expect(parseCapabilities({ modes: ["stored_reference"] }).experimentalMl.available).toBe(false); });
});

describe("result identity checks", () => {
  const req = req20k();
  it("accepts a consistent stored lookup", () => { expect(validateResult(fixtureResult(req), req, ctx)).toEqual([]); });
  it("rejects a result for another request (mismatched ID)", () => { expect(validateResult(fixtureResult(req, { request_id: "other-request" }), req, ctx).join()).toMatch(/different request ID/); });
  it("rejects an exact selection that returns a different peak", () => { expect(validateResult(fixtureResult(req, { actual_peak_release_m3s: 30000 }), req, ctx).join()).toMatch(/exact selection/); });
  it("shows requested versus actual for an opted-in nearest selection", () => {
    const near = req20k("demo-request-002", true, 26000);
    const ok = fixtureResult(near);
    expect([ok.requested_peak_release_m3s, ok.actual_peak_release_m3s]).toEqual([26000, 30000]);
    expect(validateResult(ok, near, ctx)).toEqual([]);
    expect(validateResult({ ...ok, actual_peak_release_m3s: 20000 }, near, ctx).join()).toMatch(/nearest/);
  });
  it("rejects computed results and validation claims", () => {
    expect(validateResult(fixtureResult(req, { computed: true }), req, ctx).join()).toMatch(/computed: false/);
    expect(validateResult(fixtureResult(req, { scientifically_validated: true }), req, ctx).join()).toMatch(/scientific validation/);
    expect(validateResult(fixtureResult(req, { calibration_status: "calibrated" }), req, ctx).join()).toMatch(/calibration/);
  });
  it("requires a known source scenario and reference URLs inside the reference API", () => {
    expect(validateResult(fixtureResult(req, { source_scenario_id: "invented" }), req, ctx).join()).toMatch(/not one of the loaded/);
    const r = fixtureResult(req);
    expect(validateResult({ ...r, reference_resources: { ...r.reference_resources, layers: "http://evil.example/x" } }, req, ctx).join()).toMatch(/does not point into the reference API/);
    expect(validateResult({ ...r, reference_resources: { detail: "/api/v1/prototypes/scenarios/ukai-hyp-h01-release15000-combined-v1" } }, req, ctx).join()).toMatch(/does not point/);
  });
  it("names every missing field", () => { const { job_id: _j, ...rest } = fixtureResult(req); void _j; expect(validateResult(rest, req, ctx)).toEqual(["Missing field: job_id."]); });
});

describe("client against a stand-in fetch (mocked HTTP, not the real service)", () => {
  it("unreachable service and a proxy without a route are both 'unavailable'", async () => {
    const down = fakeFetch(() => "throw");
    await expect(createCandidateClient({ fetchImpl: down.f }).getCapabilities()).rejects.toMatchObject({ kind: "unavailable" });
    const noRoute = fakeFetch(() => new Response("<html>not found</html>", { status: 404 }));
    await expect(createCandidateClient({ fetchImpl: noRoute.f }).getCapabilities()).rejects.toMatchObject({ kind: "unavailable" });
  });
  it("request errors carry the status and a safe code, never server text", async () => {
    const c = createCandidateClient({ fetchImpl: fakeFetch(() => json({ detail: "C:\\secret\\path", code: "release_out_of_range" }, 422)).f });
    await expect(c.submit(req20k())).rejects.toMatchObject({ kind: "http", status: 422, code: "release_out_of_range" });
    try { await c.submit(req20k()); } catch (e) { expect((e as CandidateError).message.includes("secret")).toBe(false); }
  });
  it("posts JSON to the configured base and sends the contract body", async () => {
    const h = fakeFetch(() => json(fixtureResult(req20k())));
    await createCandidateClient({ base: "http://127.0.0.1:8770/api/v1/candidates/", fetchImpl: h.f }).submit(req20k());
    expect(h.calls[0].url).toBe("http://127.0.0.1:8770/api/v1/candidates/jobs");
    expect(JSON.parse(String(h.calls[0].init?.body))).toEqual(req20k());
  });
});

describe("runLookup", () => {
  it("returns a completed, identity-checked result", async () => {
    const h = fakeFetch(() => json(fixtureResult(req20k())));
    const r = await runLookup(createCandidateClient({ fetchImpl: h.f }), req20k(), ctx);
    expect(r.status).toBe("completed"); expect(r.computed).toBe(false);
  });
  it("follows queued and running states to completion (fixture of reserved states)", async () => {
    const states = ["queued", "running", "completed"] as const; let i = 0;
    const h = fakeFetch(() => json(fixtureResult(req20k(), { status: states[Math.min(i++, 2)] })));
    const r = await runLookup(createCandidateClient({ fetchImpl: h.f }), req20k(), ctx, undefined, { pollMs: 1 });
    expect(r.status).toBe("completed"); expect(h.calls.map((c) => c.init?.method)).toEqual(["POST", "GET", "GET"]);
  });
  it("returns a failed job as failed, not as a result", async () => {
    const h = fakeFetch(() => json(fixtureResult(req20k(), { status: "failed", warnings: ["source check failed"] })));
    expect((await runLookup(createCandidateClient({ fetchImpl: h.f }), req20k(), ctx)).status).toBe("failed");
  });
  it("throws CandidateInvalid for a mismatched identity instead of showing it", async () => {
    const h = fakeFetch(() => json(fixtureResult(req20k(), { request_id: "someone-elses-request" })));
    await expect(runLookup(createCandidateClient({ fetchImpl: h.f }), req20k(), ctx)).rejects.toThrow(/does not match/);
    try { await runLookup(createCandidateClient({ fetchImpl: h.f }), req20k(), ctx); } catch (e) { expect(e instanceof CandidateInvalid).toBe(true); }
  });
  it("does not poll forever", async () => {
    const h = fakeFetch(() => json(fixtureResult(req20k(), { status: "running" })));
    await expect(runLookup(createCandidateClient({ fetchImpl: h.f }), req20k(), ctx, undefined, { pollMs: 1, maxPolls: 2 })).rejects.toThrow(/did not finish/);
  });
});
