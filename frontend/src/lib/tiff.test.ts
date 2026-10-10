import { describe, expect, it } from "vitest";
import { readFloat32Tiff } from "./tiff";
import { loadRaster, clearRasterCache } from "./rasterCache";

// Builds a tiny classic little-endian float32 tiled TIFF. Compression is the identity in tests (inflate is injected).
function buildTiff(opts: { w: number; h: number; tile: number; values: number[]; bits?: number; compression?: number; predictor?: number; big?: boolean }): ArrayBuffer {
  const { w, h, tile } = opts;
  const across = Math.ceil(w / tile), down = Math.ceil(h / tile);
  const tiles: Float32Array[] = [];
  for (let ty = 0; ty < down; ty++) for (let tx = 0; tx < across; tx++) {
    const t = new Float32Array(tile * tile).fill(-9999);
    for (let r = 0; r < tile; r++) for (let c = 0; c < tile; c++) { const x = tx * tile + c, y = ty * tile + r; if (x < w && y < h) t[r * tile + c] = opts.values[y * w + x]; }
    tiles.push(t);
  }
  const entries: [number, number, number, number[] | "off"][] = [];
  const nEntries = 14, ifdOff = 8, ifdSize = 2 + nEntries * 12 + 4;
  let cursor = ifdOff + ifdSize;
  const extra: { at: number; bytes: Uint8Array }[] = [];
  const place = (bytes: Uint8Array) => { const at = cursor; extra.push({ at, bytes }); cursor += bytes.byteLength + (bytes.byteLength % 2); return at; };
  const f64 = (...v: number[]) => new Uint8Array(new Float64Array(v).buffer);
  const scaleAt = place(f64(10, 10, 0)), tieAt = place(f64(0, 0, 0, 1000, 5000, 0)), ndAt = place(new TextEncoder().encode("-9999\0"));
  const offsAt = place(new Uint8Array(tiles.length * 4)), cntAt = place(new Uint8Array(tiles.length * 4));
  const dataStart = cursor;
  const tileBytes = tiles.map((t) => new Uint8Array(t.buffer));
  const offs: number[] = []; let o = dataStart; for (const b of tileBytes) { offs.push(o); o += b.byteLength; }
  const buf = new ArrayBuffer(o); const dv = new DataView(buf); const u8 = new Uint8Array(buf);
  dv.setUint16(0, 0x4949, true); dv.setUint16(2, opts.big ? 43 : 42, true); dv.setUint32(4, ifdOff, true);
  dv.setUint16(ifdOff, nEntries, true);
  const E: [number, number, number, number][] = [
    [256, 4, 1, w], [257, 4, 1, h], [258, 3, 1, opts.bits ?? 32], [259, 3, 1, opts.compression ?? 8], [277, 3, 1, 1], [317, 3, 1, opts.predictor ?? 1],
    [322, 4, 1, tile], [323, 4, 1, tile], [324, 4, tiles.length, offsAt], [325, 4, tiles.length, cntAt], [339, 3, 1, 3],
    [33550, 12, 3, scaleAt], [33922, 12, 6, tieAt], [42113, 2, 6, ndAt],
  ];
  void entries;
  E.forEach(([tag, type, count, val], i) => {
    const e = ifdOff + 2 + i * 12;
    dv.setUint16(e, tag, true); dv.setUint16(e + 2, type, true); dv.setUint32(e + 4, count, true);
    if (type === 3 && count === 1) dv.setUint16(e + 8, val, true); else dv.setUint32(e + 8, val, true);
  });
  extra.forEach((x) => u8.set(x.bytes, x.at));
  offs.forEach((v, i) => { dv.setUint32(offsAt + i * 4, v, true); dv.setUint32(cntAt + i * 4, tileBytes[i].byteLength, true); });
  if (tiles.length === 1) { // one value fits inline in the entry (as real writers do)
    const at = (tag: number) => ifdOff + 2 + E.findIndex((x) => x[0] === tag) * 12 + 8;
    dv.setUint32(at(324), offs[0], true); dv.setUint32(at(325), tileBytes[0].byteLength, true);
  }
  tileBytes.forEach((b, i) => u8.set(b, offs[i]));
  return buf;
}
const identity = async (u: Uint8Array) => u;

describe("readFloat32Tiff", () => {
  const values = [60, 120, -9999, 180, 240, 300, 360, -9999, 420, 480, 540, 600];
  it("reads values across several tiles, georeferencing and nodata", async () => {
    const r = await readFloat32Tiff(buildTiff({ w: 4, h: 3, tile: 2, values }), identity);
    expect([r.width, r.height]).toEqual([4, 3]);
    expect(Array.from(r.data)).toEqual(values);
    expect([r.pixelWidth, r.pixelHeight, r.originX, r.originY]).toEqual([10, 10, 1000, 5000]);
    expect(r.nodata).toBe(-9999);
  });
  it("rejects unsupported layouts instead of guessing", async () => {
    await expect(readFloat32Tiff(buildTiff({ w: 4, h: 3, tile: 2, values, bits: 16 }), identity)).rejects.toThrow(/float32/);
    await expect(readFloat32Tiff(buildTiff({ w: 4, h: 3, tile: 2, values, compression: 5 }), identity)).rejects.toThrow(/Deflate/);
    await expect(readFloat32Tiff(buildTiff({ w: 4, h: 3, tile: 2, values, predictor: 3 }), identity)).rejects.toThrow(/predictor/);
    await expect(readFloat32Tiff(buildTiff({ w: 4, h: 3, tile: 2, values, big: true }), identity)).rejects.toThrow(/BigTIFF/);
    await expect(readFloat32Tiff(new ArrayBuffer(4), identity)).rejects.toThrow();
  });
  it("rejects a tile with the wrong decompressed size", async () => {
    await expect(readFloat32Tiff(buildTiff({ w: 4, h: 3, tile: 2, values }), async (u) => u.subarray(0, 4))).rejects.toThrow(/unexpected size/);
  });
});

describe("raster cache", () => {
  it("fetches a URL once, shares the result and does not cache failures", async () => {
    clearRasterCache();
    const body = buildTiff({ w: 2, h: 2, tile: 2, values: [1, 2, 3, 4] });
    let calls = 0, fail = true;
    const f = (async () => { calls++; return fail ? new Response("x", { status: 503 }) : new Response(body.slice(0)); }) as unknown as typeof fetch;
    await expect(loadRaster("/api/x.tif", f, identity)).rejects.toThrow(/HTTP 503/);
    fail = false;
    const [a, b] = await Promise.all([loadRaster("/api/x.tif", f, identity), loadRaster("/api/x.tif", f, identity)]);
    expect(a).toBe(b); expect(calls).toBe(2);
    await loadRaster("/api/x.tif", f, identity); expect(calls).toBe(2);
  });
});
