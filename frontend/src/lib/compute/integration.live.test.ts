// Real producer/consumer checks. Never substitutes a test transport or saved
// example. A receiving profile computes its first 25,000 request genuinely.
import { describe, expect, it } from "vitest";
import { nodeIo } from "../../testing/nodeIo";
import { createComputeClient } from "./client";
import { ComputeController } from "./controller";
import { referenceArrivalBlock, type RequestV2, type ResultV2 } from "./contract";
import { loadCandidateReference } from "./reference";
import { compareCandidate, type CompareGrid } from "./candidateCompare";
import { computeCandidateZones, reconcileZones } from "./candidateZones";
import type { PrototypeLayers } from "../api";

const env = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env;
const base = env.UKAI_CANDIDATE_TEST_BASE;

describe.skipIf(!base)("genuine merged compute-v2 producer and frontend", () => {
  it("computes exact 25000, checks every real product, compares H02, reconciles zones, then reuses checked cache", async () => {
    const io = await nodeIo(); const inflate = async (bytes: Uint8Array) => io.inflate(bytes);
    const client = createComputeClient({ base });
    let seq = 0;
    const controller = new ComputeController({ client, inflate, pollMs: 500, timeoutMs: 240000,
      newRequestId: () => `merge-25000-v03-${++seq}` });
    const phases: string[] = [];
    controller.subscribe(() => phases.push(controller.getState().run.phase));
    await controller.run(25000);
    const run = controller.getState().run;
    expect(run.error).toBeNull(); expect(run.phase).toBe("completed");
    const accepted = run.current!;
    expect(accepted.result.actual_peak_release_m3s).toBe(25000);
    expect(accepted.result.computed).toBe(true);
    expect(accepted.result.scientifically_validated).toBe(false);
    expect(accepted.result.engine).toBe("experimental_fast_solver");
    for (const entry of Object.values(accepted.products.entries)) expect(entry.status).toBe("ok");
    const decoded = accepted.products.decoded!;
    expect(decoded.unavailable).toEqual({});
    expect(decoded.depth?.width).toBe(3072); expect(decoded.depth?.height).toBe(1024);
    expect(decoded.arrival).not.toBeNull(); expect(decoded.velocity).not.toBeNull(); expect(decoded.extent).not.toBeNull();
    expect(accepted.result.scenario_id).not.toBe(accepted.result.derived_grid.target_reference_scenario_id);
    const id = accepted.result.derived_grid.target_reference_scenario_id;
    const detail = await (await fetch(`${base}/api/v1/prototypes/scenarios/${id}`)).json();
    const layers = await (await fetch(`${base}/api/v1/prototypes/scenarios/${id}/layers`)).json() as PrototypeLayers;
    const reference = await loadCandidateReference(layers, ((url, init) => fetch(`${base}${url}`, init)) as typeof fetch, inflate);
    const candidate: CompareGrid = { width: decoded.depth!.width, height: decoded.depth!.height,
      geo: decoded.depth!.geo, crs: accepted.result.derived_grid.crs,
      depth: decoded.depth!.data, arrival: decoded.arrival!.data };
    expect(referenceArrivalBlock(detail.arrival)).toBeNull();
    const comparison = compareCandidate(reference, candidate, null);
    expect(typeof comparison).not.toBe("string");
    if (typeof comparison === "string") throw new Error(comparison);
    expect(comparison.km2.confirmedGained).toBeCloseTo(5.578, 2);
    expect(comparison.km2.candidateWetUnknownBaseline).toBeCloseTo(69.081, 2);
    expect(comparison.arrival.available).toBe(true);
    const zones = computeCandidateZones(reference, candidate, null);
    if (typeof zones === "string") throw new Error(zones);
    expect(reconcileZones(zones, comparison)).toEqual([]);
    expect(zones.ranked.length).toBeGreaterThan(0);
    const originalRunId = accepted.result.run_id;
    await controller.run(25000);
    expect(controller.getState().run.current!.result.cache_hit).toBe(true);
    expect(controller.getState().run.current!.result.run_id).toBe(originalRunId);
    // Save public, source-bound evidence via the injected Node test-only helper.
    const fsName = "node:fs"; const fs = await import(/* @vite-ignore */ fsName);
    if (env.UKAI_COMPUTE_EVIDENCE_PATH) fs.writeFileSync(env.UKAI_COMPUTE_EVIDENCE_PATH, JSON.stringify({
      checked_at: new Date().toISOString(), passed: true, phases,
      request: accepted.request as RequestV2, result: accepted.result as ResultV2,
      first_request_cache_hit: accepted.result.cache_hit,
      products: Object.fromEntries(Object.entries(accepted.products.entries).map(([role, entry]) => [role, { status: entry.status }])),
      comparison: { ...comparison, classes: "omitted byte array" }, zones: { ...zones }, cached_run_id: originalRunId,
    }, null, 2));
    controller.dispose();
  }, 300000);
});
