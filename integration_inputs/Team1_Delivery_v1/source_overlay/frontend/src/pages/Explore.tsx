import { useCallback, useState } from "react";
import type { ScenarioView } from "../model";
import { getLayers } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import type { ViewMode } from "../lib/scales";
import { clampHours, elapsedMinutes, timelineMaxHours, type TimelineColorBy } from "../lib/timeline";
import FloodMap from "../map/FloodMap";
import MapControls from "../components/MapControls";
import Legend from "../components/Legend";
import SummaryRow from "../components/SummaryRow";
import Inspector from "../components/Inspector";
import Banner from "../components/Banner";
import TimelinePanel from "../components/TimelinePanel";

export default function Explore({ s, onEvidence }: { s: ScenarioView; onEvidence: () => void }) {
  const [mode, setMode] = useState<ViewMode>("depth");
  const [opacity, setOpacity] = useState(0.85);
  const [fit, setFit] = useState(0);
  const [cursor, setCursor] = useState<[number, number] | null>(null);
  const [hours, setHours] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [colorBy, setColorBy] = useState<TimelineColorBy>("arrival");
  const layers = useAsync((sig) => getLayers(s.id, sig), [s.id]);
  // Explore is keyed by scenario id in App, so changing scenario remounts this page: time resets to 0
  // and the previous scenario's grid cannot stay on screen.
  const maxHours = timelineMaxHours(s.detail.coverage_start, s.detail.coverage_end);
  const setHoursClamped = useCallback((h: number) => setHours(clampHours(h, maxHours ?? 0)), [maxHours]);
  const changeMode = (m: ViewMode) => { setMode(m); setPlaying(false); };
  const reset = () => { setPlaying(false); setHours(0); };
  return (
    <div className="explore">
      <div className="explore-main">
        <SummaryRow s={s} />
        <MapControls mode={mode} onMode={changeMode} opacity={opacity} onOpacity={setOpacity} onFit={() => setFit((n) => n + 1)} />
        {mode === "timeline" && (
          <TimelinePanel hours={hours} maxHours={maxHours} playing={playing} colorBy={colorBy} onHours={setHoursClamped}
            onPlaying={setPlaying} onColorBy={setColorBy} onReset={reset} />
        )}
        {layers.error && <Banner message={layers.error} onRetry={layers.reload} />}
        <div className="map-wrap">
          <FloodMap layers={layers.data} mode={mode} opacity={opacity} fitToken={fit} label={`${s.info.long} map`} onCursor={setCursor}
            timeline={{ elapsedMin: elapsedMinutes(hours), colorBy }} />
          <Legend mode={mode} colorBy={colorBy} />
          <div className="coord" aria-live="off">{cursor ? `E ${Math.round(cursor[0]).toLocaleString("en-US")} m · N ${Math.round(cursor[1]).toLocaleString("en-US")} m (EPSG:32643)` : "EPSG:32643 · metres · no basemap"}</div>
        </div>
      </div>
      <Inspector s={s} onEvidence={onEvidence} />
    </div>
  );
}
