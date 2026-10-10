"""Local Docker verification; never changes or rebuilds B1's working DB."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from scripts.backup_db import snapshot, source_url
from scripts.rehearse_b1_handoff import object_inventory, require
from services.api.app.storage import default_store, LocalObjectStore


def identity(name):
    require(bool(re.fullmatch(r"b2_container_[0-9a-f]{16}", name)), "unsafe container rehearsal identity")
    return name


def destination(path):
    path = Path(path).resolve()
    boundary = (ROOT / "data/handoff").resolve()
    require(path.is_relative_to(boundary) and path != boundary and not path.exists(),
            "choose a new directory beneath data/handoff")
    return path


def rehearse(output, *, large_assets=False, performance_profile=None):
    if performance_profile is not None:
        from scripts.b2_performance_probe import read_profile
        performance = read_profile(performance_profile)
        performance_profile_hash = __import__('hashlib').sha256(Path(performance_profile).read_bytes()).hexdigest()
        large_assets = True
    output = destination(output)
    name = identity("b2_container_" + uuid.uuid4().hex[:16])
    network, volume, database = name + "_net", name + "_objects", name + "_db"
    live = create_engine(source_url())
    original = {"database": snapshot(live), "objects": object_inventory(default_store())}
    source_before = object_inventory(LocalObjectStore(ROOT / "database"))
    root_pins = (ROOT / "requirements.txt").read_bytes()
    b1_compose = (ROOT / "compose.yaml").read_bytes()
    output.mkdir(parents=True)
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
              "scope": "local Linux API container engineering verification with synthetic fixtures",
              "result": "failed", "scientific_approval": False, "production_accepted": False,
              "checks": [], "identity": name}
    created_network = created_volume = created_db = compose_started = False
    environment = dict(os.environ)
    # Temporary test credentials are generated, not read from or applied to B1.
    password, reader_password = secrets.token_hex(24), secrets.token_hex(24)
    admin_url = URL.create("postgresql+psycopg", username="verification", password=password,
                           host="catalogue", database=name).render_as_string(hide_password=False)
    reader_url = URL.create("postgresql+psycopg", username="b2_reader", password=reader_password,
                            host="catalogue", database=name).render_as_string(hide_password=False)
    environment.update(POSTGRES_PASSWORD=password, DATABASE_URL=admin_url,
                       B2_READER_PASSWORD=reader_password)

    def docker(args, *, label=None, timeout=300, allow_failure=False):
        completed = subprocess.run(["docker", *args], cwd=ROOT, env=environment,
                                   capture_output=True, text=True, timeout=timeout)
        if label:
            print("Checking: " + label, flush=True)
            report["checks"].append({"check": label, "passed": completed.returncode == 0})
        if not allow_failure:
            if completed.returncode:
                safe = (completed.stdout + "\n" + completed.stderr).replace(password, "[redacted]").replace(reader_password, "[redacted]")
                (output / "failure-diagnostics.txt").write_text(safe, encoding="utf-8")
            require(completed.returncode == 0, (label or "Docker operation") + " failed; private diagnostics not published")
        return completed

    def verify(args, label, *, user=None, read_only=False):
        command = ["run", "--rm", "--network", network, "--env", "DATABASE_URL",
                   "--env", "B2_READER_PASSWORD", "--env", "OBJECT_STORAGE_ROOT=/objects",
                   "--mount", "type=volume,src=" + volume + ",dst=/objects" + (",readonly" if read_only else "")]
        if user:
            command += ["--user", user]
        return docker(command + ["ukai-b2-api:verification", *args], label=label)

    try:
        report["runtime_image"] = docker(["image", "inspect", "ukai-b2-api:local", "--format", "{{.Id}}"] ).stdout.strip()
        report["verification_image"] = docker(["image", "inspect", "ukai-b2-api:verification", "--format", "{{.Id}}"] ).stdout.strip()
        # These are expected startup rejections, not failing acceptance checks.
        for label, env_args in [
            ("container rejects local-mode fallback", ["--env", "B2_ENV=local", "--env", "DATABASE_URL"]),
            ("container rejects missing explicit database", ["--env", "B2_ENV=production"]),
            ("container rejects wildcard host policy", ["--env", "B2_ENV=production", "--env", "DATABASE_URL",
                "--env", "B2_STORAGE_ID=fixture-store", "--env", "B2_ALLOWED_HOSTS=*"]),
        ]:
            rejected = docker(["run", "--rm", "--network", "none", *env_args,
                               "ukai-b2-api:local"], allow_failure=True)
            require(rejected.returncode == 2 and "configuration is invalid" in rejected.stderr
                    and password not in rejected.stderr, "invalid startup did not fail closed")
            report["checks"].append({"check": label, "passed": True})
        # Internal-only gateway mode suppresses published ports on this engine.
        # Use an owned test bridge; DB ports remain unpublished.
        docker(["network", "create", network]); created_network = True
        docker(["volume", "create", volume]); created_volume = True
        docker(["run", "-d", "--name", database, "--network", network, "--network-alias", "catalogue",
                "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_USER=verification", "--env", "POSTGRES_DB=" + name,
                "--tmpfs", "/var/lib/postgresql/data:rw,size=512m", "postgis/postgis:16-3.4"])
        created_db = True
        deadline = time.monotonic() + 60
        while docker(["exec", database, "pg_isready", "-U", "verification", "-d", name], allow_failure=True).returncode:
            require(time.monotonic() < deadline, "disposable PostGIS startup timed out")
            time.sleep(.5)
        verify(["-c", "import os; os.chown('/objects',10001,10001)"], "owned synthetic volume permissions", user="0:0")
        verify(["-m", "alembic", "upgrade", "head"], "Linux complete migration chain")
        verify(["-m", "alembic", "check"], "Linux schema parity")
        verify(["scripts/seed_db.py"], "Linux legacy seed")
        # B1's existing backup drill requires a host Docker CLI/socket and a
        # loopback DB, and hard-codes its working container. Never expose that
        # Docker socket to the API verifier or weaken B1's backup safety guard.
        excluded = "tests/test_published_registry.py::test_populated_bundle_backup_and_restore"
        report["linux_host_only_exclusion"] = excluded
        suite = verify(["-m", "pytest", "-q", "-p", "no:cacheprovider", "--deselect", excluded],
                       "Linux B2 suite and applicable B1 tests")
        summary = re.search(r"\d+ passed[^\n]*", suite.stdout)
        require(summary and not re.search(r"\d+ (failed|skipped|errors?)", suite.stdout), "Linux suite incomplete")
        report["linux_suite_summary"] = summary.group(0)
        verify(["scripts/export_b2_openapi.py", "--check"], "Linux OpenAPI freshness")
        verify(["-m", "pip", "check"], "Linux dependency consistency")
        verify(["scripts/b2_container_fixture.py", "prepare"], "actual GIS-aware Linux fixture imports")
        environment["DATABASE_URL"] = reader_url
        verify(["scripts/b2_container_fixture.py", "reader"], "reader database write privilege denied")
        environment["DATABASE_URL"] = admin_url
        with tempfile.TemporaryDirectory(prefix="b2-container-private-") as private:
            private = Path(private)
            secret = private / "database-url.txt"
            secret.write_text(reader_url, encoding="utf-8")
            override = private / "compose-fixture.yaml"
            override.write_text("services:\n  api:\n    volumes:\n      - type: volume\n"
                                "        source: fixture\n        target: /objects\n        read_only: true\n"
                                "volumes:\n  fixture:\n    external: true\n    name: " + volume + "\n")
            with socket.socket() as available:
                available.bind(("127.0.0.1", 0))
                selected_port = available.getsockname()[1]
            environment.update(B2_DATABASE_URL_FILE=str(secret), B2_DATABASE_NETWORK=network,
                               B2_OBJECT_STORAGE_PATH=str(output), B2_API_PORT=str(selected_port),
                               B2_STORAGE_ID="b2-container-fixture")
            environment["B2_CORS_ORIGINS"] = '["https://fixture-frontend.invalid"]'
            compose = ["compose", "-p", name, "-f", str(ROOT / "services/api/compose.yaml"), "-f", str(override)]
            docker(compose + ["config", "--quiet"], label="standalone Compose configuration")
            try:
                compose_started = True
                docker(compose + ["up", "-d", "--no-build"], label="actual hardened Compose API startup")
                container = docker(compose + ["ps", "-q", "api"]).stdout.strip()
                inspected = json.loads(docker(["inspect", container]).stdout)[0]
                # Desktop can return from Compose up before published-port
                # network state is populated. Inspect boundedly before asserting.
                inspect_deadline = time.monotonic() + 15
                while not inspected["NetworkSettings"]["Ports"].get("8000/tcp"):
                    require(time.monotonic() < inspect_deadline, "API ports not ready; inspect runtime startup")
                    time.sleep(.2)
                    inspected = json.loads(docker(["inspect", container]).stdout)[0]
                host = inspected["HostConfig"]
                require(host["ReadonlyRootfs"] and host["CapDrop"] == ["ALL"]
                        and "no-new-privileges:true" in host["SecurityOpt"], "runtime isolation mismatch")
                require(inspected["Config"]["User"] == "10001:10001", "API is not non-root")
                bindings = inspected["NetworkSettings"]["Ports"]["8000/tcp"]
                report["published_bindings"] = bindings
                require(len(bindings) == 1 and bindings[0]["HostIp"] == "127.0.0.1", "API exposed beyond loopback")
                port = bindings[0]["HostPort"]
                with httpx.Client(base_url="http://127.0.0.1:" + port, trust_env=False, timeout=10) as client:
                    deadline = time.monotonic() + 45
                    while True:
                        try:
                            if client.get("/api/v1/health").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        require(time.monotonic() < deadline, "container API startup timed out")
                        time.sleep(.5)
                    runtime = docker(["exec", container, "python", "-c",
                                      "import sys,os; from pathlib import Path; import importlib.metadata as m; "
                                      "print(__import__('json').dumps({'python':sys.version.split()[0],'uid':os.getuid(),"
                                      "'private_env_absent':not Path('/app/.env').exists(),"
                                      "'test_source_absent':not Path('/app/tests').exists(),"
                                      "'packages':{d.metadata['Name']:d.version for d in m.distributions()}}))"])
                    report["runtime"] = json.loads(runtime.stdout)
                    require(report["runtime"]["python"].startswith("3.13.") and report["runtime"]["uid"] == 10001,
                            "incorrect container Python or user")
                    safety = docker(["exec", container, "python", "-m", "services.api.app.runtime_inventory"],
                                    label="patched native library and runtime attack-surface facts")
                    report["runtime_safety"] = json.loads(safety.stdout)
                    facts = report["runtime_safety"]
                    require(facts.get("python_expat_version") == "expat_2.9.0", "Python bundled parser remains unpatched")
                    require(facts["expat_version"] == "expat_2.9.0" and facts["uid"] == 10001
                            and facts["effective_capabilities"] == "0000000000000000"
                            and facts["no_new_privileges"] and facts["pip_absent"] and facts["ensurepip_absent"]
                            and facts["telemetry_exporter_absent"] and not facts["privileged_executables"]
                            and not facts["perl_interpreters"]
                            and all(facts["absent_executables"].values()), "runtime safety evidence mismatch")
                    verify(["scripts/b2_container_fixture.py", "accept"], "all eight endpoints and byte integrity over container TCP", read_only=True)
                    verify(["scripts/b2_container_fixture.py", "readiness-cases"], "real readiness failure and recovery matrix")
                    verify(["scripts/b2_container_fixture.py", "security-cases"], "actual production security boundary over container TCP", read_only=True)
                    # Change only the generated API's tmpfs, never object data.
                    docker(["exec", container, "python", "-c", "import os; os.chmod('/tmp',0o500)"])
                    try:
                        require(client.get("/readyz").status_code == 503, "read-only scratch was accepted")
                        require(client.get("/api/v1/health").status_code == 200, "scratch failure blocked liveness")
                    finally:
                        docker(["exec", container, "python", "-c", "import os; os.chmod('/tmp',0o700)"])
                    require(client.get("/readyz").status_code == 200, "scratch permission recovery failed")
                    docker(["exec", container, "python", "-c",
                            "import os,shutil; from pathlib import Path; f=Path('/tmp/readiness-budget-test').open('wb'); "
                            "os.posix_fallocate(f.fileno(),0,shutil.disk_usage('/tmp').free-7*1024*1024); f.close()"])
                    try:
                        require(client.get("/readyz").status_code == 503, "insufficient scratch reserve accepted")
                        require(client.get("/api/v1/health").status_code == 200, "scratch reserve blocked liveness")
                    finally:
                        docker(["exec", container, "python", "-c",
                                "from pathlib import Path; Path('/tmp/readiness-budget-test').unlink()"])
                    require(client.get("/readyz").status_code == 200, "scratch reserve recovery failed")
                    report["actual_scratch_failure_recovery_verified"] = True
                    if large_assets:
                        verify(["scripts/b2_large_asset_probe.py", "prepare"], "real >300 MiB aligned COGs through B1 GIS-aware publication")
                        large = verify(["scripts/b2_large_asset_probe.py", "check"], "large TCP downloads/concurrency/disconnect/capacity recovery", read_only=True)
                        report["large_asset_reliability"] = json.loads(large.stdout.strip().splitlines()[-1])
                        faults = verify(["scripts/b2_large_asset_probe.py", "failures"], "large missing/corrupt/truncated/unreadable failures and byte recovery")
                        report["large_asset_failures"] = json.loads(faults.stdout.strip().splitlines()[-1])
                        usage = docker(["exec", container, "python", "-c",
                            "import shutil,json; from pathlib import Path; print(json.dumps({'scratch_free':shutil.disk_usage('/tmp').free,"
                            "'memory_peak_bytes':int(Path('/sys/fs/cgroup/memory.peak').read_text()),"
                            "'memory_events':Path('/sys/fs/cgroup/memory.events').read_text()}))"])
                        report["scratch_after_large_probe"] = json.loads(usage.stdout)
                        require(report["scratch_after_large_probe"]["scratch_free"] > 1000*1024*1024, "large download scratch leaked")
                        require(report["scratch_after_large_probe"]["memory_peak_bytes"] < host["Memory"]
                                and 'oom_kill 0' in report["scratch_after_large_probe"]["memory_events"], "large downloads caused memory exhaustion")
                        report["resource_limits"] = {"memory_bytes": host["Memory"], "tmpfs": host["Tmpfs"],
                                                      "cpu_nanos": host["NanoCpus"], "pids": host["PidsLimit"]}
                    if performance_profile is not None:
                        from scripts.b2_performance_probe import probe
                        prepared = verify(["scripts/b2_performance_fixture.py", "prepare", str(performance["catalogue_extra_scenarios"])],
                                          "bounded synthetic catalogue scale and performance fingerprint")
                        fixture = json.loads(prepared.stdout.strip().splitlines()[-1])
                        before_perf = json.loads(docker(["inspect", container]).stdout)[0]
                        require(__import__('hashlib').sha256(Path(performance_profile).read_bytes()).hexdigest()==performance_profile_hash,
                                "performance profile changed during setup")
                        report["performance_profile_sha256"] = performance_profile_hash
                        measured = probe("http://127.0.0.1:"+port, container, fixture, performance,
                                         output/"performance-resource.json", host["Memory"])
                        require(__import__('hashlib').sha256(Path(performance_profile).read_bytes()).hexdigest()==performance_profile_hash,
                                "performance profile changed during measurement")
                        final_fingerprint = verify(["scripts/b2_performance_fixture.py", "fingerprint"],
                                                   "performance read-only catalogue/object fingerprint")
                        preserved = json.loads(final_fingerprint.stdout.strip().splitlines()[-1]) == fixture["fingerprint"]
                        after_perf = json.loads(docker(["inspect", container]).stdout)[0]
                        no_restart = before_perf["RestartCount"] == after_perf["RestartCount"] and not after_perf["State"]["OOMKilled"]
                        report["performance_reads_preserved_fixture"] = preserved
                        report["performance_no_restart_or_oom"] = no_restart
                        report["performance_result"] = measured["result"]
                        report["performance_gate"] = measured.get("gate")
                        require(preserved and no_restart, "performance mutated fixture or restarted/OOM-killed API")
                    verify(["scripts/b2_container_fixture.py", "failure-cases"], "actual container revocation/tampering safety")
                    protected = docker(["exec", container, "python", "-c",
                        "from pathlib import Path; "
                        "Path('/objects/forbidden-write').write_text('must fail')"], allow_failure=True)
                    require(protected.returncode != 0, "API object mount is writable")
                    docker(["exec", container, "python", "-m", "services.api.app.container_runtime", "health"], label="built-in liveness healthcheck")
                    docker(["exec", container, "python", "-m", "services.api.app.container_runtime", "ready"], label="built-in readiness healthcheck")
                    docker(["exec", "--env", "HTTP_PROXY=http://fixture-invalid-proxy:9",
                            "--env", "http_proxy=http://fixture-invalid-proxy:9", "--env", "NO_PROXY=",
                            "--env", "no_proxy=", container, "python", "-m",
                            "services.api.app.container_runtime", "ready"],
                           label="health command ignores environment proxy overrides")
                    deadline = time.monotonic() + 30
                    while json.loads(docker(["inspect", container]).stdout)[0]["State"]["Health"]["Status"] != "healthy":
                        require(time.monotonic() < deadline, "Docker readiness health did not become healthy")
                        time.sleep(.5)
                    report["docker_readiness_healthy_verified"] = True
                    # Pause ONLY the generated disposable DB, preserving its
                    # tmpfs, to test bounded readiness failure and recovery.
                    docker(["pause", database])
                    try:
                        started = time.monotonic()
                        require(client.get("/readyz").status_code == 503, "paused DB readiness stayed green")
                        elapsed = time.monotonic() - started
                        require(elapsed < 6, "readiness response exceeded bounded probe budget")
                        require(client.get("/api/v1/health").status_code == 200, "paused DB blocked liveness")
                        report["paused_db_readiness_seconds"] = round(elapsed, 3)
                    finally:
                        docker(["unpause", database])
                    deadline = time.monotonic() + 15
                    while client.get("/readyz").status_code != 200:
                        require(time.monotonic() < deadline, "readiness did not recover")
                        time.sleep(.2)
                    report["readiness_outage_recovery_verified"] = True
                    docker(["restart", container], label="API restart with secret configuration")
                    deadline = time.monotonic() + 30
                    while True:
                        try:
                            if client.get("/api/v1/scenarios").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        require(time.monotonic() < deadline, "API restart timed out")
                        time.sleep(.5)
                    require(client.get("/readyz").status_code == 200, "readiness failed after restart")
                    docker(["stop", "-t", "10", database])
                    require(client.get("/readyz").status_code == 503, "stopped DB readiness stayed green")
                    require(client.get("/api/v1/health").status_code == 200, "liveness coupled to DB")
                    response = client.get("/api/v1/scenarios")
                    require(response.status_code == 503 and response.headers["content-type"] == "application/problem+json",
                            "DB outage did not fail safely")
                    report["db_outage_safe_503_liveness_200"] = True
                shutdown_since = datetime.now(timezone.utc).isoformat()
                docker(compose + ["stop", "-t", "20"], label="graceful API stop")
                stopped = json.loads(docker(["inspect", container]).stdout)[0]["State"]
                shutdown = docker(["logs", "--since", shutdown_since, container])
                shutdown_text = shutdown.stdout + shutdown.stderr
                # Uvicorn re-raises SIGTERM after graceful application shutdown;
                # init can therefore report 143. Require fresh completion logs,
                # not merely a signal exit, and reject SIGKILL/OOM termination.
                completed_shutdown = ("Application shutdown complete." in shutdown_text
                                      and "Finished server process" in shutdown_text)
                report["api_graceful_exit_code"] = stopped["ExitCode"]
                report["fresh_application_shutdown_logs_complete"] = completed_shutdown
                require(stopped["ExitCode"] in {0, 143} and not stopped["OOMKilled"]
                        and completed_shutdown, "API shutdown was not clean")
                report["runtime_isolation_verified"] = True
                report["object_mount_write_denied"] = True
                report["result"] = "passed"
            finally:
                if compose_started:
                    docker(compose + ["down", "--timeout", "20"], label="owned API container removal")
    finally:
        identity(name)
        cleanup = []
        for enabled, args in ((created_db, ["rm", "-f", database]),
                              (created_volume, ["volume", "rm", volume]),
                              (created_network, ["network", "rm", network])):
            if enabled:
                cleanup.append(docker(args, allow_failure=True).returncode == 0)
        report["owned_resources_removed"] = all(cleanup)
        report["working_data_preserved"] = original == {"database": snapshot(live), "objects": object_inventory(default_store())}
        report["b1_database_source_and_config_preserved"] = (
            source_before == object_inventory(LocalObjectStore(ROOT / "database"))
            and root_pins == (ROOT / "requirements.txt").read_bytes()
            and b1_compose == (ROOT / "compose.yaml").read_bytes())
        live.dispose()
        if not all(report[key] for key in ("owned_resources_removed", "working_data_preserved", "b1_database_source_and_config_preserved")):
            report["result"] = "failed"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "container-verification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    require(report["result"] == "passed", "container verification failed")
    print("B2 local container verification passed; B1 preserved; owned resources removed.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--large-assets", action="store_true", help="Owned >300 MiB real COG reliability/failure checks")
    parser.add_argument("--performance-profile", type=Path, help="Bounded local performance targets; implies --large-assets")
    args = parser.parse_args()
    rehearse(args.output, large_assets=args.large_assets, performance_profile=args.performance_profile)
