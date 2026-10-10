import { useEffect, useState } from "react";
import type { PrototypeLayers } from "../lib/api";
import { readPoint, type MapPoint, type PointValues } from "../lib/pointInspection";

export interface PointSelection { coordinate: MapPoint; sequence: number }
export type PointReadState = { kind: "idle" | "loading" } | { kind: "ready"; values: PointValues } | { kind: "error"; message: string };

/** Each point/scenario has its own cancellation boundary. Stale results never display. */
export function usePointInspection(layers: PrototypeLayers | undefined, selection: PointSelection | null): PointReadState {
  const [loaded, setLoaded] = useState<{ layers: PrototypeLayers; selection: PointSelection; state: PointReadState } | null>(null);
  useEffect(() => {
    if (!layers || !selection) return;
    const controller = new AbortController(); let active = true;
    setLoaded({ layers, selection, state: { kind: "loading" } });
    readPoint(layers, selection.coordinate, controller.signal).then(values => {
      if (active) setLoaded({ layers, selection, state: { kind: "ready", values } });
    }, error => { if (active) setLoaded({ layers, selection, state: { kind: "error", message: error instanceof Error ? error.message : "Point read failed." } }); });
    return () => { active = false; controller.abort(); };
  }, [layers, selection]);
  if (!selection) return { kind: "idle" };
  if (!loaded || loaded.layers !== layers || loaded.selection !== selection) return { kind: "loading" };
  return loaded.state;
}
