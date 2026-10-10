// Test-only access to Node built-ins through variable specifiers (the app's tsconfig has no Node types and Vite must not bundle them).
export interface NodeIo {
  readFile: (path: string) => Uint8Array;
  deflate: (u: Uint8Array) => Uint8Array;
  inflate: (u: Uint8Array) => Uint8Array;
  sha256Hex: (u: Uint8Array) => string;
  fileUrl: (rel: string, base: string | URL) => string;
}
export async function nodeIo(): Promise<NodeIo> {
  const fsName = "node:fs", zName = "node:zlib", uName = "node:url", cName = "node:crypto";
  const fs = await import(/* @vite-ignore */ fsName), zlib = await import(/* @vite-ignore */ zName), url = await import(/* @vite-ignore */ uName), crypto = await import(/* @vite-ignore */ cName);
  return {
    readFile: (p) => new Uint8Array(fs.readFileSync(p)),
    deflate: (u) => new Uint8Array(zlib.deflateSync(u)),
    inflate: (u) => new Uint8Array(zlib.inflateSync(u)),
    sha256Hex: (u) => crypto.createHash("sha256").update(u).digest("hex"),
    fileUrl: (rel, base) => url.fileURLToPath(new URL(rel, base)),
  };
}
export const toArrayBuffer = (u: Uint8Array): ArrayBuffer => u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength) as ArrayBuffer;
