"""Strict container-only startup; does not alter B1's local configuration loader."""
import os
import sys
from urllib.request import build_opener, ProxyHandler

from services.api.app.settings import production_settings
from services.api.app.security import security_settings
from services.api.app.services.download_policy import download_policy


def configure(environment=None):
    environment = os.environ if environment is None else environment
    environment.setdefault("B2_ENV", "production")
    settings = production_settings(environment, required=True)
    security_settings(environment)
    download_policy(environment)
    environment["DATABASE_URL"] = settings.database_url
    environment.pop("DATABASE_URL_FILE", None)
    return settings.workers


def main():
    if sys.argv[1:] in (["health"], ["ready"]):
        try:
            path = "/readyz" if sys.argv[1] == "ready" else "/api/v1/health"
            with build_opener(ProxyHandler({})).open("http://127.0.0.1:8000" + path, timeout=5) as response:
                return 0 if response.status == 200 else 1
        except Exception:
            return 1
    if sys.argv[1:]:
        print("Unsupported container command.", file=sys.stderr)
        return 2
    try:
        workers = configure()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    # Exec preserves normal signal delivery. No query-bearing access logs or
    # unreviewed forwarding headers; external proxy/security is a separate gate.
    os.execvp("python", ["python", "-m", "uvicorn", "services.api.app.main:app",
                        "--host", "0.0.0.0", "--port", "8000", "--workers", str(workers),
                        "--no-access-log", "--no-proxy-headers", "--no-server-header",
                        "--timeout-graceful-shutdown", "15"])


if __name__ == "__main__":
    raise SystemExit(main())
