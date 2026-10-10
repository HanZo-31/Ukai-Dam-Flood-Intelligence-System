"""Actual loopback HTTP acceptance and bounded baseline in an owned receiving DB."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def receiving_guard(database, storage_root, host="127.0.0.1"):
    require(host in {"127.0.0.1", "localhost"}, "probe requires the local database host")
    require(bool(re.fullmatch(r"b2_receive_[0-9a-f]{32}", database or "")), "probe requires an owned receiving database")
    require(Path(storage_root).resolve() == (ROOT.parent / "objects").resolve(), "probe requires isolated receiving objects")


def latency_summary(values):
    require(bool(values) and all(math.isfinite(v) and v >= 0 for v in values), "invalid timing samples")
    ordered = sorted(values)
    percentile = lambda p: round(ordered[max(0, math.ceil(p * len(ordered)) - 1)], 3)
    return {"samples": len(values), "p50_ms": percentile(.50), "p95_ms": percentile(.95),
            "p99_ms": percentile(.99), "max_ms": round(ordered[-1], 3)}


@contextmanager
def local_http_server(app):
    import uvicorn
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    base = "http://127.0.0.1:" + str(sock.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False,
        workers=1, timeout_graceful_shutdown=5, lifespan="off", loop="asyncio", http="h11"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while not server.started:
            require(thread.is_alive() and time.monotonic() < deadline, "loopback server startup failed")
            time.sleep(.02)
        yield base
    finally:
        server.should_exit = True
        thread.join(10)
        if thread.is_alive():
            server.force_exit = True
            thread.join(5)
        sock.close()
        require(not thread.is_alive(), "loopback server did not stop")


def prepare_fixture(store, engine):
    from sqlalchemy.orm import Session
    from scripts.gis_fixture import build_fixture
    from scripts.rehearse_b1_handoff import approved_fixture, catalog_fixture, REVIEWER
    draft, root, _ = build_fixture(store, prefix="receiving/synthetic-gis/")
    data = store.resolve_uri(root + draft.assets["extent_geojson"]).read_bytes()
    _, checksum = store.put("receiving/synthetic-gis/results/export.geojson", data)
    draft.assets["export_geojson"] = "results/export.geojson"
    draft.asset_metadata["export_geojson"] = draft.asset_metadata["extent_geojson"].model_copy(
        deep=True, update={"checksum": checksum})
    with Session(engine) as session, session.begin():
        catalog_fixture(session, draft, store, root)
    identities = ["b2-receive-replay", "b2-receive-hypothetical-1", "b2-receive-hypothetical-2", "b2-receive-hypothetical-3"]
    items = [approved_fixture(draft, identity, historical=index == 0) for index, identity in enumerate(identities)]
    hidden = draft.model_copy(deep=True)
    hidden.scenario_id, hidden.run_id = "b2-receive-draft", "b2-receive-draft-run"
    for item in [hidden, *items]:
        manifest_uri, _ = store.put("receiving/manifests/" + item.scenario_id + ".json", item.model_dump_json(indent=2).encode())
        result = subprocess.run([sys.executable, "scripts/register_published_bundle.py", str(store.resolve_uri(manifest_uri)),
            "--bundle-root", root, "--registered-by", "synthetic-b2-receiving-operator", "--trusted-approver", REVIEWER],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
        require(result.returncode == 0, "real GIS-aware receiving import failed")
    return items, hidden


def check_http(client, items, hidden, *, documentation_enabled=True):
    from services.api.app.api_schemas.export import ScenarioExportResponse
    from services.api.app.api_schemas.scenario import ScenarioDetail
    require(client.get("/api/v1/health").json()["status"] == "ok", "health failed")
    page = client.get("/api/v1/scenarios?data_mode=demo&limit=2").json()
    second = client.get("/api/v1/scenarios?data_mode=demo&limit=2&offset=" + str(page["pagination"]["next_offset"])).json()
    actual = [r["scenario_id"] for r in page["items"] + second["items"]]
    require(actual == sorted(i.scenario_id for i in items) and second["pagination"]["next_offset"] is None, "paging failed")
    require(client.get("/api/v1/scenarios?data_mode=production").json()["items"] == [], "mode isolation failed")
    downloads = []
    for item in items:
        base = "/api/v1/scenarios/" + item.scenario_id
        response = client.get(base)
        require(response.status_code == 200, "scenario detail failed")
        body = response.json()
        ScenarioDetail.model_validate(body)
        require(body["summary"] == item.summary.model_dump() and body["parameters"] == item.parameters.model_dump(), "registered values drifted")
        require(body["data_mode"] == body["data_kind"] == "demo", "demo identity lost")
        require(not any(key in response.text for key in ("file:", "storage_uri", "manifest_json", "source_reference")), "private metadata leaked")
        impact = client.get(base + "/impact").json()
        require(all(impact[k] == v for k, v in item.summary.model_dump().items()), "impact drifted")
        layers = client.get(base + "/layers").json()["layers"]
        require(len(layers) == 4 and all(not l["asset_type"].startswith("export_") for l in layers), "layer roles failed")
        for layer in layers:
            result = client.get(layer["url"])
            require(result.status_code == 200 and "sha256:" + hashlib.sha256(result.content).hexdigest() == layer["checksum"], "artifact integrity failed")
            require(result.headers["cache-control"] == "no-store" and result.headers["x-content-type-options"] == "nosniff", "download safety headers failed")
        export_response = client.get("/api/v1/exports/" + item.scenario_id + "?format=geojson&data_mode=demo")
        require(export_response.status_code == 200, "export discovery failed")
        export = export_response.json()
        ScenarioExportResponse.model_validate(export)
        require("sha256:" + hashlib.sha256(client.get(export["download_url"]).content).hexdigest() == export["checksum"], "export integrity failed")
        downloads.append(export["download_url"])
        require(client.get("/api/v1/exports/" + item.scenario_id + "?format=kml").status_code == 404, "absent KML invented")
        assumptions = client.get(body["assumptions"]["url"])
        require("sha256:" + hashlib.sha256(assumptions.content).hexdigest() == body["assumptions"]["checksum"], "assumptions failed")
    base = "/api/v1/scenarios/" + items[0].scenario_id
    url = base + "/assets/max_depth_cog"
    full = client.get(url)
    partial = client.get(url, headers={"Range": "bytes=0-15", "If-Range": full.headers["etag"]})
    require(partial.status_code == 206 and partial.content == full.content[:16], "COG range failed")
    head = client.head(url)
    require(head.status_code == 200 and not head.content and int(head.headers["content-length"]) == len(full.content), "HEAD failed")
    for path in ("", "/layers", "/impact", "/assumptions", "/assets/max_depth_cog"):
        require(client.get("/api/v1/scenarios/" + hidden.scenario_id + path).status_code == 404, "draft leaked")
    require(client.get("/api/v1/exports/" + hidden.scenario_id + "?format=geojson").status_code == 404, "draft export leaked")
    event = client.get("/api/v1/historical-events").json()["items"][0]
    require(event["replay"]["available"] and event["replay"]["example"]["scenario_id"] == items[0].scenario_id, "replay unavailable")
    require([row["scenario_id"] for row in client.get(event["replay"]["scenarios_url"]).json()["items"]] == [items[0].scenario_id], "replay link failed")
    status = client.get("/api/v1/status/current").json()
    require(status["data_mode"] == "demo" and status["is_live"] is False and status["timestamp"] == "2026-10-02T00:00:00Z", "demo status changed")
    for endpoint in ("/docs", "/redoc", "/openapi.json"):
        require(client.get(endpoint).status_code == (200 if documentation_enabled else 404),
                "documentation exposure policy mismatch")
    if documentation_enabled:
        require(client.get("/openapi.json").json() == json.loads((ROOT / "docs/contracts/b2-openapi-v1.json").read_text()), "served OpenAPI drifted")
    for path, headers, expected in [("/api/v1/scenarios?limit=0", {}, 422), (url, {"Range": "bytes=9-2"}, 416)]:
        response = client.get(path, headers=headers)
        require(response.status_code == expected and response.headers["content-type"] == "application/problem+json", "safe error failed")
    return downloads


def http_baseline(client, identity, *, samples, concurrency):
    base = "/api/v1/scenarios/" + identity
    workloads = [
        ("health", "GET", "/api/v1/health", {}, 200),
        ("catalog", "GET", "/api/v1/scenarios?data_mode=demo&limit=20", {}, 200),
        ("detail", "GET", base, {}, 200), ("layers", "GET", base + "/layers", {}, 200),
        ("impact", "GET", base + "/impact", {}, 200),
        ("events", "GET", "/api/v1/historical-events", {}, 200),
        ("demo_status", "GET", "/api/v1/status/current", {}, 200),
        ("export_discovery", "GET", "/api/v1/exports/" + identity + "?format=geojson", {}, 200),
        ("cog_full", "GET", base + "/assets/max_depth_cog", {}, 200),
        ("cog_range", "GET", base + "/assets/max_depth_cog", {"Range": "bytes=0-15"}, 206),
        ("cog_head", "HEAD", base + "/assets/max_depth_cog", {}, 200),
        ("export_download", "GET", base + "/assets/export_geojson", {}, 200),
    ]
    results = {}
    for label, method, path, headers, expected in workloads:
        def one(_):
            start = time.perf_counter()
            response = client.request(method, path, headers=headers)
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed, response.status_code == expected
        for index in range(3):
            require(one(index)[1], "performance warmup failed")
        sequential = [one(index) for index in range(samples)]
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as workers:
            parallel = list(workers.map(one, range(samples)))
        batch_seconds = time.perf_counter() - start
        failures = sum(not ok for _, ok in sequential + parallel)
        results[label] = {"sequential": latency_summary([ms for ms, _ in sequential]),
            "concurrent": latency_summary([ms for ms, _ in parallel]), "concurrency": concurrency,
            "concurrent_batch_requests_per_second": round(samples / batch_seconds, 2), "unexpected_statuses": failures}
        require(failures == 0, "performance baseline observed functional failures")
    return results


def io_baseline(store, uri, checksum, *, size, samples=5):
    from services.api.app.services.asset_service import verified_download
    values = []
    for index in range(samples + 1):
        start = time.perf_counter()
        download = verified_download(store, uri, checksum, media_type="application/octet-stream", filename="synthetic-io.bin")
        verified_seconds = time.perf_counter() - start
        digest = hashlib.sha256()
        count = 0
        for chunk in download.chunks(0, download.size):
            digest.update(chunk)
            count += len(chunk)
        require(count == size and "sha256:" + digest.hexdigest() == checksum and download.handle.closed, "IO snapshot verification failed")
        if index:
            values.append(verified_seconds * 1000)
    return {"scope": "opaque synthetic bytes; adapter IO only, NOT a COG or approved GIS result",
        "size_bytes": size, "warmups": 1, "verification": latency_summary(values),
        "median_logical_source_mib_per_second": round(size / 2**20 / (statistics.median(values) / 1000), 2),
        "rss_and_peak_disk_not_measured": True}


def probe(output, *, samples, concurrency, io_mib):
    from sqlalchemy.engine import make_url
    connection_url = make_url(os.environ["DATABASE_URL"])
    receiving_guard(connection_url.database, os.environ["OBJECT_STORAGE_ROOT"], connection_url.host)
    output = Path(output).resolve()
    require(output.parent == ROOT.parent.resolve() and not output.exists(), "probe output must be new and inside receiving directory")
    require(5 <= samples <= 200 and 1 <= concurrency <= 16 and 1 <= io_mib <= 128, "unsafe probe bounds")
    import httpx
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from scripts.backup_db import snapshot
    from services.api.app.db.session import engine
    from services.api.app.db.models import ResultAsset
    from services.api.app.main import app
    from services.api.app.repositories.published_repository import PublishedScenarioRepository
    from services.api.app.storage import default_store
    store = default_store()
    items, hidden = prepare_fixture(store, engine)
    size = io_mib * 2**20
    opaque_uri, opaque_checksum = store.put("performance/opaque-io.bin", b"S" * size)
    stable = snapshot(engine)
    report = {"scope": "synthetic engineering checks and same-host loopback baseline",
        "scientific_approval": False, "performance_signoff": "pending_agreed_targets_and_representative_assets",
        "samples_per_workload_per_mode": samples, "http_warmups_per_workload": 3,
        "percentiles": "nearest-rank; small samples, warm cache, no soak or production capacity claim",
        "result": "failed"}
    try:
        with local_http_server(app) as base, httpx.Client(base_url=base, timeout=15,
            trust_env=False, limits=httpx.Limits(max_connections=max(concurrency, 4), max_keepalive_connections=max(concurrency, 4))) as client:
            downloads = check_http(client, items, hidden)
            report["http"] = http_baseline(client, items[0].scenario_id, samples=samples, concurrency=concurrency)
            report["adapter_io"] = io_baseline(store, opaque_uri, opaque_checksum, size=size)
            require(snapshot(engine) == stable, "HTTP reads/performance changed receiving database")
            report["read_only_database_preserved"] = True
            report["fixture"] = {"approved_scenarios": 4, "historical_replays": 1, "hypotheticals": 3,
                "hidden_drafts": 1, "cog_bytes": len(client.get("/api/v1/scenarios/" + items[0].scenario_id + "/assets/max_depth_cog").content)}
            # Mutations below are explicit acceptance cases only in the guarded DB.
            with Session(engine) as session, session.begin():
                PublishedScenarioRepository(session).revoke(items[-1].scenario_id,
                    actor="synthetic-b2-receiving-operator", reason="Engineering withdrawal test only")
            require(client.get(downloads[-1]).status_code == 404, "issued export link survived revocation")
            with Session(engine) as session:
                asset = session.scalar(select(ResultAsset).where(ResultAsset.scenario_id == items[0].scenario_id,
                    ResultAsset.asset_type == "export_geojson"))
                path = store.resolve_uri(asset.storage_uri)
            original = path.read_bytes()
            try:
                path.write_bytes(b"Synthetic tamper case; not private data")
                response = client.get(downloads[0])
                require(response.status_code == 503 and "file:" not in response.text, "tamper was not rejected safely")
            finally:
                path.write_bytes(original)
            report["acceptance"] = {"all_eight_endpoints": True, "actual_tcp_not_testclient": True,
                "gis_aware_cli_imports": True, "parameters_impacts_provenance": True,
                "artifact_checksums_ranges_head": True, "pagination_mode_and_draft_hiding": True,
                "historical_replay_and_persisted_demo_status": True, "served_documentation_parity": True,
                "revocation_and_tamper_rejection": True}
        report["server_stopped"] = True
        report["result"] = "passed"
    finally:
        engine.dispose()
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--io-mib", type=int, default=16)
    args = parser.parse_args()
    try:
        probe(args.output, samples=args.samples, concurrency=args.concurrency, io_mib=args.io_mib)
    except Exception:
        print("Receiving HTTP/performance probe failed; no scientific or performance sign-off.", file=sys.stderr)
        return 1
    print("Actual receiving HTTP acceptance passed; baseline recorded; loopback server stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
