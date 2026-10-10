// Minimal reader for the stored reference COGs: classic little-endian TIFF, one band, float32,
// 256x256 tiles, Deflate (zlib) compression, no predictor. Anything else is rejected, never guessed.
// Only the full-resolution image (first IFD) is read. The inflate function is injected so the same
// code runs in the browser (DecompressionStream) and in Node tests (zlib).
export interface Raster {
  width: number;
  height: number;
  data: Float32Array;
  /** pixel size in metres (positive) and top-left corner of the top-left pixel (ModelTiepoint) */
  pixelWidth: number;
  pixelHeight: number;
  originX: number;
  originY: number;
  nodata: number | null;
}
export type Inflate = (compressed: Uint8Array) => Promise<Uint8Array>;

const T = { width: 256, height: 257, bits: 258, compression: 259, spp: 277, tileW: 322, tileH: 323, tileOff: 324, tileCnt: 325, fmt: 339,
  scale: 33550, tie: 33922, nodata: 42113, predictor: 317, planar: 284 };

export async function readFloat32Tiff(buf: ArrayBuffer, inflate: Inflate): Promise<Raster> {
  const dv = new DataView(buf);
  if (dv.byteLength < 8 || dv.getUint16(0, true) !== 0x4949) throw new Error("Unsupported TIFF: only little-endian files are supported.");
  if (dv.getUint16(2, true) !== 42) throw new Error("Unsupported TIFF: BigTIFF is not supported.");
  const ifd = dv.getUint32(4, true);
  const n = dv.getUint16(ifd, true);
  const tags = new Map<number, { type: number; count: number; off: number }>();
  for (let i = 0; i < n; i++) {
    const e = ifd + 2 + i * 12;
    tags.set(dv.getUint16(e, true), { type: dv.getUint16(e + 2, true), count: dv.getUint32(e + 4, true), off: e + 8 });
  }
  const size: Record<number, number> = { 1: 1, 2: 1, 3: 2, 4: 4, 12: 8 };
  const valueOffset = (t: { type: number; count: number; off: number }) => (size[t.type] * t.count <= 4 ? t.off : dv.getUint32(t.off, true));
  const num = (tag: number, i = 0): number => {
    const t = tags.get(tag); if (!t) throw new Error(`Missing TIFF tag ${tag}.`);
    const o = valueOffset(t) + i * size[t.type];
    return t.type === 3 ? dv.getUint16(o, true) : t.type === 4 ? dv.getUint32(o, true) : t.type === 12 ? dv.getFloat64(o, true) : NaN;
  };
  const opt = (tag: number, d: number) => (tags.has(tag) ? num(tag) : d);
  const width = num(T.width), height = num(T.height);
  if (num(T.bits) !== 32 || opt(T.fmt, 1) !== 3 || opt(T.spp, 1) !== 1) throw new Error("Unsupported TIFF: expected one float32 band.");
  if (opt(T.compression, 1) !== 8 && opt(T.compression, 1) !== 32946) throw new Error("Unsupported TIFF: expected Deflate compression.");
  if (opt(T.predictor, 1) !== 1) throw new Error("Unsupported TIFF: predictor not supported.");
  if (opt(T.planar, 1) !== 1) throw new Error("Unsupported TIFF: planar layout not supported.");
  const tw = num(T.tileW), th = num(T.tileH);
  const across = Math.ceil(width / tw), down = Math.ceil(height / th);
  const cnt = tags.get(T.tileCnt)!.count;
  if (cnt !== across * down) throw new Error("Unsupported TIFF: tile count mismatch.");
  const scale = tags.get(T.scale), tie = tags.get(T.tie);
  if (!scale || !tie) throw new Error("TIFF has no georeferencing tags.");
  let nodata: number | null = null;
  const nd = tags.get(T.nodata);
  if (nd) { const o = nd.count <= 4 ? nd.off : dv.getUint32(nd.off, true); let s = ""; for (let i = 0; i < nd.count; i++) { const c = dv.getUint8(o + i); if (c) s += String.fromCharCode(c); } const v = Number(s.trim()); nodata = Number.isFinite(v) ? v : null; }

  const data = new Float32Array(width * height);
  const u8 = new Uint8Array(buf);
  for (let ty = 0; ty < down; ty++) {
    for (let tx = 0; tx < across; tx++) {
      const k = ty * across + tx;
      const off = num(T.tileOff, k), len = num(T.tileCnt, k);
      const raw = await inflate(u8.subarray(off, off + len));
      if (raw.byteLength !== tw * th * 4) throw new Error("TIFF tile has an unexpected size.");
      const tile = new Float32Array(raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength));
      const x0 = tx * tw, y0 = ty * th, w = Math.min(tw, width - x0), h = Math.min(th, height - y0);
      for (let r = 0; r < h; r++) data.set(tile.subarray(r * tw, r * tw + w), (y0 + r) * width + x0);
    }
  }
  const sc = valueOffset(scale), ti = valueOffset(tie);
  return {
    width, height, data, nodata,
    pixelWidth: dv.getFloat64(sc, true), pixelHeight: dv.getFloat64(sc + 8, true),
    originX: dv.getFloat64(ti + 24, true), originY: dv.getFloat64(ti + 32, true),
  };
}

/** Browser inflate (zlib/Deflate). Chrome and Edge support DecompressionStream. */
export const browserInflate: Inflate = async (compressed) => {
  const stream = new Blob([compressed as BlobPart]).stream().pipeThrough(new DecompressionStream("deflate"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
};
