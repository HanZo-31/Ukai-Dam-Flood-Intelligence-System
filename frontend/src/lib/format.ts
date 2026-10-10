export const NOT_AVAILABLE = "Not available";
export const NOT_CALCULATED = "Not calculated";

export function isNum(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/** null/undefined/NaN is "unavailable", never zero. */
export function formatValue(v: number | null | undefined, digits = 0, empty: string = NOT_AVAILABLE): string {
  if (!isNum(v)) return empty;
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Stored arrival is in minutes. The UI shows hours by dividing once, presentation only. */
export function minutesToHours(minutes: number): number {
  return minutes / 60;
}

export function formatHours(minutes: number | null | undefined): string {
  if (!isNum(minutes)) return NOT_AVAILABLE;
  const h = minutesToHours(minutes);
  return Number.isInteger(h) ? String(h) : h.toFixed(1);
}

/** Declared nominal model-clock index, printed as stored (UTC letters of the index), no local-time shift. */
export function formatNominal(iso: string | null | undefined): string {
  if (!iso) return NOT_AVAILABLE;
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(iso);
  return m ? `${m[1]} ${m[2]}` : NOT_AVAILABLE;
}

export function shortChecksum(c: string | null | undefined): string {
  if (!c) return NOT_AVAILABLE;
  const hex = c.replace(/^sha256:/, "");
  return hex.length > 16 ? `sha256:${hex.slice(0, 12)}…${hex.slice(-6)}` : c;
}

export function formatBytes(n: number | null | undefined): string {
  if (!isNum(n)) return NOT_AVAILABLE;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
