import { useEffect, useMemo, useState } from "react";
import type View from "ol/View";
import { ArrowLeftRight } from "lucide-react";
import type { ScenarioView } from "../model";
import type { PrototypeLayers } from "../lib/api";
import { loadGrid } from "../lib/rasterCache";
import { arrivalChangeBins, ARRIVAL_BIN_LABELS, compareGrids, COMPARE_VERSION, WET_THRESHOLD_M, type DiffResult, type Grid } from "../lib/compare";
import { computeZones, explainZone, ZONE_RULE_VERSION, type ZoneResult, type ZoneRow } from "../lib/zones";
import DiffMap, { ARRIVAL_COLOURS, DIFF_COLOURS, EXTENT_PALETTE } from "../map/DiffMap";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "computing" }
  | { kind: "unavailable"; reason: string }
  | { kind: "ready"; diff: DiffResult; zones: ZoneResult | string; grid: Grid; cand: Grid };

const km2 = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const int = (v: number) => v.toLocaleString("en-US");
const signed = (v: number | null, d: number, unit: string) => (v === null ? "Not available" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(d)} ${unit}`);
const REASON: Record<string, string> = { new_flooded_area: "Newly flooded area", earlier_arrival: "Earlier arrival" };

export default function DiffPanel({ baseline, candidate, baseLayers, candLayers, view, fit, onSwap }: {
  baseline: ScenarioView | undefined; candidate: ScenarioView | undefined; baseLayers: PrototypeLayers | undefined; candLayers: PrototypeLayers | undefined;
  view: View; fit: number; onSwap: () => void;
}) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const [opacity, setOpacity] = useState(0.85);
  const [selected, setSelected] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [layer, setLayer] = useState<"extent" | "arrival">("extent");

  useEffect(() => {
    setSelected(null);
    if (!baseLayers || !candLayers) { setState({ kind: "idle" }); return; }
    let cancelled = false;
    setState({ kind: "loading" });
    Promise.all([loadGrid(baseLayers), loadGrid(candLayers)]).then(([b, c]) => {
      if (cancelled) return;
      setState({ kind: "computing" });
      // let the "computing" state paint before the (synchronous) arithmetic
      window.setTimeout(() => {
        if (cancelled) return;
        const diff = compareGrids(b, c);
        if (typeof diff === "string") { setState({ kind: "unavailable", reason: diff }); return; }
        setState({ kind: "ready", diff, zones: computeZones(b, c), grid: b, cand: c });
      }, 30);
    }, (e: unknown) => { if (!cancelled) setState({ kind: "unavailable", reason: e instanceof Error ? e.message : "The comparison inputs could not be loaded." }); });
    return () => { cancelled = true; };
  }, [baseLayers, candLayers]);

  const zoneResult = state.kind === "ready" && typeof state.zones !== "string" ? state.zones : null;
  const highlight = useMemo(() => {
    const z = zoneResult?.zones.find((x) => x.id === selected);
    return z ? z.bounds : null;
  }, [zoneResult, selected]);
  const arrival = useMemo(() => (state.kind === "ready" && layer === "arrival" ? arrivalChangeBins(state.grid, state.cand) : null), [state, layer]);
  const bn = baseline?.info.long ?? "Baseline", cn = candidate?.info.long ?? "Candidate";

  return (
    <section aria-labelledby="diff-h" className="diff-panel">
      <h3 id="diff-h">Difference: candidate minus baseline</h3>
      <div className="role-row">
        <div><span className="role-tag">Baseline</span> {bn}</div>
        <button type="button" className="btn" onClick={onSwap}><ArrowLeftRight size={14} aria-hidden /> Swap baseline and candidate</button>
        <div><span className="role-tag cand">Candidate</span> {cn}</div>
      </div>
      <p className="muted">
        Stored HEC-RAS reference scenarios compared on their shared grid. Simulated results, uncalibrated and not scientifically validated.
        A cell counts as flooded when maximum depth is above {WET_THRESHOLD_M} m. Differences are always candidate minus baseline ({COMPARE_VERSION}).
      </p>

      {(state.kind === "loading" || state.kind === "computing") && <p role="status" className="muted">{state.kind === "loading" ? "Reading the depth and arrival rasters…" : "Computing differences…"}</p>}
      {state.kind === "unavailable" && <div className="banner" role="alert">Comparison unavailable: {state.reason}</div>}

      {state.kind === "ready" && (
        <>
          <div className="diff-grid">
            <div>
              <div className="seg" role="group" aria-label="Difference layer">
                <button type="button" className={layer === "extent" ? "on" : ""} aria-pressed={layer === "extent"} onClick={() => setLayer("extent")}>Flood extent</button>
                <button type="button" className={layer === "arrival" ? "on" : ""} aria-pressed={layer === "arrival"} onClick={() => setLayer("arrival")}>Arrival time</button>
              </div>
              {layer === "arrival" && typeof arrival === "string" && <div className="banner" role="alert">Arrival difference unavailable: {arrival}</div>}
              <div className="map-wrap short">
                {layer === "extent" || arrival === null || typeof arrival === "string"
                  ? <DiffMap classes={state.diff.classes} palette={EXTENT_PALETTE} geo={state.grid.geo} width={state.grid.width} height={state.grid.height} view={view} opacity={opacity} highlight={highlight} fitToken={fit} label="Flood extent difference map" />
                  : <DiffMap classes={arrival.bins} palette={ARRIVAL_COLOURS} geo={state.grid.geo} width={state.grid.width} height={state.grid.height} view={view} opacity={opacity} highlight={highlight} fitToken={fit} label="Arrival time difference map" />}
              </div>
              {layer === "extent" || arrival === null || typeof arrival === "string" ? (
                <div className="diff-key" aria-label="Difference map key">
                  <span><i style={{ background: `rgba(${DIFF_COLOURS.new.join(",")})` }} /> New flooded (candidate only)</span>
                  <span><i style={{ background: `rgba(${DIFF_COLOURS.common.join(",")})` }} /> Flooded in both</span>
                  <span><i style={{ background: `rgba(${DIFF_COLOURS.lost.join(",")})` }} /> Baseline only (no longer flooded)</span>
                </div>
              ) : (
                <div className="diff-key" aria-label="Arrival difference key">
                  {ARRIVAL_BIN_LABELS.map((label, k) => k === 0 ? null : (
                    <span key={k}><i style={{ background: `rgba(${ARRIVAL_COLOURS[k].join(",")})` }} /> {label} ({int(arrival.counts[k])} cells)</span>
                  ))}
                  <span className="muted">Cells without an arrival in both scenarios are not coloured ({int(arrival.counts[0])} cells).</span>
                </div>
              )}
              <label className="opacity">Difference opacity
                <input type="range" min={0.1} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} aria-label="Difference layer opacity" />
              </label>
            </div>
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Extent and paired differences, candidate minus baseline</caption>
                <thead><tr><th>Measure</th><th>Value</th></tr></thead>
                <tbody>
                  <tr><th scope="row">New flooded area (candidate only)</th><td>{km2(state.diff.km2.newWet)} km² <span className="muted">({int(state.diff.counts.newWet)} cells)</span></td></tr>
                  <tr><th scope="row">Flooded in both</th><td>{km2(state.diff.km2.commonWet)} km² <span className="muted">({int(state.diff.counts.commonWet)} cells)</span></td></tr>
                  <tr><th scope="row">Baseline-only flooded area</th><td>{km2(state.diff.km2.lostWet)} km² <span className="muted">({int(state.diff.counts.lostWet)} cells)</span></td></tr>
                  <tr><th scope="row">Net change in flooded area</th><td>{signed(state.diff.km2.netChange, 2, "km²")}</td></tr>
                  <tr><th scope="row">Depth coverage: valid only in baseline / only in candidate</th><td>{int(state.diff.counts.baselineOnlyValid)} / {int(state.diff.counts.candidateOnlyValid)} cells <span className="muted">(not counted as dry)</span></td></tr>
                  <tr><th scope="row">Depth change, cells flooded in both (mean)</th><td>{signed(state.diff.depth.meanDiffM, 2, "m")} <span className="muted">({int(state.diff.depth.pairedCells)} cells)</span></td></tr>
                  <tr><th scope="row">Arrival change, cells with an arrival in both (median / mean)</th><td>{signed(state.diff.arrival.medianDiffH, 1, "h")} / {signed(state.diff.arrival.meanDiffH, 2, "h")} <span className="muted">({int(state.diff.arrival.pairedCells)} cells; negative = candidate earlier)</span></td></tr>
                  <tr><th scope="row">Candidate earlier / later / same arrival</th><td>{int(state.diff.arrival.earlier)} / {int(state.diff.arrival.later)} / {int(state.diff.arrival.same)} cells</td></tr>
                  <tr><th scope="row">Arrival coverage: valid only in baseline / only in candidate</th><td>{int(state.diff.arrival.baselineOnlyValid)} / {int(state.diff.arrival.candidateOnlyValid)} cells</td></tr>
                </tbody>
              </table>
              <p className="muted">One pixel is {state.diff.pixelAreaM2.toFixed(1)} m² (|a·e − b·d| of the raster transform); km² = cells × pixel area ÷ 1,000,000. Maximum velocity is not compared because its definition can differ between engines.</p>
            </div>
          </div>

          <h3>Coordinate review zones</h3>
          {typeof state.zones === "string" && <div className="banner" role="alert">Review zones unavailable: {state.zones}</div>}
          {zoneResult && <ZoneTable zones={zoneResult} selected={selected} onSelect={setSelected} showAll={showAll} onShowAll={setShowAll} />}
        </>
      )}
    </section>
  );
}

function ZoneTable({ zones, selected, onSelect, showAll, onShowAll }: { zones: ZoneResult; selected: string | null; onSelect: (id: string | null) => void; showAll: boolean; onShowAll: (b: boolean) => void }) {
  const rows: ZoneRow[] = showAll ? zones.zones : zones.ranked;
  return (
    <div>
      <p className="muted">
        Fixed {zones.zoneSizeM / 1000} km squares of the projected map grid (EPSG:32643), not administrative areas; each raster cell belongs to exactly one zone ({ZONE_RULE_VERSION}).
        “Priority for review” orders zones for checking, first by newly flooded area, then by how much earlier the candidate reaches cells (median over cells with an arrival time in both,
        needing at least {zones.minPairedCells} paired cells covering {zones.minPairedFraction * 100}% of cells with an arrival in either scenario). It is not an evacuation order or a recommended release.
      </p>
      <p>{zones.ranked.length === 0 ? "No zone is flagged: the candidate adds no flooded area and reaches no zone earlier." : `${zones.ranked.length} of ${zones.zones.length} zones are flagged for review.`}
        {" "}Reconciliation: zones total {km2(zones.totals.newWetKm2)} km² new flooded and {km2(zones.totals.lostWetKm2)} km² baseline-only flooded.
        <button type="button" className="btn" onClick={() => onShowAll(!showAll)}>{showAll ? "Show flagged zones only" : `Show all ${zones.zones.length} zones`}</button></p>
      {rows.length > 0 && (
        <div className="table-wrap zone-table">
          <table>
            <caption className="sr-only">Coordinate review zones</caption>
            <thead><tr><th>Priority</th><th>Zone</th><th>Why</th><th>New flooded (km²)</th><th>Baseline-only (km²)</th><th>Median arrival change (h)</th><th>Paired cells</th><th>Zone in raster</th></tr></thead>
            <tbody>
              {rows.map((z) => (
                <tr key={z.id} className={selected === z.id ? "sel" : ""}>
                  <td>{z.priority ? z.priority.rank : "—"}</td>
                  <th scope="row">
                    <button type="button" className="link" aria-pressed={selected === z.id} onClick={() => onSelect(selected === z.id ? null : z.id)}>{z.id}</button>
                    <div className="muted small">{explainZone(z)}</div>
                  </th>
                  <td>{z.priority ? REASON[z.priority.reason] : "Not flagged"}</td>
                  <td>{km2(z.newWetKm2)}</td><td>{km2(z.lostWetKm2)}</td>
                  <td>{z.medianAdvanceH === null ? <span title={z.timingUnavailableReason ?? undefined}>Not available</span> : signed(-z.medianAdvanceH, 1, "h")}</td>
                  <td>{int(z.pairedArrivalCells)}</td><td>{(z.rasterCoverage * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted small">Arrival change = candidate minus baseline, so a negative value means the candidate reaches the zone earlier. “Not available” means too few paired cells; it is never shown as zero. Exposure (people, buildings, roads) is not available for these zones.</p>
    </div>
  );
}
