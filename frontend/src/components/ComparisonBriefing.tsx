import type { ScenarioView } from "../model";
import type { PrototypeLayers } from "../lib/api";
import type { DiffResult } from "../lib/compare";
import type { ZoneResult } from "../lib/zones";
import { buildComparisonBriefing } from "../lib/briefing";

export default function ComparisonBriefing({ baseline, candidate, baseLayers, candLayers, diff, zones }: {
  baseline: ScenarioView; candidate: ScenarioView; baseLayers: PrototypeLayers; candLayers: PrototypeLayers; diff: DiffResult; zones: ZoneResult | null;
}) {
  const download = () => {
    const text = buildComparisonBriefing(baseline, candidate, baseLayers, candLayers, diff, zones, new Date().toISOString());
    const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url; link.download = "UKAI_COMPARISON_BRIEFING.md"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <section className="briefing" aria-labelledby="briefing-title">
    <h3 id="briefing-title">Comparison briefing</h3>
    <p><strong>{baseline.info.short} → {candidate.info.short}</strong>: {diff.km2.newWet.toFixed(2)} km² candidate-only and {diff.km2.lostWet.toFixed(2)} km² baseline-only recorded wet footprint. These include unmatched coverage, not confirmed dry-to-wet transitions.</p>
    <p>Median paired arrival change: {diff.arrival.medianDiffH === null ? "Not available" : `${diff.arrival.medianDiffH.toFixed(2)} h`} across {diff.arrival.pairedCells.toLocaleString("en-US")} paired cells. Negative means earlier candidate arrival. {zones ? `${zones.ranked.length} coordinate zones flagged for review.` : "Zone summary unavailable."}</p>
    <p className="muted">Download a derived Markdown note with the selected run IDs, asset checksums, coverage and limitations. It is not a new model result, approval or operational recommendation.</p>
    <button type="button" className="btn" onClick={download}>Download comparison briefing</button>
  </section>;
}
