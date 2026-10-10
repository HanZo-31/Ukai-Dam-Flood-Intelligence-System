import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import PointInspector, { pointText } from "./PointInspector";
import type { ScenarioView } from "../model";

const scenario = { info: { short: "H02" }, detail: { engine: { name: "HEC-RAS", software_version: "fixture" } } } as ScenarioView;
const noop = () => {};
describe("point inspector presentation", () => {
  it("does not start with fabricated sample values", () => {
    const html = renderToStaticMarkup(<PointInspector selection={null} scenarios={[{ scenario, layers: undefined }]} onSelect={noop} onClear={noop} />);
    expect(html).toContain("No location selected");
    expect(html).toContain("Point easting in metres");
    expect(html).not.toContain("0.00");
  });
  it("shows explicit full-run/no-data limitations for selected points", () => {
    const html = renderToStaticMarkup(<PointInspector selection={{ coordinate: [300000, 2400000], sequence: 1 }} scenarios={[{ scenario, layers: undefined }]} onSelect={noop} onClear={noop} elapsedHours={48} />);
    for (const text of ["Stored full-run maxima", "No data is unknown", "not scientifically validated", "Arrival state unknown", "Retry point reads", "Clear selected location"]) expect(html).toContain(text);
    expect(html).toContain("Waiting for raster data");
  });
  it("labels both scenarios and the direction without guessing velocity differences", () => {
    const html = renderToStaticMarkup(<PointInspector selection={{ coordinate: [300000, 2400000], sequence: 1 }} scenarios={[{ scenario, layers: undefined }, { scenario: { ...scenario, info: { ...scenario.info, short: "H03" } }, layers: undefined }]} onSelect={noop} onClear={noop} />);
    for (const text of ["Baseline", "Candidate", "H03", "Candidate − baseline", "no velocity delta", "not synchronized calendar times"]) expect(html).toContain(text);
  });
  it("formats arrival minutes once and keeps zero/nodata distinct", () => {
    expect(pointText({ kind: "value", value: 2880 }, true)).toBe("48.00 h");
    expect(pointText({ kind: "value", value: 0 })).toBe("0.00");
    expect(pointText({ kind: "nodata", value: null })).toBe("No data");
    expect(pointText({ kind: "outside", value: null })).toBe("Outside raster coverage");
    expect(pointText({ kind: "error", value: null })).toBe("Unavailable");
  });
});
