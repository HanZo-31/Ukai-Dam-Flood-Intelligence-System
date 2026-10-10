import { Crosshair, Layers3 } from "lucide-react";
import type { RasterMode, ViewMode } from "../lib/scales";
import type { TimelineColorBy } from "../lib/timeline";

const OPTIONS: { id: RasterMode; label: string }[] = [
  { id: "depth", label: "Depth (m)" },
  { id: "arrival", label: "Arrival time (h)" },
  { id: "velocity", label: "Velocity (m/s)" },
];

export interface ExploreLayersProps {
  mode: ViewMode;
  colorBy: TimelineColorBy;
  opacity: number;
  timelineAvailable: boolean;
  onRaster: (mode: RasterMode) => void;
  onTimeline: (enabled: boolean) => void;
  onExtent: () => void;
  onOpacity: (opacity: number) => void;
  onFit: () => void;
}

export default function ExploreLayers(p: ExploreLayersProps) {
  const active = p.mode === "timeline" ? p.colorBy : p.mode;
  return <>
    <section className="layer-navbar" aria-label="Map layer controls">
      <h2 className="sr-only"><Layers3 size={21} aria-hidden /> Layers</h2>
      <fieldset>
        <legend className="sr-only">Map layer</legend>
        {OPTIONS.map(({ id, label }) => (
          <label className="layer-choice" key={id}>
            <input type="radio" name="explore-layer" value={id} checked={active === id} onChange={() => p.onRaster(id)} />
            <span>{label}</span>
          </label>
        ))}
      </fieldset>
      <details className="layer-settings layer-more-controls" name="explore-toolbar-panels">
        <summary>More controls</summary>
        <div className="layer-settings-body">
      <label className="reveal-choice">
        <input type="checkbox" checked={p.mode === "timeline"} disabled={!p.timelineAvailable} onChange={(e) => p.onTimeline(e.target.checked)} />
        Reveal by arrival time
      </label>
      {!p.timelineAvailable && <p className="layer-help">No usable model-clock window supplied.</p>}
      <button type="button" className={`extent-choice ${p.mode === "extent" ? "selected" : ""}`} aria-pressed={p.mode === "extent"} onClick={p.onExtent}>Extent outline</button>
        <label className="opacity-setting">Layer opacity <input type="range" min={0.1} max={1} step={0.05} value={p.opacity} onChange={(e) => p.onOpacity(Number(e.target.value))} aria-label="Layer opacity" /></label>
        </div>
      </details>
      <button type="button" className="layer-fit" aria-label="Fit to flood area" title="Fit to flood area" onClick={p.onFit}><Crosshair size={18} aria-hidden /> Fit</button>
    </section>
  </>;
}
