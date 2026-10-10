import type { ApiStatus } from "../hooks/useHealth";

const TEXT: Record<ApiStatus, string> = { checking: "Checking API…", connected: "Local API connected", unreachable: "API not reachable" };

export default function TopBar({ status, title, subtitle }: { status: ApiStatus; title: string; subtitle?: string }) {
  return (
    <header className="topbar">
      <div className="top-heading"><h1 className="top-title">{title}</h1>{subtitle && <p className="top-subtitle">{subtitle}</p>}</div>
      <div className="top-right">
        <span className={`api api-${status}`} role="status" title="Local connection status only; not a scientific validation status."><i aria-hidden /> {TEXT[status]}</span>
      </div>
    </header>
  );
}
