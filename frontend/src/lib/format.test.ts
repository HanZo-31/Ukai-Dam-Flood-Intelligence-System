import { describe, expect, it } from "vitest";
import { formatBytes, formatHours, formatNominal, formatValue, minutesToHours, NOT_AVAILABLE, shortChecksum } from "./format";

describe("unavailable values", () => {
  it("null/undefined/NaN are 'Not available', never zero", () => {
    expect(formatValue(null)).toBe(NOT_AVAILABLE);
    expect(formatValue(undefined, 1)).toBe(NOT_AVAILABLE);
    expect(formatValue(NaN)).toBe(NOT_AVAILABLE);
    expect(formatValue(0, 1)).toBe("0.0");
    expect(formatHours(null)).toBe(NOT_AVAILABLE);
    expect(formatBytes(null)).toBe(NOT_AVAILABLE);
    expect(shortChecksum(null)).toBe(NOT_AVAILABLE);
  });
  it("custom empty text", () => expect(formatValue(null, 0, "Not calculated")).toBe("Not calculated"));
});
describe("arrival units", () => {
  it("minutes to hours divides once", () => {
    expect(minutesToHours(90)).toBe(1.5);
    expect(formatHours(60)).toBe("1");
    expect(formatHours(90)).toBe("1.5");
    expect(formatHours(0)).toBe("0");
  });
});
describe("nominal time", () => {
  it("prints the stored clock without timezone shifting", () => {
    expect(formatNominal("2006-08-06T00:00:00Z")).toBe("2006-08-06 00:00");
    expect(formatNominal(null)).toBe(NOT_AVAILABLE);
    expect(formatNominal("garbage")).toBe(NOT_AVAILABLE);
  });
});
