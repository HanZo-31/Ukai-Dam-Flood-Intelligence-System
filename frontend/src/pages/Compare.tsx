import { useMemo, useState } from "react";
import "../compare-scroll.css";
import View from "ol/View";
import { ArrowLeftRight } from "lucide-react";
import type { ScenarioView } from "../model";
import { getLayers } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { formatValue, NOT_AVAILABLE, formatHours } from "../lib/format";
import { peakRelease } from "../lib/scenarios";
import type { ViewMode } from "../lib/scales";
import { registerUtm43 } from "../map/projection";
import FloodMap from "../map/FloodMap";
import MapControls from "../components/MapControls";
import Legend from "../components/Legend";
import Banner from "../components/Banner";
import DiffPanel from "../components/DiffPanel";
import PointInspector from "../components/PointInspector";
import type { PointSelection } from "../hooks/usePointInspection";
import type { MapPoint } from "../lib/pointInspection";

type Metric = { key: string; label: string; unit: string; get: (s: ScenarioView) => number | null; digits: number };
const METRICS: Metric[] = [
  { key: "peak", label: "Peak release", unit: "m³/s", get: (s) => peakRelease(s.detail), digits: 0 },
  { key: "area", label: "Flooded area", unit: "km²", get: (s) => s.impact.flooded_area_km2, digits: 1 },
  { key: "depth", label: "Maximum depth", unit: "m", get: (s) => s.impact.max_depth_m, digits: 2 },
];

function Bars({ items, m }: { items: ScenarioView[]; m: Metric }) {
  const vals = items.map(m.get).filter((v): v is number => typeof v === "number");
  const max = vals.length ? Math.max(...vals) : 0; // one shared scale for all scenarios
  return (
    <div className="bars" role="img" aria-label={`${m.label} by scenario, shared scale`}>
      <h4>{m.label} ({m.unit})</h4>
      {items.map((s) => {
        const v = m.get(s);
        return (
          <div className="bar-row" key={s.id}>
            <span className="bar-name">{s.info.short}</span>
            <span className="bar-track">{v !== null && max > 0 && <span className="bar-fill" style={{ width: `${(v / max) * 100}%` }} />}</span>
            <span className="bar-val">{formatValue(v, m.digits)}</span>
          </div>
        );
      })}
    </div>
  );
}

function Pick({ label, items, value, onChange }: { label: string; items: ScenarioView[]; value: string; onChange: (id: string) => void }) {
  return (
    <label className="pick">{label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>{items.map((s) => <option key={s.id} value={s.id}>{s.info.long}</option>)}</select>
    </label>
  );
}

export default function Compare({ items }: { items: ScenarioView[] }) {
  const [left, setLeft] = useState(items[0]?.id ?? "");
  const [right, setRight] = useState(items[1]?.id ?? items[0]?.id ?? "");
  const [mode, setMode] = useState<ViewMode>("depth");
  const [opacity, setOpacity] = useState(0.85);
  const [fit, setFit] = useState(0);
  const [selection, setSelection] = useState<PointSelection | null>(null);
  const selectPoint = (coordinate: MapPoint) => setSelection(previous => ({ coordinate, sequence: (previous?.sequence ?? 0) + 1 }));
  const view = useMemo(() => new View({ projection: registerUtm43(), center: [380000, 2400000], zoom: 8 }), []);
  const L = useAsync((sig) => getLayers(left, sig), [left]);
  const R = useAsync((sig) => getLayers(right, sig), [right]);
  const swap = () => { setLeft(right); setRight(left); };
  const ls = items.find((x) => x.id === left), rs = items.find((x) => x.id === right);
  return (
    <div className="page-scroll compare-page">
      <h2>Compare scenarios</h2>
      <p className="muted compare-lead">Choose two stored references. Both maps use the same colour scale and move together.</p>
      <div className="compare-controls">
        <Pick label="Left (baseline)" items={items} value={left} onChange={setLeft} />
        <Pick label="Right (candidate)" items={items} value={right} onChange={setRight} />
        <button type="button" className="btn" onClick={swap}><ArrowLeftRight size={14} aria-hidden /> Swap</button>
      </div>
      <MapControls modes={["extent", "depth", "velocity", "arrival"]} mode={mode} onMode={setMode} opacity={opacity} onOpacity={setOpacity} onFit={() => setFit((n) => n + 1)} />
      {(L.error || R.error) && <Banner message={(L.error ?? R.error)!} onRetry={() => { L.reload(); R.reload(); }} />}
      <div className="two-maps">
        <div><div className="map-title">{ls?.info.long}</div><div className="map-wrap short"><FloodMap layers={L.data} mode={mode} opacity={opacity} view={view} fitToken={fit} label={`${ls?.info.long ?? "Left"} map`} onSelectPoint={selectPoint} selectedPoint={selection?.coordinate} /></div></div>
        <div><div className="map-title">{rs?.info.long}</div><div className="map-wrap short"><FloodMap layers={R.data} mode={mode} opacity={opacity} view={view} fitToken={fit} label={`${rs?.info.long ?? "Right"} map`} onSelectPoint={selectPoint} selectedPoint={selection?.coordinate} /></div></div>
      </div>
      <Legend mode={mode} />
      {ls && rs && <PointInspector selection={selection} onSelect={selectPoint} onClear={() => setSelection(null)} scenarios={[
        { scenario: ls, layers: L.data?.scenario_id === left && L.data.run_id === ls.summary.run_id ? L.data : undefined, error: L.error },
        { scenario: rs, layers: R.data?.scenario_id === right && R.data.run_id === rs.summary.run_id ? R.data : undefined, error: R.error },
      ]} />}
      <details className="reference-overview">
        <summary>Reference metrics and overview</summary>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Scenario</th><th>Type</th><th>Peak release (m³/s)</th><th>Flooded area (km²)</th><th>Max depth (m)</th><th>Arrival resolution (h)</th><th>Population exposed</th></tr></thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <th scope="row">{s.info.short}</th><td>{s.info.kindLabel}</td>
                  <td>{formatValue(peakRelease(s.detail), 0)}</td><td>{formatValue(s.impact.flooded_area_km2, 1)}</td><td>{formatValue(s.impact.max_depth_m, 2)}</td>
                  <td>{formatHours(s.detail.arrival?.temporal_resolution_minutes)}</td><td>{formatValue(s.impact.population_exposed, 0, NOT_AVAILABLE)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="bars-grid">{METRICS.map((m) => <Bars key={m.key} items={items} m={m} />)}</div>
      </details>
      <DiffPanel baseline={ls} candidate={rs} baseLayers={L.data} candLayers={R.data} view={view} fit={fit} onSwap={swap} />
    </div>
  );
}
