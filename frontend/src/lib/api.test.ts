import { describe, expect, it } from "vitest";
import { ApiError, getJson, listScenarios, describeApiError } from "./api";

const resp = (status: number, body: string) => (async () => new Response(body, { status })) as unknown as typeof fetch;

describe("API client", () => {
  it("returns parsed JSON", async () => {
    expect(await getJson<{ a: number }>("/x", undefined, resp(200, '{"a":1}'))).toEqual({ a: 1 });
  });
  it("network failure -> network error with actionable text", async () => {
    const f = (async () => { throw new TypeError("fetch failed"); }) as unknown as typeof fetch;
    await expect(getJson("/x", undefined, f)).rejects.toMatchObject({ kind: "network" });
  });
  it("proxy 5xx with empty body is reported as backend not running", async () => {
    const e = await getJson("/x", undefined, resp(500, "")).catch((x) => x as ApiError);
    expect(e).toBeInstanceOf(ApiError);
    expect(describeApiError(e)).toMatch(/backend running/);
  });
  it("HTTP 404 uses the API detail", async () => {
    const e = await getJson("/x", undefined, resp(404, '{"detail":"Scenario not found"}')).catch((x) => x as ApiError);
    if (!(e instanceof ApiError)) throw new Error("Expected the request to reject with ApiError");
    expect(e.kind).toBe("http"); expect(e.status).toBe(404); expect(e.message).toBe("Scenario not found");
  });
  it("invalid JSON -> parse error", async () => {
    await expect(getJson("/x", undefined, resp(200, "<html>"))).rejects.toMatchObject({ kind: "parse" });
  });
  it("lists every page", async () => {
    const pages = [
      { items: [{ scenario_id: "a" }], pagination: { limit: 1, offset: 0, next_offset: 1 } },
      { items: [{ scenario_id: "b" }], pagination: { limit: 1, offset: 1, next_offset: null } },
    ];
    let i = 0;
    const f = (async () => new Response(JSON.stringify(pages[i++]), { status: 200 })) as unknown as typeof fetch;
    expect((await listScenarios(undefined, f)).map((s) => s.scenario_id)).toEqual(["a", "b"]);
  });
});
