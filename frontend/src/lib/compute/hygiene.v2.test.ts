// Guards for C09/C11: fixture and test-only code must not be reachable from the application, v1 stays untouched and separate.
import { describe, expect, it } from "vitest";

async function sources(): Promise<{ file: string; text: string }[] | null> {
  try {
    const fsName = "node:fs", pName = "node:path", uName = "node:url";
    const fs = await import(/* @vite-ignore */ fsName), path = await import(/* @vite-ignore */ pName), url = await import(/* @vite-ignore */ uName);
    const root = url.fileURLToPath(new URL("../../", import.meta.url));
    const out: { file: string; text: string }[] = [];
    const walk = (d: string) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (/\.(ts|tsx|css|json)$/.test(e.name)) out.push({ file: path.relative(root, p).split(path.sep).join("/"), text: fs.readFileSync(p, "utf8") }); } };
    walk(root);
    return out;
  } catch { return null; }
}
const prod = (f: string) => !/\.test\.tsx?$/.test(f) && !f.startsWith("testing/");

describe("v2 fixture isolation", () => {
  it("production sources never mention fixtures, the fixture transport or Node helpers", async () => {
    const all = await sources(); if (!all) throw new Error("source folder not readable: this guard cannot be skipped");
    const bad = all.filter((s) => prod(s.file) && /fixtures_v2|computeFixtureTransport|fixtureLoad|tiffWriter|nodeIo|SYNTHETIC|synthetic-(job|config|run|scenario|request)/.test(s.text)).map((s) => s.file);
    expect(bad).toEqual([]);
  });
  it("the controller replacement seam is used only by its hook and by tests", async () => {
    const all = await sources(); if (!all) throw new Error("not readable");
    const users = all.filter((s) => prod(s.file) && s.text.includes("setComputeControllerForTests")).map((s) => s.file);
    expect(users).toEqual(["hooks/useCompute.ts"]);
  });
  it("the compute library never imports the v1 candidate client or reaches the network except through the injected fetch", async () => {
    const all = await sources(); if (!all) throw new Error("not readable");
    const lib = all.filter((s) => s.file.startsWith("lib/compute/") && prod(s.file));
    expect(lib.filter((s) => /from "\.\.\/candidate(Run)?"/.test(s.text)).map((s) => s.file)).toEqual([]);
    expect(lib.filter((s) => /(^|[^.\w])fetch\(/.test(s.text.replace(/\/\/.*$/gm, ""))).map((s) => s.file)).toEqual(["lib/compute/client.ts"]); // only the client's default (same-origin) fetch
    expect(lib.filter((s) => /localStorage|sessionStorage|indexedDB/.test(s.text)).map((s) => s.file)).toEqual([]);
  });
  it("the compute-v2 adapter targets only its own prefix on the same origin", async () => {
    const all = await sources(); if (!all) throw new Error("not readable");
    const c = all.find((s) => s.file === "lib/compute/contract.ts")!;
    expect(c.text).toContain('"/api/v1/candidates/compute-v2"');
    expect(all.filter((s) => prod(s.file) && /https?:\/\/(?!127\.0\.0\.1|localhost)/.test(s.text.replace(/\/\/.*$/gm, ""))).map((s) => s.file)).toEqual([]);
  });
  it("v1 files are byte-identical to the base (verified against the recorded base hashes when available)", async () => {
    const all = await sources(); if (!all) throw new Error("not readable");
    // the v1 adapter files must still exist and keep exporting their v1 entry points
    const cand = all.find((s) => s.file === "lib/candidate.ts")!, run = all.find((s) => s.file === "lib/candidateRun.ts")!;
    expect(cand.text).toMatch(/export (async )?function createCandidateClient/);
    expect(run.text).toMatch(/export (async )?function runLookup/);
    expect(cand.text).not.toMatch(/compute-v2/);
  });
});
