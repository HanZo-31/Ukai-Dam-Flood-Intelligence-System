import { useCallback, useRef, useState } from "react";
import type { ScenarioView } from "../model";
import { getLayers } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import type { RasterMode, ViewMode } from "../lib/scales";
import { clampHours, elapsedMinutes, timelineMaxHours, type TimelineColorBy } from "../lib/timeline";
import FloodMap from "../map/FloodMap";
import ExploreLayers from "../components/ExploreLayers";
import Legend from "../components/Legend";
import ExploreScenario from "../components/ExploreScenario";
import Banner from "../components/Banner";
import ExploreTimeline from "../components/ExploreTimeline";
import PointInspector from "../components/PointInspector";
import type { PointSelection } from "../hooks/usePointInspection";
import type { MapPoint } from "../lib/pointInspection";

export default function Explore({ s, onEvidence }: { s: ScenarioView; onEvidence: () => void }) {
  const [mode, setMode] = useState<ViewMode>("depth");
  const [opacity, setOpacity] = useState(0.85);
  const [fit, setFit] = useState(0);
  const [cursor, setCursor] = useState<[number, number] | null>(null);
  const [hours, setHours] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [colorBy, setColorBy] = useState<TimelineColorBy>("arrival");
  const [selection, setSelection] = useState<PointSelection | null>(null);
  const pointDrawer = useRef<HTMLDetailsElement>(null);
  const selectPoint = useCallback((coordinate: MapPoint) => {
    setSelection(previous => ({ coordinate, sequence: (previous?.sequence ?? 0) + 1 }));
    if (pointDrawer.current) pointDrawer.current.open = true;
  }, []);
  const layers = useAsync((sig) => getLayers(s.id, sig), [s.id]);
  // Explore is keyed by scenario id in App, so changing scenario remounts this page: time resets to 0
  // and the previous scenario's grid cannot stay on screen.
  const maxHours = timelineMaxHours(s.detail.coverage_start, s.detail.coverage_end);
  const setHoursClamped = useCallback((h: number) => setHours(clampHours(h, maxHours ?? 0)), [maxHours]);
  const changeMode = (m: ViewMode) => { setMode(m); setPlaying(false); };
  const reset = () => { setPlaying(false); setHours(0); };
  const selectRaster = (m: RasterMode) => {
    if (mode === "timeline") { setColorBy(m); setPlaying(false); }
    else changeMode(m);
  };
  const toggleTimeline = (enabled: boolean) => {
    if (enabled) {
      if (mode === "depth" || mode === "velocity" || mode === "arrival") setColorBy(mode);
      changeMode("timeline");
    } else changeMode(colorBy);
  };
  return (
    <div className="explore explore-studio">
      <div className="explore-toolbar">
        <ExploreLayers mode={mode} colorBy={colorBy} opacity={opacity} timelineAvailable={maxHours !== null}
          onRaster={selectRaster} onTimeline={toggleTimeline} onExtent={() => changeMode("extent")}
          onOpacity={setOpacity} onFit={() => setFit((n) => n + 1)} />
        <details className="point-drawer" name="explore-toolbar-panels" ref={pointDrawer}>
          <summary>Inspect location</summary>
          <PointInspector selection={selection} onSelect={selectPoint} onClear={() => setSelection(null)}
            elapsedHours={mode === "timeline" ? hours : undefined}
            scenarios={[{ scenario: s, layers: layers.data?.scenario_id === s.id && layers.data.run_id === s.summary.run_id ? layers.data : undefined, error: layers.error }]} />
        </details>
        <details className="scenario-drawer" name="explore-toolbar-panels">
          <summary>{s.info.short} · Scenario details</summary>
          <ExploreScenario s={s} mode={mode} hours={hours} onEvidence={onEvidence} />
        </details>
      </div>
      <div className="explore-main">
        {layers.error && <Banner message={layers.error} onRetry={layers.reload} />}
        <div className="map-wrap studio-map">
          <FloodMap layers={layers.data} mode={mode} opacity={opacity} fitToken={fit} label={`${s.info.long} map`} onCursor={setCursor}
            onSelectPoint={selectPoint} selectedPoint={selection?.coordinate}
            onOutline={() => changeMode("extent")}
            timeline={{ elapsedMin: elapsedMinutes(hours), colorBy }} />
          <div className="coord" aria-live="off">{cursor ? `E ${Math.round(cursor[0]).toLocaleString("en-US")} m · N ${Math.round(cursor[1]).toLocaleString("en-US")} m (EPSG:32643)` : "EPSG:32643 · projected coordinates in metres"}</div>
        </div>
      </div>
      <div className="explore-footer">
      <ExploreTimeline enabled={mode === "timeline"} hours={hours} maxHours={maxHours} playing={playing} colorBy={colorBy}
        onHours={setHoursClamped} onPlaying={setPlaying} onColorBy={setColorBy} onReset={reset} onEnable={() => toggleTimeline(true)} />
        <aside className="page-legend-corner" aria-label="Selected layer scale">
          <Legend mode={mode} colorBy={colorBy} />
        </aside>
      </div>
    </div>
  );
}
