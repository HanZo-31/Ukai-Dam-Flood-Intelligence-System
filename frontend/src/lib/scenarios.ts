import type { PrototypeDetail } from "./api";

export interface ScenarioInfo {
  id: string;
  short: string; // H02, 2006
  long: string; // H02 · Hypothetical release
  kindLabel: string; // Hypothetical release | Reconstructed historical
  historical: boolean;
}

/** Friendly names derived from the API ids and type; nothing is hard-coded to a fixed id. */
export function describeScenario(id: string, type: string): ScenarioInfo {
  const historical = type === "historical_replay";
  const h = /-h(\d{1,2})-/i.exec(id);
  const year = /(?:^|-)((?:19|20)\d{2})(?:-|$)/.exec(id);
  const short = historical ? (year ? year[1] : id) : h ? `H${h[1].padStart(2, "0")}` : id;
  const kindLabel = historical ? "Reconstructed historical" : "Hypothetical release";
  return { id, short, long: `${short} · ${kindLabel}`, kindLabel, historical };
}

export function sortScenarios<T extends { id: string; info: ScenarioInfo }>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    if (a.info.historical !== b.info.historical) return a.info.historical ? 1 : -1;
    return a.info.short.localeCompare(b.info.short, undefined, { numeric: true });
  });
}

export function peakRelease(d: Pick<PrototypeDetail, "parameters"> | undefined): number | null {
  const v = d?.parameters?.peak_release_m3s;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}
