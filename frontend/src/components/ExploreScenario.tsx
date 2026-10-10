import { ArrowRight, Clock3, FileText, Layers3, Waves } from "lucide-react";
import type { ScenarioView } from "../model";
import type { ViewMode } from "../lib/scales";
import { formatValue } from "../lib/format";
import { peakRelease } from "../lib/scenarios";
import Inspector from "./Inspector";
import SummaryRow from "./SummaryRow";

export default function ExploreScenario(p: { s: ScenarioView; mode: ViewMode; hours: number; onEvidence: () => void }) {
  const { s, mode, hours } = p;
  const exposureMissing = [s.impact.population_exposed, s.impact.buildings_exposed,
    s.impact.roads_affected_km, s.impact.critical_facilities_exposed].every((v) => v == null);
  return <aside className="scenario-panel" aria-label="Selected scenario">
    <div className="scenario-panel-card">
      <h2><span>{s.info.short}</span><span className="scenario-divider"> · </span>Reference simulation</h2>
      <dl className="scenario-facts">
        <div><Waves size={25} aria-hidden /><dt>Peak release</dt><dd>{formatValue(peakRelease(s.detail), 0)} <small>m³/s</small></dd></div>
        <div><Clock3 size={25} aria-hidden /><dt>Model time</dt><dd>{mode === "timeline" ? `${hours} h` : "Full-run result"}</dd>
          <p>{mode === "timeline" ? "Elapsed from simulation start" : "Enable arrival reveal for elapsed time"}</p></div>
        <div><Layers3 size={25} aria-hidden /><dt>Exposure data</dt><dd>{exposureMissing ? "Unavailable" : "See exposure evidence"}</dd></div>
        <div><FileText size={25} aria-hidden /><dt>Scenario type</dt><dd className="scenario-kind">{s.info.kindLabel}</dd></div>
      </dl>
      <p className="scenario-science">{s.detail.label}<br />Validation: {s.detail.validation_status.replace(/_/g, " ")}</p>
      <button type="button" className="scenario-evidence" onClick={p.onEvidence}><FileText size={20} aria-hidden /> View evidence &amp; limitations <ArrowRight size={18} aria-hidden /></button>
      <details className="scenario-more">
        <summary>Stored metrics &amp; run details</summary>
        <SummaryRow s={s} />
        <Inspector s={s} onEvidence={p.onEvidence} />
      </details>
    </div>
  </aside>;
}
