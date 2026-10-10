import type { ScenarioView } from "../model";
import type { PrototypeLayers } from "./api";
import type { DiffResult } from "./compare";
import type { ZoneResult } from "./zones";

type Reference = Pick<ScenarioView, "id" | "info" | "detail">;
const value = (v: number | null, unit: string) => v === null || !Number.isFinite(v) ? "Not available" : `${v.toFixed(2)} ${unit}`;
const field = (v: string) => JSON.stringify(v); // Preserve identity as data, including newlines and delimiters.

/** A derived review note, never an imported model result, approval or scientific report. */
export function buildComparisonBriefing(b: Reference, c: Reference, bl: PrototypeLayers, cl: PrototypeLayers, diff: DiffResult, zones: ZoneResult | null, generatedAt: string): string {
  if (bl.scenario_id !== b.id || cl.scenario_id !== c.id || bl.run_id !== b.detail.run_id || cl.run_id !== c.detail.run_id)
    throw new Error("The comparison metadata does not match the selected scenario/run identities.");
  const reference = (name: string, s: Reference, layers: PrototypeLayers) => [
    `## ${name}: ${s.info.long}`, `Scenario ID: ${field(s.id)}`, `Run ID: ${field(s.detail.run_id)}`,
    `Engine: ${field(s.detail.engine.name)}; software ${field(s.detail.engine.software_version)}`,
    `Peak release: ${value(s.detail.parameters.peak_release_m3s, "m³/s")}`,
    `Original manifest checksum: ${field(s.detail.provenance.source_manifest_checksum)}`,
    ...layers.layers.map((l) => `Asset ${field(l.asset_type)}: ${field(l.checksum)}; CRS ${field(l.crs)}; unit ${field(l.unit)}`),
    "Limitations:", ...s.detail.limitations.map((l) => `- ${l.replace(/\r?\n/g, " ")}`), "",
  ];
  return [
    "# Ukai stored-scenario comparison briefing", `Generated: ${generatedAt}`,
    "Derived local review note. Stored HEC-RAS simulations; uncalibrated and not scientifically validated. No fresh simulation or ML prediction.", "",
    ...reference("Baseline", b, bl), ...reference("Candidate", c, cl),
    "## Comparison: candidate minus baseline", `Rule: ${diff.version}; aligned native grid; depth wet threshold > 0.1 m.`,
    `Pixel area: ${value(diff.pixelAreaM2, "m²")}`,
    `Candidate-only recorded wet footprint: ${value(diff.km2.newWet, "km²")} (${diff.counts.newWet} cells)`,
    `Baseline-only recorded wet footprint: ${value(diff.km2.lostWet, "km²")} (${diff.counts.lostWet} cells)`,
    `Common wet footprint: ${value(diff.km2.commonWet, "km²")}`,
    `Depth coverage: ${diff.counts.bothValid} both-valid; ${diff.counts.baselineOnlyValid} baseline-only valid; ${diff.counts.candidateOnlyValid} candidate-only valid cells.`,
    `Paired depth mean signed change: ${value(diff.depth.meanDiffM, "m")} (${diff.depth.pairedCells} both-wet cells)`,
    `Paired arrival mean signed change: ${value(diff.arrival.meanDiffH, "h")}`,
    `Paired arrival median signed change: ${value(diff.arrival.medianDiffH, "h")} (${diff.arrival.pairedCells} both-valid arrival cells)`,
    "Negative arrival change means earlier candidate arrival; this is elapsed model time, not a real historical clock.",
    "Candidate-only/baseline-only footprints include unmatched coverage. Nodata is unknown, not observed dry land or safe land.", "",
    "## Coordinate review zones", zones ? `${zones.ranked.length} of ${zones.zones.length} zones flagged; rule ${zones.version}.` : "Not available",
    ...(zones ? zones.ranked.slice(0, 3).map((z) => `${z.id}: candidate-only wet ${value(z.newWetKm2, "km²")}; paired arrival change ${value(z.medianAdvanceH === null ? null : -z.medianAdvanceH, "h")}; ${z.pairedArrivalCells} paired cells; timing unavailable reason: ${(z.timingUnavailableReason ?? "none").replace(/\.$/, "")}.`) : []),
    "Fixed coordinate zones, not administrative areas. Priority for review is not an evacuation order or recommended dam release.",
    "Population, buildings, roads and facilities: not assessed; unavailable, not zero.",
    "Velocity differences are not assessed. No forecast accuracy, scientific approval or operational safety is asserted.", "",
  ].join("\n");
}
