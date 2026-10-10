"""Real four-scenario fallback tests; no new simulated/ML scenario is generated."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_service import create_app
from fastapi.testclient import TestClient
import pytest
import hashlib
import re

SOURCE = Path(os.environ.get('UKAI_REFERENCE_ROOT', str(Path(sys.executable).resolve().parents[2])))


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(SOURCE, tmp_path / 'jobs'), client=('127.0.0.1', 1234))


def request(identity='test-request-001', peak=20000, **changes):
    return {'schema_version': '1.0.0', 'request_id': identity, 'mode': 'stored_reference',
            'input_family': 'ukai-hyp-fixed-shape-v1', 'peak_release_m3s': peak,
            'allow_nearest_stored': False} | changes


def test_capabilities_do_not_enable_unaccepted_ml(client):
    response = client.get('/api/v1/candidates/capabilities')
    assert response.status_code == 200
    data = response.json()
    assert data['supported_modes'] == ['stored_reference']
    assert data['stored_peaks_m3s'] == [15000, 20000, 30000]
    assert data['experimental_ml_enabled'] is False
    assert data['historical_2006_is_separate_reference']


@pytest.mark.parametrize('peak', [15000, 20000, 30000])
def test_real_reference_has_exact_identity_and_no_computation(client, peak):
    response = client.post('/api/v1/candidates/jobs', json=request(peak=peak))
    assert response.status_code == 200
    data = response.json()
    assert data['requested_peak_release_m3s'] == data['actual_peak_release_m3s'] == peak
    assert data['status'] == 'completed' and not data['computed']
    assert not data['scientifically_validated'] and not data['cache_hit']
    assert 'stored_reference_not_new_prediction' in data['warnings']
    assert all(url.startswith('/api/v1/prototypes/scenarios/') for url in data['reference_resources'].values())
    assert client.get('/api/v1/candidates/jobs/' + data['job_id']).json()['source_run_id'] == data['source_run_id']


def test_idempotency_conflict_and_restart_do_not_overwrite(client, tmp_path):
    first = client.post('/api/v1/candidates/jobs', json=request()).json()
    repeated = client.post('/api/v1/candidates/jobs', json=request()).json()
    assert repeated['cache_hit'] and repeated['source_run_id'] == first['source_run_id']
    assert client.post('/api/v1/candidates/jobs', json=request(peak=15000)).status_code == 409
    restarted = TestClient(create_app(SOURCE, tmp_path / 'jobs'), client=('127.0.0.1', 1234))
    assert restarted.post('/api/v1/candidates/jobs', json=request()).json()['cache_hit']


def test_nearest_lookup_requires_opt_in_and_discloses_actual_peak(client):
    assert client.post('/api/v1/candidates/jobs', json=request(peak=25000)).status_code == 400
    result = client.post('/api/v1/candidates/jobs', json=request(peak=25000, allow_nearest_stored=True)).json()
    assert result['requested_peak_release_m3s'] == 25000 and result['actual_peak_release_m3s'] == 20000
    assert result['computed'] is False


@pytest.mark.parametrize('changes', [{'peak_release_m3s': 14999}, {'peak_release_m3s': 30001},
    {'mode': 'experimental_ml'}, {'input_family': 'historical-2006'}, {'run_simulation': True},
    {'request_id': '../escape'}, {'allow_nearest_stored': 'true'}])
def test_invalid_requests_cannot_start_or_write(client, tmp_path, changes):
    assert client.post('/api/v1/candidates/jobs', json=request(**changes)).status_code == 422
    assert list((tmp_path / 'jobs').iterdir()) == []


def test_nonlocal_peer_and_forwarded_headers_do_not_bypass(tmp_path):
    remote = TestClient(create_app(SOURCE, tmp_path / 'jobs'), client=('192.168.1.4', 1234))
    assert remote.get('/api/v1/candidates/capabilities', headers={'X-Forwarded-For': '127.0.0.1'}).status_code == 404


def test_truncated_job_evidence_fails_safely(client, tmp_path):
    (tmp_path / 'jobs/test-request-001.json').write_text('{')
    assert client.get('/api/v1/candidates/jobs/test-request-001').status_code == 503
    assert client.post('/api/v1/candidates/jobs', json=request()).status_code == 503


def test_failed_reference_validation_publishes_no_job(client, tmp_path, monkeypatch):
    import candidate_service
    monkeypatch.setattr(candidate_service, 'checksum', lambda path: 'sha256:' + '0' * 64)
    response = client.post('/api/v1/candidates/jobs', json=request())
    assert response.status_code == 503 and 'D:' not in response.text
    assert list((tmp_path / 'jobs').iterdir()) == []


def test_export_actual_contract(client, tmp_path):
    spec = client.app.openapi()
    assert set(spec['paths']) == {'/api/v1/candidates/capabilities', '/api/v1/candidates/jobs', '/api/v1/candidates/jobs/{job_id}'}
    json.dumps(spec, allow_nan=False)


@pytest.mark.parametrize('change', ['source_run', 'source_id', 'link', 'actual_peak', 'requested_peak', 'warnings', 'oversize'])
def test_changed_cached_job_cannot_cross_wire_references(client, tmp_path, change):
    client.post('/api/v1/candidates/jobs', json=request())
    path = tmp_path / 'jobs/test-request-001.json'
    saved = json.loads(path.read_text())
    result = saved['result']
    if change == 'source_run':
        result['source_run_id'] = 'wrong-source-run'
    elif change == 'source_id':
        result['source_scenario_id'] = 'wrong-source-scenario'
    elif change == 'link':
        result['reference_resources']['detail'] += '/wrong'
    elif change == 'actual_peak':
        result['actual_peak_release_m3s'] = 15000
    elif change == 'requested_peak':
        result['requested_peak_release_m3s'] = 25000
    elif change == 'warnings':
        result['warnings'] = []
    path.write_text(json.dumps(saved) + (' ' * 65536 if change == 'oversize' else ''))
    assert client.post('/api/v1/candidates/jobs', json=request()).status_code == 503


@pytest.fixture
def input_fixture(tmp_path):
    """Explicit synthetic hash-only files; never alter real scientific receipts."""
    source = tmp_path / 'synthetic-source'
    for peak, relative in [(15000, 'receipts/h01'), (20000, 'part_a'), (30000, 'receipts/h03')]:
        original = SOURCE / relative
        root = source / relative
        root.mkdir(parents=True)
        manifest = json.loads((original / 'prototype-manifest.json').read_text())
        manifest['scenario_id'] = 'synthetic-input-test-' + str(peak)
        manifest['run_id'] = manifest['scenario_id'] + '-run'
        def make_file(name):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = ('Synthetic hash-only fixture: ' + name).encode()
            path.write_bytes(data)
            return 'sha256:' + hashlib.sha256(data).hexdigest()
        for dataset in manifest['datasets']:
            dataset['checksum'] = make_file(dataset['source_reference'])
        for role, name in manifest['assets'].items():
            manifest['asset_metadata'][role]['checksum'] = make_file(name)
        manifest['assumptions_checksum'] = make_file(manifest['assumptions_url'])
        manifest['quality']['report_checksum'] = make_file(manifest['quality']['report_reference'])
        (root / 'prototype-manifest.json').write_text(json.dumps(manifest))
    state = tmp_path / 'fixture-jobs'
    return source, state


@pytest.mark.parametrize('index', range(4))
@pytest.mark.parametrize('fault', ['changed', 'missing'])
@pytest.mark.parametrize('operation', ['new', 'cached-get', 'cached-post'])
def test_every_bound_input_revalidated(input_fixture, index, fault, operation):
    source, state = input_fixture
    client = TestClient(create_app(source, state), client=('127.0.0.1', 1234))
    job = state / 'test-request-001.json'
    before = None
    if operation != 'new':
        assert client.post('/api/v1/candidates/jobs', json=request()).status_code == 200
        before = job.read_bytes()
    root = source / 'part_a'
    dataset = json.loads((root / 'prototype-manifest.json').read_text())['datasets'][index]
    path = root / dataset['source_reference']
    if fault == 'missing':
        path.unlink()  # Only synthetic temporary fixture bytes.
    else:
        path.write_bytes(b'Changed synthetic input')
    response = (client.get('/api/v1/candidates/jobs/test-request-001') if operation == 'cached-get'
                else client.post('/api/v1/candidates/jobs', json=request()))
    assert response.status_code == 503 and str(source) not in response.text
    assert not list(state.glob('*.pending'))
    assert job.read_bytes() == before if before is not None else not job.exists()


@pytest.mark.parametrize('relative', ['../outside.bin', '/absolute.bin', 'C:/absolute.bin', 'inputs\\invalid.bin'])
def test_input_path_cannot_escape_receipt(input_fixture, relative):
    source, state = input_fixture
    path = source / 'part_a/prototype-manifest.json'
    manifest = json.loads(path.read_text())
    manifest['datasets'][0]['source_reference'] = relative
    path.write_text(json.dumps(manifest))
    client = TestClient(create_app(source, state), client=('127.0.0.1', 1234))
    assert client.post('/api/v1/candidates/jobs', json=request()).status_code == 503
    assert not list(state.glob('*.json'))


def test_documentation_has_no_remote_assets(client):
    response = client.get('/docs')
    assert response.status_code == 200
    assert 'offline reference' in response.text and 'not an interactive Swagger' in response.text
    assert not re.findall(r'(?:src|href)=[\"\']https?://', response.text)
    assert "default-src 'none'" in response.headers['content-security-policy']
    assert client.get('/openapi.json').status_code == 200
    assert client.get('/api/v1/candidates/capabilities').status_code == 200
    assert client.get('/redoc').status_code == 404
    assert '/docs' not in client.app.openapi()['paths']
