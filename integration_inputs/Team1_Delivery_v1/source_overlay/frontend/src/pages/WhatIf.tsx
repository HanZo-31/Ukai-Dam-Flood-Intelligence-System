import { useId, useState } from "react";
import { RefreshCw, Play } from "lucide-react";
import type { ScenarioView } from "../model";
import { useCandidate } from "../hooks/useCandidate";
import { PEAK_MAX, PEAK_MIN, validateRequestInput, type CandidateResult } from "../lib/candidate";
import { sameOriginPath } from "../lib/assets";

const RES_LABEL: Record<string, string> = { detail: "Scenario detail", layers: "Map layers", impact: "Impact summary", assumptions: "Assumptions", quality_report: "Quality report" };
const m3 = (v: number) => `${v.toLocaleString("en-US")} m³/s`;

function ResultCard({ r, views, onOpen, stale }: { r: CandidateResult; views: ScenarioView[]; onOpen: (id: string) => void; stale: boolean }) {
  const differs = r.requested_peak_release_m3s !== r.actual_peak_release_m3s;
  const src = views.find((v) => v.id === r.source_scenario_id);
  return (
    <section className="whatif-card" aria-labelledby="wi-result-h" aria-busy={stale}>
      <h3 id="wi-result-h">Stored reference selected</h3>
      {stale && <p className="muted" role="status">Showing the previous result while the new request runs.</p>}
      <p className="whatif-badge">Stored lookup — <strong>not computed</strong>, no new simulation, no machine learning</p>
      <div className="table-wrap">
        <table>
          <tbody>
            <tr><th scope="row">Requested peak release</th><td>{m3(r.requested_peak_release_m3s)}</td></tr>
            <tr><th scope="row">Actual peak release returned</th><td><strong>{m3(r.actual_peak_release_m3s)}</strong>{differs && <span className="whatif-warn"> — differs from the request (nearest stored reference, opted in)</span>}</td></tr>
            <tr><th scope="row">Source scenario</th><td>{src ? src.info.long : r.source_scenario_id} <span className="muted">({r.source_scenario_id}, run {r.source_run_id})</span></td></tr>
            <tr><th scope="row">Engine</th><td>{r.engine}</td></tr>
            <tr><th scope="row">Computed by the service</th><td>{r.computed ? "Yes" : "No"}</td></tr>
            <tr><th scope="row">Calibration</th><td>{r.calibration_status}</td></tr>
            <tr><th scope="row">Scientifically validated</th><td>{r.scientifically_validated ? "Yes" : "No"}</td></tr>
            <tr><th scope="row">Served from cache</th><td>{r.cache_hit ? "Yes" : "No"}</td></tr>
            <tr><th scope="row">Request ID / job ID</th><td><code>{r.request_id}</code> / <code>{r.job_id}</code></td></tr>
            <tr><th scope="row">Service lookup time</th><td>{r.elapsed_wall_seconds.toFixed(3)} s <span className="muted">— checking and finding stored data only. It is not model run time and not the time to show the map.</span><br /><span className="muted small">Service timing scope: {r.timing_scope}</span></td></tr>
          </tbody>
        </table>
      </div>
      {r.warnings.length > 0 && <ul className="whatif-warnings" aria-label="Service warnings">{r.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
      <p>
        <button type="button" className="btn" disabled={!src} onClick={() => onOpen(r.source_scenario_id)}>Open this scenario in Explore</button>
        {!src && <span className="muted"> The source scenario is not loaded.</span>}
      </p>
      <p className="muted small">Reference links (served by the reference API, not the candidate service):{" "}
        {Object.entries(r.reference_resources).map(([k, u]) => u ? <a key={k} href={sameOriginPath(u)} target="_blank" rel="noreferrer" className="reslink">{RES_LABEL[k] ?? k}</a> : null)}
      </p>
    </section>
  );
}

export default function WhatIf({ views, onOpenScenario }: { views: ScenarioView[]; onOpenScenario: (id: string) => void }) {
  const { caps, run, start, reloadCaps } = useCandidate(views.map((v) => v.id));
  const [peakText, setPeakText] = useState("20000");
  const [nearest, setNearest] = useState(false);
  const peakId = useId(), listId = useId(), nearId = useId();
  const peak = peakText.trim() === "" ? Number.NaN : Number(peakText);
  const c = caps.status === "ready" ? caps.caps : null;
  const lo = c?.minPeak ?? PEAK_MIN, hi = c?.maxPeak ?? PEAK_MAX;
  const inputProblem = validateRequestInput(peak, "check-id-ok");
  const canRun = !!c && c.storedReference.available && !inputProblem && run.phase !== "loading";

  return (
    <div className="page-scroll whatif">
      <h2>What-if: choose a stored reference</h2>
      <p className="whatif-badge">This looks up an existing HEC-RAS reference result for a peak release. It does not run a new flood simulation and does not use machine learning. Results are simulated, uncalibrated and not scientifically validated.</p>

      {caps.status === "loading" && <p role="status" className="muted">Checking what the candidate service offers…</p>}
      {caps.status === "unavailable" && (
        <div className="banner" role="alert">
          Candidate service unavailable: {caps.message} The Explore, Compare and Evidence pages still work with the stored reference scenarios.
          <button type="button" className="btn" onClick={reloadCaps}><RefreshCw size={14} aria-hidden /> Try again</button>
        </div>
      )}

      {c && !c.storedReference.available && <div className="banner" role="alert">Stored-reference selection is not available: {c.storedReference.reason ?? "the service did not say why."}</div>}

      <form className="whatif-form" onSubmit={(e) => { e.preventDefault(); if (canRun) start(peak, nearest); }} aria-describedby="wi-help">
        <label htmlFor={peakId}>Peak release (m³/s)</label>
        <input id={peakId} type="number" inputMode="numeric" min={lo} max={hi} step={1} value={peakText} list={listId} onChange={(e) => setPeakText(e.target.value)} disabled={!c} aria-invalid={!!inputProblem} />
        <datalist id={listId}>{(c?.storedPeaks ?? []).map((p) => <option key={p} value={p} />)}</datalist>
        <div className="check">
          <input id={nearId} type="checkbox" checked={nearest} onChange={(e) => setNearest(e.target.checked)} disabled={!c} />
          <label htmlFor={nearId}>If there is no stored reference at exactly this release, use the nearest stored one (ties go to the lower peak). The result will show both numbers.</label>
        </div>
        <p id="wi-help" className="muted small">
          Allowed range {m3(lo)} to {m3(hi)}. {c?.storedPeaks ? `Stored references exist for ${c.storedPeaks.map((p) => p.toLocaleString("en-US")).join(", ")} m³/s.` : ""} Without the option above, only an exact stored release succeeds. Nothing is sent until you press the button.
        </p>
        {inputProblem && peakText !== "" && <p className="whatif-warn" role="alert">{inputProblem}</p>}
        <button type="submit" className="btn primary" disabled={!canRun}><Play size={14} aria-hidden /> {run.phase === "loading" ? "Looking up…" : "Look up stored reference"}</button>
      </form>

      <section className="whatif-card" aria-labelledby="wi-ml-h">
        <h3 id="wi-ml-h">Experimental machine-learning prediction</h3>
        {c?.experimentalMl.available
          ? <p className="whatif-warn">The service declares this mode available, but this interface only offers stored-reference selection.</p>
          : <p><strong>Unavailable.</strong> {c ? (c.experimentalMl.reason ?? "The service does not offer this mode.") : "Shown once the service answers."}</p>}
      </section>

      {run.phase === "error" && (
        <div className="banner" role="alert">
          {run.error}
          {run.problems.length > 0 && <ul>{run.problems.map((p, i) => <li key={i}>{p}</li>)}</ul>}
          {run.failedJob && run.failedJob.warnings.length > 0 && <ul>{run.failedJob.warnings.map((p, i) => <li key={i}>{p}</li>)}</ul>}
          {run.last && <div className="muted">The result below is the last one that succeeded.</div>}
        </div>
      )}
      {run.last && <ResultCard r={run.last.result} views={views} onOpen={onOpenScenario} stale={run.phase === "loading"} />}
    </div>
  );
}
