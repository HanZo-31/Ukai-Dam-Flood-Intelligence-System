import { describe, expect, it } from "vitest";
import { LatestGuard } from "./latest";

describe("stale request guard", () => {
  it("only the newest token is current", () => {
    const g = new LatestGuard();
    const a = g.begin(); const b = g.begin();
    expect(g.isCurrent(a)).toBe(false);
    expect(g.isCurrent(b)).toBe(true);
    g.invalidate();
    expect(g.isCurrent(b)).toBe(false);
  });
});
