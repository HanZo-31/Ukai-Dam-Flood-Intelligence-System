import { expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import Sidebar from "../components/Sidebar";
import TopBar from "../components/TopBar";
import { supportsRaster } from "./rendering";
import { buildComparisonBriefing } from "./briefing";
import { compareGrids, type Grid } from "./compare";
import { computeZones } from "./zones";
import type { ScenarioView } from "../model";
import type { PrototypeLayers } from "./api";

const grid = (d: number[], a: number[]): Grid => ({ width: 2, height: 1, geo: { originX: 0, originY: 30, pixelWidth: 30, pixelHeight: 30 }, depth: Float32Array.from(d), arrival: Float32Array.from(a) });
const b = grid([1, -9999], [180, -9999]), c = grid([2, 1], [120, -9999]);
const diff = compareGrids(b, c);
if (typeof diff === "string") throw new Error(diff);
const source = (id: string): ScenarioView => ({ id, info: { id, short: id, long: id, kindLabel: "Hypothetical release", historical: false },
  detail: { run_id: `${id}-run`, engine: { name: "HEC-RAS", software_version: "7.0.1" }, parameters: { peak_release_m3s: null }, provenance: { source_manifest_checksum: "sha256:original" }, limitations: ["Uncalibrated"] } } as ScenarioView);
const layers = (id: string): PrototypeLayers => ({ scenario_id: id, run_id: `${id}-run`, layers: [{ asset_type: "max_depth_cog", checksum: "sha256:asset", crs: "EPSG:32643", unit: "m" }] } as PrototypeLayers);
const note = () => buildComparisonBriefing(source("H01"), source("H02"), layers("H01"), layers("H02"), diff, null, "2026-10-09T00:00:00+05:30");

it("detects no WebGL without interpreting an empty context as success", () => {
  expect(supportsRaster(() => ({ getContext: () => null }))).toBe(false);
});
it("handles thrown context creation and falls back to WebGL1", () => {
  expect(supportsRaster(() => { throw Error("Unavailable"); })).toBe(false);
  const factory = (() => ({ getContext: (name: string) => name === "webgl" ? {} : null })) as unknown as () => HTMLCanvasElement;
  expect(supportsRaster(factory)).toBe(true);
});
it("manual fallback skips the context probe, without changing model capabilities", () => {
  expect(supportsRaster(() => { throw Error("Must not probe"); }, "?raster=off")).toBe(false);
});
it("releases the probe context when available", () => {
  let lost = false;
  const factory = (() => ({ getContext: () => ({ getExtension: () => ({ loseContext: () => { lost = true; } }) }) })) as unknown as () => HTMLCanvasElement;
  expect(supportsRaster(factory)).toBe(true); expect(lost).toBe(true);
});
it("briefing preserves identities, checksums, signed direction and denominators", () => {
  const text = note();
  expect(text).toContain('Scenario ID: "H01"'); expect(text).toContain('Run ID: "H02-run"');
  expect(text).toContain("sha256:asset"); expect(text).toContain("-1.00 h (1 both-valid arrival cells)");
  expect(text).toContain("1 candidate-only valid cells"); expect(text).toContain("Nodata is unknown");
});
it("briefing keeps missing measurements unavailable, never NaN or fabricated zero exposure", () => {
  expect(note()).toContain("Peak release: Not available"); expect(note()).toContain("not assessed; unavailable, not zero");
  expect(note()).not.toMatch(/NaN|undefined/);
  const empty = compareGrids(grid([-9999, -9999], [-9999, -9999]), grid([-9999, -9999], [-9999, -9999]));
  if (typeof empty === "string") throw Error(empty);
  expect(buildComparisonBriefing(source("H01"), source("H02"), layers("H01"), layers("H02"), empty, null, "now")).toContain("Paired arrival median signed change: Not available");
});
it("briefing rejects a stale scenario or run identity", () => {
  expect(() => buildComparisonBriefing(source("H03"), source("H02"), layers("H01"), layers("H02"), diff, null, "now")).toThrow(/identities/);
  expect(() => buildComparisonBriefing(source("H01"), source("H02"), { ...layers("H01"), run_id: "other" }, layers("H02"), diff, null, "now")).toThrow(/identities/);
});
it("same-scenario briefing reports zero changed wet footprint and zones reconcile", () => {
  const same = compareGrids(b, b), zones = computeZones(b, b);
  if (typeof same === "string" || typeof zones === "string") throw Error("Invalid fixture");
  expect(buildComparisonBriefing(source("H01"), source("H01"), layers("H01"), layers("H01"), same, zones, "now")).toContain("0 of");
  expect(same.km2.newWet).toBe(0); expect(zones.totals.newWetKm2).toBe(0);
});
it("navigation contains only the four product sections, with no review guide", () => {
  const html = renderToStaticMarkup(createElement(Sidebar, { section: "explore", onSection: () => {}, scenarios: [], selected: undefined, onSelect: () => {}, loading: false }));
  expect((html.match(/<button/g) ?? []).length).toBe(4);
  expect(html).not.toContain("Review guide"); expect(html).toContain("Evidence");
});
it("top bar provides one page-level heading and an announced backend state", () => {
  const html = renderToStaticMarkup(createElement(TopBar, { status: "unreachable", title: "Explore" }));
  expect(html).toContain("<h1"); expect(html).toContain('role="status"'); expect(html).toContain("API not reachable");
});
