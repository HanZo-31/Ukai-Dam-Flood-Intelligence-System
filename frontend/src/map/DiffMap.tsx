import { useEffect, useRef } from "react";
import Map from "ol/Map";
import View from "ol/View";
import ImageLayer from "ol/layer/Image";
import ImageStatic from "ol/source/ImageStatic";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import { fromExtent } from "ol/geom/Polygon";
import Graticule from "ol/layer/Graticule";
import ScaleLine from "ol/control/ScaleLine";
import Zoom from "ol/control/Zoom";
import { Fill, Stroke, Style } from "ol/style";
import { UTM43 } from "./projection";
import type { GridGeo } from "../lib/compare";

/** Colours of the extent-difference map (also used by the key in DiffPanel). Same hues for every comparison. */
export const DIFF_COLOURS = { common: [120, 144, 170, 150], new: [214, 40, 40, 235], lost: [22, 119, 239, 235] } as const;

/** Arrival-change bins 1..7 (see ARRIVAL_BIN_LABELS): reds = candidate earlier, blues = later. Index 0 is transparent. */
export const ARRIVAL_COLOURS: readonly (readonly number[])[] = [
  [0, 0, 0, 0], [153, 27, 27, 235], [220, 38, 38, 225], [248, 150, 120, 215], [200, 205, 212, 200], [150, 190, 245, 215], [59, 130, 246, 225], [29, 78, 216, 235],
];
export const EXTENT_PALETTE: readonly (readonly number[])[] = [[0, 0, 0, 0], DIFF_COLOURS.common, DIFF_COLOURS.new, DIFF_COLOURS.lost];

function classCanvas(classes: Uint8Array, w: number, h: number, palette: readonly (readonly number[])[]): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  const ctx = c.getContext("2d");
  if (!ctx) throw new Error("Canvas is not available.");
  const img = ctx.createImageData(w, h);
  const put = (i: number, col: readonly number[]) => { img.data[i * 4] = col[0]; img.data[i * 4 + 1] = col[1]; img.data[i * 4 + 2] = col[2]; img.data[i * 4 + 3] = col[3]; };
  for (let i = 0; i < classes.length; i++) { const k = classes[i]; if (k > 0 && k < palette.length) put(i, palette[k]); }
  ctx.putImageData(img, 0, 0);
  return c;
}

const zoneStyle = new Style({ stroke: new Stroke({ color: "#111827", width: 2.5 }), fill: new Fill({ color: "rgba(17,24,39,0.06)" }) });

/** Extent difference (candidate minus baseline): new wet, common wet, baseline-only wet. Shares the compare View. */
export default function DiffMap({ classes, palette, geo, width, height, view, opacity, highlight, fitToken, label }: {
  classes: Uint8Array; palette: readonly (readonly number[])[]; geo: GridGeo; width: number; height: number; view: View; opacity: number; highlight: [number, number, number, number] | null; fitToken: number; label: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const layerRef = useRef<ImageLayer<ImageStatic> | null>(null);
  const zoneSrc = useRef(new VectorSource());
  const extent: [number, number, number, number] = [geo.originX, geo.originY - height * geo.pixelHeight, geo.originX + width * geo.pixelWidth, geo.originY];
  const extentRef = useRef(extent);
  extentRef.current = extent;

  useEffect(() => {
    if (!host.current) return;
    const map = new Map({ target: host.current, view, controls: [new Zoom(), new ScaleLine({ units: "metric" })],
      layers: [new Graticule({ strokeStyle: new Stroke({ color: "rgba(23,43,66,0.18)", width: 1 }), showLabels: true, wrapX: false, targetSize: 120 })] });
    map.addLayer(new VectorLayer({ source: zoneSrc.current, style: zoneStyle, zIndex: 10 }));
    mapRef.current = map;
    return () => { map.setTarget(undefined); map.dispose(); mapRef.current = null; layerRef.current = null; };
    // the shared View is fixed for the life of the page
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // the image layer is replaced whenever a new comparison arrives
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const canvas = classCanvas(classes, width, height, palette);
    const layer = new ImageLayer({ source: new ImageStatic({ url: canvas.toDataURL("image/png"), imageExtent: extentRef.current, projection: UTM43, interpolate: false }), opacity, zIndex: 5 });
    layerRef.current = layer;
    map.addLayer(layer);
    return () => { map.removeLayer(layer); layerRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classes, palette, width, height]);

  useEffect(() => { layerRef.current?.setOpacity(opacity); }, [opacity]);
  useEffect(() => {
    zoneSrc.current.clear();
    if (highlight) zoneSrc.current.addFeature(new Feature(fromExtent(highlight)));
  }, [highlight]);
  useEffect(() => { if (fitToken > 0) view.fit(extentRef.current, { padding: [40, 40, 40, 40], duration: 250 }); }, [fitToken, view]);
  return <div className="map-frame" role="region" aria-label={label}><div className="map-host" ref={host} tabIndex={0} aria-label={`${label}; arrow keys pan, plus and minus zoom`} /></div>;
}
