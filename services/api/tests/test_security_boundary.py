"""B2 security controls do not invent user identities or scientific approvals."""
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from services.api.app.security import SecurityBoundary, security_settings


@pytest.mark.parametrize("changes", [
    {"B2_ALLOWED_HOSTS": "*"}, {"B2_ALLOWED_HOSTS": "*.example.org"},
    {"B2_ALLOWED_HOSTS": "https://api.example.org"}, {"B2_ALLOWED_HOSTS": "api:8000"},
    {"B2_ALLOWED_HOSTS": "localhost,localhost"}, {"B2_ALLOWED_HOSTS": "localhost."},
    {"B2_CORS_ORIGINS": '["*"]'}, {"B2_CORS_ORIGINS": '["null"]'},
    {"B2_CORS_ORIGINS": '["http://frontend.example.org"]'},
    {"B2_CORS_ORIGINS": '["https://private-token@frontend.example.org"]'},
    {"B2_CORS_ORIGINS": '["https://frontend.example.org/path"]'},
    {"B2_CORS_ORIGINS": '["https://frontend.example.org?private-token"]'},
    {"B2_CORS_ORIGINS": '["https://frontend.example.org:0"]'},
    {"B2_CORS_ORIGINS": '"https://frontend.example.org"'},
    {"B2_CORS_ORIGINS": '[1]'}, {"B2_CORS_ORIGINS": '['},
    {"B2_CORS_ORIGINS": '["https://a.example.org","https://a.example.org"]'},
    {"B2_MAX_HEADER_BYTES": "0"}, {"B2_MAX_HEADER_BYTES": "65537"},
    {"B2_TRUSTED_PROXY_IPS": "*"},
])
def test_security_configuration_rejects_unsafe_values(changes):
    with pytest.raises(ValueError) as error:
        security_settings(changes)
    assert "private-token" not in str(error.value)


def make_app(environment=None):
    api = FastAPI()
    @api.get("/ok")
    def okay():
        return {"status": "ok"}
    @api.get("/fail")
    def failure():
        raise RuntimeError("private-token")
    return SecurityBoundary(api, security_settings(environment or {"B2_ALLOWED_HOSTS": "testserver"}))


@pytest.mark.parametrize("path,expected", [("/ok", 200), ("/missing", 404), ("/fail", 500)])
def test_headers_cover_success_errors_and_unhandled_failures(path, expected):
    with TestClient(make_app(), raise_server_exceptions=False) as client:
        response = client.get(path)
    assert response.status_code == expected
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert "private-token" not in response.text


@pytest.mark.parametrize("host", ["evil.invalid", "testserver.evil.invalid", "private-token@testserver",
                                  "testserver:0", "testserver/extra", "testserver."])
def test_host_spoofing_is_denied(host):
    with TestClient(make_app()) as client:
        response = client.get("/ok", headers={"Host": host, "X-Forwarded-Host": "testserver"})
    assert response.status_code == 400 and "private-token" not in response.text
    assert response.headers["content-type"] == "application/problem+json"


def test_duplicate_and_missing_host_headers_are_rejected_without_reading_body():
    async def run(headers):
        messages = []
        async def receive():
            pytest.fail("body was read")
        async def send(message):
            messages.append(message)
        scope = {"type": "http", "method": "GET", "scheme": "http", "path": "/ok",
                 "headers": headers, "query_string": b""}
        await make_app()(scope, receive, send)
        assert messages[0]["status"] == 400
    asyncio.run(run([]))
    asyncio.run(run([(b"host", b"testserver"), (b"host", b"evil.invalid")]))


def test_only_explicit_browser_origins_methods_and_range_headers_are_allowed():
    app = make_app({"B2_ALLOWED_HOSTS": "testserver", "B2_CORS_ORIGINS": '["https://frontend.example.org"]'})
    with TestClient(app) as client:
        headers = {"Origin": "https://frontend.example.org", "Access-Control-Request-Method": "GET",
                   "Access-Control-Request-Headers": "Range,If-Range"}
        allowed = client.options("/ok", headers=headers)
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == headers["Origin"]
        assert "access-control-allow-credentials" not in allowed.headers
        assert "*" not in allowed.headers["access-control-allow-methods"]
        for changes in ({"Origin": "https://evil.invalid"}, {"Access-Control-Request-Method": "POST"},
                        {"Access-Control-Request-Headers": "Authorization"},
                        {"Access-Control-Request-Private-Network": "true"}):
            assert client.options("/ok", headers=headers | changes).status_code == 400
        simple = client.get("/ok", headers={"Origin": headers["Origin"]})
        assert "etag" in simple.headers["access-control-expose-headers"].lower()
        assert "access-control-allow-origin" not in client.get("/ok", headers={"Origin": "https://evil.invalid"}).headers


def test_cors_defaults_closed_but_is_not_authorization():
    with TestClient(make_app()) as client:
        response = client.get("/ok", headers={"Origin": "https://evil.invalid"})
        assert response.status_code == 200 and "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT"])
def test_write_and_trace_methods_are_rejected(method):
    with TestClient(make_app()) as client:
        assert client.request(method, "/ok").status_code == 405


def test_body_and_header_limits_do_not_leak_rejected_values():
    with TestClient(make_app()) as client:
        assert client.request("GET", "/ok", content=b"private-token").status_code == 400
        assert client.get("/ok", headers={"X-Private-Token": "x" * 17000}).status_code == 431


def test_forwarding_headers_cannot_spoof_tls():
    with TestClient(make_app()) as client:
        response = client.get("/ok", headers={"X-Forwarded-Proto": "https", "Forwarded": "proto=https"})
        assert "strict-transport-security" not in response.headers
    with TestClient(make_app(), base_url="https://testserver") as client:
        assert client.get("/ok").headers["strict-transport-security"] == "max-age=31536000"


def test_loopback_http_origin_and_exact_ipv6_host_supported():
    config = security_settings({"B2_ALLOWED_HOSTS": "::1", "B2_CORS_ORIGINS": '["http://localhost:5173"]'})
    # Starlette 0.52.1's test transport cannot parse an IPv6 base_url. Exercise
    # the real IPv6 authority parser via the Host header, not a weakened rule.
    with TestClient(SecurityBoundary(FastAPI(), config)) as client:
        assert client.get("/missing", headers={"Host": "[::1]:8000"}).status_code == 404
