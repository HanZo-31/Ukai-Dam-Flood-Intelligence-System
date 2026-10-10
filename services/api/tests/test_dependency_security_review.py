"""Reachability/mitigation evidence, not suppression or proof of patched packages."""
import inspect

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest
from starlette.endpoints import HTTPEndpoint
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from services.api.app.main import app
from services.api.app.security import SecurityBoundary, security_settings
from services.api.tests.route_inventory import route_contexts


def test_no_staticfiles_or_unrestricted_httpendpoint_routes():
    # These assertions support the two advisory applicability assessments. A
    # future new file-serving/class-based endpoint must trigger a fresh review.
    for context in route_contexts(app):
        route = context.route
        assert not isinstance(route, Mount)
        assert not isinstance(getattr(route, 'app', None), StaticFiles)
        endpoint = getattr(route, 'endpoint', None)
        assert not (inspect.isclass(endpoint) and issubclass(endpoint, HTTPEndpoint))


def test_business_routes_do_not_accept_form_bodies():
    business = [context for context in route_contexts(app) if isinstance(context.route, APIRoute)
                and context.path.startswith('/api/v1/')]
    assert business
    for route in business:
        assert route.body_field is None
        assert route.methods <= {'GET', 'HEAD'}


@pytest.mark.parametrize('host', ['testserver/poison?bar=', 'testserver?bar=', 'testserver#poison'])
def test_local_problem_instance_uses_actual_scope_not_poisoned_url(host):
    with TestClient(app) as client:
        response = client.get('/missing-security-review-route', headers={'Host': host})
    assert response.status_code == 404
    assert response.json()['instance'] == '/missing-security-review-route'


@pytest.mark.parametrize('host', ['testserver/poison?bar=', 'testserver?bar=',
                                 'testserver#poison', 'private-user@testserver'])
def test_production_boundary_blocks_host_poison_before_url_reconstruction(host):
    boundary = SecurityBoundary(app, security_settings({'B2_ALLOWED_HOSTS': 'testserver'}))
    with TestClient(boundary) as client:
        response = client.get('/missing-security-review-route', headers={'Host': host})
    assert response.status_code == 400
    assert response.json()['instance'] == '/missing-security-review-route'


@pytest.mark.parametrize('method', ['_DO_DELETE', '_PRIVATE_HELPER', '__INIT__'])
def test_production_boundary_rejects_nonstandard_dispatch_methods(method):
    boundary = SecurityBoundary(app, security_settings({'B2_ALLOWED_HOSTS': 'testserver'}))
    with TestClient(boundary) as client:
        assert client.request(method, '/api/v1/health').status_code == 405
