import { legendGradientCss, legendTicks, SCALES, type ViewMode } from "../lib/scales";
import { UNREACHED_RGBA, REACHED_NO_VALUE_RGBA, type TimelineColorBy } from "../lib/timeline";

const rgba = (c: readonly number[]) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${c[3]})`;

export default function Legend({ mode, colorBy = "arrival" }: { mode: ViewMode; colorBy?: TimelineColorBy }) {
  if (mode === "timeline") {
    const s = SCALES[colorBy];
    return (
      <div className="legend" aria-label="Legend">
        <div className="legend-title">{s.title} ({s.unit}) {colorBy === "arrival" ? "" : "· maximum over the run"}</div>
        <div className="legend-bar" style={{ background: legendGradientCss(colorBy) }} />
        <div className="legend-ticks">{legendTicks(colorBy).map((t) => <span key={t.value} style={{ left: `${t.pct}%` }}>{t.value}</span>)}</div>
        <div className="legend-state"><span className="swatch-box" style={{ background: rgba(UNREACHED_RGBA) }} /> Valid arrival, not yet reached</div>
        {colorBy !== "arrival" && <div className="legend-state"><span className="swatch-box" style={{ background: rgba(REACHED_NO_VALUE_RGBA) }} /> Reached, value not available</div>}
        <div className="legend-note">Transparent = no valid arrival time (no data).</div>
      </div>
    );
  }
  if (mode === "extent") {
    return (
      <div className="legend" aria-label="Legend">
        <div className="legend-title">Flood extent</div>
        <div className="legend-swatch"><span className="swatch" /> Simulated area where depth &gt; 0.1 m</div>
        <div className="legend-note">Outline of the simulated extent. Outside the outline is not a statement of safety.</div>
      </div>
    );
  }
  const s = SCALES[mode];
  return (
    <div className="legend" aria-label="Legend">
      <div className="legend-title">{s.title} ({s.unit})</div>
      <div className="legend-bar" style={{ background: legendGradientCss(mode) }} />
      <div className="legend-ticks">
        {legendTicks(mode).map((t) => <span key={t.value} style={{ left: `${t.pct}%` }}>{t.value}</span>)}
      </div>
      <div className="legend-note">{s.note} Transparent = no data / not flooded in this result.</div>
    </div>
  );
}
