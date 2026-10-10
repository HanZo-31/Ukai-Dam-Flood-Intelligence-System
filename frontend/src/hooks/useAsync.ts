import { useCallback, useEffect, useRef, useState } from "react";
import { LatestGuard } from "../lib/latest";
import { describeApiError, isAbort } from "../lib/api";

export interface AsyncState<T> { data: T | undefined; error: string | null; loading: boolean; reload: () => void }

/** Runs fn(signal) when deps change. Older/aborted requests can never overwrite newer state. */
export function useAsync<T>(fn: ((signal: AbortSignal) => Promise<T>) | null, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<{ data: T | undefined; error: string | null; loading: boolean }>({ data: undefined, error: null, loading: !!fn });
  const guard = useRef(new LatestGuard());
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  useEffect(() => {
    if (!fn) { guard.current.invalidate(); setState({ data: undefined, error: null, loading: false }); return; }
    const token = guard.current.begin();
    const ac = new AbortController();
    setState({ data: undefined, error: null, loading: true });
    fn(ac.signal).then(
      (data) => { if (guard.current.isCurrent(token)) setState({ data, error: null, loading: false }); },
      (e) => { if (isAbort(e) || !guard.current.isCurrent(token)) return; setState({ data: undefined, error: describeApiError(e), loading: false }); },
    );
    return () => { ac.abort(); guard.current.invalidate(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload };
}
