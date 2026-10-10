"""Loopback-only preview launcher. No migrations, seeding, imports or approval."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if sys.version_info[:2] not in {(3, 12), (3, 13)} or not 1 <= args.port <= 65535:
        raise ValueError("Python3.12/3.13 and valid local port required")
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    url = make_url(os.environ["DATABASE_URL"])
    if (url.host not in {"127.0.0.1", "localhost", "::1"} or url.database != args.expected_database
            or url.drivername != "postgresql+psycopg" or set(url.query) - {"options", "connect_timeout"}):
        raise ValueError("Explicit expected local database required")
    configured = [Path(os.environ[key]) for key in ("OBJECT_STORAGE_ROOT", "TMPDIR")]
    paths = [path.resolve() for path in configured]
    if (not all(path.is_absolute() and path.is_dir() for path in configured)
            or paths[0].is_relative_to(paths[1]) or paths[1].is_relative_to(paths[0])):
        raise ValueError("Explicit disjoint object/scratch roots required")
    if os.environ.get("B2_ENV", "local") != "local":
        raise ValueError("Preview supports local profile only")
    if url.host == "localhost":
        url = url.set(host="127.0.0.1")
    url = url.update_query_dict({"connect_timeout": "5", "options": "-c default_transaction_read_only=on -c statement_timeout=10000"})
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT current_database()")) != args.expected_database:
                raise ValueError("Database identity mismatch")
            if connection.scalar(text("SELECT version_num FROM public.alembic_version")) != "g05b8eab1001":
                raise ValueError("Current schema required")
    finally:
        engine.dispose()
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    os.environ.update(B2_ENV="local", B2_ENABLE_PROTOTYPE_PREVIEW="true",
                      B2_PROTOTYPE_ADMISSION_FILE=str(args.admission.resolve()),
                      B2_PROTOTYPE_LAUNCH_BOUND="127.0.0.1")
    from services.api.app.prototype_settings import prototype_settings
    prototype_settings()
    import uvicorn
    uvicorn.run("services.api.app.main:app", host="127.0.0.1", port=args.port,
                proxy_headers=False, access_log=False, workers=1)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("Prototype launcher failed: configuration or local dependency unavailable (" + type(error).__name__ + ").", file=sys.stderr)
        raise SystemExit(1)
