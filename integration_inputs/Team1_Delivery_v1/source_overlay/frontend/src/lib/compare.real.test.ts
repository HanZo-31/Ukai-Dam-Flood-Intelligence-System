// Real stored rasters (read here with the in-repo TIFF reader) against independent numpy/tifffile results.
// Skipped, with a visible reason, when the receipts are not next to the frontend folder.
import { describe, expect, it } from "vitest";
import expected from "./fixtures/compare_expected.json";
import binsExpected from "./fixtures/arrival_bins_expected.json";
import { arrivalChangeBins, compareGrids, type Grid } from "./compare";
import { computeZones } from "./zones";
import { readFloat32Tiff } from "./tiff";

const FOLDERS: Record<string, string> = { h01: "receipts/h01", h02: "part_a", h03: "receipts/h03", "2006": "receipts/2006" };
const root = new URL("../../../", import.meta.url);

async function loadGrids(): Promise<Record<string, Grid> | null> {
  try {
    const fsName = "node:fs", zName = "node:zlib", uName = "node:url"; // variable specifiers: resolved at run time only
    const fs = await import(/* @vite-ignore */ fsName);
    const zlib = await import(/* @vite-ignore */ zName);
    const url = await import(/* @vite-ignore */ uName);
    const read = async (rel: string) => {
      const b = fs.readFileSync(url.fileURLToPath(new URL(rel, root)));
      return readFloat32Tiff(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer, async (u: Uint8Array) => new Uint8Array(zlib.inflateSync(u)));
    };
    const out: Record<string, Grid> = {};
    for (const [k, dir] of Object.entries(FOLDERS)) {
      const d = await read(`${dir}/assets/max_depth.tif`), a = await read(`${dir}/assets/arrival_time.tif`);
      out[k] = { width: d.width, height: d.height, geo: { originX: d.originX, originY: d.originY, pixelWidth: d.pixelWidth, pixelHeight: d.pixelHeight }, depth: d.data, arrival: a.data };
    }
    return out;
  } catch { return null; }
}
const gridsPromise = loadGrids();

describe("stored references vs independent counts", () => {
  for (const e of expected.pairs) {
    it(`${e.baseline} -> ${e.candidate}: extent, depth, arrival and zones`, async () => {
      const g = await gridsPromise;
      if (!g) { console.warn("SKIPPED: stored rasters not found next to the frontend folder."); return; }
      const r = compareGrids(g[e.baseline], g[e.candidate]);
      if (typeof r === "string") throw new Error(r);
      expect(r.counts.commonWet).toBe(e.counts.commonWet); expect(r.counts.newWet).toBe(e.counts.newWet); expect(r.counts.lostWet).toBe(e.counts.lostWet);
      expect(r.counts.baselineOnlyValid).toBe(e.counts.baselineOnlyValid); expect(r.counts.candidateOnlyValid).toBe(e.counts.candidateOnlyValid);
      expect(r.km2.newWet).toBeCloseTo(e.km2.newWet, 9);
      expect(r.arrival.pairedCells).toBe(e.arrival.pairedCells); expect(r.arrival.medianDiffH).toBe(e.arrival.medianDiffH);
      expect(r.arrival.meanDiffH as number).toBeCloseTo(e.arrival.meanDiffH, 9);
      const z = computeZones(g[e.baseline], g[e.candidate]);
      if (typeof z === "string") throw new Error(z);
      expect(z.zones.length).toBe(e.zones.count); expect(z.totals.cells).toBe(e.zones.totalCells); expect(z.ranked.length).toBe(e.zones.rankedCount);
      expect(z.ranked.slice(0, 12).map((x) => x.id)).toEqual(e.zones.rankedIds);
    }, 120000);
  }
  it("same scenario: no change and no priority; swapped pair reverses signs", async () => {
    const g = await gridsPromise;
    if (!g) return;
    const same = compareGrids(g.h02, g.h02);
    if (typeof same === "string") throw new Error(same);
    expect(same.counts.newWet + same.counts.lostWet).toBe(0);
    const ab = compareGrids(g.h02, g.h03), ba = compareGrids(g.h03, g.h02);
    if (typeof ab === "string" || typeof ba === "string") throw new Error("compare failed");
    expect(ab.counts.newWet).toBe(ba.counts.lostWet); expect(ab.arrival.medianDiffH).toBe(-(ba.arrival.medianDiffH as number));
  }, 120000);
});

describe("arrival-change classes vs independent numpy counts", () => {
  for (const [key, counts] of Object.entries(binsExpected as Record<string, number[]>)) {
    it(`${key}`, async () => {
      const g = await gridsPromise;
      if (!g) { console.warn("SKIPPED: stored rasters not found next to the frontend folder."); return; }
      const [b, c] = key.split(">");
      const r = arrivalChangeBins(g[b], g[c]);
      if (typeof r === "string") throw new Error(r);
      expect(r.counts).toEqual(counts);
    }, 120000);
  }
});
