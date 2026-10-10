import { describe, expect, it } from "vitest";

describe("Compare scroll containment", () => {
  it("anchors hidden captions to Compare without clipping content or changing map layout", async () => {
    // Vitest deliberately stubs CSS imports; read the actual rule for this guard.
    const fsName = "node:fs";
    const fs = await import(/* @vite-ignore */ fsName);
    const stylesheet = fs.readFileSync(new URL("../compare-scroll.css", import.meta.url), "utf8") as string;
    const css = stylesheet.replace(/\/\*[\s\S]*?\*\//g, "").trim();
    expect(css).toMatch(/^\.compare-page\s*\{\s*position:\s*relative;\s*\}$/);
    expect(css).not.toMatch(/overflow|height|display|\.map|\.ol-|caption.*none/);
  });
});
