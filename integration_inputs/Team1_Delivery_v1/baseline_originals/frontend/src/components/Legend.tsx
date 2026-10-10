import { legendGradientCss, legendTicks, SCALES, type ViewMode } from "../lib/scales";

export default function Legend({ mode }: { mode: ViewMode }) {
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
