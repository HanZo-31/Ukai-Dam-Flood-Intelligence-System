import { Play } from "lucide-react";
import TimelinePanel from "./TimelinePanel";
import type { TimelineColorBy } from "../lib/timeline";

export interface ExploreTimelineProps {
  enabled: boolean;
  hours: number;
  maxHours: number | null;
  playing: boolean;
  colorBy: TimelineColorBy;
  onHours: (hours: number) => void;
  onPlaying: (playing: boolean) => void;
  onColorBy: (color: TimelineColorBy) => void;
  onReset: () => void;
  onEnable: () => void;
}

export default function ExploreTimeline(p: ExploreTimelineProps) {
  return <div className="studio-timeline-dock">
    {p.enabled ? <TimelinePanel {...p} compact /> :
      <section className="timeline-inactive" aria-label="Arrival timeline">
        <button type="button" className="timeline-enable" disabled={p.maxHours === null} onClick={p.onEnable} aria-label="Enable arrival timeline"><Play size={23} aria-hidden /></button>
        <div><strong>Elapsed model time</strong><p>{p.maxHours === null ? "No usable model-clock window supplied." : "Enable arrival reveal to play the stored timeline."}</p></div>
        <div className="inactive-track" aria-hidden><span /></div>
        <span className="timeline-duration">{p.maxHours === null ? "Unavailable" : `${p.maxHours} h model window`}</span>
      </section>}
  </div>;
}
