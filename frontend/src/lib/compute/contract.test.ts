// Contract 2.0.0 validators against the packet's SYNTHETIC examples and hand-made mutations. Expected outcomes are written by hand from
// contract/compute-v2.schema.json and SHARED_SCOPE_AND_CONTRACT.md, not derived from the production code.
import { describe, expect, it } from "vitest";
import examples from "../../testing/fixtures_v2/examples.json";
import {
  arrivalComparisonBlock, assetPath, buildComputeRequest, hourlyCeilingMinutes, parseCapabilitiesV2, referenceArrivalBlock, resultPath, validateJob, validatePeak, validateResult,
  type RequestV2,
} from "./contract";

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const req = examples.request as RequestV2;
const JOB = "synthetic-job-001";
const ex = { request: req, jobId: JOB };
const mut = (base: unknown, f: (o: Record<string, any>) => void) => { const o = clone(base) as Record<string, any>; f(o); return o; };
const bad = (p: string[], re: RegExp) => expect(p.join(" | ")).toMatch(re);

describe("capabilities 2.0.0", () => {
  it("accepts the enabled and disabled packet examples", () => {
    const e = parseCapabilitiesV2(examples.capabilities_enabled), d = parseCapabilitiesV2(examples.capabilities_disabled);
    expect(e.ok).toBe(true);
    expect(d.ok).toBe(true);
    if (d.ok) { expect(d.caps.enabled).toBe(false); expect(d.caps.configuration_id).toBeNull(); }
  });
  it("rejects anything that is not a complete, strictly typed document", () => {
    const base = examples.capabilities_enabled;
    for (const [name, doc, re] of [
      ["not an object", [], /not an object/],
      ["wrong version", mut(base, (o) => { o.schema_version = "1.0.0"; }), /Unsupported contract version/],
      ["unknown version 3", mut(base, (o) => { o.schema_version = "3.0.0"; }), /Unsupported contract version/],
      ["extra field", mut(base, (o) => { o.surprise = 1; }), /unknown field/],
      ["missing field", mut(base, (o) => { delete o.available_roles; }), /missing/],
      ["string flag", mut(base, (o) => { o.enabled = "true"; }), /true or false/],
      ["enabled without config id", mut(base, (o) => { o.configuration_id = null; }), /verified configuration/],
      ["enabled without checksum", mut(base, (o) => { o.configuration_checksum = null; }), /verified configuration/],
      ["enabled with reason", mut(base, (o) => { o.reason = "x"; }), /must not carry a disabling reason/],
      ["bad checksum", mut(base, (o) => { o.configuration_checksum = "sha256:abc"; }), /checksum/],
      ["bad id", mut(base, (o) => { o.configuration_id = "UPPER"; }), /configuration ID/],
      ["peak range changed", mut(base, (o) => { o.peak_range_m3s = [10000, 30000]; }), /peak range/],
      ["validated true", mut(base, (o) => { o.scientifically_validated = true; }), /scientifically_validated/],
      ["unknown role", mut(base, (o) => { o.available_roles = ["max_depth_cog", "wse"]; }), /roles/],
      ["duplicate roles", mut(base, (o) => { o.available_roles = ["max_depth_cog", "max_depth_cog", "extent_geojson"]; }), /roles/],
      ["enabled without required roles", mut(base, (o) => { o.available_roles = ["arrival_time_cog"]; }), /maximum-depth raster and the extent/],
      ["disabled without reason", mut(examples.capabilities_disabled, (o) => { o.reason = null; }), /say why/],
      ["disabled with blank reason", mut(examples.capabilities_disabled, (o) => { o.reason = "  "; }), /reason/],
    ] as [string, unknown, RegExp][]) {
      const r = parseCapabilitiesV2(doc);
      expect(r.ok).toBe(false);
      if (!r.ok) bad(r.problems, re);
      void name;
    }
  });
});

describe("request building", () => {
  const caps = { configuration_id: examples.request.configuration_id, configuration_checksum: examples.request.configuration_checksum };
  it("sends exactly the contract fields with the advertised configuration", () => {
    const r = buildComputeRequest("abc-123", 25000, caps);
    expect(r).toEqual({ schema_version: "2.0.0", input_family: "ukai-hyp-fixed-shape-v1", configuration_id: "synthetic-config-v01", configuration_checksum: examples.request.configuration_checksum, request_id: "abc-123", peak_release_m3s: 25000 });
    expect(Object.keys(r as object).sort()).toEqual(["configuration_checksum", "configuration_id", "input_family", "peak_release_m3s", "request_id", "schema_version"]);
  });
  it("blocks out-of-range and non-finite peaks (15,000 and 30,000 inclusive)", () => {
    expect(validatePeak(15000)).toBeNull();
    expect(validatePeak(30000)).toBeNull();
    expect(validatePeak(25000.5)).toBeNull();
    for (const v of [14999.999, 30000.001, 0, -1, Number.NaN, Infinity, -Infinity, "25000", null, undefined]) expect(typeof validatePeak(v)).toBe("string");
  });
  it("refuses to build a request without a verified configuration or with a bad id", () => {
    expect(typeof buildComputeRequest("abc-123", 25000, { configuration_id: null, configuration_checksum: null })).toBe("string");
    expect(typeof buildComputeRequest("abc-123", 25000, { configuration_id: "synthetic-config-v01", configuration_checksum: "sha256:short" })).toBe("string");
    expect(typeof buildComputeRequest("A", 25000, caps)).toBe("string");
    expect(typeof buildComputeRequest("-abc", 25000, caps)).toBe("string");
    expect(typeof buildComputeRequest("abc-123", 12000, caps)).toBe("string");
  });
});

describe("job states", () => {
  const jobs = examples.jobs;
  it("accepts the four packet job states for the packet request", () => {
    expect(jobs.map((j) => j.status)).toEqual(["queued", "running", "completed", "failed"]);
    for (const j of jobs) expect(validateJob(j, ex)).toEqual([]);
  });
  it("rejects identity, URL, error and time inconsistencies", () => {
    const [queued, , completed, failed] = jobs;
    for (const [doc, re] of [
      [mut(queued, (o) => { o.result_url = resultPath(JOB); }), /Only a completed job/],
      [mut(completed, (o) => { o.result_url = null; }), /own result/],
      [mut(completed, (o) => { o.result_url = resultPath("synthetic-job-other"); }), /own result/],
      [mut(completed, (o) => { o.result_url = `http://127.0.0.1${resultPath(JOB)}`; }), /own result/],
      [mut(completed, (o) => { o.result_url = `${resultPath(JOB)}?x=1`; }), /own result/],
      [mut(completed, (o) => { o.error = { code: "interrupted", message: "x" }; }), /must not carry an error/],
      [mut(failed, (o) => { o.error = null; }), /safe error/],
      [mut(failed, (o) => { o.error = { code: "interrupted" }; }), /safe error/],
      [mut(failed, (o) => { o.error = { code: "interrupted", message: "x", path: "C:\\private" }; }), /safe error/],
      [mut(queued, (o) => { o.error = { code: "interrupted", message: "x" }; }), /Only a failed job/],
      [mut(queued, (o) => { o.status = "paused"; }), /Unknown job status/],
      [mut(queued, (o) => { o.created_at = "2026-10-09T06:00:00"; }), /offset/],
      [mut(queued, (o) => { o.updated_at = "yesterday"; }), /offset/],
      [mut(queued, (o) => { o.elapsed_wall_seconds = -1; }), /non-negative/],
      [mut(queued, (o) => { o.cache_hit = "no"; }), /true or false/],
      [mut(queued, (o) => { o.configuration_id = "synthetic-config-other"; }), /configuration ID/],
      [mut(queued, (o) => { o.configuration_checksum = "sha256:" + "0".repeat(64); }), /configuration checksum/],
      [mut(queued, (o) => { o.request_id = "someone-else"; }), /different request/],
      [mut(queued, (o) => { o.requested_peak_release_m3s = 20000; }), /requested peak/],
      [mut(queued, (o) => { o.job_id = "../x"; }), /job ID/],
      [mut(queued, (o) => { o.schema_version = "1.0.0"; }), /contract version/],
      [mut(queued, (o) => { o.extra = 1; }), /unknown field/],
    ] as [unknown, RegExp][]) bad(validateJob(doc, ex), re);
  });
  it("detects a job id that changes between polls", () => {
    bad(validateJob(jobs[1], { request: req, jobId: "synthetic-job-002" }), /changed between responses/);
  });
});

describe("result", () => {
  const R = examples.result;
  const rex = { request: req, jobId: JOB };
  it("accepts the packet result (a SYNTHETIC fixture shaped like a result)", () => { expect(validateResult(R, rex)).toEqual([]); });
  it("rejects every identity or semantic mismatch before assets are touched", () => {
    for (const [doc, re] of [
      [mut(R, (o) => { o.job_id = "synthetic-job-002"; }), /different job/],
      [mut(R, (o) => { o.request_id = "other-request"; }), /different request/],
      [mut(R, (o) => { o.configuration_id = "synthetic-config-v02"; }), /configuration ID/],
      [mut(R, (o) => { o.configuration_checksum = "sha256:" + "a".repeat(64); }), /configuration checksum/],
      [mut(R, (o) => { o.actual_peak_release_m3s = 20000; }), /actual peak differs/],
      [mut(R, (o) => { o.requested_peak_release_m3s = 20000; }), /requested peak/],
      [mut(R, (o) => { o.computed = false; }), /computed: true/],
      [mut(R, (o) => { o.engine = "HEC-RAS stored reference"; }), /experimental fast solver/],
      [mut(R, (o) => { o.scientifically_validated = true; }), /scientifically_validated/],
      [mut(R, (o) => { o.calibration_status = "calibrated"; }), /uncalibrated/],
      [mut(R, (o) => { o.limitations = []; }), /Limitations/],
      [mut(R, (o) => { o.input_checksums = {}; }), /input checksums/],
      [mut(R, (o) => { o.native_results_checksum = "sha256:zz"; }), /checksum is malformed/],
      [mut(R, (o) => { o.timings.scope = "browser_ready"; }), /timing scope/],
      [mut(R, (o) => { o.timings.solver_seconds = -1; }), /solver_seconds/],
      [mut(R, (o) => { delete o.timings.prepare_seconds; }), /Timings is missing/],
      [mut(R, (o) => { o.surprise = true; }), /unknown field/],
      [mut(R, (o) => { o.derived_grid.crs = "EPSG:4326"; }), /EPSG:32643/],
      [mut(R, (o) => { o.derived_grid.nodata = 0; }), /nodata must be -9999/],
      [mut(R, (o) => { o.derived_grid.mapping = "bilinear"; }), /nearest-neighbour/],
      [mut(R, (o) => { o.derived_grid.transform = [100, 0, 270000, 0, 100, 2360000]; }), /north-up/],
      [mut(R, (o) => { o.derived_grid.width = 0; }), /size is invalid/],
      [mut(R, (o) => { o.arrival_definition.threshold_m = 0.2; }), /threshold/],
      [mut(R, (o) => { o.arrival_definition.origin = "calendar"; }), /origin/],
      [mut(R, (o) => { o.arrival_definition.native_unit = "h"; }), /native arrival unit/],
      [mut(R, (o) => { o.arrival_definition.comparison_transform = "round(x)"; }), /hourly ceiling/],
      [mut(R, (o) => { o.arrival_definition.definition_compatible = false; }), /say why/],
      [mut(R, (o) => { o.assets.max_depth_cog.url = assetPath("synthetic-job-other", "max_depth_cog"); }), /own asset path/],
      [mut(R, (o) => { o.assets.max_depth_cog.url = "https://example.invalid/x.tif"; }), /own asset path/],
      [mut(R, (o) => { o.assets.max_depth_cog.url += "?token=1"; }), /own asset path/],
      [mut(R, (o) => { o.assets.max_depth_cog.url = assetPath(JOB, "max_depth_cog") + "/../arrival_time_cog"; }), /own asset path/],
      [mut(R, (o) => { o.assets.arrival_time_cog.url = assetPath(JOB, "max_depth_cog"); }), /own asset path/],
      [mut(R, (o) => { o.assets.max_depth_cog.sha256 = "sha256:short"; }), /malformed checksum/],
      [mut(R, (o) => { o.assets.max_depth_cog.bytes = 0; }), /byte count/],
      [mut(R, (o) => { o.assets.max_depth_cog.unit = "ft"; }), /unit/],
      [mut(R, (o) => { o.assets.arrival_time_cog.unit = "h"; }), /unit/],
      [mut(R, (o) => { o.assets.max_depth_cog = null; }), /required product/],
      [mut(R, (o) => { o.assets.extent_geojson = null; o.unavailable_reasons.extent_geojson = "x"; }), /required product/],
      [mut(R, (o) => { o.unavailable_reasons.max_velocity_cog = null; }), /no stated reason/],
      [mut(R, (o) => { o.unavailable_reasons.max_depth_cog = "also unavailable"; }), /present but also has an unavailable reason/],
      [mut(R, (o) => { o.assets.max_velocity_cog = { url: assetPath(JOB, "max_velocity_cog"), sha256: "sha256:" + "1".repeat(64), bytes: 5, unit: "m/s" }; o.unavailable_reasons.max_velocity_cog = null; }), /velocity definition/],
    ] as [unknown, RegExp][]) bad(validateResult(doc, rex), re);
  });
  it("accepts a velocity product only together with a verbatim definition", () => {
    const ok = mut(R, (o) => {
      o.assets.max_velocity_cog = { url: assetPath(JOB, "max_velocity_cog"), sha256: "sha256:" + "1".repeat(64), bytes: 5, unit: "m/s" };
      o.unavailable_reasons.max_velocity_cog = null; o.velocity_definition = "face-normal component at cell faces, not speed magnitude";
    });
    expect(validateResult(ok, rex)).toEqual([]);
  });
  it("allows optional products to be absent only with a reason, and arrival to lack a definition (comparison then blocked)", () => {
    const noArrival = mut(R, (o) => { o.assets.arrival_time_cog = null; o.unavailable_reasons.arrival_time_cog = "Native arrival unsupported."; o.arrival_definition = null; });
    expect(validateResult(noArrival, rex)).toEqual([]);
    expect(arrivalComparisonBlock(noArrival as never)).toMatch(/no arrival-time product/);
    const noDef = mut(R, (o) => { o.arrival_definition = null; });
    expect(validateResult(noDef, rex)).toEqual([]);
    expect(arrivalComparisonBlock(noDef as never)).toMatch(/did not declare/);
    const incompatible = mut(R, (o) => { o.arrival_definition.definition_compatible = false; o.arrival_definition.unavailable_reason = "Native threshold differs."; });
    expect(validateResult(incompatible, rex)).toEqual([]);
    expect(arrivalComparisonBlock(incompatible as never)).toBe("Native threshold differs.");
    expect(arrivalComparisonBlock(R as never)).toBeNull();
  });
});

describe("arrival definitions and the single hour conversion", () => {
  it("hourly ceiling: native seconds -> minutes exactly once (hand-calculated)", () => {
    expect(hourlyCeilingMinutes(0)).toBe(0);
    expect(hourlyCeilingMinutes(1)).toBe(60);
    expect(hourlyCeilingMinutes(3599)).toBe(60);
    expect(hourlyCeilingMinutes(3600)).toBe(60);
    expect(hourlyCeilingMinutes(3601)).toBe(120);
    expect(hourlyCeilingMinutes(7200)).toBe(120);
    expect(hourlyCeilingMinutes(10 * 3600 + 1)).toBe(660);
  });
  it("reference arrival must be minutes, 0.1 m, hourly, from simulation start", () => {
    const ok = { unit: "min", origin: "simulation_start", threshold_m: 0.1, temporal_resolution_minutes: 60 };
    expect(referenceArrivalBlock(ok)).toBeNull();
    expect(referenceArrivalBlock(null)).toMatch(/does not declare/);
    expect(referenceArrivalBlock({ ...ok, unit: "h" })).toMatch(/minutes/);
    expect(referenceArrivalBlock({ ...ok, threshold_m: 0.3 })).toMatch(/threshold/);
    expect(referenceArrivalBlock({ ...ok, temporal_resolution_minutes: 15 })).toMatch(/hourly/);
    expect(referenceArrivalBlock({ ...ok, origin: "event_time" })).toMatch(/origin/);
  });
});
