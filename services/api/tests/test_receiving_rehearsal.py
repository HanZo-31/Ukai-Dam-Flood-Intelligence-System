"""Step 18 safety checks; full receiving execution is recorded separately."""
import hashlib

import httpx
import pytest
from fastapi import FastAPI

from scripts import b2_receiving_probe as probe
from scripts import rehearse_b2_receiving as receiving
from scripts.rehearse_b1_handoff import source_package
from services.api.app.storage import LocalObjectStore


def test_receiving_refuses_existing_destination_before_database_access(tmp_path, monkeypatch):
    monkeypatch.setattr(receiving, "source_url", lambda: pytest.fail("database accessed"))
    with pytest.raises(ValueError, match="new directory"):
        receiving.rehearsal(tmp_path)


def test_receiving_refuses_outside_destination_before_database_access(tmp_path, monkeypatch):
    monkeypatch.setattr(receiving, "source_url", lambda: pytest.fail("database accessed"))
    with pytest.raises(ValueError, match="beneath data/handoff"):
        receiving.rehearsal(tmp_path / "outside")


@pytest.mark.parametrize("name", ["ukai", "postgres", "b2_receive_x", 'b2_receive_";DROP DATABASE ukai;--'])
def test_only_exact_generated_database_names_can_be_used_or_removed(name):
    with pytest.raises(ValueError, match="unsafe disposable"):
        receiving.validate_database_name(name, "ukai")


def test_even_a_generated_name_cannot_equal_the_working_database():
    name = "b2_receive_" + "a" * 32
    with pytest.raises(ValueError, match="unsafe disposable"):
        receiving.validate_database_name(name, name)
    assert receiving.validate_database_name(name, "ukai") == name


@pytest.mark.parametrize("settings", [{"samples": 4}, {"samples": 201}, {"concurrency": 0},
                                      {"concurrency": 17}, {"io_mib": 0}, {"io_mib": 129}])
def test_unsafe_workloads_are_refused_before_database_access(tmp_path, monkeypatch, settings):
    monkeypatch.setattr(receiving, "ROOT", tmp_path)
    monkeypatch.setattr(receiving, "source_url", lambda: pytest.fail("database accessed"))
    with pytest.raises(ValueError, match="safe local bounds"):
        receiving.rehearsal(tmp_path / "data/handoff/new", **settings)


def test_probe_guards_database_host_and_owned_object_root(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "ROOT", tmp_path / "source")
    name = "b2_receive_" + "a" * 32
    probe.receiving_guard(name, tmp_path / "objects")
    with pytest.raises(ValueError, match="owned receiving database"):
        probe.receiving_guard("ukai", tmp_path / "objects")
    with pytest.raises(ValueError, match="isolated receiving objects"):
        probe.receiving_guard(name, tmp_path / "live-objects")
    with pytest.raises(ValueError, match="local database host"):
        probe.receiving_guard(name, tmp_path / "objects", "remote.example.org")


def test_source_allowlist_carries_b2_runtime_examples_and_development_requirements(tmp_path):
    inventory = source_package(tmp_path / "source")
    assert {"services/api/requirements-dev.txt", "services/api/app/api_examples/v1.json",
            "docs/contracts/b2-openapi-v1.json", "scripts/b2_receiving_probe.py",
            "scripts/rehearse_b2_receiving.py"} <= set(inventory)
    assert not any(key == ".env" or key.startswith((".venv/", "data/", ".git/")) or "__pycache__" in key for key in inventory)


def test_latency_statistics_are_nearest_rank_and_reject_invalid_values():
    result = probe.latency_summary(list(range(1, 21)))
    assert result == {"samples": 20, "p50_ms": 10, "p95_ms": 19, "p99_ms": 20, "max_ms": 20}
    for values in ([], [-1], [float("nan")], [float("inf")]):
        with pytest.raises(ValueError, match="invalid timing"):
            probe.latency_summary(values)


def test_loopback_server_owns_ephemeral_socket_and_stops():
    app = FastAPI()
    @app.get("/health")
    def health():
        return {"status": "ok"}
    with probe.local_http_server(app) as base:
        assert base.startswith("http://127.0.0.1:")
        assert httpx.get(base + "/health", trust_env=False).json() == {"status": "ok"}
    # Windows may time out rather than immediately reject a closed TCP port.
    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        httpx.get(base + "/health", timeout=1, trust_env=False)


def test_io_baseline_is_explicitly_not_a_gis_or_capacity_claim(tmp_path):
    store = LocalObjectStore(tmp_path / "objects")
    data = b"S" * 4096
    uri, checksum = store.put("performance/opaque.bin", data)
    before = store.resolve_uri(uri).read_bytes()
    result = probe.io_baseline(store, uri, checksum, size=len(data), samples=2)
    assert result["size_bytes"] == len(data) and result["verification"]["samples"] == 2
    assert "NOT a COG" in result["scope"] and result["rss_and_peak_disk_not_measured"]
    assert store.resolve_uri(uri).read_bytes() == before
    assert checksum == "sha256:" + hashlib.sha256(before).hexdigest()
