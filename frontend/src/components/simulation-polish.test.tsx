import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import TopBar from "./TopBar";
import PointInspector from "./PointInspector";
import type { ScenarioView } from "../model";

// Synthetic presentation fixture; no runtime data or scientific approval.
const scenario = { info: { short: "H02" }, detail: { engine: { name: "HEC-RAS", software_version: "fixture" } } } as ScenarioView;
const noop = () => {};

describe("Simulation interface polish", () => {
  it("labels the connected backend as local without implying model validation", () => {
    const html = renderToStaticMarkup(<TopBar status="connected" title="Explore scenarios" />);
    expect(html).toContain("Local API connected");
    expect(html).toContain("not a scientific validation status");
    expect(html).toContain('role="status"');
    expect(html).not.toContain("Uncalibrated simulation");
  });
  it.each(["checking", "unreachable"] as const)("retains truthful %s status", status => {
    const html = renderToStaticMarkup(<TopBar status={status} title="Explore scenarios" />);
    expect(html).not.toContain("Local API connected");
    expect(html).toContain(status === "checking" ? "Checking API" : "API not reachable");
  });
  it("describes one map in Explore rather than two", () => {
    const html = renderToStaticMarkup(<PointInspector selection={null} scenarios={[{ scenario, layers: undefined }]} onSelect={noop} onClear={noop} />);
    expect(html).toContain("Click the map");
    expect(html).not.toContain("Click either map");
    expect(html).toContain("press Enter");
  });
  it("keeps both maps selectable in Compare", () => {
    const html = renderToStaticMarkup(<PointInspector selection={null} scenarios={[{ scenario, layers: undefined }, { scenario, layers: undefined }]} onSelect={noop} onClear={noop} />);
    expect(html).toContain("Click either map");
    expect(html).toContain("No location selected");
    expect(html).not.toContain("0.00");
  });
});
