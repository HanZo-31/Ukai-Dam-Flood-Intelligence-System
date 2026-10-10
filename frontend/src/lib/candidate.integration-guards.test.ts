import { expect, it } from "vitest";
import { validateResult } from "./candidate";
import { fixtureResult, KNOWN_IDS, req20k } from "../testing/candidateFixtures";
const req = req20k();
const ctx = { knownScenarioIds: KNOWN_IDS, storedPeaks: [15000, 20000, 30000] };

it("refuses prefix-confusable, traversing, encoded and query-bearing reference links", () => {
  const good = fixtureResult(req);
  for (const extra of ["-other/layers", "/../other/layers", "/%2e%2e/other/layers", "/layers?redirect=other"]) {
    expect(validateResult({ ...good, reference_resources: { ...good.reference_resources, layers: `${good.reference_resources.detail}${extra}` } }, req, ctx).join()).toMatch(/does not point into/);
  }
});
it("refuses malformed warning and cache data before React renders it", () => {
  const good = fixtureResult(req);
  expect(validateResult({ ...good, warnings: [{}] }, req, ctx).join()).toMatch(/list of strings/);
  expect(validateResult({ ...good, cache_hit: "false" }, req, ctx).join()).toMatch(/boolean/);
});
it("refuses malformed job identifiers before any follow-up GET", () => {
  expect(validateResult({ ...fixtureResult(req), job_id: "../other-job" }, req, ctx).join()).toMatch(/job ID/);
});
