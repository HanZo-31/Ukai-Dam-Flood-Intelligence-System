import { useEffect, useMemo, useRef, useState } from "react";
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
import WhatIf from "./pages/WhatIf";
import Experimental from "./pages/Experimental";

type Page = Section | "experimental";

export default function App() {
  const [page, setPage] = useState<Page>("explore");
  // The experimental computed run is a sub-view opened from What-if; the navigation keeps What-if highlighted while it is shown.
  const section: Section = page === "experimental" ? "whatif" : page;
  const setSection = (s: Section) => setPage(s);
  const [selected, setSelected] = useState<string | undefined>();
  const content = useRef<HTMLElement>(null);
  const previousSection = useRef(page);
  useEffect(() => {
    if (previousSection.current !== page) {
      content.current?.focus({ preventScroll: true });
      content.current?.scrollTo({ top: 0 });
    }
    previousSection.current = page;
  }, [page]);
  const health = useHealth();
  const all = useAsync((sig) => loadAllScenarios(sig), []);
  const views = useMemo(() => (all.data ? toViews(all.data) : []), [all.data]);
  // reload data automatically once the backend comes back
  useEffect(() => { if (health === "connected" && all.error) all.reload(); }, [health]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!selected && views.length) setSelected(views[0].id); }, [views, selected]);
  const current = views.find((v) => v.id === selected);
  const titles: Record<Page, string> = { explore: "Explore flood scenarios", compare: "Compare scenarios", whatif: "What-if stored reference", experimental: "Experimental computed run", evidence: "Evidence and downloads" };

  return (
    <div className="shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <Sidebar section={section} onSection={setSection} scenarios={views} selected={selected} onSelect={setSelected} loading={all.loading} />
      <div className="workspace">
        <TopBar status={health} title={page === "explore" ? "Explore scenarios" : titles[page]}
          subtitle={page === "explore" ? "Visualise the four stored flood reference simulations." : undefined} />
        <main id="main-content" tabIndex={-1} ref={content}>
          {all.error && <Banner message={`${all.error} Start it with START_SIMULATION.cmd, then try again.`} onRetry={all.reload} />}
          {all.loading && !all.error && <p className="muted pad">Loading scenarios…</p>}
          {!all.loading && !all.error && views.length === 0 && <p className="pad">The API returned no scenarios.</p>}
          {current && section === "explore" && <Explore key={current.id} s={current} onEvidence={() => setSection("evidence")} />}
          {views.length > 0 && section === "compare" && <Compare items={views} />}
          {views.length > 0 && page === "whatif" && <WhatIf views={views} onOpenScenario={(id) => { setSelected(id); setSection("explore"); }} onOpenExperimental={() => setPage("experimental")} />}
          {views.length > 0 && <div hidden={page !== "experimental"}><Experimental views={views} active={page === "experimental"} onOpenWhatIf={() => setPage("whatif")} /></div>}
          {current && section === "evidence" && <Evidence key={current.id} s={current} />}
        </main>
      </div>
    </div>
  );
}
