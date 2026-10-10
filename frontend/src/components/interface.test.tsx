import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import TopBar from "./TopBar";
import Sidebar from "./Sidebar";
import Inspector from "./Inspector";
import type { ApiStatus } from "../hooks/useHealth";
import type { ScenarioView } from "../model";

// Presentation-only synthetic fixture, never imported by runtime code.
const reference = {
  id: "ukai-hyp-h02-release20000-hr-int-v1",
  info: { short: "H02", long: "H02 · Hypothetical release", kindLabel: "Hypothetical release" },
  summary: { run_id: "fixture-run-not-real" },
  detail: {
    label: "Uncalibrated simulation", engine: { name: "HEC-RAS", software_version: "fixture" },
    calibration_status: "uncalibrated", validation_status: "not_validated",
    coverage_start: "2026-01-01T00:00:00Z", coverage_end: "2026-01-02T00:00:00Z",
    timing: { coverage_clock_kind: "elapsed_model_time", timezone_convention: "unknown" },
    limitations: ["No observational validation."], unavailable_reasons: { duration_cog: "No duration supplied." },
  },
  impact: { population_exposed: null, buildings_exposed: null, unavailable_reasons: { roads_affected_km: "No exposure inputs." } },
} as unknown as ScenarioView;

describe("light interface boundaries", () => {
  it.each<[ApiStatus, string]>([
    ["checking", "Checking API…"], ["connected", "API connected"], ["unreachable", "API not reachable"],
  ])("keeps truthful %s status without the removed topbar badge", (status, text) => {
    const html = renderToStaticMarkup(<TopBar status={status} title="Explore flood scenarios" />);
    expect(html).toContain(text);
    expect(html).toContain('role="status"');
    expect(html).not.toContain("Uncalibrated simulation");
    expect(html).not.toContain('class="uncal"');
  });
  it.each(["explore", "compare", "whatif", "evidence"] as const)("preserves accessible %s navigation", (section) => {
    const html = renderToStaticMarkup(<Sidebar section={section} onSection={() => {}} scenarios={[reference]} selected={reference.id} onSelect={() => {}} loading={false} />);
    expect(html.match(/aria-current="page"/g)).toHaveLength(1);
    expect(html).toContain('aria-pressed="true"');
    for (const label of ["Explore", "Compare", "What-if", "Evidence", "H02"]) expect(html).toContain(label);
    expect(html).not.toContain('class="side-foot"');
    expect(html).not.toContain("Simulated, uncalibrated prototype. Not scientifically validated.");
  });
  it("retains checking state when catalog is loading", () => {
    expect(renderToStaticMarkup(<Sidebar section="explore" onSection={() => {}} scenarios={[]} selected={undefined} onSelect={() => {}} loading />)).toContain("Loading scenarios…");
  });
  it("keeps scientific status and unavailable data outside the removed header label", () => {
    const html = renderToStaticMarkup(<Inspector s={reference} onEvidence={() => {}} />);
    expect(html).toContain("Uncalibrated simulation");
    expect(html).toContain("not validated");
    expect(html).toContain("No observational validation.");
    expect(html).toContain("No exposure inputs.");
    expect(html).toContain("No duration supplied.");
    expect(html).toContain("Evidence &amp; limitations");
    expect(html).toContain("Run &amp; model details");
    expect(html).toContain("Open full evidence and downloads");
    expect(html).not.toContain("<details open");
  });
});
