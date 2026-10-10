"""Local handoff checks: no production approval or live-data transfer."""
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts import package_b2_handoff as handoff


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/private", ".env",
                                    "source/.env.local", "source/.venv/file",
                                    "source/.git/config", "source/__pycache__/file"])
def test_unsafe_archive_members_rejected(name):
    with pytest.raises(ValueError):
        handoff.safe_name(name)


def test_public_env_template_and_source_paths_allowed():
    handoff.safe_name("source/.env.example")
    handoff.safe_name("source/services/api/app/main.py")


@pytest.mark.parametrize('name', [
    'source/.ENV', 'source/.Env.local', 'source/.Git/config', 'source/.AWS/key',
    'source/.VENV/file', 'source/CON', 'source/nul.txt', 'source/COM1.log',
    'source/LPT9', 'source/COM¹.log', 'source/readme.', 'source/readme ', 'source/a./file',
    'source//file', 'source/./file', 'source/bad?name', 'source/new\nline',
])
def test_nonportable_or_private_windows_names_rejected(name):
    with pytest.raises(ValueError):
        handoff.safe_name(name)


def test_windows_case_colliding_archive_members_refused(tmp_path):
    manifest = {'scope': 'local_engineering_handoff', 'production_accepted': False,
                'scientific_approval': False, 'agreed_performance_signoff': False,
                'files': {name: {'sha256': hashlib.sha256(b'data').hexdigest(), 'bytes': 4}
                          for name in ['source/README.md', 'source/readme.md']}}
    archive = tmp_path / 'aliases.zip'
    with zipfile.ZipFile(archive, 'w') as writer:
        writer.writestr('manifest.json', json.dumps(manifest))
        for name in manifest['files']:
            writer.writestr(name, b'data')
    with pytest.raises(ValueError, match='alias'):
        handoff.verify_archive(archive)


def test_archive_case_colliding_directories_refused():
    with pytest.raises(ValueError, match='alias'):
        handoff.portable_names(['source/Folder/a.py', 'source/folder/b.py'])


def test_archive_file_directory_collision_refused():
    with pytest.raises(ValueError, match='alias'):
        handoff.portable_names(['source/file', 'source/file/child.py'])


def test_archive_symlink_member_refused(tmp_path):
    data = b'../outside'
    name = 'source/link'
    manifest = {'scope': 'local_engineering_handoff', 'production_accepted': False,
                'scientific_approval': False, 'agreed_performance_signoff': False,
                'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}}}
    archive = tmp_path / 'link.zip'
    with zipfile.ZipFile(archive, 'w') as writer:
        writer.writestr('manifest.json', json.dumps(manifest))
        link = zipfile.ZipInfo(name)
        link.create_system = 3
        link.external_attr = 0o120777 << 16
        writer.writestr(link, data)
    with pytest.raises(ValueError, match='nonregular'):
        handoff.verify_archive(archive)


@pytest.fixture
def evidence(tmp_path):
    directory = tmp_path / "evidence"
    directory.mkdir()
    receiving = {"result": "passed", "python": "3.13.15", "steps": [{"passed": True}],
                 "agreed_performance_signoff": False, "scientific_approval": False}
    for key in ("fresh_python_environment", "source_copy_preserved", "working_data_preserved",
                "disposable_database_removed"):
        receiving[key] = True
    performance = {"result": "passed", "server_stopped": True}
    tests = {"result": "passed", "python": "3.13.15", "working_data_preserved": True,
             "b1_source_preserved": True, "checks": [{"passed": True}],
             "source_hashes": {"README.md": hashlib.sha256(b"test source").hexdigest()}}
    for name in handoff.EVIDENCE:
        value = receiving if name == handoff.EVIDENCE[2] else performance if name == handoff.EVIDENCE[3] else tests
        (directory / name).write_text(json.dumps(value), encoding="utf-8")
    return directory


def test_missing_evidence_refused(evidence):
    (evidence / handoff.EVIDENCE[0]).unlink()
    with pytest.raises(ValueError, match="missing"):
        handoff.check_evidence(evidence)


@pytest.mark.parametrize("key", ["result", "working_data_preserved", "disposable_database_removed"])
def test_failed_receiving_evidence_refused(evidence, key):
    path = evidence / handoff.EVIDENCE[2]
    value = json.loads(path.read_text())
    value[key] = "failed" if key == "result" else False
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        handoff.check_evidence(evidence)


def test_joint_approval_claim_refused(evidence):
    path = evidence / handoff.EVIDENCE[2]
    value = json.loads(path.read_text())
    value["scientific_approval"] = True
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="joint approval"):
        handoff.check_evidence(evidence)


def fake_source(destination):
    destination.mkdir()
    (destination / "README.md").write_bytes(b"test source")
    return {"README.md": hashlib.sha256(b"test source").hexdigest()}


def test_package_roundtrip_excludes_unlisted_evidence(tmp_path, evidence, monkeypatch):
    monkeypatch.setattr(handoff, "ROOT", tmp_path / "original")
    monkeypatch.setattr(handoff, "source_package", fake_source)
    (evidence / ".env").write_text("private-not-for-package")
    target = tmp_path / "deliverable"
    manifest = handoff.package(target, evidence)
    assert handoff.verify_archive(target.with_suffix(".zip")) == manifest
    assert (target / "source/README.md").read_bytes() == b"test source"
    assert not (target / "evidence/.env").exists()
    assert not manifest["scientific_approval"]


def test_existing_output_refused_without_copying(tmp_path, evidence, monkeypatch):
    destination = tmp_path / "existing"
    destination.mkdir()
    monkeypatch.setattr(handoff, "source_package", lambda _: pytest.fail("copied"))
    with pytest.raises(ValueError, match="new package"):
        handoff.package(destination, evidence)


def test_output_inside_project_refused(tmp_path, evidence, monkeypatch):
    monkeypatch.setattr(handoff, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="outside"):
        handoff.package(tmp_path / "deliverable", evidence)


def test_stale_source_refused_and_staging_cleaned(tmp_path, evidence, monkeypatch):
    monkeypatch.setattr(handoff, "ROOT", tmp_path / "original")
    monkeypatch.setattr(handoff, "source_package", fake_source)
    path = evidence / handoff.EVIDENCE[4]
    value = json.loads(path.read_text())
    value["source_hashes"] = {}
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="source changed"):
        handoff.package(tmp_path / "deliverable", evidence)
    assert not (tmp_path / "deliverable").exists()
    assert not list(tmp_path.glob("b2-handoff-*"))


def archive_with(tmp_path, *, corrupt=False, extra=False):
    data = b"original"
    manifest = {"scope": "local_engineering_handoff", "production_accepted": False,
                "scientific_approval": False, "agreed_performance_signoff": False,
                "files": {"source/README.md": {"sha256": hashlib.sha256(data).hexdigest(),
                                                "bytes": len(data)}}}
    archive = tmp_path / "test.zip"
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("manifest.json", json.dumps(manifest))
        writer.writestr("source/README.md", b"modified" if corrupt else data)
        if extra:
            writer.writestr("unlisted.txt", b"extra")
    return archive


@pytest.mark.parametrize("case", ["corrupt", "extra"])
def test_altered_archive_refused(tmp_path, case):
    with pytest.raises(ValueError, match="checksum|inventory"):
        handoff.verify_archive(archive_with(tmp_path, **{case: True}))


def test_handoff_documents_present_with_honest_scope():
    root = Path(__file__).resolve().parents[3]
    guide = (root / "docs/runbooks/b2-local-handoff.md").read_text()
    setup = (root / "docs/runbooks/b2-receiver-setup.md").read_text()
    pending = (root / "docs/b2-pending-items.md").read_text()
    assert "Step 20" in guide and "predates Step 19" in guide
    assert "py -3.13" in setup and "127.0.0.1" in setup
    assert "Step 17" in pending and "Step 18 formal performance" in pending
    assert "KML" in pending and "Receiving-team acknowledgement" in pending
    assert "--profile refreshed" in guide and "not a new benchmark" in guide
    assert "Windows file:///D:/" in setup and "Production /docs" in setup
    assert "no receiving acknowledgement" in (root / "docs/runbooks/b2-receiver-acceptance.md").read_text()


@pytest.fixture
def refreshed_evidence(tmp_path):
    directory = tmp_path / "refreshed"
    directory.mkdir()
    image = "sha256:fixture-image"
    container = {"result": "passed", "checks": [{"passed": True}], "runtime_image": image,
                 "production_accepted": False, "scientific_approval": False}
    for key in ("owned_resources_removed", "working_data_preserved", "b1_database_source_and_config_preserved",
                "runtime_isolation_verified", "readiness_outage_recovery_verified"):
        container[key] = True
    summary = {"local_performance_resource_checkpoint_complete": True,
               "raw_percentiles_independently_recomputed": True, "runtime_image": image,
               "team_a_final_performance_accepted": False}
    measured = {"result": "passed_local_targets", "gate": {"local_provisional_acceptance": True,
                "team_a_final_performance_accepted": False}}
    security = {"gate_passed_for_supported_runtime": True, "zero_reported_critical": True,
                "python_findings": 0, "raw_findings_suppressed": False,
                "image": image, "re_review_before": "9999-12-31"}
    payloads = {"B2-step-6-container-verification.json": container,
                "B2-step-5-performance-container-verification.json": container,
                "B2-step-5-performance-verification.json": summary,
                "B2-step-5-performance-resource.json": measured,
                "B2-step-5-performance-runtime-gate.json": security,
                "B2-local-quality-verification.json": {"result": "passed", "source_unchanged_during_checks": True,
                                                       "checks": [{"passed": True}, {"passed": True}]},
                "B2-step-4-final-runtime.trivy.json": {"Metadata": {"ImageID": image}}}
    for name in handoff.REFRESHED_EVIDENCE[1:]:
        (directory / name).write_text(json.dumps(payloads.get(name, {})))
    hashes = {"README.md": hashlib.sha256(b"test source").hexdigest()}
    tests = {"result": "passed", "python": "3.13.15", "temporary_test_schemas_remaining": 0,
             "checks": [{"passed": True}], "source_hashes": hashes,
             "runtime_source_hashes": hashes, "benchmark_source_hashes": hashes, "quality_source_hashes": hashes}
    for key in ("working_data_preserved", "b1_source_preserved", "source_unchanged_during_verification",
                "runtime_unchanged_from_performance", "benchmark_unchanged_from_performance"):
        tests[key] = True
    (directory / handoff.REFRESHED_EVIDENCE[0]).write_text(json.dumps(tests))
    refresh_evidence_hashes(directory)
    return directory


def refresh_evidence_hashes(directory):
    path = directory / handoff.REFRESHED_EVIDENCE[0]
    tests = json.loads(path.read_text())
    tests["evidence_hashes"] = {n: handoff.digest(directory / n) for n in handoff.REFRESHED_EVIDENCE[1:]}
    path.write_text(json.dumps(tests))


def test_refreshed_package_roundtrip(tmp_path, refreshed_evidence, monkeypatch):
    monkeypatch.setattr(handoff, "ROOT", tmp_path / "original")
    monkeypatch.setattr(handoff, "source_package", fake_source)
    manifest = handoff.package(tmp_path / "current", refreshed_evidence, profile="refreshed")
    assert handoff.verify_archive(tmp_path / "current.zip") == manifest
    assert manifest["local_performance_checkpoint_passed"]
    assert manifest["evidence_profile"] == "refreshed"
    assert not manifest["receiver_acknowledged"] and not manifest["agreed_performance_signoff"]


def test_refreshed_missing_file_refused(refreshed_evidence):
    (refreshed_evidence / handoff.REFRESHED_EVIDENCE[-1]).unlink()
    with pytest.raises(ValueError, match="missing"):
        handoff.check_refreshed_evidence(refreshed_evidence)


def test_changed_measurement_evidence_refused(refreshed_evidence):
    (refreshed_evidence / "B2-step-5-performance-resource.json").write_text("{}")
    with pytest.raises(ValueError, match="changed after"):
        handoff.check_refreshed_evidence(refreshed_evidence)


@pytest.mark.parametrize("file,key,value", [
    ("B2-step-6-test-evidence.json", "runtime_unchanged_from_performance", False),
    ("B2-step-6-test-evidence.json", "benchmark_unchanged_from_performance", False),
    ("B2-step-6-test-evidence.json", "temporary_test_schemas_remaining", 1),
    ("B2-step-6-test-evidence.json", "checks", []),
    ("B2-step-6-container-verification.json", "working_data_preserved", False),
    ("B2-step-6-container-verification.json", "runtime_image", "changed"),
    ("B2-step-6-container-verification.json", "production_accepted", True),
    ("B2-step-5-performance-verification.json", "team_a_final_performance_accepted", True),
    ("B2-step-5-performance-runtime-gate.json", "raw_findings_suppressed", True),
    ("B2-step-5-performance-runtime-gate.json", "re_review_before", "2000-01-01"),
])
def test_refreshed_failed_or_overstated_evidence_refused(refreshed_evidence, file, key, value):
    path = refreshed_evidence / file
    report = json.loads(path.read_text())
    report[key] = value
    path.write_text(json.dumps(report))
    refresh_evidence_hashes(refreshed_evidence)
    with pytest.raises(ValueError):
        handoff.check_refreshed_evidence(refreshed_evidence)


def test_refreshed_stale_linked_source_refused(tmp_path, refreshed_evidence, monkeypatch):
    monkeypatch.setattr(handoff, "ROOT", tmp_path / "original")
    monkeypatch.setattr(handoff, "source_package", fake_source)
    path = refreshed_evidence / handoff.REFRESHED_EVIDENCE[0]
    report = json.loads(path.read_text())
    report["benchmark_source_hashes"] = {"README.md": "changed"}
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="benchmark source changed"):
        handoff.package(tmp_path / "stale", refreshed_evidence, profile="refreshed")
    assert not (tmp_path / "stale.zip").exists()
