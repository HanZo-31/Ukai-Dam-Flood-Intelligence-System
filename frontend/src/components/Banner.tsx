import { RefreshCw, AlertTriangle } from "lucide-react";
export default function Banner(p: { message: string; onRetry?: () => void }) {
  return (
    <div className="banner" role="alert">
      <AlertTriangle size={18} aria-hidden /> <span>{p.message}</span>
      {p.onRetry && <button type="button" className="btn" onClick={p.onRetry}><RefreshCw size={14} aria-hidden /> Try again</button>}
    </div>
  );
}
