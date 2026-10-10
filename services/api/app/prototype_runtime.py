"""Local prototype installation and peer checks; disabled leaves the API intact."""
from copy import deepcopy
import ipaddress
from urllib.parse import parse_qs
from fastapi.responses import JSONResponse
from services.api.app.api_schemas.problem import Problem

PREFIX = "/api/v1/prototypes"


class PrototypePeerBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == PREFIX or path.startswith(PREFIX + "/")):
            return await self.app(scope, receive, send)
        allowed = False
        try:
            peer = ipaddress.ip_address(scope["client"][0])
            mapped = peer.ipv4_mapped if isinstance(peer, ipaddress.IPv6Address) else None
            allowed = peer.is_loopback or (mapped is not None and mapped.is_loopback)
        except (ValueError, TypeError, KeyError, IndexError):
            pass
        status, detail = 404, "Prototype preview is unavailable."
        if allowed:
            accepted = {"limit", "offset"} if path.rstrip("/") == PREFIX + "/scenarios" else set()
            raw_query = scope.get("query_string", b"")
            try:
                query = parse_qs(raw_query.decode("ascii", errors="strict"), keep_blank_values=True, max_num_fields=8)
                valid = len(raw_query) <= 4096 and set(query) <= accepted and all(len(values) == 1 for values in query.values())
            except (ValueError, UnicodeError):
                valid = False
            if valid:
                return await self.app(scope, receive, send)
            status, detail = 422, "Prototype query parameters are invalid."
        problem = Problem(title="Not found" if status == 404 else "Invalid request", status=status,
                          detail=detail, instance=path)
        return await JSONResponse(problem.model_dump(), status_code=status, media_type="application/problem+json",
                                  headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})(scope, receive, send)


def install_preview(app, settings):
    if settings is None:
        return
    from services.api.app.api.v1.prototypes import router
    app.state.prototype_settings = settings
    app.include_router(router)
    app.add_middleware(PrototypePeerBoundary)


def build_preview_openapi(app):
    if app.openapi_schema is not None and app.openapi_schema.get("x-prototype-enabled"):
        return app.openapi_schema
    from services.api.app.openapi import build_openapi
    spec = deepcopy(build_openapi(app))
    spec["x-prototype-enabled"] = True
    spec["info"]["description"] += " Explicit local prototype namespace exposes admitted draft/pending uncalibrated simulations only; never scientific approval."
    spec["tags"].append({"name": "prototype-preview", "description": "Uncalibrated prototype — simulated. Local operator admission only."})
    for path, methods in spec["paths"].items():
        if path.startswith(PREFIX + "/"):
            for method, operation in methods.items():
                if method in {"get", "head"}:
                    operation["description"] = "Enabled only in local profile with exact operator admission and a loopback peer. Disabled routes are404 and absent from default OpenAPI."
                    if "/assets/" in path or path.endswith(("/assumptions", "/quality-report")):
                        for code in ("200", "206"):
                            if code in operation["responses"]:
                                operation["responses"][code].setdefault("headers", {}).update({
                                    "X-Ukai-Prototype": {"schema": {"type": "string", "const": "true"}},
                                    "X-Ukai-Scientific-Validation": {"schema": {"type": "string", "const": "not_validated"}},
                                    "Cache-Control": {"schema": {"type": "string", "const": "no-store"}},
                                })
    app.openapi_schema = spec
    return spec
