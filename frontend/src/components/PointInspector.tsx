import { useEffect, useState } from "react";
import type { ScenarioView } from "../model";
import type { PrototypeLayers } from "../lib/api";
import { usePointInspection, type PointSelection, type PointReadState } from "../hooks/usePointInspection";
import { arrivalPointCompatible, POINT_FIELDS, pointDifference, type MapPoint, type PointValue } from "../lib/pointInspection";
import { cellState, elapsedMinutes } from "../lib/timeline";
import { utm43ToLonLat } from "../lib/utm";

export interface PointScenario { scenario: ScenarioView; layers: PrototypeLayers | undefined; error?: string | null }
export const pointText = (value: PointValue | undefined, arrival = false): string => {
  if (!value) return "Waiting for raster data…";
  if (value.kind === "value" && value.value !== null) return `${(arrival ? value.value / 60 : value.value).toFixed(2)} ${arrival ? "h" : ""}`.trim();
  return value.kind === "nodata" ? "No data" : value.kind === "outside" ? "Outside raster coverage" : "Unavailable";
};
const field = (state: PointReadState, key: "depth" | "arrival" | "velocity") => state.kind === "ready" ? state.values[key] : undefined;

export default function PointInspector(p: { selection: PointSelection | null; scenarios: PointScenario[];
  onSelect: (point: MapPoint) => void; onClear: () => void; elapsedHours?: number }) {
  const first = p.scenarios[0], second = p.scenarios[1];
  const A = usePointInspection(first?.layers, p.selection), B = usePointInspection(second?.layers, p.selection);
  const states = [A, B];
  const [east, setEast] = useState(""), [north, setNorth] = useState(""), [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (p.selection) { setEast(p.selection.coordinate[0].toFixed(3)); setNorth(p.selection.coordinate[1].toFixed(3)); }
    setError(null);
  }, [p.selection]);
  const apply = (e: React.FormEvent) => {
    e.preventDefault(); const coordinate: MapPoint = [Number(east), Number(north)];
    if (!east.trim() || !north.trim() || !coordinate.every(Number.isFinite)
        || coordinate[0] < 0 || coordinate[0] > 1000000 || coordinate[1] < 0 || coordinate[1] > 10000000) {
      setError("Enter valid EPSG:32643 easting/northing in metres."); return;
    }
    setError(null); p.onSelect(coordinate);
  };
  const engineMatches = !!second && first.scenario.detail.engine.name === second.scenario.detail.engine.name
    && first.scenario.detail.engine.software_version === second.scenario.detail.engine.software_version;
  const lonLat = p.selection ? utm43ToLonLat(p.selection.coordinate) : null;
  return <section className={`point-inspector${second ? " point-comparison" : ""}`} aria-label={second ? "Selected-location scenario comparison" : "Selected-location values"}>
    <h3>{second ? "Compare the same location" : "Inspect a map location"}</h3>
    <p className="muted">{second ? "Click either map" : "Click the map"}, or focus the map and press Enter to inspect its centre. You can also enter projected coordinates below.</p>
    <form className="point-coordinate-form" onSubmit={apply}>
      <label>Easting (m)<input type="number" step="any" value={east} onChange={e => setEast(e.target.value)} aria-label="Point easting in metres" required /></label>
      <label>Northing (m)<input type="number" step="any" value={north} onChange={e => setNorth(e.target.value)} aria-label="Point northing in metres" required /></label>
      <button type="submit" className="btn">Inspect coordinates</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {!p.selection ? <p>No location selected. No raster reads are made until you select one.</p> : <>
      <p className="point-location">EPSG:32643 · E {p.selection.coordinate[0].toFixed(2)} m · N {p.selection.coordinate[1].toFixed(2)} m
        {lonLat && <small>Longitude {lonLat[0].toFixed(5)}° · Latitude {lonLat[1].toFixed(5)}°</small>}</p>
      <p className="point-caveat">Stored full-run maxima, not water levels or velocities at the selected elapsed time. Values describe original export cells, not a survey-precise point. No data is unknown—not zero, dry or safe. Simulated, uncalibrated and not scientifically validated.</p>
      <div className="point-table-wrap"><table>
        <caption>Original-resolution raster cells at the selected location</caption>
        <thead><tr><th scope="col">Metric</th>{p.scenarios.map((s, i) => <th scope="col" key={i}>{i === 0 && second ? "Baseline · " : i === 1 ? "Candidate · " : ""}{s.scenario.info.short}</th>)}{second && <th scope="col">Candidate − baseline</th>}</tr></thead>
        <tbody>{POINT_FIELDS.map(f => {
          const av = field(A, f.key), bv = field(B, f.key);
          const delta = av && bv && f.key !== "velocity" && engineMatches
            && (f.key !== "arrival" || arrivalPointCompatible(first.scenario.detail, second!.scenario.detail)) ? pointDifference(av, bv) : null;
          return <tr key={f.key}><th scope="row">{f.label}{f.key !== "arrival" && ` (${f.unit})`}</th>
            {p.scenarios.map((s, i) => {
              const value = field(states[i], f.key), state = states[i];
              return <td key={i}>{s.error ? "Unavailable" : pointText(value, f.key === "arrival")}
                {value?.reason && <small>{value.reason}</small>}
                {state.kind === "error" && <small>{state.message}</small>}
                {f.key === "arrival" && value?.kind === "value" && <small>{value.value} stored min since simulation start</small>}
              </td>;
            })}
            {second && <td>{delta?.value != null ? `${delta.value > 0 ? "+" : ""}${(f.key === "arrival" ? delta.value / 60 : delta.value).toFixed(2)} ${f.key === "arrival" ? "h" : f.unit}` : "Not compared"}
              <small>{delta?.value != null ? "Same original-resolution grid cell." : delta?.reason ?? (f.key === "velocity" ? "Velocity definitions are not harmonized; no velocity delta is computed." : !engineMatches ? "Engine/version mismatch." : f.key === "arrival" && !arrivalPointCompatible(first.scenario.detail, second.scenario.detail) ? "Arrival origins, thresholds or timing metadata are incompatible." : "Valid aligned cells are required.")}</small>
            </td>}
          </tr>;
        })}</tbody>
      </table></div>
      {p.scenarios.map((s, i) => {
        const arrival = field(states[i], "arrival");
        return <div className="point-read-status" key={i}>
          {s.error && <p role="alert">{s.scenario.info.short}: layer catalog unavailable. {s.error}</p>}
          {!s.error && states[i].kind === "loading" && <p role="status">Reading {s.scenario.info.short} original raster cells…</p>}
          {p.elapsedHours !== undefined && <p>{s.scenario.info.short} at {p.elapsedHours} elapsed model h: {arrival?.kind === "value" && arrival.value !== null
            ? cellState(arrival.value, elapsedMinutes(p.elapsedHours)) === "reached" ? "Reached according to stored arrival time." : "Not yet reached according to stored arrival time."
            : "Arrival state unknown; not a safety statement."}</p>}
        </div>;
      })}
      {second && <p className="muted">Different simulated hydrographs/runs are compared. Relative arrival differences are elapsed-from-start differences, not synchronized calendar times, forecasts, exposure or evacuation advice.</p>}
      <div className="point-actions"><button type="button" className="btn" onClick={() => p.onSelect(p.selection!.coordinate)}>Retry point reads</button><button type="button" className="btn" onClick={p.onClear}>Clear selected location</button></div>
    </>}
  </section>;
}
