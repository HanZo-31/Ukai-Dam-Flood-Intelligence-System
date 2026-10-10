"""Readiness must verify the real scenario catalog before opening a browser."""
import json
from scripts.start_combined import catalog_ready


class Response:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, maximum):
        return json.dumps(self.payload).encode()


class Opener:
    def __init__(self, response):
        self.response = response
    def open(self, url, timeout):
        return self.response


def test_catalog_is_required_not_just_a_listening_process():
    expected = {('scenario-a', 'run-a'), ('scenario-b', 'run-b')}
    items = [{'scenario_id': s, 'run_id': r} for s, r in expected]
    assert catalog_ready(expected, Opener(Response({'items': items})))
    assert not catalog_ready(expected, Opener(Response({'items': items[:1]})))
    assert not catalog_ready(expected, Opener(Response({'items': items}, 503)))
    assert not catalog_ready(expected, Opener(Response({'items': []})))


def test_timeout_and_malformed_response_are_not_ready():
    class Timeout:
        def open(self, *args, **kwargs):
            raise TimeoutError('unreachable')
    assert not catalog_ready({('scenario-a', 'run-a')}, Timeout())
    assert not catalog_ready({('scenario-a', 'run-a')}, Opener(Response({'message': 'wrong service'})))
