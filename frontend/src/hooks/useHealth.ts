import { useEffect, useState } from "react";
import { getHealth, isAbort } from "../lib/api";

export type ApiStatus = "checking" | "connected" | "unreachable";

export function useHealth(intervalMs = 15000): ApiStatus {
  const [status, setStatus] = useState<ApiStatus>("checking");
  useEffect(() => {
    let alive = true;
    let ac = new AbortController();
    const check = () => {
      ac.abort(); ac = new AbortController();
      getHealth(ac.signal).then(() => alive && setStatus("connected"), (e) => { if (alive && !isAbort(e)) setStatus("unreachable"); });
    };
    check();
    const t = window.setInterval(check, intervalMs);
    return () => { alive = false; ac.abort(); window.clearInterval(t); };
  }, [intervalMs]);
  return status;
}
