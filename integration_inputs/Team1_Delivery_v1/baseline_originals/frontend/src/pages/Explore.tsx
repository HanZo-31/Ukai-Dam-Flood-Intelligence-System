import { useState } from "react";
import type { ScenarioView } from "../model";
import { getLayers } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import type { ViewMode } from "../lib/scales";
import FloodMap from "../map/FloodMap";
import MapControls from "../components/MapControls";
import Legend from "../components/Legend";
import SummaryRow from "../components/SummaryRow";
import Inspector from "../components/Inspector";
import Banner from "../components/Banner";

export default function Explore({ s, onEvidence }: { s: ScenarioView; onEvidence: () => void }) {
  const [mode, setMode] = useState<ViewMode>("depth");
  const [opacity, setOpacity] = useState(0.85);
  const [fit, setFit] = useState(0);
  const [cursor, setCursor] = useState<[number, number] | null>(null);
  const layers = useAsync((sig) => getLayers(s.id, sig), [s.id]);
  return (
    <div className="explore">
      <div className="explore-main">
        <SummaryRow s={s} />
        <MapControls mode={mode} onMode={setMode} opacity={opacity} onOpacity={setOpacity} onFit={() => setFit((n) => n + 1)} />
        {layers.error && <Banner message={layers.error} onRetry={layers.reload} />}
        <div className="map-wrap">
          <FloodMap layers={layers.data} mode={mode} opacity={opacity} fitToken={fit} label={`${s.info.long} map`} onCursor={setCursor} />
          <Legend mode={mode} />
          <div className="coord" aria-live="off">{cursor ? `E ${Math.round(cursor[0]).toLocaleString("en-US")} m · N ${Math.round(cursor[1]).toLocaleString("en-US")} m (EPSG:32643)` : "EPSG:32643 · metres · no basemap"}</div>
        </div>
      </div>
      <Inspector s={s} onEvidence={onEvidence} />
    </div>
  );
}
