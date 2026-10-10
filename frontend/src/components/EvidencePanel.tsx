import { useState } from "react";
import { Download } from "lucide-react";
import type { ScenarioView } from "../model";
import { getLayers, getStoredJson } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { formatNominal, formatValue, NOT_AVAILABLE, shortChecksum } from "../lib/format";
import { fileHint, ROLE_LABEL, sameOriginPath } from "../lib/assets";
import Banner from "./Banner";

const dash = (v: unknown) => (v === null || v === undefined || v === "" ? NOT_AVAILABLE : String(v));

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="kv"><dt>{k}</dt><dd>{v}</dd></div>;
}

function JsonPreview({ url }: { url: string }) {
  const r = useAsync((s) => getStoredJson(url, s), [url]);
  if (r.loading) return <p className="muted">Loading…</p>;
  if (r.error) return <Banner message={r.error} onRetry={r.reload} />;
  return <pre className="json" tabIndex={0}>{JSON.stringify(r.data, null, 2)}</pre>;
}

function Preview({ title, url }: { title: string; url: string }) {
  const [open, setOpen] = useState(false);
  return (
    <details onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary>{title}</summary>
      {open && <JsonPreview url={url} />}
    </details>
  );
}

export function Limitations({ s }: { s: ScenarioView }) {
  const d = s.detail;
  return (
    <>
      <h4>Limitations</h4>
      {d.limitations?.length ? <ul>{d.limitations.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="muted">{NOT_AVAILABLE}</p>}
      <h4>Products not available</h4>
      {Object.keys(d.unavailable_reasons ?? {}).length || Object.keys(s.impact.unavailable_reasons ?? {}).length ? (
        <ul>{Object.entries({ ...(d.unavailable_reasons ?? {}), ...(s.impact.unavailable_reasons ?? {}) }).map(([k, v]) => <li key={k}><strong>{k.replace(/_/g, " ")}:</strong> {v}</li>)}</ul>
      ) : <p className="muted">None listed by the API.</p>}
    </>
  );
}

export default function EvidencePanel({ s }: { s: ScenarioView }) {
  const d = s.detail;
  const layers = useAsync((sig) => getLayers(s.id, sig), [s.id]);
  return (
    <div className="evidence">
      <div className="status-box">
        <strong>{d.label}</strong>
        <span>Calibration: {d.calibration_status.replace(/_/g, " ")} · Validation: {d.validation_status.replace(/_/g, " ")} · Scientifically validated: {d.scientifically_validated ? "yes" : "no"}</span>
        {d.warnings?.map((w, i) => <span key={i}>{w}</span>)}
      </div>

      <h4>Run</h4>
      <dl>
        <Row k="Run ID" v={<code>{s.summary.run_id}</code>} />
        <Row k="Scenario ID" v={<code>{s.id}</code>} />
        <Row k="Model version" v={dash(d.model_version)} />
        <Row k="Engine" v={`${d.engine.name} ${d.engine.software_version}`} />
        <Row k="Engine build" v={d.engine.build ?? d.engine.build_unavailable_reason ?? NOT_AVAILABLE} />
        <Row k="Run timestamp" v={d.run_timestamp ? formatNominal(d.run_timestamp) : (d.run_timestamp_unknown_reason ?? NOT_AVAILABLE)} />
      </dl>

      <h4>Model clock</h4>
      <dl>
        <Row k="Clock kind" v={dash(d.timing.coverage_clock_kind)} />
        <Row k="Timezone convention" v={dash(d.timing.timezone_convention)} />
        <Row k="Coverage" v={`${formatNominal(d.coverage_start)} → ${formatNominal(d.coverage_end)}`} />
        <Row k="Output interval" v={`${formatValue(d.timing.result_output_interval_minutes, 0)} min`} />
        <Row k="Arrival reference" v={`${formatNominal(d.arrival.reference_timestamp)}; stored in ${d.arrival.unit}, shown in hours`} />
      </dl>

      <h4>Data sources and licences</h4>
      {d.datasets?.length ? (
        <ul className="plain">{d.datasets.map((x) => (
          <li key={x.dataset_id}><strong>{x.source_label}</strong> <span className="muted">({x.dataset_id} v{x.version})</span><br />Licence: {dash(x.license)} · <code>{shortChecksum(x.checksum)}</code></li>
        ))}</ul>
      ) : <p className="muted">{NOT_AVAILABLE}</p>}

      <Limitations s={s} />

      <h4>Downloads</h4>
      {layers.loading && <p className="muted">Loading asset list…</p>}
      {layers.error && <Banner message={layers.error} onRetry={layers.reload} />}
      <ul className="downloads">
        {layers.data?.layers.map((l) => (
          <li key={l.asset_type}>
            <div><strong>{ROLE_LABEL[l.asset_type] ?? l.asset_type}</strong><br /><span className="muted">{fileHint(l)} · {l.crs} · unit {l.unit} · <code>{shortChecksum(l.checksum)}</code></span></div>
            <a className="btn" href={sameOriginPath(l.url)} download><Download size={14} aria-hidden /> Download</a>
          </li>
        ))}
        <li>
          <div><strong>Assumptions</strong><br /><span className="muted">JSON</span></div>
          <a className="btn" href={sameOriginPath(d.links.assumptions)} download={`${s.id}-assumptions.json`}><Download size={14} aria-hidden /> Download</a>
        </li>
        <li>
          <div><strong>Quality report</strong><br /><span className="muted">JSON</span></div>
          <a className="btn" href={sameOriginPath(d.links.quality_report)} download={`${s.id}-quality-report.json`}><Download size={14} aria-hidden /> Download</a>
        </li>
      </ul>

      <details className="tech">
        <summary>Technical details</summary>
        <dl>
          <Row k="CRS" v={d.crs} />
          <Row k="Source checksum (engine)" v={d.engine.source_checksum ?? d.engine.source_checksum_unavailable_reason ?? NOT_AVAILABLE} />
          <Row k="Source manifest checksum" v={<code>{d.provenance.source_manifest_checksum}</code>} />
          <Row k="Scenario family" v={dash(d.provenance.scenario_family)} />
          <Row k="Derivation" v={`${d.provenance.derivation_processor} ${d.provenance.derivation_version}`} />
          <Row k="Arrival threshold" v={`${d.arrival.threshold_m} m; resolution ${d.arrival.temporal_resolution_minutes} min; origin ${d.arrival.origin}`} />
          <Row k="Data kind / mode" v={`${d.data_kind} / ${d.data_mode}`} />
        </dl>
        <h4>Assumptions</h4>
        {d.assumptions?.length ? <ul>{d.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul> : <p className="muted">{NOT_AVAILABLE}</p>}
        <Preview title="Stored assumptions (JSON)" url={sameOriginPath(d.links.assumptions)} />
        <Preview title="Stored quality report (JSON)" url={sameOriginPath(d.links.quality_report)} />
      </details>
    </div>
  );
}
