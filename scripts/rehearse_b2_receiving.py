"""Step 18: new source copy, Python 3.13 venv and disposable PostGIS database.

Reuses B1's safe source allowlist and read-only inventories, never its live data.
Performance is a baseline unless the receiving teams separately agree targets.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import create_engine, text
from scripts.backup_db import snapshot, source_url
from scripts.rehearse_b1_handoff import object_inventory, source_package, require
from services.api.app.storage import LocalObjectStore, default_store


def validate_output(destination):
    destination = Path(destination).resolve()
    require(not destination.exists(), "receiving destination must be a new directory")
    boundary = (ROOT / "data/handoff").resolve()
    require(destination.is_relative_to(boundary) and destination != boundary,
            "receiving destination must be beneath data/handoff")
    return destination


def validate_database_name(name, working_name):
    require(bool(re.fullmatch(r"b2_receive_[0-9a-f]{32}", name)) and name != working_name,
            "unsafe disposable database identity")
    return name


def rehearsal(destination, *, samples=20, concurrency=4, io_mib=16):
    destination = validate_output(destination)
    require(sys.version_info[:2] in {(3, 12), (3, 13)}, "receiving setup requires Python 3.12 or 3.13")
    require(5 <= samples <= 200 and 1 <= concurrency <= 16 and 1 <= io_mib <= 128,
            "rehearsal measurements exceed safe local bounds")
    working_url = source_url()
    name = validate_database_name("b2_receive_" + uuid.uuid4().hex, working_url.database)
    target = working_url.set(database=name).update_query_dict({"options": "-csearch_path=public"})
    live = create_engine(working_url)
    working_store = default_store()
    before = {"database": snapshot(live), "objects": object_inventory(working_store)}
    destination.mkdir(parents=True)
    package = destination / "source"
    source_hashes = source_package(package)
    venv = destination / ".venv"
    receiving_python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    store = LocalObjectStore(destination / "objects")
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "DATABASE_URL", "OBJECT_STORAGE_ROOT"):
        environment.pop(key, None)
    environment.update(DATABASE_URL=target.render_as_string(hide_password=False),
        OBJECT_STORAGE_ROOT=str(store.root), PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    admin = create_engine(working_url, isolation_level="AUTOCOMMIT")
    receiving = None
    created = False
    steps = []
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
        "scope": "B2 clean same-host receiving and synthetic HTTP/performance rehearsal",
        "database_name": name, "scientific_approval": False,
        "agreed_performance_signoff": False, "steps": steps, "result": "failed"}

    def run(label, args, *, executable=None, timeout=600):
        print("Checking: " + label, flush=True)
        result = subprocess.run([str(executable or receiving_python), *args], cwd=package,
            env=environment, capture_output=True, text=True, timeout=timeout)
        # Do not persist raw CLI logs: database/index credentials could be present.
        require(result.returncode == 0, label + ": failed; diagnostic output kept out of public evidence")
        steps.append({"check": label, "passed": True})
        return result

    try:
        run("new independent Python 3.13 virtual environment", ["-m", "venv", str(venv)],
            executable=sys._base_executable)
        require(receiving_python.is_file(), "fresh Python executable missing")
        run("fresh runtime and B2 development dependency installation",
            ["-m", "pip", "install", "-r", "services/api/requirements-dev.txt", "--quiet"], timeout=900)
        run("fresh environment dependency consistency", ["-m", "pip", "check"])
        environment_check = run("interpreter isolation and installed inventory", ["-c",
            "import sys,json,importlib.metadata; print(json.dumps({'python':sys.version.split()[0],"
            "'prefix':sys.prefix,'base_prefix':sys.base_prefix,'packages':{d.metadata['Name']:d.version "
            "for d in importlib.metadata.distributions()}}))"])
        info = json.loads(environment_check.stdout)
        require(Path(info["prefix"]).resolve() == venv.resolve() and info["prefix"] != info["base_prefix"],
                "receiving interpreter reused the working environment")
        require(info["python"].startswith("3.13."), "incorrect receiving Python version")
        report["python"] = info["python"]
        report["fresh_python_environment"] = True
        report["installed_packages"] = info["packages"]
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
            created = True
        receiving = create_engine(target)
        with receiving.begin() as connection:
            connection.execute(text("CREATE EXTENSION postgis"))
        steps.append({"check": "new empty database with PostGIS, never a working restore", "passed": True})
        run("complete migration chain from clean source", ["-m", "alembic", "upgrade", "head"])
        require(len(snapshot(receiving)["tables"]) == 16, "receiving schema inventory differs")
        run("receiving model/schema parity", ["-m", "alembic", "check"])
        run("first receiving demo seed", ["scripts/seed_db.py"])
        seeded = {"database": snapshot(receiving), "objects": object_inventory(store)}
        run("second receiving demo seed", ["scripts/seed_db.py"])
        require(seeded == {"database": snapshot(receiving), "objects": object_inventory(store)},
                "seed repeat changed receiving rows/sequences/files")
        steps.append({"check": "seed idempotence including sequences and object hashes", "passed": True})
        tests = run("entire B1/B2 suite from receiving copy and new environment",
                    ["-m", "pytest", "-q", "-p", "no:cacheprovider"])
        summary = re.search(r"(\d+) passed[^\n]*", tests.stdout)
        require(summary is not None and not re.search(r"\b\d+ (?:failed|skipped|errors?)\b", tests.stdout),
                "receiving regression suite did not fully pass")
        report["clean_suite_summary"] = summary.group(0)
        require(seeded == {"database": snapshot(receiving), "objects": object_inventory(store)},
                "receiving tests changed seeded baseline")
        run("saved OpenAPI freshness", ["scripts/export_b2_openapi.py", "--check"])
        run("saved OpenAPI conformance", ["-m", "openapi_spec_validator", "docs/contracts/b2-openapi-v1.json"])
        run("real loopback HTTP acceptance and bounded performance baseline",
            ["scripts/b2_receiving_probe.py", "--output", str(destination / "http-performance.json"),
             "--samples", str(samples), "--concurrency", str(concurrency), "--io-mib", str(io_mib)], timeout=300)
        report["http_performance"] = json.loads((destination / "http-performance.json").read_text())
        require(report["http_performance"]["result"] == "passed", "HTTP rehearsal failed")
        require(source_hashes == object_inventory(LocalObjectStore(package)), "receiving source changed during checks")
        require(not (package / ".env").exists(), "private configuration was copied")
        report["source_copy_preserved"] = True
        report["source_hashes"] = source_hashes
        report["object_hashes"] = object_inventory(store)
        report["receiving_database"] = snapshot(receiving)
        steps.append({"check": "source-copy integrity and private-config exclusion", "passed": True})
        report["result"] = "passed"
    except Exception:
        report["failed_after_checks"] = len(steps)
        raise
    finally:
        if receiving is not None:
            receiving.dispose()
        try:
            if created:
                validate_database_name(name, working_url.database)
                with admin.connect() as connection:
                    connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
                    require(connection.execute(text("SELECT count(*) FROM pg_database WHERE datname=:name"),
                        {"name": name}).scalar_one() == 0, "disposable database cleanup failed")
                report["disposable_database_removed"] = True
        except Exception:
            report["result"] = "failed"
            report["disposable_database_removed"] = False
        finally:
            admin.dispose()
            try:
                after = {"database": snapshot(live), "objects": object_inventory(working_store)}
                report["working_data_preserved"] = before == after
                if before != after:
                    report["result"] = "failed"
            finally:
                live.dispose()
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            (destination / "receiving.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    require(report["result"] == "passed" and report.get("disposable_database_removed"), "receiving cleanup/preservation failed")
    print("B2 clean local receiving passed; working data preserved; disposable database removed.", flush=True)
    print("Performance is a measured baseline, not agreed scientific/production acceptance.", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--io-mib", type=int, default=16)
    args = parser.parse_args()
    try:
        rehearsal(args.output, samples=args.samples, concurrency=args.concurrency, io_mib=args.io_mib)
    except Exception:
        print("B2 receiving rehearsal failed; inspect its safe stage evidence; no acceptance sign-off.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
