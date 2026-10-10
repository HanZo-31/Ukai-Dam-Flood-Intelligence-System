import type { ScenarioView } from "../model";
import { formatNominal, formatValue, NOT_AVAILABLE } from "../lib/format";
import { Limitations } from "./EvidencePanel";

export default function Inspector({ s, onEvidence }: { s: ScenarioView; onEvidence: () => void }) {
  const d = s.detail;
  return (
    <aside className="inspector" aria-label="Evidence inspector">
      <p className="inspector-kicker">Scenario details</p>
      <h3>{s.info.long}</h3>
      <p className="status-pill">{d.label}</p>
      <dl>
        <div className="kv"><dt>Engine</dt><dd>{d.engine.name} {d.engine.software_version}</dd></div>
        <div className="kv"><dt>Calibration</dt><dd>{d.calibration_status.replace(/_/g, " ")}</dd></div>
        <div className="kv"><dt>Validation</dt><dd>{d.validation_status.replace(/_/g, " ")}</dd></div>
        <div className="kv"><dt>Population exposed</dt><dd>{formatValue(s.impact.population_exposed, 0, NOT_AVAILABLE)}</dd></div>
        <div className="kv"><dt>Buildings exposed</dt><dd>{formatValue(s.impact.buildings_exposed, 0, NOT_AVAILABLE)}</dd></div>
      </dl>
      <details className="inspector-details">
        <summary>Run &amp; model details</summary>
        <dl>
          <div className="kv"><dt>Run ID</dt><dd><code>{s.summary.run_id}</code></dd></div>
          <div className="kv"><dt>Model clock</dt><dd>{d.timing.coverage_clock_kind}; {d.timing.timezone_convention}</dd></div>
          <div className="kv"><dt>Coverage</dt><dd>{formatNominal(d.coverage_start)} → {formatNominal(d.coverage_end)}</dd></div>
        </dl>
      </details>
      <details className="inspector-details">
        <summary>Evidence &amp; limitations</summary>
        <Limitations s={s} />
      </details>
      <button type="button" className="btn primary" onClick={onEvidence}>Open full evidence and downloads</button>
    </aside>
  );
}
