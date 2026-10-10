"""Preserve exact route coverage across FastAPI's included-router transition."""
from types import SimpleNamespace


def route_contexts(app):
    try:
        from fastapi.routing import iter_route_contexts
    except ImportError:
        return [SimpleNamespace(route=route, path=getattr(route, 'path', None),
                                methods=getattr(route, 'methods', None),
                                endpoint=getattr(route, 'endpoint', None),
                                body_field=getattr(route, 'body_field', None)) for route in app.routes]
    return list(iter_route_contexts(app.routes))
