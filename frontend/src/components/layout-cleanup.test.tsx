import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ExploreLayers, { type ExploreLayersProps } from "./ExploreLayers";
import ExploreTimeline, { type ExploreTimelineProps } from "./ExploreTimeline";
import TimelinePanel from "./TimelinePanel";

const layers: ExploreLayersProps = { mode: "arrival", colorBy: "arrival", opacity: .85,
  timelineAvailable: true, onRaster: () => {}, onTimeline: () => {}, onExtent: () => {},
  onOpacity: () => {}, onFit: () => {} };
const timeline: ExploreTimelineProps = { enabled: true, hours: 48, maxHours: 114,
  playing: false, colorBy: "arrival", onHours: () => {}, onPlaying: () => {},
  onColorBy: () => {}, onReset: () => {}, onEnable: () => {} };

describe("V05 less cluttered presentation", () => {
  it("keeps all three primary layer choices outside closed secondary settings", () => {
    const html = renderToStaticMarkup(<ExploreLayers {...layers} />);
    const primary = html.slice(0, html.indexOf('<details'));
    expect(primary.match(/type="radio"/g)).toHaveLength(3);
    expect(html).toContain('<summary>More controls</summary>');
    expect(html.match(/<details[^>]*>/)?.[0]).not.toContain('open=');
  });
  it("preserves secondary controls with their native accessibility and actual values", () => {
    const html = renderToStaticMarkup(<ExploreLayers {...layers} mode="timeline" />);
    const secondary = html.slice(html.indexOf('<details'), html.indexOf('</details>'));
    for (const label of ["Reveal by arrival time", "Extent outline", "Layer opacity"])
      expect(secondary).toContain(label);
    expect(secondary).toContain('type="checkbox" checked=""');
    expect(secondary).toContain('aria-label="Layer opacity"');
    expect(secondary).toContain('value="0.85"');
    expect(html).toContain('aria-label="Fit to flood area"');
  });
  it("keeps the original active clock and puts only explanatory controls in a closed disclosure", () => {
    const html = renderToStaticMarkup(<ExploreTimeline {...timeline} />);
    expect(html).toContain('timeline-compact');
    expect(html).toContain('max="114"');
    expect(html).toContain('value="48"');
    expect(html).toContain('2880 min since simulation start');
    expect(html).toContain('<summary>Timeline details</summary>');
    expect(html.match(/<details[^>]*>/)?.[0]).not.toContain('open=');
    expect(html.indexOf('aria-label="Elapsed model time in hours"')).toBeLessThan(html.indexOf('<details'));
    expect(html).toContain('Maximum velocity (revealed by arrival)');
  });
  it("does not hide the maximum-over-run caveat in collapsed timeline details", () => {
    const html = renderToStaticMarkup(<ExploreTimeline {...timeline} colorBy="depth" />);
    expect(html.slice(html.indexOf('</details>'))).toContain('They are not changing water levels and do not show recession.');
  });
  it("does not invent an active clock for full-run results", () => {
    const html = renderToStaticMarkup(<ExploreTimeline {...timeline} enabled={false} />);
    expect(html).toContain('Enable arrival reveal');
    expect(html).not.toContain('type="range"');
    expect(html).not.toContain('2880');
  });
  it("preserves the original non-compact timeline presentation for other consumers", () => {
    const html = renderToStaticMarkup(<TimelinePanel {...timeline} />);
    expect(html).not.toContain('timeline-compact');
    expect(html).not.toContain('Timeline details');
    expect(html).toContain('Area reached by elapsed model time');
    expect(html).toContain('Colour by');
  });
  it("preserves the unavailable-window state rather than showing a fake slider", () => {
    const html = renderToStaticMarkup(<ExploreTimeline {...timeline} maxHours={null} />);
    expect(html).toContain('role="status"');
    expect(html).toContain('not declared');
    expect(html).not.toContain('type="range"');
  });
});
