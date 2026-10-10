import { useEffect, useMemo, useState } from "react";
import { loadAllScenarios } from "./lib/api";
import { useAsync } from "./hooks/useAsync";
import { useHealth } from "./hooks/useHealth";
import { toViews } from "./model";
import Sidebar, { type Section } from "./components/Sidebar";
import TopBar from "./components/TopBar";
import Banner from "./components/Banner";
import Explore from "./pages/Explore";
import Compare from "./pages/Compare";
import Evidence from "./pages/Evidence";

export default function App() {
  const [section, setSection] = useState<Section>("explore");
  const [selected, setSelected] = useState<string | undefined>();
  const health = useHealth();
  const all = useAsync((sig) => loadAllScenarios(sig), []);
  const views = useMemo(() => (all.data ? toViews(all.data) : []), [all.data]);
  // reload data automatically once the backend comes back
  useEffect(() => { if (health === "connected" && all.error) all.reload(); }, [health]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!selected && views.length) setSelected(views[0].id); }, [views, selected]);
  const current = views.find((v) => v.id === selected);
  const titles: Record<Section, string> = { explore: "Explore flood scenarios", compare: "Compare scenarios", evidence: "Evidence and downloads" };

  return (
    <div className="shell">
      <Sidebar section={section} onSection={setSection} scenarios={views} selected={selected} onSelect={setSelected} loading={all.loading} />
      <div className="workspace">
        <TopBar status={health} title={titles[section]} />
        <main>
          {all.error && <Banner message={`${all.error} Start it with START_UKAI.cmd, then try again.`} onRetry={all.reload} />}
          {all.loading && !all.error && <p className="muted pad">Loading scenarios…</p>}
          {!all.loading && !all.error && views.length === 0 && <p className="pad">The API returned no scenarios.</p>}
          {current && section === "explore" && <Explore key={current.id} s={current} onEvidence={() => setSection("evidence")} />}
          {views.length > 0 && section === "compare" && <Compare items={views} />}
          {current && section === "evidence" && <Evidence key={current.id} s={current} />}
        </main>
      </div>
    </div>
  );
}
