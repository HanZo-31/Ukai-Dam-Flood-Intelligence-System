"""Linux-only synthetic fixture/check helper for an owned disposable container DB."""
import json
import os
from pathlib import Path
import re
import sys
import asyncio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from scripts.backup_db import snapshot
from scripts.b2_receiving_probe import prepare_fixture, check_http
from services.api.app.published_contract import PublishedScenarioManifest
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.storage import default_store


def main(action):
    url = make_url(os.environ["DATABASE_URL"])
    if url.host != "catalogue" or not re.fullmatch(r"b2_container_[0-9a-f]{16}", url.database or ""):
        raise ValueError("container fixture requires an owned isolated DB")
    store = default_store()
    if str(store.root) != "/objects":
        raise ValueError("container fixture requires owned Linux storage")
    engine = create_engine(url)
    try:
        if action == "prepare":
            # Parameterized, test-only role password; never included in logs/argv.
            with engine.begin() as connection:
                connection.execute(text("SELECT set_config('b2.reader_password', :password, false)"),
                                   {"password": os.environ["B2_READER_PASSWORD"]})
                connection.execute(text("""DO $$ BEGIN
                    EXECUTE format('CREATE ROLE b2_reader LOGIN PASSWORD %L', current_setting('b2.reader_password'));
                    END $$"""))
                connection.execute(text("GRANT CONNECT ON DATABASE " + url.database + " TO b2_reader"))
                connection.execute(text("GRANT USAGE ON SCHEMA public TO b2_reader"))
                connection.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO b2_reader"))
                connection.execute(text("ALTER ROLE b2_reader SET default_transaction_read_only = on"))
            (store.root / ".b2-storage-ready.json").write_text(json.dumps({
                "schema_version": 1, "store_id": "b2-container-fixture"}))
            from services.api.app.readiness import Readiness
            from services.api.app.settings import production_settings
            reader_url = url.set(username="b2_reader", password=os.environ["B2_READER_PASSWORD"])
            settings = production_settings(dict(os.environ, B2_ENV="production", TMPDIR="/tmp",
                DATABASE_URL=reader_url.render_as_string(hide_password=False), B2_STORAGE_ID="b2-container-fixture"))
            with engine.connect() as connection:
                assert connection.execute(text("SELECT count(*) FROM public.scenarios WHERE publication_status='approved'")).scalar_one() == 0
            assert asyncio.run(Readiness(settings).check()) is True
            print("Empty-public-catalogue dependency readiness passed without inventing approved data.")
            items, hidden = prepare_fixture(store, engine)
            (store.root / "container-fixture.json").write_text(json.dumps({
                "items": [item.model_dump(mode="json") for item in items],
                "hidden": hidden.model_dump(mode="json")}), encoding="utf-8")
            (store.root / "container-baseline.json").write_text(json.dumps(snapshot(engine)))
            print("Container-native synthetic fixtures and SELECT-only role prepared.")
        elif action == "reader":
            assert url.username == "b2_reader"
            with engine.connect() as connection:
                connection.execute(text("SET TRANSACTION READ WRITE"))
                try:
                    connection.execute(text("DELETE FROM public.scenarios WHERE false"))
                except DBAPIError as error:
                    assert error.orig.sqlstate == "42501"
                else:
                    raise ValueError("reader role unexpectedly has write permission")
            print("Reader SELECT-only privilege enforced even after opting into read/write transactions.")
            from services.api.app.readiness import database_probe, expected_columns
            from services.api.app.settings import production_settings
            with engine.connect() as connection:
                rows = connection.execute(text("""SELECT c.relname, a.attname,
                    lower(format_type(a.atttypid,a.atttypmod)), NOT a.attnotnull
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    JOIN pg_attribute a ON a.attrelid=c.oid WHERE n.nspname='public'
                    AND a.attnum>0 AND NOT a.attisdropped""")).all()
                actual = {(table, column): (kind, nullable) for table, column, kind, nullable in rows}
                differences = [(key, expected, actual.get(key)) for key, expected in expected_columns().items()
                               if expected != actual.get(key)]
                if differences:
                    # Only schema metadata from this owned synthetic catalogue;
                    # never emit a connection URL or any working B1 data.
                    print("Disposable schema differences: " + json.dumps(differences))
            settings = production_settings(dict(os.environ, B2_ENV="production", TMPDIR="/tmp",
                                                 B2_STORAGE_ID="b2-container-fixture"))
            asyncio.run(database_probe(settings))
            print("Fresh reader dependency/schema probe passed independently of HTTP.")
        else:
            fixture = json.loads((store.root / "container-fixture.json").read_text())
            items = [PublishedScenarioManifest.model_validate(item) for item in fixture["items"]]
            hidden = PublishedScenarioManifest.model_validate(fixture["hidden"])
            with httpx.Client(base_url="http://api:8000", timeout=15, trust_env=False) as client:
                if action == "accept":
                    assert client.get("/readyz").status_code == 200
                    check_http(client, items, hidden, documentation_enabled=False)
                    assert snapshot(engine) == json.loads((store.root / "container-baseline.json").read_text())
                    print("Actual container TCP acceptance: all eight endpoints, downloads, ranges, HEAD, docs and safe errors passed; DB unchanged.")
                elif action == "security-cases":
                    for path in ("/api/v1/health", "/api/v1/scenarios", "/readyz", "/does-not-exist", "/docs"):
                        response = client.get(path)
                        assert response.headers["x-content-type-options"] == "nosniff"
                        assert response.headers["x-frame-options"] == "DENY"
                        assert response.headers["referrer-policy"] == "no-referrer"
                        assert "default-src 'none'" in response.headers["content-security-policy"]
                        assert response.headers["cache-control"] == "no-store"
                        assert "server" not in response.headers
                    for path in ("/api/v1/health", "/readyz", "/api/v1/scenarios"):
                        response = client.get(path, headers={"Host": "evil.invalid", "X-Forwarded-Host": "api"})
                        assert response.status_code == 400 and "evil.invalid" not in response.text
                    response = client.get("/api/v1/health", headers={"X-Forwarded-Proto": "https",
                        "X-Forwarded-For": "127.0.0.1", "Forwarded": 'proto=https;host="evil.invalid"'})
                    assert response.status_code == 200 and "strict-transport-security" not in response.headers
                    response = client.options("/api/v1/scenarios", headers={
                        "Origin": "https://fixture-frontend.invalid", "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Range,If-Range"})
                    assert response.status_code == 200
                    assert response.headers["access-control-allow-origin"] == "https://fixture-frontend.invalid"
                    assert "access-control-allow-credentials" not in response.headers
                    assert "*" not in response.headers["access-control-allow-methods"]
                    assert client.options("/api/v1/scenarios", headers={"Origin": "https://evil.invalid",
                        "Access-Control-Request-Method": "GET"}).status_code == 400
                    assert client.options("/api/v1/scenarios", headers={"Origin": "https://fixture-frontend.invalid",
                        "Access-Control-Request-Method": "POST"}).status_code == 400
                    response = client.get("/api/v1/scenarios", headers={"Origin": "https://fixture-frontend.invalid"})
                    assert response.status_code == 200 and response.headers["access-control-allow-origin"] == "https://fixture-frontend.invalid"
                    assert client.post("/api/v1/scenarios").status_code == 405
                    assert client.request("GET", "/api/v1/health", content=b"unwanted body").status_code == 400
                    response = client.get("/api/v1/health", headers={"X-Fill": "x" * 17000})
                    assert response.status_code == 431 and "X-Fill" not in response.text
                    print("Actual container security checks passed: host spoofing, proxy-header distrust, read-only/no-body limits, allowlisted CORS, private-network preflight default denial, safe headers and hidden docs.")
                elif action == "readiness-cases":
                    def ready(expected):
                        response = client.get("/readyz")
                        assert response.status_code == expected
                        assert response.headers["cache-control"] == "no-store"
                        assert "catalogue" not in response.text and "b2_reader" not in response.text
                        assert client.get("/api/v1/health").status_code == 200
                    ready(200)
                    with engine.connect() as connection:
                        assert connection.execute(text("SELECT count(*) FROM pg_stat_activity WHERE application_name='b2-readiness'")).scalar_one() == 0
                    changes = [
                        ("UPDATE public.alembic_version SET version_num='wrong'",
                         "UPDATE public.alembic_version SET version_num='g05b8eab1001'"),
                        ("ALTER TABLE public.scenarios RENAME COLUMN model_version TO probe_model_version",
                         "ALTER TABLE public.scenarios RENAME COLUMN probe_model_version TO model_version"),
                        ("ALTER TABLE public.scenarios ALTER COLUMN time_step_minutes TYPE bigint",
                         "ALTER TABLE public.scenarios ALTER COLUMN time_step_minutes TYPE integer"),
                        ("REVOKE SELECT ON public.scenarios FROM b2_reader",
                         "GRANT SELECT ON public.scenarios TO b2_reader"),
                        ("GRANT INSERT ON public.scenarios TO b2_reader",
                         "REVOKE INSERT ON public.scenarios FROM b2_reader"),
                        ("GRANT UPDATE(model_version) ON public.scenarios TO b2_reader",
                         "REVOKE UPDATE(model_version) ON public.scenarios FROM b2_reader"),
                        ("ALTER ROLE b2_reader CREATEDB", "ALTER ROLE b2_reader NOCREATEDB"),
                        ("GRANT CREATE ON SCHEMA public TO b2_reader",
                         "REVOKE CREATE ON SCHEMA public FROM b2_reader"),
                        ("GRANT USAGE ON SEQUENCE public.scenarios_id_seq TO b2_reader",
                         "REVOKE USAGE ON SEQUENCE public.scenarios_id_seq FROM b2_reader"),
                    ]
                    for damage, repair in changes:
                        try:
                            with engine.begin() as connection:
                                connection.execute(text(damage))
                            ready(503)
                        finally:
                            with engine.begin() as connection:
                                connection.execute(text(repair))
                        ready(200)
                    marker = store.root / ".b2-storage-ready.json"
                    original = marker.read_bytes()
                    try:
                        marker.unlink(); ready(503)
                        marker.write_text('{"schema_version":1,"store_id":"wrong-store"}'); ready(503)
                    finally:
                        marker.write_bytes(original)
                    ready(200)
                    assert snapshot(engine) == json.loads((store.root / "container-baseline.json").read_text())
                    print("Real readiness failures/recovery passed: revision, column, type, SELECT, table/column writes, powerful role, schema CREATE and missing/wrong mount identity; DB restored.")
                elif action == "failure-cases":
                    identity = items[-1].scenario_id
                    link = client.get("/api/v1/exports/" + identity + "?format=geojson").json()["download_url"]
                    with Session(engine) as session, session.begin():
                        PublishedScenarioRepository(session).revoke(identity, actor="synthetic-container-operator",
                                                                   reason="Container engineering withdrawal test")
                    assert client.get(link).status_code == 404
                    link = client.get("/api/v1/exports/" + items[0].scenario_id + "?format=geojson").json()["download_url"]
                    path = store.path_for_key("receiving/synthetic-gis/results/export.geojson")
                    original = path.read_bytes()
                    try:
                        path.write_bytes(b"synthetic container tamper check")
                        response = client.get(link)
                        assert response.status_code == 503 and "file:" not in response.text
                    finally:
                        path.write_bytes(original)
                    print("Issued-link revocation and artifact tampering rejected safely; fixture bytes restored.")
                else:
                    raise ValueError("unknown fixture action")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main(sys.argv[1])
