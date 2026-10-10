import { Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";
import { elapsedMinutes, type TimelineColorBy } from "../lib/timeline";
import { SCALES } from "../lib/scales";

interface Props {
  compact?: boolean; // Presentation only; the original clock/controls are shared.
  hours: number;
  maxHours: number | null; // null => timeline unavailable (window not declared)
  playing: boolean;
  colorBy: TimelineColorBy;
  onHours: (h: number) => void;
  onPlaying: (p: boolean) => void;
  onColorBy: (c: TimelineColorBy) => void;
  onReset: () => void;
}

const STEP_MS = 600; // one model hour per tick

export default function TimelinePanel(p: Props) {
  const { hours, maxHours, playing, onHours, onPlaying } = p;
  const hoursRef = useRef(hours);
  hoursRef.current = hours;

  useEffect(() => {
    if (!playing || maxHours === null) return;
    const id = window.setInterval(() => {
      const next = hoursRef.current + 1;
      if (next >= maxHours) { onHours(maxHours); onPlaying(false); } else onHours(next);
    }, STEP_MS);
    return () => window.clearInterval(id);
  }, [playing, maxHours, onHours, onPlaying]);

  if (maxHours === null) {
    return <div className="timeline" role="status">The arrival timeline is not available: the model-clock window for this scenario is not declared.</div>;
  }
  const explanation = <div className="timeline-head">
        <strong>Area reached by elapsed model time</strong>
        <span className="muted"> — first depth &gt; 0.1 m, hourly steps; model time, not a real clock</span>
      </div>;
  const colourControl = <label className="timeline-by">Colour by
        <select value={p.colorBy} onChange={(e) => p.onColorBy(e.target.value as TimelineColorBy)}>
          <option value="arrival">{SCALES.arrival.title}</option>
          <option value="depth">Maximum depth (revealed by arrival)</option>
          <option value="velocity">Maximum velocity (revealed by arrival)</option>
        </select>
      </label>;
  return (
    <section className={`timeline${p.compact ? " timeline-compact" : ""}`} aria-label="Arrival timeline">
      {!p.compact && explanation}
      <div className="timeline-row">
        <button type="button" className="btn" onClick={() => onPlaying(!playing)} aria-pressed={playing}>
          {playing ? <><Pause size={14} aria-hidden /> Pause</> : <><Play size={14} aria-hidden /> Play</>}
        </button>
        <input type="range" min={0} max={maxHours} step={1} value={hours} onChange={(e) => { onPlaying(false); onHours(Number(e.target.value)); }}
          aria-label="Elapsed model time in hours" aria-valuetext={`${hours} hours elapsed`} />
        <button type="button" className="btn" onClick={p.onReset}><RotateCcw size={14} aria-hidden /> Reset</button>
      </div>
      <div className="timeline-label" aria-live="polite">Elapsed: <strong>{hours} h</strong> of {maxHours} h <span className="muted">({elapsedMinutes(hours)} min since simulation start)</span></div>
      {p.compact ? <details className="timeline-details"><summary>Timeline details</summary>{explanation}{colourControl}</details> : colourControl}
      {p.colorBy !== "arrival" && (
        <p className="timeline-note">Depth and velocity here are maximum-over-run values, shown for cells once they are reached. They are not changing water levels and do not show recession.</p>
      )}
    </section>
  );
}
