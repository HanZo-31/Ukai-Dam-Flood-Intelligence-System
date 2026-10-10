// Downloads the registered products named by an already-validated Result and verifies each one's length and SHA-256 before anything reads it.
import { ComputeError, isAbortError, sha256Of, type ComputeClient } from "./client";
import { ROLES, type ResultV2, type Role } from "./contract";

export type ProductEntry =
  | { status: "ok"; role: Role; bytes: number; sha256: string; buffer: ArrayBuffer }
  | { status: "not_offered"; role: Role; reason: string }
  | { status: "rejected"; role: Role; kind: "missing" | "length" | "checksum" | "error"; message: string };

export async function fetchProduct(client: ComputeClient, result: ResultV2, role: Role, signal?: AbortSignal): Promise<ProductEntry> {
  const asset = result.assets[role];
  if (!asset) return { status: "not_offered", role, reason: result.unavailable_reasons[role] ?? "The service did not provide this product." };
  try {
    const buf = await client.getAssetBytes(result.job_id, role, signal);
    if (buf.byteLength !== asset.bytes) return { status: "rejected", role, kind: "length", message: `Received ${buf.byteLength} bytes but the Result declares ${asset.bytes}; the product was discarded.` };
    const got = await sha256Of(buf);
    if (got !== asset.sha256) return { status: "rejected", role, kind: "checksum", message: "The product's checksum does not match the Result; it was discarded unread." };
    return { status: "ok", role, bytes: buf.byteLength, sha256: got, buffer: buf };
  } catch (e) {
    if (isAbortError(e)) throw e;
    if (e instanceof ComputeError) return { status: "rejected", role, kind: e.status === 404 ? "missing" : "error", message: e.message };
    return { status: "rejected", role, kind: "error", message: "The product could not be downloaded." };
  }
}

export async function fetchProducts(client: ComputeClient, result: ResultV2, signal?: AbortSignal): Promise<Record<Role, ProductEntry>> {
  const entries = await Promise.all(ROLES.map((r) => fetchProduct(client, result, r, signal)));
  return Object.fromEntries(entries.map((e) => [e.role, e])) as Record<Role, ProductEntry>;
}
