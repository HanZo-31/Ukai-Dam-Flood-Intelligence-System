"""Build a credential-free local B2 source/evidence archive, not a deployment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.rehearse_b1_handoff import source_package, require

EVIDENCE = (
    "B2-step-16-verification.md",
    "B2-step-18-verification.md",
    "B2-step-18-receiving-evidence.json",
    "B2-step-18-performance-baseline.json",
    "B2-step-19-test-evidence.json",
)
REFRESHED_EVIDENCE = (
    "B2-step-6-test-evidence.json",
    "B2-step-6-container-verification.json",
    "B2-step-5-performance-completed.md",
    "B2-step-5-performance-verification.json",
    "B2-step-5-performance-host-verification.json",
    "B2-step-5-performance-container-verification.json",
    "B2-step-5-performance-resource.json",
    "B2-step-5-performance-runtime-gate.json",
    "B2-step-4-final-runtime.trivy.json",
    "B2-step-4-runtime-python.json",
    "B2-step-4-windows-python.json",
    "B2-local-quality-verification.json",
)
FORBIDDEN_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".aws", ".ssh"}
WINDOWS_DEVICES = {"con", "prn", "aux", "nul", "clock$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789¹²³"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    require(bool(name) and not name.startswith(("/", "\\")) and "\\" not in name
            and not path.is_absolute() and ".." not in path.parts and ":" not in name,
            "unsafe archive member")
    require("/".join(path.parts) == name and bool(path.parts), "noncanonical archive member")
    require(not any(part.endswith((".", " ")) or part.casefold().split(".", 1)[0] in WINDOWS_DEVICES
                    or any(ord(c) < 32 or c in '<>"|?*' for c in part) for part in path.parts),
            "nonportable Windows archive member")
    require(not any(part.casefold() in FORBIDDEN_PARTS for part in path.parts), "private/cache directory")
    require(not any(part.casefold().startswith(".env") and part.casefold() != ".env.example" for part in path.parts),
            "private environment file")


def portable_names(names):
    """Reject case aliases in files/directories and file-versus-directory collisions."""
    files = {name.casefold() for name in names}
    spellings = {}
    for name in names:
        safe_name(name)
        parts = PurePosixPath(name).parts
        for count in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:count])
            key = prefix.casefold()
            require(key not in spellings or spellings[key] == prefix, "Windows archive name alias")
            require(count == len(parts) or key not in files, "archive file/directory alias")
            spellings[key] = prefix


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink() and not path.is_junction(), "linked archive member")
        if path.is_file():
            name = path.relative_to(directory).as_posix()
            safe_name(name)
            result[name] = {"sha256": digest(path), "bytes": path.stat().st_size}
    portable_names(result)
    return result


def check_evidence(directory):
    for name in EVIDENCE:
        path = directory / name
        require(path.is_file() and not path.is_symlink() and not path.is_junction(),
                "required ordinary evidence file missing")
    receiving = json.loads((directory / EVIDENCE[2]).read_text(encoding="utf-8"))
    performance = json.loads((directory / EVIDENCE[3]).read_text(encoding="utf-8"))
    tests = json.loads((directory / EVIDENCE[4]).read_text(encoding="utf-8"))
    require(receiving["result"] == "passed" and receiving["python"].startswith("3.13."),
            "receiving rehearsal not passed on Python 3.13")
    for key in ("fresh_python_environment", "source_copy_preserved", "working_data_preserved",
                "disposable_database_removed"):
        require(receiving.get(key) is True, "receiving preservation/isolation/cleanup not passed")
    require(receiving["steps"] and all(step["passed"] is True for step in receiving["steps"]),
            "receiving stage did not pass")
    require(performance["result"] == "passed" and performance["server_stopped"] is True,
            "HTTP acceptance or shutdown not passed")
    require(tests["result"] == "passed" and tests["working_data_preserved"] is True
            and tests["b1_source_preserved"] is True, "current verification not passed")
    require(tests["python"].startswith("3.13.") and tests["checks"]
            and all(check["passed"] is True for check in tests["checks"]),
            "current checks or Python version not passed")
    require(receiving.get("agreed_performance_signoff") is False
            and receiving.get("scientific_approval") is False,
            "this local package must not claim joint approval")
    return tests


def check_refreshed_evidence(directory):
    """Latest source checks plus explicitly historical, unchanged-image measurements."""
    for name in REFRESHED_EVIDENCE:
        path = directory / name
        require(path.is_file() and not path.is_symlink() and not path.is_junction(),
                "required ordinary refreshed evidence file missing")
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    tests = read(REFRESHED_EVIDENCE[0])
    quality = read("B2-local-quality-verification.json")
    require(quality.get("result") == "passed" and quality.get("source_unchanged_during_checks") is True
            and len(quality.get("checks", [])) == 2
            and all(c.get("passed") is True for c in quality["checks"]), "local quality gate failed")
    require(tests.get("result") == "passed" and tests.get("python", "").startswith("3.13."),
            "fresh source verification failed")
    for key in ("working_data_preserved", "b1_source_preserved", "source_unchanged_during_verification",
                "runtime_unchanged_from_performance", "benchmark_unchanged_from_performance"):
        require(tests.get(key) is True, "fresh preservation/source linkage failed")
    require(tests.get("temporary_test_schemas_remaining") == 0 and tests.get("checks")
            and all(c.get("passed") is True for c in tests["checks"]), "fresh checks incomplete")
    require(set(tests.get("evidence_hashes", {})) == set(REFRESHED_EVIDENCE[1:]),
            "refreshed evidence hash coverage incomplete")
    for name, checksum in tests["evidence_hashes"].items():
        require(digest(directory / name) == checksum, "evidence changed after verification")
    container = read(REFRESHED_EVIDENCE[1])
    previous = read("B2-step-5-performance-container-verification.json")
    summary = read("B2-step-5-performance-verification.json")
    measured = read("B2-step-5-performance-resource.json")
    security = read("B2-step-5-performance-runtime-gate.json")
    scan = read("B2-step-4-final-runtime.trivy.json")
    require(container.get("result") == "passed" and container.get("checks")
            and all(c.get("passed") is True for c in container["checks"]), "current Linux checks failed")
    for key in ("owned_resources_removed", "working_data_preserved", "b1_database_source_and_config_preserved",
                "runtime_isolation_verified", "readiness_outage_recovery_verified"):
        require(container.get(key) is True, "current Linux preservation/runtime checks failed")
    require(container.get("runtime_image") and container["runtime_image"] == previous.get("runtime_image")
            == summary.get("runtime_image") == security.get("image") == scan["Metadata"]["ImageID"],
            "tested, measured and scanned release images differ")
    require(summary.get("local_performance_resource_checkpoint_complete") is True
            and summary.get("raw_percentiles_independently_recomputed") is True
            and measured.get("result") == "passed_local_targets"
            and measured.get("gate", {}).get("local_provisional_acceptance") is True,
            "local performance checkpoint missing")
    require(security.get("gate_passed_for_supported_runtime") is True
            and security.get("zero_reported_critical") is True
            and security.get("python_findings") == 0 and security.get("raw_findings_suppressed") is False,
            "scoped security evidence failed")
    require(datetime.now(timezone.utc).date().isoformat() < security["re_review_before"],
            "security applicability review expired")
    for value in (container, previous):
        require(value.get("production_accepted") is False and value.get("scientific_approval") is False,
                "this local package must not claim joint approval")
    require(summary.get("team_a_final_performance_accepted") is False
            and measured["gate"].get("team_a_final_performance_accepted") is False,
            "this local package must not claim joint approval")
    return tests


def verify_archive(archive):
    with zipfile.ZipFile(archive) as reader:
        names = reader.namelist()
        require(len(names) == len(set(names)), "duplicate archive entries")
        portable_names(names)
        for item in reader.infolist():
            kind = stat.S_IFMT(item.external_attr >> 16)
            require(kind in (0, stat.S_IFREG), "nonregular archive member")
        require("manifest.json" in names, "archive manifest missing")
        manifest = json.loads(reader.read("manifest.json"))
        require(manifest.get("scope") == "local_engineering_handoff"
                and manifest.get("production_accepted") is False
                and manifest.get("scientific_approval") is False
                and manifest.get("agreed_performance_signoff") is False, "invalid acceptance scope")
        require(set(names) == set(manifest["files"]) | {"manifest.json"}, "archive inventory mismatch")
        for name, expected in manifest["files"].items():
            content = reader.read(name)
            require(len(content) == expected["bytes"]
                    and hashlib.sha256(content).hexdigest() == expected["sha256"],
                    "archive checksum mismatch")
        require(reader.testzip() is None, "archive CRC failure")
    return manifest


def package(destination, evidence, *, profile="historical"):
    destination = Path(destination).resolve()
    evidence = Path(evidence).resolve()
    archive = destination.with_suffix(".zip")
    require(not destination.exists() and not archive.exists(), "choose new package and archive paths")
    require(destination != ROOT and not destination.is_relative_to(ROOT),
            "handoff output must be outside the source project")
    require(destination != evidence and not evidence.is_relative_to(destination),
            "handoff must not contain its input evidence directory")
    require(profile in {"historical", "refreshed"}, "unknown evidence profile")
    names = REFRESHED_EVIDENCE if profile == "refreshed" else EVIDENCE
    tests = check_refreshed_evidence(evidence) if profile == "refreshed" else check_evidence(evidence)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Only an owned temporary staging directory is automatically cleaned up.
    with tempfile.TemporaryDirectory(prefix="b2-handoff-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "package"
        staged.mkdir()
        source_hashes = source_package(staged / "source")
        require(tests["source_hashes"] == source_hashes,
                "source changed after tests; rerun verification before packaging")
        if profile == "refreshed":
            for key in ("runtime_source_hashes", "benchmark_source_hashes", "quality_source_hashes"):
                require(tests.get(key), "verified source linkage missing")
                require(all(source_hashes.get(name, "").removeprefix("sha256:") == checksum.removeprefix("sha256:")
                            for name, checksum in tests[key].items()),
                        "measured runtime/benchmark source changed")
        (staged / "evidence").mkdir()
        for name in names:
            (staged / "evidence" / name).write_bytes((evidence / name).read_bytes())
        if profile == "refreshed":
            check_refreshed_evidence(staged / "evidence")
        (staged / "README.md").write_text(
            "# B2 local engineering handoff\n\n"
            "Start with source/docs/runbooks/b2-local-handoff.md.\n"
            "Setup: source/docs/runbooks/b2-receiver-setup.md.\n"
            "Open gates: source/docs/b2-pending-items.md.\n"
            "Test and rehearsal records are in evidence/.\n\n"
            "No private .env, live database/objects, virtual environment or Git history is included.\n"
            "The .env.example contains public local-development defaults only; replace them privately.\n"
            "No scientific, production or agreed performance approval is claimed.\n"
            + ("Refreshed Step 6 source checks passed; earlier local performance passed on the unchanged release image.\n"
               "The new container rehearsal is same-host, not a receiver acknowledgement or new-host acceptance.\n"
               "Raw security findings and expiry-bound applicability review are included, not suppressed.\n"
               if profile == "refreshed" else "Historical Step 19 evidence profile; not the refreshed release evidence.\n") +
            "Verify every archive member against manifest.json before receiving.\n",
            encoding="utf-8")
        manifest = {"created_at": datetime.now(timezone.utc).isoformat(),
                    "scope": "local_engineering_handoff", "python": "3.13",
                    "production_accepted": False, "scientific_approval": False,
                    "agreed_performance_signoff": False,
                    "evidence_profile": profile, "receiver_acknowledged": False,
                    "local_performance_checkpoint_passed": profile == "refreshed",
                    "files": inventory(staged)}
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                               encoding="utf-8")
        temporary_archive = Path(temporary) / "handoff.zip"
        with zipfile.ZipFile(temporary_archive, "w", zipfile.ZIP_DEFLATED) as writer:
            for path in sorted(staged.rglob("*")):
                if path.is_file():
                    writer.write(path, path.relative_to(staged).as_posix())
        verify_archive(temporary_archive)
        require(not destination.exists() and not archive.exists(), "package destination appeared during build")
        # Copy rather than rename: Python's temporary directory has restrictive
        # Windows ACLs that must not travel with the delivered folder/archive.
        shutil.copytree(staged, destination)
        shutil.copyfile(temporary_archive, archive)
        require(inventory(destination) == inventory(staged), "delivered folder changed during copy")
        verify_archive(archive)
    print(f"Local handoff verified: {len(manifest['files'])} files; no joint approval claimed.")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--profile", choices=("historical", "refreshed"), default="historical",
                        help="Use refreshed for current Step 6 evidence; historical retains Step 19 compatibility")
    args = parser.parse_args()
    if args.check:
        require(not args.output and not args.evidence_dir, "check cannot be combined with build")
        manifest = verify_archive(args.check)
        print(f"Archive verified: {len(manifest['files'])} checksummed files.")
    else:
        require(args.output is not None and args.evidence_dir is not None, "output and evidence-dir required")
        package(args.output, args.evidence_dir, profile=args.profile)


if __name__ == "__main__":
    main()
