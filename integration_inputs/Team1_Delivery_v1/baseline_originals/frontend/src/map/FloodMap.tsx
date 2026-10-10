import { useEffect, useRef, useState } from "react";
import Map from "ol/Map";
import View from "ol/View";
import Graticule from "ol/layer/Graticule";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import GeoJSON from "ol/format/GeoJSON";
import WebGLTileLayer from "ol/layer/WebGLTile";
import GeoTIFF from "ol/source/GeoTIFF";
import ScaleLine from "ol/control/ScaleLine";
import Zoom from "ol/control/Zoom";
import { Fill, Stroke, Style } from "ol/style";
import type { Extent } from "ol/extent";
import type BaseLayer from "ol/layer/Base";
import { registerUtm43, UTM43 } from "./projection";
import { buildColorExpression, ROLE_FOR_MODE, type ViewMode } from "../lib/scales";
import { layerFor, type PrototypeLayers } from "../lib/api";
import { sameOriginPath } from "../lib/assets";

export type MapStatus = { state: "idle" | "loading" | "ready" | "error"; message?: string };

interface Props {
  layers: PrototypeLayers | undefined;
  mode: ViewMode;
  opacity: number;
  view?: View; // shared View => synchronized maps
  fitToken: number; // bump to refit
  label: string;
  onStatus?: (s: MapStatus) => void;
  onCursor?: (c: [number, number] | null) => void;
}

function webglOk(): boolean {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); } catch { return false; }
}

const extentStyle = new Style({ stroke: new Stroke({ color: "#1677EF", width: 1.5 }), fill: new Fill({ color: "rgba(22,119,239,0.35)" }) });

/** One OpenLayers map in EPSG:32643 (metres). No basemap: honest local coordinate view. */
export default function FloodMap({ layers, mode, opacity, view, fitToken, label, onStatus, onCursor }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const dataLayerRef = useRef<BaseLayer | null>(null);
  const extentRef = useRef<Extent | null>(null);
  const opacityRef = useRef(opacity);
  const statusRef = useRef(onStatus);
  statusRef.current = onStatus;
  opacityRef.current = opacity;
  const [gl] = useState(webglOk);
  const [status, setStatus] = useState<MapStatus>({ state: "idle" });
  const set = (s: MapStatus) => { setStatus(s); statusRef.current?.(s); };

  // create / destroy the map
  useEffect(() => {
    if (!host.current) return;
    const proj = registerUtm43();
    const v = view ?? new View({ projection: proj, center: [380000, 2400000], zoom: 8 });
    const map = new Map({
      target: host.current,
      view: v,
      controls: [new Zoom(), new ScaleLine({ units: "metric" })],
      layers: [new Graticule({ strokeStyle: new Stroke({ color: "rgba(23,43,66,0.18)", width: 1 }), showLabels: true, wrapX: false, targetSize: 120 })],
    });
    map.on("pointermove", (e) => onCursor?.(e.coordinate as [number, number]));
    host.current.addEventListener("mouseleave", () => onCursor?.(null));
    mapRef.current = map;
    return () => { map.setTarget(undefined); map.dispose(); mapRef.current = null; dataLayerRef.current = null; };
    // view identity is fixed for the life of this component
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // swap the data layer when scenario layers / mode change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (dataLayerRef.current) { map.removeLayer(dataLayerRef.current); dataLayerRef.current = null; }
    extentRef.current = null;
    if (!layers) { set({ state: "idle" }); return; }
    let cancelled = false;
    let created: BaseLayer | null = null;

    if (mode === "extent") {
      const l = layerFor(layers, "extent_geojson");
      if (!l) { set({ state: "error", message: "The flood extent outline is not available for this scenario." }); return; }
      set({ state: "loading" });
      const source = new VectorSource({ url: sameOriginPath(l.url), format: new GeoJSON({ dataProjection: UTM43, featureProjection: UTM43 }) });
      source.on("featuresloaderror", () => !cancelled && set({ state: "error", message: "The extent outline could not be loaded." }));
      source.on("featuresloadend", () => {
        if (cancelled) return;
        const ex = source.getExtent();
        if (ex && ex.every(Number.isFinite)) { extentRef.current = ex; map.getView().fit(ex, { padding: [40, 40, 40, 40], duration: 0 }); }
        set({ state: "ready" });
      });
      created = new VectorLayer({ source, style: extentStyle, opacity: opacityRef.current });
    } else {
      const l = layerFor(layers, ROLE_FOR_MODE[mode]);
      if (!l) { set({ state: "error", message: "This layer is not available for this scenario." }); return; }
      if (!gl) { set({ state: "error", message: "This browser cannot use WebGL, which the raster map needs." }); return; }
      set({ state: "loading" });
      const nodata = l.nodata ?? -9999;
      const source = new GeoTIFF({
        sources: [{ url: sameOriginPath(l.url), nodata }],
        normalize: false,
        interpolate: false,
        sourceOptions: { allowFullFile: true },
      });
      const ev = source as unknown as { on: (t: string, f: (e: unknown) => void) => void; getState: () => string };
      ev.on("error", (e) => !cancelled && set({ state: "error", message: `The raster could not be loaded (${(e as { error?: Error }).error?.message ?? "read error"}).` }));
      ev.on("change", () => { if (!cancelled && ev.getState() === "error") set({ state: "error", message: "The raster could not be loaded." }); });
      source.getView().then((opts) => {
        if (cancelled) return;
        const ex = opts.extent as Extent | undefined;
        if (ex) { extentRef.current = ex; map.getView().fit(ex, { padding: [40, 40, 40, 40], duration: 0 }); }
        set({ state: "ready" });
      }, (err: unknown) => !cancelled && set({ state: "error", message: `The raster could not be read (${err instanceof Error ? err.message : "error"}).` }));
      created = new WebGLTileLayer({ source, opacity: opacityRef.current, style: { color: buildColorExpression(mode, nodata) } as never });
    }
    if (created) { map.addLayer(created); dataLayerRef.current = created; }
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers, mode, gl]);

  useEffect(() => { dataLayerRef.current?.setOpacity(opacity); }, [opacity]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && extentRef.current && fitToken > 0) map.getView().fit(extentRef.current, { padding: [40, 40, 40, 40], duration: 250 });
  }, [fitToken]);

  return (
    <div className="map-frame" role="region" aria-label={label}>
      <div className="map-host" ref={host} data-map-state={status.state} />
      {status.state === "loading" && <div className="map-overlay" role="status">Loading map layer…</div>}
      {status.state === "error" && <div className="map-overlay error" role="alert">{status.message}</div>}
    </div>
  );
}
