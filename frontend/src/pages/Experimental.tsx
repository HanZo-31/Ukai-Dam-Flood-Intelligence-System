import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Play, RefreshCw, Square } from "lucide-react";
import type { ScenarioView } from "../model";
import { getLayers } from "../lib/api";
import { loadCandidateReference } from "../lib/compute/reference";
import { useAsync } from "../hooks/useAsync";
import { useCompute } from "../hooks/useCompute";
import { isActive, type Accepted, type Phase } from "../lib/compute/controller";
import { arrivalComparisonBlock, referenceArrivalBlock, validatePeak } from "../lib/compute/contract";
import { compareCandidate, CLASS_LABELS, CANDIDATE_CLASS_COLOURS, type CompareGrid } from "../lib/compute/candidateCompare";
import { computeCandidateZones, explainCandidateZone, reconcileZones } from "../lib/compute/candidateZones";
import { assetRows, classRgba, identityRows, rasterRgba, timingRows, TIMING_NOTE } from "../lib/compute/present";
import CandidateRasterView from "../map/CandidateRasterView";
import { formatValue } from "../lib/format";
import { SCALES } from "../lib/scales";

const PHASE_TEXT: Record<Phase, string> = {
  idle: "Ready.", submitting: "Sending the request…", queued: "Queued — waiting for the service to start.", running: "Running on the service…",
  loading_result: "Computation finished. Checking the result…", loading_products: "Result accepted. Downloading and verifying the map products…",
  completed: "Finished.", failed: "The service reported that the job failed.", error: "Stopped.",
};
type MapMode = "depth" | "arrival" | "velocity" | "difference";
const MAP_LABEL: Record<MapMode, string> = { depth: "Maximum depth", arrival: "Arrival time", velocity: "Velocity component", difference: "Difference from reference" };
const areaText = (v: number) => v > 0 && v < 0.005 ? "<0.01" : formatValue(v, 2);

function Rows({ rows, caption }: { rows: { label: string; value: string; note?: string }[]; caption: string }) {
  return (
    <div className="table-wrap"><table><caption className="sr-only">{caption}</caption><tbody>
      {rows.map((r) => <tr key={r.label}><th scope="row">{r.label}</th><td>{r.value}{r.note && <div className="muted small">{r.note}</div>}</td></tr>)}
    </tbody></table></div>
  );
}

function ResultView({ a, refArrival, baselineGrid, baselineError, baselineLoading, previous }: { a: Accepted; refArrival: Parameters<typeof referenceArrivalBlock>[0]; baselineGrid: CompareGrid | null; baselineError: string | null; baselineLoading: boolean; previous: boolean }) {
  const [mode, setMode] = useState<MapMode>("depth");
  const [outline, setOutline] = useState(true);
  const d = a.products.decoded, r = a.result;
  const cand: CompareGrid | null = useMemo(() => d?.depth ? { width: d.depth.width, height: d.depth.height, geo: d.depth.geo, crs: r.derived_grid.crs, depth: d.depth.data, arrival: d.arrival?.data ?? null } : null, [d, r.derived_grid.crs]);
  const block = useMemo(() => arrivalComparisonBlock(r) ?? referenceArrivalBlock(refArrival) ?? (baselineGrid && !baselineGrid.arrival ? "The reference scenario has no arrival raster." : null), [r, refArrival, baselineGrid]);
  const cmp = useMemo(() => (cand && baselineGrid ? compareCandidate(baselineGrid, cand, block) : null), [cand, baselineGrid, block]);
  const zones = useMemo(() => (cand && baselineGrid && typeof cmp === "object" && cmp ? computeCandidateZones(baselineGrid, cand, block) : null), [cand, baselineGrid, block, cmp]);
  const recon = useMemo(() => (typeof zones === "object" && zones && typeof cmp === "object" && cmp ? reconcileZones(zones, cmp) : []), [zones, cmp]);
  const rgba = useMemo(() => {
    if (!d?.depth) return null;
    if (mode === "depth") return rasterRgba(d.depth, "depth");
    if (mode === "arrival") return d.arrival ? rasterRgba(d.arrival, "arrival") : null;
    if (mode === "velocity") return d.velocity ? rasterRgba(d.velocity, "velocity") : null;
    return typeof cmp === "object" && cmp ? classRgba(cmp.classes) : null;
  }, [d, mode, cmp]);
  const assets = assetRows(a);

  return (
    <section className="whatif-card exp-result" aria-labelledby="exp-result-h">
      <h3 id="exp-result-h">{previous ? "Previous computed result (not the latest run)" : "Computed candidate result"}</h3>
      <p className="whatif-badge"><strong>Experimental.</strong> Computed by a fast solver on this computer. It is uncalibrated and not scientifically validated. Differences from the stored reference are differences between two models, not forecast errors.</p>
      <Rows rows={identityRows(a)} caption="Identity and provenance of this computed result" />

      <h4>{r.cache_hit ? "Original computation timing (cached result)" : "Service-side timing"}</h4>
      <Rows rows={timingRows(r)} caption="Service-side stage timing" />
      <p className="muted small">{TIMING_NOTE}</p>

      <h4>Limitations declared by the service</h4>
      <ul>{r.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
      {r.warnings.length > 0 && <><h4>Warnings</h4><ul>{r.warnings.map((l, i) => <li key={i}>{l}</li>)}</ul></>}

      <h4>Products</h4>
      <div className="table-wrap"><table><caption className="sr-only">Products delivered for this run</caption>
        <thead><tr><th scope="col">Product</th><th scope="col">Status</th><th scope="col">Detail</th></tr></thead>
        <tbody>{assets.map((x) => <tr key={x.role}><th scope="row">{x.title}</th><td>{x.status === "received" ? "Received and verified" : "Unavailable"}</td><td>{x.detail}{x.status === "received" && r.assets[x.role] && <> · <a href={r.assets[x.role]!.url} download={`${r.run_id}-${x.role}.${x.role === "extent_geojson" ? "geojson" : "tif"}`}>Download {x.title}</a></>}</td></tr>)}</tbody></table></div>

      {d?.depth && (
        <>
          <h4>Map preview</h4>
          <div className="seg" role="group" aria-label="Map preview layer">
            {(["depth", "arrival", "velocity", "difference"] as MapMode[]).map((m) => (
              <button key={m} type="button" className={mode === m ? "on" : ""} aria-pressed={mode === m} onClick={() => setMode(m)}>{MAP_LABEL[m]}</button>
            ))}
          </div>
          {d.extent && <label className="check-inline"><input type="checkbox" checked={outline} onChange={(e) => setOutline(e.target.checked)} /> Show wet-extent outline</label>}
          {rgba
            ? <CandidateRasterView width={d.depth.width} height={d.depth.height} geo={d.depth.geo} rgba={rgba} outline={d.extent?.geojson} showOutline={outline && !!d.extent}
                label={`${MAP_LABEL[mode]} for the computed run ${r.run_id}. A table with the same information follows.`} />
            : <p className="muted" role="status">{mode === "arrival" ? (d.unavailable.arrival_time_cog ?? "No arrival raster is available for this run.") : mode === "velocity" ? (d.unavailable.max_velocity_cog ?? "No velocity component raster is available for this run.") : baselineLoading ? "Loading the stored reference for comparison…" : (baselineError ?? "The comparison is not available.")}</p>}
          {mode !== "difference" && <div aria-label={`${MAP_LABEL[mode]} display legend`}>
            <p className="muted small">Display colours ({SCALES[mode].unit}), not validated hazard classes. Grey = unknown; unshaded depth = known depth ≤0.1 m.</p>
            <ul className="legend-list">{SCALES[mode].stops.map(([v, hex], i, all) => <li key={v}><i style={{ background: hex }} aria-hidden />{i === all.length - 1 ? `≥${v}` : `${mode === "depth" && i === 0 ? ">0.1" : v}–<${all[i + 1][0]}`} {SCALES[mode].unit}</li>)}</ul>
          </div>}
          {mode === "velocity" && <p className="muted small">{r.velocity_definition} This is not speed magnitude and is never directly differenced with HEC-RAS velocity.</p>}
          <p className="muted small">{mode === "difference" ? "Unshaded cells have no highlighted wet footprint/change or are not comparable; they can include unknown coverage. This does not prove dry or safe land." : "Preview of the delivered raster at its own resolution. Neutral grey marks cells with no known value (never shown as dry); known dry depth cells are left unshaded."}</p>
          {d.extent && <p className="muted small">Outline: {d.extent.featureCount} feature(s), {d.extent.ringCount} ring(s); bounds in EPSG:32643 {d.extent.bboxUtm.map((v) => Math.round(v).toLocaleString("en-US")).join(", ")}.</p>}
          <div className="table-wrap"><table><caption>Raster summary (table alternative to the preview)</caption>
            <thead><tr><th scope="col">Product</th><th scope="col">Grid</th><th scope="col">Known cells</th><th scope="col">No data</th><th scope="col">Range</th></tr></thead>
            <tbody>{([["Maximum depth (m)", d.depth], ["Arrival (minutes)", d.arrival], ["Velocity component (m/s)", d.velocity]] as const).map(([n, g]) => g
              ? <tr key={n}><th scope="row">{n}</th><td>{g.width}×{g.height}</td><td>{g.valid.toLocaleString("en-US")}</td><td>{g.nodata.toLocaleString("en-US")}</td><td>{g.min === null ? "none" : `${formatValue(g.min, 2)} to ${formatValue(g.max, 2)}`}</td></tr>
              : <tr key={n}><th scope="row">{n}</th><td colSpan={4}>Unavailable</td></tr>)}</tbody></table></div>
        </>
      )}

      <h4>Comparison with the stored reference</h4>
      {!d?.depth && <p role="status">No usable depth raster, so no comparison is possible. {d?.unavailable.max_depth_cog}</p>}
      {d?.depth && baselineLoading && <p role="status" className="muted">Loading the stored reference scenario {r.derived_grid.target_reference_scenario_id}…</p>}
      {d?.depth && !baselineLoading && baselineError && <p className="whatif-warn" role="alert">{baselineError}</p>}
      {typeof cmp === "string" && <p className="whatif-warn" role="alert">Comparison blocked: {cmp}</p>}
      {typeof cmp === "object" && cmp && (
        <>
          <p className="muted small">Candidate compared with <strong>{r.derived_grid.target_reference_scenario_id}</strong> on the same {cmp.width}×{cmp.height} derived grid, {Math.sqrt(cmp.pixelAreaM2).toFixed(3)} m display pixels (rule {cmp.version}). Native solver resolution remains approximately 100 m. Wet means depth above 0.1 m; no-data is unknown, never dry. Velocity is not compared. Both engine and release differ from the reference, so this does not isolate release effects or establish accuracy.</p>
          <div className="table-wrap"><table><caption className="sr-only">Wet-area comparison</caption><tbody>
            <tr><th scope="row">Confirmed newly wet (known in both, wet only in the new run)</th><td>{formatValue(cmp.km2.confirmedGained, 2)} km² ({cmp.wet.confirmedGained.toLocaleString("en-US")} cells)</td></tr>
            <tr><th scope="row">Confirmed no longer wet (known in both, wet only in the stored reference)</th><td>{formatValue(cmp.km2.confirmedLost, 2)} km² ({cmp.wet.confirmedLost.toLocaleString("en-US")} cells)</td></tr>
            <tr><th scope="row">Wet in both</th><td>{formatValue(cmp.km2.bothWet, 2)} km²</td></tr>
            <tr><th scope="row">Recorded only — new run wet where the reference has no data</th><td>{formatValue(cmp.km2.candidateWetUnknownBaseline, 2)} km² <span className="muted">(not counted as gained)</span></td></tr>
            <tr><th scope="row">Recorded only — reference wet where the new run has no data</th><td>{formatValue(cmp.km2.baselineWetUnknownCandidate, 2)} km² <span className="muted">(not counted as lost)</span></td></tr>
          </tbody></table></div>
          <h5>Arrival</h5>
          {cmp.arrival.available
            ? <p>{cmp.arrival.pairedCells.toLocaleString("en-US")} cells have an arrival time in both. Median difference (new run minus reference): {formatValue(cmp.arrival.medianDiffH, 1)} h; mean {formatValue(cmp.arrival.meanDiffH, 2)} h (negative = the new run is earlier). The reference is hourly and the new run is converted by the declared hourly ceiling, so differences below one hour are not resolved.</p>
            : <p role="status">Arrival comparison unavailable: {cmp.arrival.reason}</p>}
          {mode === "difference" && <ul className="legend-list" aria-label="Difference map legend">{CLASS_LABELS.map((l, i) => i === 0 ? null : <li key={l}><i style={{ background: `rgba(${CANDIDATE_CLASS_COLOURS[i].slice(0, 3).join(",")},1)` }} aria-hidden /> {l}</li>)}</ul>}
        </>
      )}
      {typeof zones === "object" && zones && (
        <>
          <h4>Zones to review first</h4>
          <p className="muted small">5 km squares ({zones.version}). Ranked by confirmed newly wet cells, then by median earlier arrival, then by zone ID. This is a review order, not a risk or exposure ranking.{!zones.arrivalAvailable && ` Timing is not used: ${zones.arrivalReason}`}</p>
          {recon.length > 0 && <p className="whatif-warn" role="alert">Zone totals do not match the comparison: {recon.join("; ")}.</p>}
          {zones.ranked.length === 0 ? <p>No zone has a confirmed newly wet area or an eligible earlier arrival.</p> : (
            <div className="table-wrap"><table><caption className="sr-only">Zones ranked for review</caption>
              <thead><tr><th scope="col">Rank</th><th scope="col">Zone</th><th scope="col">Confirmed newly wet (km²)</th><th scope="col">Arrival advance (h; negative = later)</th><th scope="col">Why flagged</th></tr></thead>
              <tbody>{zones.ranked.map((z) => <tr key={z.id}><td>{z.priority?.rank}</td><th scope="row">{z.id}</th><td>{areaText(z.confirmedGainedKm2)}</td><td>{z.medianAdvanceH === null ? "Unavailable" : formatValue(z.medianAdvanceH, 1)}</td><td>{explainCandidateZone(z)}</td></tr>)}</tbody></table></div>
          )}
        </>
      )}
    </section>
  );
}

export default function Experimental({ views, active, onOpenWhatIf }: { views: ScenarioView[]; active: boolean; onOpenWhatIf: () => void }) {
  const { state, controller } = useCompute(active);
  const { caps, run } = state;
  const [peakText, setPeakText] = useState("25000");
  const [blocked, setBlocked] = useState<string | null>(null);
  const peakId = useId(), helpId = useId(), probId = useId();
  const statusRef = useRef<HTMLParagraphElement>(null);
  const peak = peakText.trim() === "" ? Number.NaN : Number(peakText);
  const problem = validatePeak(peak);
  const ready = caps.kind === "ready";
  const lo = ready ? caps.caps.peak_range_m3s[0] : 15000, hi = ready ? caps.caps.peak_range_m3s[1] : 30000;
  const busy = isActive(run.phase);
  const shown = run.current?.products.status === "ready" ? run.current : run.previous;
  const showingPrevious = !!shown && shown !== run.current;
  const refId = shown?.result.derived_grid.target_reference_scenario_id ?? null;
  const refKnown = refId ? views.some((v) => v.id === refId) : false;
  const base = useAsync(refId && shown && shown.products.status === "ready" ? async (sig) => {
    const layers = await getLayers(refId, sig);
    return loadCandidateReference(layers);
  } : null, [refId, shown?.job.job_id, shown?.products.status]);
  // keep keyboard focus in sensible places: announce completion/failure, then let the user continue from the heading
  useEffect(() => { if (run.phase === "completed" || run.phase === "failed" || run.phase === "error") statusRef.current?.focus({ preventScroll: true }); }, [run.phase]);

  return (
    <div className="page-scroll whatif exp" aria-busy={busy}>
      <h2>Experimental computed run</h2>
      <p className="whatif-badge"><strong>New computation, experimental.</strong> This asks a fast solver to compute a flood for a peak release. It is not the stored HEC-RAS reference, it is uncalibrated and it is not scientifically validated. For stored references use <button type="button" className="linklike" onClick={onOpenWhatIf}>What-if</button>.</p>
      <details className="help">
        <summary>How this works and what the results mean</summary>
        <ul>
          <li>Enter a peak release between {lo.toLocaleString("en-US")} and {hi.toLocaleString("en-US")} m³/s and press Run. Exactly that value is computed — nothing is rounded to a stored case.</li>
          <li>The job can take a while. You can stay on this page; status is announced as it changes. Leaving the page pauses status checks and returning continues the same job.</li>
          <li>The result is shown only after the service's answers match what was sent (peak, configuration, identities) and every downloaded product matches its checksum.</li>
          <li>The comparison uses the stored reference of the same grid. Newly wet means known depth in both, above 0.1 m only in the new run; cells with no data are reported separately.</li>
          <li>Keyboard: Tab to the peak box, type a value, press Enter to run. Tab to “Stop waiting” to pause checks.</li>
        </ul>
      </details>

      {caps.kind === "loading" && <p role="status" className="muted">Checking what the computation service offers…</p>}
      {caps.kind === "unavailable" && <div className="banner" role="alert">Computation service unavailable: {caps.message} Explore, Compare, What-if (stored) and Evidence still work.<button type="button" className="btn" onClick={() => void controller.loadCapabilities()}><RefreshCw size={14} aria-hidden /> Try again</button></div>}
      {caps.kind === "invalid" && <div className="banner" role="alert">The service's capability document is not valid, so computation is switched off.<ul>{caps.problems.slice(0, 6).map((p, i) => <li key={i}>{p}</li>)}</ul><button type="button" className="btn" onClick={() => void controller.loadCapabilities()}><RefreshCw size={14} aria-hidden /> Try again</button></div>}
      {caps.kind === "disabled" && <div className="banner" role="alert">Computation is switched off by the service: {caps.reason}<button type="button" className="btn" onClick={() => void controller.loadCapabilities()}><RefreshCw size={14} aria-hidden /> Check again</button></div>}

      <form className="whatif-form" onSubmit={async (e) => { e.preventDefault(); if (!ready || busy) return; setBlocked(await controller.run(peak)); }} aria-describedby={`${helpId} ${probId}`}>
        <label htmlFor={peakId}>Peak release (m³/s)</label>
        <input id={peakId} type="number" inputMode="numeric" min={lo} max={hi} step="any" value={peakText} onChange={(e) => { setPeakText(e.target.value); setBlocked(null); }} disabled={!ready || busy} aria-invalid={!!problem} aria-describedby={`${helpId} ${probId}`} />
        <p id={helpId} className="muted small">Allowed {lo.toLocaleString("en-US")} to {hi.toLocaleString("en-US")} m³/s. Nothing is sent until you press Run.</p>
        <p id={probId} className="whatif-warn" role={(problem && peakText !== "") || blocked ? "alert" : undefined}>{blocked ?? (problem && peakText !== "" ? problem : "")}</p>
        <div className="row-gap">
          <button type="submit" className="btn primary" disabled={!ready || busy || !!problem}><Play size={14} aria-hidden /> {busy ? "Running…" : "Run computation"}</button>
          {busy && <button type="button" className="btn" onClick={() => controller.cancelWaiting()}><Square size={14} aria-hidden /> Stop waiting</button>}
        </div>
      </form>

      <p ref={statusRef} tabIndex={-1} role="status" aria-live="polite" className={`exp-status ${busy ? "busy" : ""}`}>
        {PHASE_TEXT[run.phase]}{run.request ? ` Request for ${run.request.peak_release_m3s.toLocaleString("en-US")} m³/s.` : ""}{run.retrying ? " Retrying after a brief connection problem…" : ""}{busy && run.polls > 0 ? ` Status checks made: ${run.polls}.` : ""}
      </p>

      {run.phase === "failed" && run.failedJob?.error && <div className="banner" role="alert">The computation failed: {run.failedJob.error.message} <span className="muted">(code {run.failedJob.error.code}; job {run.failedJob.job_id})</span></div>}
      {run.phase === "error" && run.error && (
        <div className="banner" role="alert">
          <div>{run.error.message}{run.error.problems.length > 0 && <ul>{run.error.problems.slice(0, 8).map((p, i) => <li key={i}>{p}</li>)}</ul>}</div>
          {run.error.resumable && <button type="button" className="btn" onClick={() => void controller.checkAgain()}><RefreshCw size={14} aria-hidden /> Check this job again</button>}
        </div>
      )}
      {(run.phase === "failed" || run.phase === "error" || busy) && run.previous && !run.current && <p className="muted" role="note">The earlier computed result below is from run {run.previous.result.run_id} ({run.previous.request.peak_release_m3s.toLocaleString("en-US")} m³/s), not the run above.</p>}

      {shown && shown.products.status === "ready" && !refKnown && refId && <p className="whatif-warn" role="alert">The reference scenario {refId} is not among the loaded stored scenarios, so no comparison can be shown.</p>}
      {shown && (shown.products.status === "ready"
        ? <ResultView a={shown} refArrival={views.find((v) => v.id === refId)?.detail.arrival ?? null} baselineGrid={base.data ?? null} baselineError={refKnown ? base.error : null} baselineLoading={refKnown && base.loading} previous={showingPrevious} />
        : <p role="status" className="muted">Downloading and verifying products…</p>)}
    </div>
  );
}
