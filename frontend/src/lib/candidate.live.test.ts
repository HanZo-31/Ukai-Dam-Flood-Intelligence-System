// Genuine HTTP checks of the delivered adapter against the integrated running service.
// Explicitly skipped for offline unit-only builds; set UKAI_CANDIDATE_TEST_BASE to run them.
import { describe, expect, it } from "vitest";
import { buildRequest, createCandidateClient, validateResult } from "./candidate";
import { runLookup } from "./candidateRun";

const env = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env;
const base = env.UKAI_CANDIDATE_TEST_BASE;
const prefix = `live-${Date.now().toString(36)}`;
const client = createCandidateClient({ base: `${base}/api/v1/candidates` });
let known: string[] = [];
const ctx = () => ({ knownScenarioIds: known, storedPeaks: [15000, 20000, 30000] });

describe.skipIf(!base)("real integrated candidate service (not mocked)", () => {
  it("advertises stored-only mode and the actual four-reference catalog", async () => {
    const caps = await client.getCapabilities();
    expect(caps.understood).toBe(true);
    expect(caps.storedReference.available).toBe(true);
    expect(caps.experimentalMl.available).toBe(false);
    expect(caps.storedPeaks).toEqual([15000, 20000, 30000]);
    const catalog = await (await fetch(`${base}/api/v1/prototypes/scenarios`)).json();
    known = catalog.items.map((x: { scenario_id: string }) => x.scenario_id);
    expect(known.length).toBe(4);
  });
  it("accepts an exact selection and resolves every returned resource through the reference proxy", async () => {
    const req = buildRequest(`${prefix}-exact`, 20000, false);
    const result = await runLookup(client, req, ctx());
    expect(validateResult(result, req, ctx())).toEqual([]);
    expect(result.actual_peak_release_m3s).toBe(20000);
    expect(result.computed).toBe(false);
    for (const [role, url] of Object.entries(result.reference_resources)) {
      const response = await fetch(`${base}${url}`);
      expect(response.status).toBe(200);
      if (["detail", "layers", "impact"].includes(role)) {
        expect(response.headers.get("content-type")).toContain("application/json");
      } else {
        // Assumptions and quality reports are immutable file downloads, not metadata routes.
        expect(response.headers.get("x-ukai-scientific-validation")).toBe("not_validated");
        expect((await response.arrayBuffer()).byteLength).toBeGreaterThan(0);
      }
    }
    const detail = await (await fetch(`${base}${result.reference_resources.detail}`)).json();
    expect(detail.run_id).toBe(result.source_run_id);
  });
  it("rejects an intermediate peak without explicit nearest opt-in", async () => {
    await expect(client.submit(buildRequest(`${prefix}-reject`, 26000, false))).rejects.toMatchObject({ status: 400 });
  });
  it("returns 30000 for opted-in 26000, without pretending to compute 26000", async () => {
    const r = await runLookup(client, buildRequest(`${prefix}-near`, 26000, true), ctx());
    expect([r.requested_peak_release_m3s, r.actual_peak_release_m3s]).toEqual([26000, 30000]);
    expect(r.computed).toBe(false);
  });
  it("keeps lower-peak ties, caches repeated IDs, and refuses changed content", async () => {
    const req = buildRequest(`${prefix}-tie`, 25000, true);
    const first = await runLookup(client, req, ctx());
    const second = await runLookup(client, req, ctx());
    expect(first.actual_peak_release_m3s).toBe(20000);
    expect(second.job_id).toBe(first.job_id);
    expect(second.cache_hit).toBe(true);
    await expect(client.submit({ ...req, peak_release_m3s: 20000 })).rejects.toMatchObject({ status: 409 });
  });
  it("returns an honest missing-job error", async () => {
    await expect(client.getJob(`${prefix}-missing`)).rejects.toMatchObject({ status: 404 });
  });
  it("enforces the bounded input family on the actual service", async () => {
    await expect(client.submit(buildRequest(`${prefix}-bounds`, 31000, false))).rejects.toMatchObject({ status: 422 });
  });
});
