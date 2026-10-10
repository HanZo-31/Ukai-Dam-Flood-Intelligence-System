// Test-only: writes classic little-endian tiled TIFFs (float32, one band, Deflate, no predictor) in the exact layout the product reader accepts,
// with switches to break one property at a time. The Deflate function is injected so this module has no Node dependency.
export interface TiffSpec {
  width: number; height: number; values: ArrayLike<number>;
  originX: number; originY: number; pixelWidth: number; pixelHeight: number;
  deflate: (u: Uint8Array) => Uint8Array;
  tile?: number;
  /** null = omit the tag; default "-9999" */
  nodata?: string | null;
  /** null = omit the GeoKeyDirectory; default 32643 */
  epsg?: number | null;
  bits?: number; predictor?: number; compression?: number;
}
const f64 = (...v: number[]) => new Uint8Array(new Float64Array(v).buffer);
const u16s = (...v: number[]) => new Uint8Array(new Uint16Array(v).buffer);

export function buildDeflateTiff(s: TiffSpec): ArrayBuffer {
  const tile = s.tile ?? 256, across = Math.ceil(s.width / tile), down = Math.ceil(s.height / tile);
  const comp: Uint8Array[] = [];
  for (let ty = 0; ty < down; ty++) for (let tx = 0; tx < across; tx++) {
    const t = new Float32Array(tile * tile).fill(-9999);
    for (let r = 0; r < tile; r++) for (let c = 0; c < tile; c++) { const x = tx * tile + c, y = ty * tile + r; if (x < s.width && y < s.height) t[r * tile + c] = s.values[y * s.width + x]; }
    comp.push(s.deflate(new Uint8Array(t.buffer)));
  }
  const geokeys = s.epsg === null ? null : u16s(1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, s.epsg ?? 32643);
  const nd = s.nodata === null ? null : new TextEncoder().encode((s.nodata ?? "-9999") + "\0");
  type E = [number, number, number, number | "scale" | "tie" | "offs" | "cnts" | "geo" | "nd"];
  const entries: E[] = [
    [256, 4, 1, s.width], [257, 4, 1, s.height], [258, 3, 1, s.bits ?? 32], [259, 3, 1, s.compression ?? 8], [262, 3, 1, 1], [277, 3, 1, 1], [284, 3, 1, 1],
    [317, 3, 1, s.predictor ?? 1], [322, 4, 1, tile], [323, 4, 1, tile], [324, 4, comp.length, "offs"], [325, 4, comp.length, "cnts"], [339, 3, 1, 3],
    [33550, 12, 3, "scale"], [33922, 12, 6, "tie"],
  ];
  if (geokeys) entries.push([34735, 3, geokeys.length / 2, "geo"]);
  if (nd) entries.push([42113, 2, nd.length, "nd"]);
  const ifdOff = 8, ifdSize = 2 + entries.length * 12 + 4;
  let cursor = ifdOff + ifdSize;
  const extra: { at: number; bytes: Uint8Array }[] = [];
  const place = (bytes: Uint8Array) => { const at = cursor; extra.push({ at, bytes }); cursor += bytes.byteLength + (bytes.byteLength % 2); return at; };
  const at = {
    scale: place(f64(s.pixelWidth, s.pixelHeight, 0)), tie: place(f64(0, 0, 0, s.originX, s.originY, 0)),
    geo: geokeys ? place(geokeys) : 0, nd: nd ? place(nd) : 0,
    offs: place(new Uint8Array(comp.length * 4)), cnts: place(new Uint8Array(comp.length * 4)),
  };
  let o = cursor; const offs: number[] = [];
  for (const c of comp) { offs.push(o); o += c.byteLength; }
  const buf = new ArrayBuffer(o), dv = new DataView(buf), u8 = new Uint8Array(buf);
  dv.setUint16(0, 0x4949, true); dv.setUint16(2, 42, true); dv.setUint32(4, ifdOff, true); dv.setUint16(ifdOff, entries.length, true);
  entries.forEach(([tag, type, count, val], i) => {
    const e = ifdOff + 2 + i * 12;
    dv.setUint16(e, tag, true); dv.setUint16(e + 2, type, true); dv.setUint32(e + 4, count, true);
    let v = typeof val === "string" ? at[val] : val;
    if (comp.length === 1 && val === "offs") v = offs[0]; // a single LONG is stored inline in the IFD entry, not behind a pointer
    if (comp.length === 1 && val === "cnts") v = comp[0].byteLength;
    if (type === 3 && count === 1) dv.setUint16(e + 8, v, true); else dv.setUint32(e + 8, v, true);
  });
  extra.forEach((x) => u8.set(x.bytes, x.at));
  offs.forEach((off, i) => { dv.setUint32(at.offs + i * 4, off, true); dv.setUint32(at.cnts + i * 4, comp[i].byteLength, true); });
  comp.forEach((c, i) => u8.set(c, offs[i]));
  return buf;
}
