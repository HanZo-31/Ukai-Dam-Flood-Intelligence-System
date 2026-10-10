// Optional READ-ONLY real-API verification. Never submits jobs/imports/approvals.
import { describe, expect, it } from "vitest";
import expected from "./fixtures/point_samples.json";
import { readPoint, pointDifference, type MapPoint } from "./pointInspection";
import type { PrototypeLayers, PrototypeList } from "./api";

const env = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env;
const base = env.UKAI_POINT_TEST_BASE;

describe.skipIf(!base)("read-only point requests through the real V05 API", () => {
  for (const [name, fixture] of Object.entries(expected.scenarios)) {
    it(`${name}: bounded ranges match independent raster values`, async () => {
      expect(base).toBe("http://127.0.0.1:5176");
      const list = await (await fetch(`${base}/api/v1/prototypes/scenarios`)).json() as PrototypeList;
      const id = list.items.find(s => name === "2006" ? s.scenario_type === "historical_replay" : s.scenario_id.includes(`-${name}-`))!.scenario_id;
      const layers = await (await fetch(`${base}/api/v1/prototypes/scenarios/${id}/layers`)).json() as PrototypeLayers;
      let requests = 0, bytes = 0;
      const f = (async (path: string | URL | Request, init?: RequestInit) => {
        expect(String(path)).toMatch(/^\/api\/v1\/prototypes\/scenarios\//);
        expect(new Headers(init?.headers).get("Range")).toMatch(/^bytes=\d+-\d+$/);
        const response = await fetch(`${base}${path}`, init);
        expect(response.status).toBe(206);
        requests++; bytes += Number(response.headers.get("Content-Length"));
        return response;
      }) as typeof fetch;
      for (const point of fixture.points) {
        const values = await readPoint(layers, point.coordinate as MapPoint, undefined, f);
        for (const key of ["depth", "arrival", "velocity"] as const) {
          const value = point.values[key];
          if (value <= -9000) expect(values[key]).toMatchObject({ kind: "nodata", value: null });
          else { expect(values[key].kind).toBe("value"); expect(values[key].value).toBeCloseTo(value, 6); }
        }
      }
      expect(requests).toBeGreaterThan(0);
      expect(bytes).toBeLessThan(12 * 1024 * 1024); // three roles × three points, actually small tile/range reads
      const fsName = "node:fs"; const fs = await import(/* @vite-ignore */ fsName);
      if (env.UKAI_POINT_EVIDENCE_DIR) fs.writeFileSync(`${env.UKAI_POINT_EVIDENCE_DIR}/${name}.json`, JSON.stringify({
        checked_at: new Date().toISOString(), passed: true, scenario: id, points: fixture.points.length,
        range_requests: requests, bytes_transferred: bytes, original_resolution: true, writes_or_jobs: false,
      }, null, 2));
    }, 120000);
  }
  it("same location produces signed depth and relative-arrival deltas", async () => {
    const list = await (await fetch(`${base}/api/v1/prototypes/scenarios`)).json() as PrototypeList;
    const layers = await Promise.all(["h01", "h02"].map(async name => {
      const id = list.items.find(s => s.scenario_id.includes(`-${name}-`))!.scenario_id;
      return (await fetch(`${base}/api/v1/prototypes/scenarios/${id}/layers`)).json() as Promise<PrototypeLayers>;
    }));
    const f = ((path, init) => fetch(`${base}${path}`, init)) as typeof fetch;
    const point = expected.scenarios.h02.points[0].coordinate as MapPoint;
    const [a, b] = await Promise.all(layers.map(l => readPoint(l, point, undefined, f)));
    const forward = pointDifference(a.depth, b.depth), reverse = pointDifference(b.depth, a.depth);
    expect(forward.value).toBeCloseTo(expected.scenarios.h02.points[0].values.depth - expected.scenarios.h01.points[0].values.depth, 6);
    expect(reverse.value).toBeCloseTo(-forward.value!, 6);
    expect(pointDifference(a.arrival, b.arrival).value).toBe(0);
  }, 120000);
});
