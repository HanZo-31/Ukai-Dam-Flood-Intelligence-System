import type { ScenarioView } from "../model";
import EvidencePanel from "../components/EvidencePanel";
import MethodsPanel from "../components/MethodsPanel";

export default function Evidence({ s }: { s: ScenarioView }) {
  return (
    <div className="page-scroll">
      <h2>Evidence — {s.info.long}</h2>
      <p className="muted">Everything below is read from the API for this scenario. Missing values are shown as unavailable, never as zero.</p>
      <EvidencePanel s={s} />
      <MethodsPanel />
    </div>
  );
}
