// Test-only loader for the SYNTHETIC packet fixtures (see testing/fixtures_v2/README.md). Never imported by application code.
import { nodeIo, toArrayBuffer } from "./nodeIo";
import type { FixtureFiles } from "./computeFixtureTransport";
import oracle from "./fixtures_v2/arrays-and-oracle.json";

export const ORACLE = oracle;
export async function loadFixtures() {
  const io = await nodeIo();
  const dir = new URL("./fixtures_v2/", import.meta.url);
  const rd = (n: string) => io.readFile(io.fileUrl(n, dir));
  const f = {
    baselineDepth: rd("baseline-depth.tif"), baselineArrival: rd("baseline-arrival.tif"), candidateDepth: rd("candidate-depth.tif"), candidateArrival: rd("candidate-arrival.tif"), extent: rd("extent.geojson"),
  };
  const sha = (u: Uint8Array) => `sha256:${io.sha256Hex(u)}`;
  const files: FixtureFiles = { tif: { candidateDepth: f.candidateDepth, candidateArrival: f.candidateArrival }, extent: f.extent, sha256: sha };
  const inflate = async (u: Uint8Array) => io.inflate(u);
  return { io, f, files, sha, inflate, ab: toArrayBuffer };
}
export type Fixtures = Awaited<ReturnType<typeof loadFixtures>>;
