"""B2 transport-independent safeguards; no invented identity/login authority."""
from dataclasses import dataclass
import ipaddress
import json
import os
import re
from urllib.parse import urlsplit

from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse


SECURITY_ERROR = "API host, browser-origin or request-boundary configuration is invalid."


def canonical_host(value):
    try:
        return ipaddress.ip_address(value.strip("[]")).compressed
    except ValueError:
        if (len(value) > 253 or value != value.lower() or not all(
                re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in value.split("."))):
            raise ValueError()
        return value


@dataclass(frozen=True)
class SecuritySettings:
    allowed_hosts: tuple[str, ...]
    cors_origins: tuple[str, ...]
    max_header_bytes: int


def security_settings(environment=None):
    environment = os.environ if environment is None else environment
    try:
        hosts = environment.get("B2_ALLOWED_HOSTS", "127.0.0.1,localhost")
        if not hosts or len(hosts) > 4096:
            raise ValueError()
        allowed = tuple(canonical_host(host.strip()) for host in hosts.split(","))
        if not 1 <= len(allowed) <= 32 or len(set(allowed)) != len(allowed):
            raise ValueError()
        raw = environment.get("B2_CORS_ORIGINS", "[]")
        if len(raw) > 8192:
            raise ValueError()
        origins = json.loads(raw)
        if not isinstance(origins, list) or len(origins) > 16:
            raise ValueError()
        for origin in origins:
            if not isinstance(origin, str) or len(origin) > 512 or any(ord(c) <= 32 for c in origin):
                raise ValueError()
            url = urlsplit(origin)
            if (url.scheme not in {"http", "https"} or not url.hostname or url.username is not None
                    or url.password is not None or url.path or url.query or url.fragment
                    or origin != url.scheme + "://" + url.netloc
                    or (url.port is not None and not 1 <= url.port <= 65535)):
                raise ValueError()
            host = canonical_host(url.hostname)
            if url.scheme == "http":
                try:
                    local = ipaddress.ip_address(host).is_loopback
                except ValueError:
                    local = host == "localhost"
                if not local:
                    raise ValueError()
        if len(set(origins)) != len(origins):
            raise ValueError()
        maximum = int(environment.get("B2_MAX_HEADER_BYTES", "16384"))
        if not 1024 <= maximum <= 65536:
            raise ValueError()
        # Forwarded-header trust requires the later agreed edge/identity policy.
        # The supported local stack deliberately has no trusted proxy addresses.
        if environment.get("B2_TRUSTED_PROXY_IPS"):
            raise ValueError()
        return SecuritySettings(allowed, tuple(origins), maximum)
    except Exception:
        raise ValueError(SECURITY_ERROR) from None


def valid_request_host(headers, settings):
    values = [value for name, value in headers if name.lower() == b"host"]
    if len(values) != 1:
        return False
    try:
        value = values[0].decode("ascii")
        if any(ord(c) <= 32 for c in value):
            return False
        url = urlsplit("//" + value)
        if (not url.hostname or url.username is not None or url.password is not None
                or url.path or url.query or url.fragment
                or (url.port is not None and not 1 <= url.port <= 65535)):
            return False
        return canonical_host(url.hostname) in settings.allowed_hosts
    except (ValueError, UnicodeError):
        return False


class SecurityBoundary:
    """Outer pure-ASGI wrapper: preserves streaming and covers even error replies."""
    def __init__(self, app, settings):
        self.app = app
        self.settings = settings
        self.browser_app = CORSMiddleware(
            app, allow_origins=settings.cors_origins, allow_methods=["GET", "HEAD"],
            allow_headers=["Range", "If-Range"], allow_credentials=False,
            expose_headers=["ETag", "Content-Length", "Content-Range", "Accept-Ranges", "Content-Disposition"],
            max_age=300)

    def __getattr__(self, name):
        # Preserve FastAPI metadata inspection (OpenAPI, routes, state). Local
        # development keeps the unwrapped FastAPI object and normal docs.
        return getattr(self.app, name)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def protected_send(message):
            if message["type"] == "http.response.start":
                headers = [(name, value) for name, value in message.get("headers", [])
                           if name.lower() not in {b"server", b"x-powered-by", b"x-content-type-options",
                               b"referrer-policy", b"x-frame-options", b"content-security-policy",
                               b"strict-transport-security"}]
                headers.extend([
                    (b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"),
                ])
                if not any(name.lower() == b"cache-control" for name, value in headers):
                    headers.append((b"cache-control", b"no-store"))
                # Never derive TLS from untrusted Forwarded/X-Forwarded-*.
                if scope.get("scheme") == "https":
                    headers.append((b"strict-transport-security", b"max-age=31536000"))
                message = dict(message, headers=headers)
            await send(message)

        async def reject(status, title, detail, extra=None):
            response = JSONResponse({"type": "about:blank", "title": title, "status": status,
                                     "detail": detail, "instance": scope["path"]}, status_code=status,
                                    media_type="application/problem+json",
                                    headers={"Cache-Control": "no-store"} | (extra or {}))
            await response(scope, receive, protected_send)

        headers = scope.get("headers", [])
        if sum(len(name) + len(value) + 4 for name, value in headers) > self.settings.max_header_bytes:
            await reject(431, "Request headers too large", "The request headers exceed the supported size.")
        elif not valid_request_host(headers, self.settings):
            await reject(400, "Invalid request", "The request host is not allowed.")
        elif scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            await reject(405, "Method not allowed", "This API supports read-only requests.",
                         {"Allow": "GET, HEAD, OPTIONS"})
        else:
            lengths = [value for name, value in headers if name.lower() == b"content-length"]
            encoded = any(name.lower() == b"transfer-encoding" for name, value in headers)
            if encoded or len(lengths) > 1 or (lengths and lengths[0] != b"0"):
                await reject(400, "Invalid request", "Read-only requests must not contain a request body.")
            else:
                await self.browser_app(scope, receive, protected_send)
