// Checks the adapter against Team 2's actual contract files (candidate-openapi-v1.json, candidate-examples.json), both copied unchanged
// into lib/fixtures. These are the service's own published examples; they are still not a test against a running service.
import { describe, expect, it } from "vitest";
import examples from "./fixtures/candidate_examples.json";
import openapi from "./fixtures/candidate_openapi_v1.json";
import { buildRequest, ID_PATTERN_SOURCE, INPUT_FAMILY, MODE_STORED, parseCapabilities, PEAK_MAX, PEAK_MIN, RESOURCE_KEYS, isValidId, validateResult, type CandidateRequest } from "./candidate";

type Schema = { required: string[]; properties: Record<string, { pattern?: string; minimum?: number; maximum?: number; const?: unknown }> };
const schemas = openapi.components.schemas as unknown as Record<string, Schema>;
const KNOWN = ["ukai-hyp-h01-release15000-combined-v1", "ukai-hyp-h02-release20000-hr-int-v1", "ukai-hyp-h03-release30000-combined-v1", "ukai-2006-historical-combined-v1"];
const ctx = { knownScenarioIds: KNOWN, storedPeaks: [15000, 20000, 30000] };

describe("capabilities: the real example document", () => {
  const c = parseCapabilities(examples.capabilities);
  it("is understood and enables the stored lookup only", () => {
    expect(c.understood).toBe(true);
    expect(c.storedReference.available).toBe(true);
    expect(c.experimentalMl.available).toBe(false);
    expect(c.experimentalMl.reason).toMatch(/intermediate scenario holdout/);
  });
  it("reads the stored peaks, the selection range and the calibration status", () => {
    expect(c.storedPeaks).toEqual([15000, 20000, 30000]);
    expect([c.minPeak, c.maxPeak]).toEqual([15000, 30000]);
    expect(c.validationStatus).toBe("uncalibrated");
  });
  it("does not enable ML even when only the explicit flag is read", () => {
    expect(parseCapabilities({ ...examples.capabilities, experimental_ml_enabled: false }).experimentalMl.available).toBe(false);
  });
});

describe("requests and results against the published schema", () => {
  const reqSchema = schemas.CandidateRequest, resSchema = schemas.CandidateResult;
  it("uses the same request-ID pattern and release bounds", () => {
    expect(ID_PATTERN_SOURCE).toBe(reqSchema.properties.request_id.pattern);
    expect([PEAK_MIN, PEAK_MAX]).toEqual([reqSchema.properties.peak_release_m3s.minimum, reqSchema.properties.peak_release_m3s.maximum]);
    expect(isValidId("-leading-hyphen")).toBe(false);
    expect(isValidId("_leading-underscore")).toBe(false);
    expect(isValidId("ok-id_1")).toBe(true);
  });
  it("sends exactly the fields the schema defines, with its constants", () => {
    const body = buildRequest("abc-123", 20000, false);
    expect(Object.keys(body).sort()).toEqual(Object.keys(reqSchema.properties).sort());
    expect(body.mode).toBe(reqSchema.properties.mode.const);
    expect(body.input_family).toBe(reqSchema.properties.input_family.const);
    expect(body.schema_version).toBe(reqSchema.properties.schema_version.const);
  });
  it("checks every field the schema marks required", () => {
    const sample = examples.examples[0];
    for (const key of resSchema.required) {
      const { [key]: _drop, ...rest } = sample.response as Record<string, unknown>; void _drop;
      expect(validateResult(rest, sample.request as CandidateRequest, ctx)).toEqual([`Missing field: ${key}.`]);
    }
  });
  it("requires every reference resource the schema requires", () => {
    expect([...RESOURCE_KEYS].sort()).toEqual([...schemas.ReferenceResources.required].sort());
  });
});

describe("the four published example calls", () => {
  it("each request is what the adapter would send, and each result is accepted", () => {
    expect(examples.examples.length).toBe(4);
    for (const ex of examples.examples) {
      const req = ex.request as CandidateRequest;
      expect(buildRequest(req.request_id, req.peak_release_m3s, req.allow_nearest_stored)).toEqual(req);
      expect(req.mode).toBe(MODE_STORED); expect(req.input_family).toBe(INPUT_FAMILY);
      expect(validateResult(ex.response, req, ctx)).toEqual([]);
    }
  });
  it("the nearest-stored example: 25,000 requested, 20,000 returned (tie goes to the lower peak)", () => {
    const ex = examples.examples[3];
    expect(ex.request.allow_nearest_stored).toBe(true);
    expect([ex.response.requested_peak_release_m3s, ex.response.actual_peak_release_m3s]).toEqual([25000, 20000]);
  });
  it("rejects the same example if a rule is broken", () => {
    const ex = examples.examples[1], req = ex.request as CandidateRequest;
    expect(validateResult({ ...ex.response, computed: true }, req, ctx).join()).toMatch(/computed: false/);
    expect(validateResult({ ...ex.response, actual_peak_release_m3s: 22000 }, req, ctx).join()).toMatch(/stored reference peaks|exact selection/);
    expect(validateResult({ ...ex.response, reference_resources: { ...ex.response.reference_resources, layers: "/api/v1/prototypes/scenarios/other/layers" } }, req, ctx).join()).toMatch(/does not point into/);
    const { quality_report: _q, ...fewer } = ex.response.reference_resources; void _q;
    expect(validateResult({ ...ex.response, reference_resources: fewer }, req, ctx).join()).toMatch(/quality_report/);
  });
});
