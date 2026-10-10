import type { ScenarioView } from "../model";
import { formatValue, NOT_AVAILABLE, NOT_CALCULATED, formatHours } from "../lib/format";
import { peakRelease } from "../lib/scenarios";

function Card(p: { label: string; value: string; unit?: string; note?: string }) {
  const missing = p.value === NOT_AVAILABLE || p.value === NOT_CALCULATED;
  return (
    <div className="card">
      <div className="card-label">{p.label}</div>
      <div className={`card-value ${missing ? "missing" : ""}`}>{p.value}{!missing && p.unit ? <small> {p.unit}</small> : null}</div>
      {p.note && <div className="card-note">{p.note}</div>}
    </div>
  );
}

export default function SummaryRow({ s }: { s: ScenarioView }) {
  const d = s.detail;
  const peak = peakRelease(d);
  return (
    <section className="summary-row" aria-label="Scenario summary">
      <Card label="Peak release" value={formatValue(peak, 0)} unit={d.parameter_units?.peak_release_m3s ?? "m³/s"} />
      <Card label="Flooded area" value={formatValue(s.impact.flooded_area_km2, 1)} unit="km²" />
      <Card label="Maximum depth" value={formatValue(s.impact.max_depth_m, 2)} unit="m" />
      <Card label="Arrival time resolution" value={formatHours(d.arrival?.temporal_resolution_minutes)} unit="h" note="stored in minutes" />
    </section>
  );
}
