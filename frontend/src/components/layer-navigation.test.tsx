import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ExploreLayers, { type ExploreLayersProps } from "./ExploreLayers";
import Legend from "./Legend";
import { legendGradientCss, legendTicks } from "../lib/scales";

const props: ExploreLayersProps = { mode: "depth", colorBy: "arrival", opacity: .85,
  timelineAvailable: true, onRaster: () => {}, onTimeline: () => {}, onExtent: () => {},
  onOpacity: () => {}, onFit: () => {} };

describe("V05 horizontal layer navigation and external page scale", () => {
  it("replaces the floating layer card with a navbar containing exactly three native choices", () => {
    const html = renderToStaticMarkup(<ExploreLayers {...props} />);
    expect(html).toContain('class="layer-navbar"');
    expect(html).not.toContain('floating-layers');
    expect(html.match(/type="radio"/g)).toHaveLength(3);
    for (const label of ["Depth (m)", "Arrival time (h)", "Velocity (m/s)"]) expect(html).toContain(label);
  });
  it("keeps fit and secondary controls without a floating map button", () => {
    const html = renderToStaticMarkup(<ExploreLayers {...props} />);
    expect(html).toContain('class="layer-fit"');
    expect(html).not.toContain('class="studio-fit"');
    for (const label of ["More controls", "Extent outline", "Layer opacity", "Reveal by arrival time", "Fit to flood area"]) expect(html).toContain(label);
  });
  it.each(["depth", "arrival", "velocity"] as const)("retains the original %s gradient/ticks when placed in the page corner", (mode) => {
    const html = renderToStaticMarkup(<aside className="page-legend-corner"><Legend mode={mode} /></aside>);
    expect(html).toContain(legendGradientCss(mode));
    for (const tick of legendTicks(mode)) expect(html).toContain(`>${tick.value}</span>`);
    expect(html).toContain('aria-label="Legend"');
  });
  it("retains reached/unknown states and maximum-over-run meaning in the external legend", () => {
    const html = renderToStaticMarkup(<aside className="page-legend-corner"><Legend mode="timeline" colorBy="depth" /></aside>);
    for (const text of ["maximum over the run", "Valid arrival, not yet reached", "Reached, value not available", "Transparent = no valid arrival time"]) expect(html).toContain(text);
  });
});
