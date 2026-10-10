import type { ScenarioRecord } from "./lib/api";
import { describeScenario, sortScenarios, type ScenarioInfo } from "./lib/scenarios";

export interface ScenarioView extends ScenarioRecord { id: string; info: ScenarioInfo }

export function toViews(records: ScenarioRecord[]): ScenarioView[] {
  return sortScenarios(records.map((r) => ({ ...r, id: r.summary.scenario_id, info: describeScenario(r.summary.scenario_id, r.summary.scenario_type) })));
}
