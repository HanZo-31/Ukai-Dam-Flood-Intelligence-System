import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ExploreLayers, { type ExploreLayersProps } from "./ExploreLayers";
import ExploreScenario from "./ExploreScenario";
import ExploreTimeline, { type ExploreTimelineProps } from "./ExploreTimeline";
import TopBar from "./TopBar";
import type { ScenarioView } from "../model";

// Clearly synthetic presentation fixture. It is never served by the app.
const s = {
  id: "fixture-h02", info: { short: "H02", long: "Fixture H02", kindLabel: "Hypothetical release" },
  summary: { run_id: "fixture-run" },
  detail: { label: "Uncalibrated prototype", engine: { name: "HEC-RAS", software_version: "fixture" },
    parameters: { peak_release_m3s: 20000 }, parameter_units: {}, calibration_status: "uncalibrated", validation_status: "pending",
    coverage_start: "2026-01-01T00:00:00Z", coverage_end: "2026-01-02T00:00:00Z",
    timing: { coverage_clock_kind: "model_clock", timezone_convention: "unknown" }, arrival: { temporal_resolution_minutes: 60 },
    limitations: ["Synthetic fixture, no scientific approval"], unavailable_reasons: {} },
  impact: { population_exposed: null, buildings_exposed: null, roads_affected_km: null, critical_facilities_exposed: null,
    max_depth_m: 2.3, flooded_area_km2: 5.4, unavailable_reasons: {} },
} as unknown as ScenarioView;
const layers: ExploreLayersProps = { mode: "depth", colorBy: "arrival", opacity: .85, timelineAvailable: true,
  onRaster: () => {}, onTimeline: () => {}, onExtent: () => {}, onOpacity: () => {}, onFit: () => {} };
const timeline: ExploreTimelineProps = { enabled: false, hours: 0, maxHours: 114, playing: false, colorBy: "arrival",
  onHours: () => {}, onPlaying: () => {}, onColorBy: () => {}, onReset: () => {}, onEnable: () => {} };

describe("reference image studio presentation", () => {
  it.each(["depth", "arrival", "velocity"] as const)("retains the %s layer and all existing operations", (mode) => {
    const html = renderToStaticMarkup(<ExploreLayers {...layers} mode={mode} />);
    const selectedInput = html.match(new RegExp(`<input[^>]*value="${mode}"[^>]*>`))?.[0];
    expect(selectedInput).toContain('checked=""');
    for (const text of ["Depth (m)", "Arrival time (h)", "Velocity (m/s)", "Extent outline", "Layer opacity", "Fit to flood area", "Reveal by arrival time"]) expect(html).toContain(text);
  });
  it("distinguishes full-run arrival from arrival reveal", () => {
    const full = renderToStaticMarkup(<ExploreLayers {...layers} mode="arrival" />);
    const reveal = renderToStaticMarkup(<ExploreLayers {...layers} mode="timeline" colorBy="velocity" />);
    expect(full).not.toContain('type="checkbox" checked=""');
    expect(reveal).toContain('type="checkbox" checked=""');
    expect(reveal.match(/<input[^>]*value="velocity"[^>]*>/)?.[0]).toContain('checked=""');
  });
  it("keeps outline selection accessible without selecting a raster", () => {
    const html = renderToStaticMarkup(<ExploreLayers {...layers} mode="extent" />);
    expect(html).toContain('aria-pressed="true"');
    expect(html).not.toContain(' checked=""');
  });
  it("disables reveal when the real window is unavailable", () => {
    expect(renderToStaticMarkup(<ExploreLayers {...layers} timelineAvailable={false} />)).toContain('disabled=""');
    expect(renderToStaticMarkup(<ExploreTimeline {...timeline} maxHours={null} />)).toContain('disabled=""');
  });
  it("uses actual duration rather than the illustration's fixed 138 hours", () => {
    const html = renderToStaticMarkup(<ExploreTimeline {...timeline} />);
    expect(html).toContain("114 h model window");
    expect(html).not.toContain("138");
    expect(html).not.toContain('type="range"');
  });
  it("retains the original timeline component and minute conversion display", () => {
    const html = renderToStaticMarkup(<ExploreTimeline {...timeline} enabled hours={48} />);
    expect(html).toContain('value="48"');
    expect(html).toContain("2880 min since simulation start");
    for (const text of ["Play", "Reset", "Maximum depth (revealed by arrival)", "Maximum velocity (revealed by arrival)"]) expect(html).toContain(text);
    expect(html).toContain('max="114"');
  });
  it("does not present elapsed time as active on a full-run layer", () => {
    const html = renderToStaticMarkup(<ExploreScenario s={s} mode="depth" hours={48} onEvidence={() => {}} />);
    expect(html).toContain("Full-run result");
    expect(html).not.toContain("48 h");
  });
  it("shows actual elapsed time, real peak, unknown exposure and retained metadata", () => {
    const html = renderToStaticMarkup(<ExploreScenario s={s} mode="timeline" hours={48} onEvidence={() => {}} />);
    for (const text of ["48 h", "20,000", "Unavailable", "Hypothetical release", "HEC-RAS", "Uncalibrated prototype", "pending", "Stored metrics &amp; run details", "Synthetic fixture"]) expect(html).toContain(text);
  });
  it("does not claim exposure unavailable if an actual exposure metric exists", () => {
    const actual = { ...s, impact: { ...s.impact, population_exposed: 0 } };
    expect(renderToStaticMarkup(<ExploreScenario s={actual} mode="depth" hours={0} onEvidence={() => {}} />)).toContain("See exposure evidence");
  });
  it("adds a truthful reference subtitle without restoring the removed badge", () => {
    const html = renderToStaticMarkup(<TopBar status="connected" title="Explore scenarios" subtitle="Visualise the four stored flood reference simulations." />);
    expect(html).toContain("stored flood reference simulations");
    expect(html).toContain("API connected");
    expect(html).not.toContain("Uncalibrated simulation");
    expect(html).not.toContain("experimental numerical solver");
  });
});
