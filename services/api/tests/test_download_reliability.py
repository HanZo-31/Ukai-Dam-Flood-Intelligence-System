"""Bounded snapshot, disk/read faults and ASGI cleanup without B1 changes."""
import asyncio
from contextlib import contextmanager
from dataclasses import replace
import io
import os
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from services.api.app.api.v1.scenarios import download_response
from services.api.app.services import asset_service as assets
from services.api.app.services import download_policy as capacity
from services.api.app.storage import LocalObjectStore


@pytest.fixture
def fixture(tmp_path):
    store = LocalObjectStore(tmp_path / 'objects')
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    uri, checksum = store.put('verified.bin', b'approved artifact' * 100)
    return store, uri, checksum, capacity.DownloadPolicy(scratch)


def get(fixture, **kwargs):
    store, uri, checksum, policy = fixture
    return assets.verified_download(store, uri, checksum, media_type='image/tiff', filename='map.tif', policy=policy, **kwargs)


@pytest.mark.parametrize('key,value', [
    ('B2_DOWNLOAD_MAX_BYTES', '0'), ('B2_DOWNLOAD_MAX_BYTES', 'x'),
    ('B2_DOWNLOAD_MAX_BYTES', str(9 * 1024**3)), ('B2_DOWNLOAD_VERIFY_SECONDS', '0'),
    ('B2_DOWNLOAD_VERIFY_SECONDS', '301'), ('B2_DOWNLOAD_STREAM_SECONDS', '0'),
    ('B2_DOWNLOAD_STREAM_SECONDS', '3601'), ('B2_SCRATCH_MIN_BYTES', '0'), ('TMPDIR', '/missing-b2-scratch')])
def test_invalid_capacity_configuration_is_safe(key, value):
    with pytest.raises(ValueError, match='configuration is invalid') as error:
        capacity.download_policy({key: value})
    assert value not in str(error.value)


def test_snapshot_uses_explicit_scratch_and_closes_on_partial_iteration(fixture):
    download = get(fixture)
    iterator = download.chunks(0, download.size)
    assert next(iterator)
    iterator.close()
    assert download.handle.closed
    download.handle.close()  # idempotent lease release


@pytest.mark.parametrize('fault', ['missing', 'wrong_checksum', 'too_large', 'disk_full', 'cannot_create', 'cannot_allocate'])
def test_pre_header_faults_are_safe_and_leave_no_snapshot(fixture, monkeypatch, fault):
    store, uri, checksum, policy = fixture
    if fault == 'missing': store.resolve_uri(uri).unlink()
    if fault == 'wrong_checksum': checksum = 'sha256:' + '0' * 64
    if fault == 'too_large': policy = replace(policy, max_bytes=1)
    if fault == 'disk_full': monkeypatch.setattr(capacity.shutil, 'disk_usage', lambda _: SimpleNamespace(free=policy.reserve_bytes))
    if fault == 'cannot_create':
        monkeypatch.setattr(capacity.tempfile, 'TemporaryFile', lambda **_: (_ for _ in ()).throw(OSError('private scratch path')))
    if fault == 'cannot_allocate':
        if os.name == 'posix':
            monkeypatch.setattr(capacity.os, 'posix_fallocate', lambda *_: (_ for _ in ()).throw(OSError('allocation full')))
        else:
            monkeypatch.setattr(capacity.tempfile, 'TemporaryFile', lambda **_: (_ for _ in ()).throw(OSError('allocation full')))
    with pytest.raises(HTTPException) as error:
        get((store, uri, checksum, policy))
    assert error.value.status_code == 503 and error.value.detail == 'The registered artifact is unavailable.'
    assert not [p for p in policy.scratch_root.iterdir() if p.name != '.b2-download-admission.lock']
    assert not capacity._pending


@pytest.mark.parametrize('fault', ['read_error', 'growth', 'timeout', 'short_write', 'flush_error'])
def test_mid_verification_fault_closes_snapshot(fixture, monkeypatch, fault):
    tracked = []
    original = capacity.tempfile.TemporaryFile
    def temporary(**kwargs):
        handle = original(**kwargs)
        tracked.append(handle)
        return handle
    monkeypatch.setattr(capacity.tempfile, 'TemporaryFile', temporary)
    if fault in {'read_error', 'growth'}:
        open_source = assets.open_local_source
        @contextmanager
        def broken(store, uri):
            with open_source(store, uri) as handle:
                class Source:
                    def fileno(self): return handle.fileno()
                    def read(self, length):
                        if fault == 'read_error': raise OSError('private source path')
                        return b'changed growth' * 1000
                yield Source()
        monkeypatch.setattr(assets, 'open_local_source', broken)
    elif fault == 'timeout':
        ticks = iter([0, 1000])
        monkeypatch.setattr(assets.time, 'monotonic', lambda: next(ticks))
    else:
        reserve = assets.reserve_snapshot
        def faulty(policy, size):
            lease = reserve(policy, size)
            if fault == 'short_write': lease.write = lambda _: 0
            else: lease.flush = lambda: (_ for _ in ()).throw(OSError('private scratch flush'))
            return lease
        monkeypatch.setattr(assets, 'reserve_snapshot', faulty)
    with pytest.raises(HTTPException) as error:
        get(fixture)
    assert error.value.status_code == 503
    assert tracked and all(h.closed for h in tracked) and not capacity._pending


def test_short_verified_stream_aborts_instead_of_succeeding():
    handle = io.BytesIO(b'bytes')
    download = assets.VerifiedDownload(handle, 10, 'checksum', 'image/tiff', 'map.tif')
    with pytest.raises(OSError, match='declared length'):
        list(download.chunks(0, download.size))
    assert handle.closed


@pytest.mark.parametrize('fault', ['before_headers', 'during_body', 'cancellation'])
def test_asgi_send_failure_closes_verified_snapshot(fixture, fault):
    download = get(fixture)
    scope = {'type': 'http', 'asgi': {'spec_version': '2.4'}, 'method': 'GET',
             'path': '/', 'headers': []}
    response = download_response(download, Request(scope))
    async def receive(): return {'type': 'http.disconnect'}
    async def send(message):
        if fault == 'cancellation': raise asyncio.CancelledError()
        if fault == 'before_headers' or message['type'] == 'http.response.body':
            raise OSError('client disconnected')
    with pytest.raises(BaseException):
        asyncio.run(response(scope, receive, send))
    assert download.handle.closed and not capacity._pending


def test_stalled_body_send_has_a_deadline_and_releases_capacity(fixture):
    download = get(fixture)
    download.stream_seconds = .03  # accelerated internal fixture, not environment configuration
    scope = {'type': 'http', 'asgi': {'spec_version': '2.4'}, 'method': 'GET', 'path': '/', 'headers': []}
    response = download_response(download, Request(scope))
    async def receive(): return {'type': 'http.disconnect'}
    async def send(message):
        if message['type'] == 'http.response.body': await asyncio.Event().wait()
    with pytest.raises(TimeoutError): asyncio.run(response(scope, receive, send))
    assert download.handle.closed and not capacity._pending


def test_head_and_invalid_range_always_close(fixture):
    for method, headers in [('HEAD', []), ('GET', [(b'range', b'bytes=9-2')])]:
        download = get(fixture)
        request = Request({'type': 'http', 'method': method, 'headers': headers})
        if method == 'HEAD': assert download_response(download, request).status_code == 200
        else:
            with pytest.raises(HTTPException) as error: download_response(download, request)
            assert error.value.status_code == 416
        assert download.handle.closed and not capacity._pending


def test_database_dependency_is_released_before_streaming(fixture):
    from fastapi.testclient import TestClient
    from services.api.app.main import app
    from services.api.app.services.scenario_service import get_scenario_service
    state = {'closed': False, 'streamed': False}
    class Service:
        def asset_download(self, *args, **kwargs):
            download = get(fixture)
            original = download.chunks
            def chunks(start, length):
                assert state['closed'], 'slow client must not retain the catalogue connection'
                state['streamed'] = True
                yield from original(start, length)
            download.chunks = chunks
            return download
    def dependency():
        try: yield Service()
        finally: state['closed'] = True
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_scenario_service] = dependency
    try:
        with TestClient(app) as client:
            response = client.get('/api/v1/scenarios/step4-demo/assets/max_depth_cog')
            assert response.status_code == 200
    finally:
        app.dependency_overrides.clear(); app.dependency_overrides.update(previous)
    assert state['closed'] and state['streamed'] and not capacity._pending


@pytest.mark.skipif(os.name != 'posix', reason='Linux cross-worker admission lock')
def test_admission_lock_coordinates_independent_processes(fixture):
    import subprocess
    import sys
    _, _, _, policy = fixture
    code = "from pathlib import Path; from services.api.app.services.download_policy import DownloadPolicy,reserve_snapshot; "
    code += "\ntry:\n h=reserve_snapshot(DownloadPolicy(Path(__import__('sys').argv[1])),1024); h.close(); raise SystemExit(2)\nexcept OSError: print('blocked')\n"
    with capacity.admission_lock(policy.scratch_root):
        run = subprocess.run([sys.executable, '-c', code, str(policy.scratch_root)],
                             capture_output=True, text=True, timeout=20)
    assert run.returncode == 0 and run.stdout.strip() == 'blocked'


@pytest.mark.parametrize('budget', ['0', '-1', '1000000001'])
def test_b1_large_raster_option_has_a_safe_bound(budget):
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[3]
    run = subprocess.run([sys.executable, 'scripts/register_published_bundle.py', 'unused-manifest.json',
                          '--bundle-root', 'file:///unused/', '--registered-by', 'unit-fixture',
                          '--max-raster-pixels', budget],cwd=root,capture_output=True,text=True,timeout=20)
    assert run.returncode == 2 and 'Raster pixel budget must be between' in run.stderr


@pytest.mark.skipif(os.name != 'posix', reason='Linux descriptor traversal/regular-file safety')
@pytest.mark.parametrize('fault', ['fifo', 'parent_swap', 'final_swap'])
def test_nonregular_and_symlink_races_cannot_escape_store(fixture, monkeypatch, tmp_path, fault):
    store, uri, checksum, policy = fixture
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'verified.bin').write_bytes(b'private')
    if fault == 'fifo':
        store.resolve_uri(uri).unlink()
        os.mkfifo(store.root / 'verified.bin')
    else:
        original = store.resolve_uri
        def swap(uri):
            resolved = original(uri)
            if fault == 'parent_swap':
                store.root.rename(tmp_path / 'old-root')
                store.root.symlink_to(outside, target_is_directory=True)
            else:
                resolved.unlink()
                resolved.symlink_to(outside / 'verified.bin')
            return resolved
        monkeypatch.setattr(store, 'resolve_uri', swap)
    with pytest.raises(HTTPException) as error: get(fixture)
    assert error.value.status_code == 503
