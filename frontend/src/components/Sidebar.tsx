import { Compass, GitCompare, FileCheck2, Waves, SlidersHorizontal } from "lucide-react";
import type { ScenarioView } from "../model";

export type Section = "explore" | "compare" | "whatif" | "evidence";
const NAV: { id: Section; label: string; icon: typeof Compass }[] = [
  { id: "explore", label: "Explore", icon: Compass }, { id: "compare", label: "Compare", icon: GitCompare }, { id: "whatif", label: "What-if", icon: SlidersHorizontal }, { id: "evidence", label: "Evidence", icon: FileCheck2 },
];

export default function Sidebar(p: { section: Section; onSection: (s: Section) => void; scenarios: ScenarioView[]; selected: string | undefined; onSelect: (id: string) => void; loading: boolean }) {
  return (
    <aside className="sidebar">
      <div className="brand"><Waves size={22} aria-hidden /> <span>Ukai Flood Explorer</span></div>
      <nav aria-label="Sections">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" className={`nav ${p.section === id ? "on" : ""}`} aria-current={p.section === id ? "page" : undefined} onClick={() => p.onSection(id)}>
            <Icon size={17} aria-hidden /> {label}
          </button>
        ))}
      </nav>
      <div className="side-title">Scenarios</div>
      <ul className="scen-list">
        {p.loading && <li className="side-muted">Loading scenarios…</li>}
        {p.scenarios.map((s) => (
          <li key={s.id}>
            <button type="button" className={`scen ${p.selected === s.id ? "on" : ""}`} aria-pressed={p.selected === s.id} onClick={() => p.onSelect(s.id)}>
              <strong>{s.info.short}</strong>
              <span>{s.info.kindLabel}</span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
