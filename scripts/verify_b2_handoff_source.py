"""Freeze and verify the current local handoff source; never claim receiver approval."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import create_engine, text
from scripts.backup_db import snapshot, source_url
from scripts.package_b2_handoff import REFRESHED_EVIDENCE, digest
from scripts.rehearse_b1_handoff import source_package, object_inventory, require
from services.api.app.storage import default_store

BENCHMARK_FILES = {
    'scripts/b2_performance_fixture.py', 'scripts/b2_performance_probe.py',
    'scripts/rehearse_b2_container.py', 'services/api/tests/test_performance_rehearsal.py',
    'docs/contracts/b2-performance-targets.local.json',
}


def benchmark_fingerprints(report):
    values = report.get('source_hashes', {})
    require(BENCHMARK_FILES <= set(values), 'benchmark source coverage missing')
    # App/build provenance is separately checked against the exact measured image.
    # Changed handoff docs/tools must not be mistaken for a changed load generator.
    return {n: values[n].removeprefix('sha256:') for n in sorted(BENCHMARK_FILES)}


def verify(evidence, runtime_baseline, foundation_baseline):
    evidence = Path(evidence).resolve()
    output = evidence / REFRESHED_EVIDENCE[0]
    require(evidence.is_dir() and not output.exists(), "choose prepared evidence with no current test report")
    require(sys.version_info[:2] == (3, 13), "Python 3.13 required")
    read = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
    older = {}
    for path in runtime_baseline:
        older.update(read(path)["source_hashes"])
    runtime = {n: h.removeprefix("sha256:") for n, h in older.items()
               if n.startswith("services/api/app/") or n in {
                   "requirements.txt", "services/api/Dockerfile", "services/api/Dockerfile.dockerignore",
                   "services/api/requirements-container.lock", "services/api/compose.yaml",
                   "services/api/expat-sbom.cdx.json"}}
    require(any(n.endswith("main.py") for n in runtime) and "services/api/Dockerfile" in runtime,
            "runtime baseline coverage missing")
    current_container = read(evidence / "B2-step-6-container-verification.json")
    previous_container = read(evidence / "B2-step-5-performance-container-verification.json")
    image = current_container["runtime_image"]
    require(image == previous_container["runtime_image"] and image.startswith("sha256:"),
            "release image changed since performance")
    # Read only the shipped application files, never environment, private config or data.
    code = ("import hashlib,json; from pathlib import Path; root=Path('/app'); "
            "print(json.dumps({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() "
            "for p in (root/'services').rglob('*') if p.is_file() and '__pycache__' not in p.parts}))")
    shipped = subprocess.run(["docker", "run", "--rm", "--read-only", "--network", "none",
                              "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                              "--entrypoint", "python", image, "-B", "-c", code],
                             capture_output=True, text=True, timeout=60)
    require(shipped.returncode == 0, "exact-image application inventory unavailable")
    image_sources = json.loads(shipped.stdout)
    require(image_sources and any(n.endswith("main.py") for n in image_sources),
            "exact-image source inventory empty")
    runtime.update(image_sources)
    previous = read(evidence / "B2-step-5-performance-host-verification.json")
    require(previous.get("result") == "passed", "previous benchmark verification missing")
    benchmark = benchmark_fingerprints(previous)
    quality = read(evidence / 'B2-local-quality-verification.json')
    require(quality.get('result') == 'passed', 'local quality verification required')
    foundation = {n: h.removeprefix("sha256:") for n, h in read(foundation_baseline)["source_hashes"].items()
                  if n.startswith(("database/", "services/api/app/db/", "services/api/app/repositories/"))
                  or n in {"compose.yaml", "services/api/app/schemas.py", "services/api/app/catalog_schemas.py",
                            "services/api/app/published_contract.py", "services/api/app/published_registry.py",
                            "services/api/app/gis_validation.py", "services/api/app/storage.py"}}
    require(foundation, "B1 baseline missing")
    engine = create_engine(source_url())
    before = {"database": snapshot(engine), "objects": object_inventory(default_store())}
    report = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "result": "failed",
              "python": sys.version.split()[0], "checks": [], "production_accepted": False,
              "scientific_approval": False, "receiver_acknowledged": False,
              "runtime_image": image, "exact_image_application_files_compared": len(image_sources),
              "runtime_source_hashes": runtime, "benchmark_source_hashes": benchmark,
              "quality_source_hashes": quality['source_hashes'],
              "evidence_hashes": {n: digest(evidence / n) for n in REFRESHED_EVIDENCE[1:]}}
    try:
        with tempfile.TemporaryDirectory(prefix="b2-source-verification-", dir=evidence.parent) as staging:
            frozen = source_package(Path(staging) / "before")
            current_app = {n for n in frozen if n.startswith("services/api/app/")}
            require(current_app == {n for n in image_sources if n.startswith("services/api/app/")},
                    "current application file set differs from exact measured image")
            report["source_hashes"] = frozen
            require(all(frozen.get(n, '').removeprefix('sha256:') == h
                        for n, h in quality['source_hashes'].items()), 'source changed after quality checks')
            report["runtime_unchanged_from_performance"] = all(frozen.get(n, "").removeprefix("sha256:") == h for n, h in runtime.items())
            report["benchmark_unchanged_from_performance"] = all(frozen.get(n, "").removeprefix("sha256:") == h for n, h in benchmark.items())
            require(report["runtime_unchanged_from_performance"] and report["benchmark_unchanged_from_performance"],
                    "release or benchmark changed; new measurement/security evidence required")
            for label, args in (
                ("full Windows B1/B2 suite", ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=no"]),
                ("dependency consistency", ["-m", "pip", "check"]),
                ("OpenAPI freshness", ["scripts/export_b2_openapi.py", "--check"]),
                ("OpenAPI conformance", ["-m", "openapi_spec_validator", "docs/contracts/b2-openapi-v1.json"]),
            ):
                print("Checking: " + label, flush=True)
                run = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True,
                                     text=True, timeout=420)
                summary = (run.stdout.strip().splitlines()[-1:] or ["No stdout summary"])[0]
                report["checks"].append({"check": label, "passed": run.returncode == 0, "summary": summary})
                print(summary, flush=True)
                require(run.returncode == 0, label + " failed; private diagnostics not published")
            report["source_unchanged_during_verification"] = frozen == source_package(Path(staging) / "after")
            require(report["source_unchanged_during_verification"], "source changed during verification")
        report["result"] = "passed"
    finally:
        report["working_data_preserved"] = before == {
            "database": snapshot(engine), "objects": object_inventory(default_store())}
        report["b1_source_preserved"] = all(digest(ROOT / n) == h for n, h in foundation.items())
        report["b1_core_files_compared"] = len(foundation)
        with engine.connect() as connection:
            report["temporary_test_schemas_remaining"] = connection.execute(text(
                "SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'b1_verify_%'"
            )).scalar_one()
        engine.dispose()
        if not report["working_data_preserved"] or not report["b1_source_preserved"] or report["temporary_test_schemas_remaining"]:
            report["result"] = "failed"
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    require(report["result"] == "passed", "handoff source verification failed")
    print("Current source verified; B1 preserved; no receiver/joint approval claimed.", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--runtime-baseline", type=Path, nargs="+", required=True,
                        help="Chronological verified baseline reports, later hashes override earlier")
    parser.add_argument("--foundation-baseline", type=Path, required=True)
    args = parser.parse_args()
    verify(args.evidence_dir, args.runtime_baseline, args.foundation_baseline)
