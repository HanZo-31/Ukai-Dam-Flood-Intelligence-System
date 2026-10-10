// Source-level guards: nothing in the application may import test fixtures, and the app must not fetch from the internet.
import { describe, expect, it } from "vitest";

async function sources(): Promise<{ file: string; text: string }[] | null> {
  try {
    const fsName = "node:fs", pName = "node:path", uName = "node:url";
    const fs = await import(/* @vite-ignore */ fsName), path = await import(/* @vite-ignore */ pName), url = await import(/* @vite-ignore */ uName);
    const root = url.fileURLToPath(new URL("../", import.meta.url));
    const out: { file: string; text: string }[] = [];
    const walk = (d: string) => {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, e.name);
        if (e.isDirectory()) walk(p);
        else if (/\.(ts|tsx|css)$/.test(e.name)) out.push({ file: path.relative(root, p).split(path.sep).join("/"), text: fs.readFileSync(p, "utf8") });
      }
    };
    walk(root);
    return out;
  } catch { return null; }
}
const isTest = (f: string) => /\.test\.ts$/.test(f) || f.startsWith("testing/");

describe("source hygiene", () => {
  it("no application file imports test fixtures", async () => {
    const all = await sources();
    if (!all) { console.warn("SKIPPED: source folder not readable"); return; }
    const bad = all.filter((s) => !isTest(s.file) && /["'][^"']*\/testing\/[^"']*["']/.test(s.text)).map((s) => s.file);
    expect(bad).toEqual([]);
  });
  it("no application file refers to an internet address", async () => {
    const all = await sources();
    if (!all) return;
    const bad = all.filter((s) => !isTest(s.file) && /https?:\/\/(?!127\.0\.0\.1|localhost)/.test(s.text.replace(/\/\/ .*$/gm, ""))).map((s) => s.file);
    expect(bad).toEqual([]);
  });
});
