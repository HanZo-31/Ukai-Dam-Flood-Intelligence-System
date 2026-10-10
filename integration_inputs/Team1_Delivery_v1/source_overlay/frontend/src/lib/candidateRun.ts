import { CandidateError, validateResult, type CandidateClient, type CandidateRequest, type CandidateResult } from "./candidate";

export class CandidateInvalid extends Error {
  readonly problems: string[];
  constructor(problems: string[]) { super("The candidate service returned a result that does not match the request."); this.name = "CandidateInvalid"; this.problems = problems; }
}
export interface RunContext { knownScenarioIds: string[] | null; storedPeaks: number[] | null }
const sleepFor = (ms: number, signal?: AbortSignal) => new Promise<void>((res, rej) => {
  const t = setTimeout(res, ms);
  signal?.addEventListener("abort", () => { clearTimeout(t); rej(new DOMException("Aborted", "AbortError")); }, { once: true });
});

/** Submit one explicit selection; follow queued/running states (reserved for future modes); every response is checked against the request. */
export async function runLookup(client: CandidateClient, req: CandidateRequest, ctx: RunContext, signal?: AbortSignal, opts: { pollMs?: number; maxPolls?: number } = {}): Promise<CandidateResult> {
  const pollMs = opts.pollMs ?? 1000, maxPolls = opts.maxPolls ?? 30;
  let raw = await client.submit(req, signal);
  for (let i = 0; ; i++) {
    const problems = validateResult(raw, req, ctx);
    if (problems.length) throw new CandidateInvalid(problems);
    const r = raw as CandidateResult;
    if (r.status === "completed" || r.status === "failed") return r;
    if (i >= maxPolls) throw new CandidateError("unavailable", "The job did not finish in the expected time.");
    await sleepFor(pollMs, signal);
    raw = await client.getJob(r.job_id, signal);
  }
}
