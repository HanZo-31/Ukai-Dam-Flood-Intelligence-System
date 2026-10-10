import { Crosshair } from "lucide-react";
import type { ViewMode } from "../lib/scales";

const MODES: { id: ViewMode; label: string }[] = [
  { id: "extent", label: "Extent" }, { id: "depth", label: "Depth" }, { id: "velocity", label: "Velocity" }, { id: "arrival", label: "Arrival" },
];

export default function MapControls(p: { mode: ViewMode; onMode: (m: ViewMode) => void; opacity: number; onOpacity: (o: number) => void; onFit: () => void }) {
  return (
    <div className="map-controls">
      <div className="seg" role="group" aria-label="Map layer">
        {MODES.map((m) => (
          <button key={m.id} type="button" className={p.mode === m.id ? "on" : ""} aria-pressed={p.mode === m.id} onClick={() => p.onMode(m.id)}>{m.label}</button>
        ))}
      </div>
      <label className="opacity">Opacity
        <input type="range" min={0.1} max={1} step={0.05} value={p.opacity} onChange={(e) => p.onOpacity(Number(e.target.value))} aria-label="Layer opacity" />
      </label>
      <button type="button" className="btn" onClick={p.onFit}><Crosshair size={15} aria-hidden /> Fit to flood area</button>
    </div>
  );
}
