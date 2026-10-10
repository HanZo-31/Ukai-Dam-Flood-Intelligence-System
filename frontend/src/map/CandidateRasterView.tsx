import { useEffect, useRef, useState } from "react";
import { lonLatToUtm43 } from "../lib/utm";
import type { GridGeo } from "../lib/compute/decode";

type Ring = readonly (readonly number[])[];
function rings(doc: unknown): Ring[] {
  const out: Ring[] = [];
  const feats = (doc as { features?: { geometry?: { type?: string; coordinates?: unknown } }[] })?.features ?? [];
  for (const f of feats) {
    const g = f.geometry;
    if (g?.type === "Polygon") for (const r of g.coordinates as Ring[]) out.push(r);
    else if (g?.type === "MultiPolygon") for (const p of g.coordinates as Ring[][]) for (const r of p) out.push(r);
  }
  return out;
}

/** 2-D canvas preview of one grid (no WebGL needed) with the wet-extent outline projected EPSG:4326 -> EPSG:32643 by the existing transform. */
export default function CandidateRasterView(p: { width: number; height: number; geo: GridGeo; rgba: Uint8ClampedArray; outline?: unknown; label: string; showOutline: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [noCanvas, setNoCanvas] = useState(false);
  useEffect(() => {
    const cv = ref.current; if (!cv) return;
    let ctx: CanvasRenderingContext2D | null = null;
    try { ctx = cv.getContext("2d"); } catch { ctx = null; }
    if (!ctx) { setNoCanvas(true); return; }
    setNoCanvas(false);
    cv.width = p.width; cv.height = p.height;
    ctx.clearRect(0, 0, p.width, p.height);
    ctx.fillStyle = "#eef2f7"; ctx.fillRect(0, 0, p.width, p.height);
    const img = new ImageData(new Uint8ClampedArray(p.rgba), p.width, p.height);
    const off = document.createElement("canvas"); off.width = p.width; off.height = p.height;
    const octx = off.getContext("2d"); if (octx) { octx.putImageData(img, 0, 0); ctx.drawImage(off, 0, 0); } else ctx.putImageData(img, 0, 0);
    if (p.showOutline && p.outline) {
      ctx.strokeStyle = "#172B42"; ctx.lineWidth = Math.max(1, p.width / 400); ctx.setLineDash([Math.max(2, p.width / 150), Math.max(2, p.width / 200)]);
      for (const r of rings(p.outline)) {
        ctx.beginPath();
        r.forEach((pt, i) => {
          const [x, y] = lonLatToUtm43([pt[0], pt[1]]);
          const px = (x - p.geo.originX) / p.geo.pixelWidth, py = (p.geo.originY - y) / p.geo.pixelHeight;
          if (i === 0) ctx!.moveTo(px, py); else ctx!.lineTo(px, py);
        });
        ctx.stroke();
      }
    }
  }, [p.rgba, p.width, p.height, p.geo, p.outline, p.showOutline]);
  return (
    <div className="cand-view">
      <canvas ref={ref} role="img" aria-label={p.label} className="cand-canvas" style={{ aspectRatio: `${p.width} / ${p.height}`, display: noCanvas ? "none" : undefined }} />
      {noCanvas && <p className="muted" role="status">This browser cannot draw the preview. The tables below hold the same information.</p>}
    </div>
  );
}
