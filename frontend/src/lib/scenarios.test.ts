import { describe, expect, it } from "vitest";
import { describeScenario, peakRelease, sortScenarios } from "./scenarios";
import { sameOriginPath } from "./assets";

describe("scenario naming", () => {
  it("labels and orders; 2006 is reconstructed historical and last", () => {
    const items = [
      { id: "ukai-2006-historical-hr-int-v2", type: "historical_replay" },
      { id: "ukai-hyp-h03-release30000-hr-int-v1", type: "hypothetical" },
      { id: "ukai-hyp-h01-release15000-hr-int-v1", type: "hypothetical" },
    ].map((x) => ({ id: x.id, info: describeScenario(x.id, x.type) }));
    const sorted = sortScenarios(items).map((x) => x.info.short);
    expect(sorted).toEqual(["H01", "H03", "2006"]);
    expect(items[0].info.kindLabel).toBe("Reconstructed historical");
  });
  it("peak release null stays null, not zero", () => {
    expect(peakRelease(undefined)).toBeNull();
    expect(peakRelease({ parameters: { peak_release_m3s: null } } as never)).toBeNull();
    expect(peakRelease({ parameters: { peak_release_m3s: 20000 } } as never)).toBe(20000);
  });
  it("downloads stay same-origin", () => {
    expect(sameOriginPath("http://127.0.0.1:8765/api/v1/x?y=1")).toBe("/api/v1/x?y=1");
    expect(sameOriginPath("/api/v1/x")).toBe("/api/v1/x");
  });
});
