import { useCallback, useEffect, useRef, useState } from "react";
import { LatestGuard } from "../lib/latest";
import { buildRequest, createCandidateClient, newRequestId, validateRequestInput, type Capabilities, type CandidateClient, type CandidateRequest, type CandidateResult } from "../lib/candidate";
import { CandidateInvalid, runLookup } from "../lib/candidateRun";
import { CandidateError } from "../lib/candidate";

export type CapsState = { status: "loading" } | { status: "ready"; caps: Capabilities } | { status: "unavailable"; message: string };
export interface RunState {
  phase: "idle" | "loading" | "error";
  /** last result that completed and passed every identity check; kept while loading or after a failure */
  last: { request: CandidateRequest; result: CandidateResult } | null;
  /** a failed job (status failed) from the most recent run, shown separately from the last successful result */
  failedJob: CandidateResult | null;
  error: string | null;
  problems: string[];
}

export function useCandidate(knownScenarioIds: string[], client?: CandidateClient) {
  const clientRef = useRef<CandidateClient>(client ?? createCandidateClient());
  const [caps, setCaps] = useState<CapsState>({ status: "loading" });
  const [run, setRun] = useState<RunState>({ phase: "idle", last: null, failedJob: null, error: null, problems: [] });
  const capGuard = useRef(new LatestGuard()), runGuard = useRef(new LatestGuard());
  const runAbort = useRef<AbortController | null>(null);
  const idsRef = useRef(knownScenarioIds);
  idsRef.current = knownScenarioIds;
  const capsRef = useRef<Capabilities | null>(null);

  const loadCaps = useCallback(() => {
    const token = capGuard.current.begin();
    const ac = new AbortController();
    setCaps({ status: "loading" });
    clientRef.current.getCapabilities(ac.signal).then(
      (c) => { if (capGuard.current.isCurrent(token)) { capsRef.current = c; setCaps({ status: "ready", caps: c }); } },
      (e: unknown) => {
        if (!capGuard.current.isCurrent(token) || (e instanceof DOMException && e.name === "AbortError")) return;
        capsRef.current = null;
        setCaps({ status: "unavailable", message: e instanceof CandidateError ? e.message : "The candidate service could not be reached." });
      });
    return () => { ac.abort(); capGuard.current.invalidate(); };
  }, []);
  useEffect(() => loadCaps(), [loadCaps]);
  useEffect(() => () => { runAbort.current?.abort(); runGuard.current.invalidate(); }, []);

  const start = useCallback((peak: number, allowNearest: boolean) => {
    const id = newRequestId();
    const bad = validateRequestInput(peak, id);
    if (bad) { setRun((r) => ({ ...r, phase: "error", error: bad, problems: [], failedJob: null })); return; }
    runAbort.current?.abort();
    const ac = new AbortController(); runAbort.current = ac;
    const token = runGuard.current.begin();
    const req = buildRequest(id, peak, allowNearest);
    setRun((r) => ({ ...r, phase: "loading", error: null, problems: [], failedJob: null }));
    runLookup(clientRef.current, req, { knownScenarioIds: idsRef.current.length ? idsRef.current : null, storedPeaks: capsRef.current?.storedPeaks ?? null }, ac.signal).then(
      (result) => {
        if (!runGuard.current.isCurrent(token)) return;
        if (result.status === "completed") setRun(() => ({ phase: "idle", last: { request: req, result }, failedJob: null, error: null, problems: [] }));
        else setRun((r) => ({ ...r, phase: "error", failedJob: result, error: "The service reported that this job failed.", problems: [] }));
      },
      (e: unknown) => {
        if (!runGuard.current.isCurrent(token) || (e instanceof DOMException && e.name === "AbortError")) return;
        if (e instanceof CandidateInvalid) setRun((r) => ({ ...r, phase: "error", error: e.message, problems: e.problems }));
        else setRun((r) => ({ ...r, phase: "error", error: e instanceof Error ? e.message : "The request failed.", problems: [] }));
      });
  }, []);

  return { caps, run, start, reloadCaps: loadCaps };
}
