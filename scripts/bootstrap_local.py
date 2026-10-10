"""Create the combined project's own loopback database; never use a source .env."""
import json
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
DATABASE = "ukai_b_integration_combined_20261008"
PORT = 55432


def run(*args):
    return subprocess.run([str(a) for a in args], cwd=ROOT, check=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def main():
    for name in ("objects", "scratch", "protected-unused"):
        (ROOT / name).mkdir(exist_ok=True)
    password_path = RUNTIME / "db-password.txt"
    if not password_path.exists():
        password_path.write_text(secrets.token_urlsafe(32), encoding="ascii")
    password = password_path.read_text().strip()
    pg = RUNTIME / "pgsql" / "bin"
    data = RUNTIME / "pgdata2"
    if not (data / "PG_VERSION").exists():
        run(pg / "initdb.exe", "-D", data, "-U", "ukai_local", "-A", "scram-sha-256",
            "--pwfile=" + str(password_path), "--encoding=UTF8", "--locale=C")
    config = data / "postgresql.conf"
    if "# Ukai combined loopback" not in config.read_text():
        with config.open("a") as file:
            file.write("\n# Ukai combined loopback\nlisten_addresses = '127.0.0.1'\nport = 55432\n")
    status = subprocess.run([str(pg / "pg_ctl.exe"), "-D", str(data), "status"], capture_output=True)
    if status.returncode:
        run(pg / "pg_ctl.exe", "-D", data, "-l", RUNTIME / "postgresql.log", "-w", "start")
    import psycopg
    with psycopg.connect(host="127.0.0.1", port=PORT, user="ukai_local", password=password,
                        dbname="postgres", autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DATABASE,)).fetchone():
            from psycopg import sql
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE)))
        from psycopg import sql
        conn.execute(sql.SQL("ALTER DATABASE {} SET timezone = 'UTC'").format(sql.Identifier(DATABASE)))
    url = f"postgresql+psycopg://ukai_local:{password}@127.0.0.1:{PORT}/{DATABASE}"
    (RUNTIME / "database-url.txt").write_text(url, encoding="utf-8")
    os.environ["DATABASE_URL"] = url
    with psycopg.connect(host="127.0.0.1", port=PORT, user="ukai_local", password=password,
                        dbname=DATABASE, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    import sys
    run(sys.executable, "-m", "alembic", "upgrade", "head")
    marker = {"database": DATABASE, "project": "Ukai Combined", "version": "1", "state": "created",
              "protected_database": "ukai", "protected_object_root": str(ROOT / "protected-unused"),
              "objects_root": str(ROOT / "objects"), "scratch_root": str(ROOT / "scratch")}
    (RUNTIME / "target-marker.json").write_text(json.dumps(marker, indent=2), encoding="utf-8")
    print("Isolated local PostgreSQL/PostGIS is ready on port 55432.")


if __name__ == "__main__":
    main()
