"""Real >300 MiB COG rehearsal in the existing owned container fixture only."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
import numpy as np
import rasterio
from rasterio.shutil import copy as copy_raster
from rasterio.transform import from_origin
from rasterio.windows import Window
from rio_cogeo.cogeo import cog_validate
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from scripts.gis_fixture import build_fixture
from scripts.rehearse_b1_handoff import approved_fixture, REVIEWER, require
from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate
from services.api.app.repositories.catalog_repository import DatasetRepository
from services.api.app.storage import default_store, sha256_file

SIZE = 8192
MIB = 1024**2
IDENTITY = 'b2-step4-large-demo'
URL = '/api/v1/scenarios/' + IDENTITY + '/assets/max_depth_cog?data_mode=demo'


def guard():
    import re
    url = make_url(os.environ['DATABASE_URL'])
    store = default_store()
    require(url.host == 'catalogue' and bool(re.fullmatch(r'b2_container_[0-9a-f]{16}', url.database or ''))
            and str(store.root) == '/objects', 'large probe requires owned disposable container storage/DB')
    return store, url


def prepare():
    store, url = guard()
    draft, root, _ = build_fixture(store, prefix='step4-large/')
    draft.datasets[0].dataset_id = 'synthetic-step4-large-input'
    for role, value in [('max_depth_cog', .5), ('max_velocity_cog', .2), ('arrival_time_cog', 15.)]:
        target = store.path_for_key('step4-large/results/large-' + role + '.tif')
        require(not target.exists(), 'large fixture already exists')
        source = target.with_suffix('.source.tif')
        try:
            with rasterio.Env(GDAL_CACHEMAX=32 * MIB):
                with rasterio.open(source, 'w', driver='GTiff', width=SIZE, height=SIZE, count=1,
                                   dtype='float32', crs='EPSG:32643', transform=from_origin(300000, 2300000, 10, 10),
                                   nodata=-9999., tiled=True, blockxsize=512, blockysize=512) as dataset:
                    block = np.full((512, 512), value, dtype='float32')
                    for y in range(0, SIZE, 512):
                        for x in range(0, SIZE, 512): dataset.write(block, 1, window=Window(x, y, 512, 512))
                    dataset.set_band_unit(1, draft.asset_metadata[role].unit)
                    dataset.update_tags(synthetic='true', coverage_start=draft.time_coverage.start.isoformat(),
                                        coverage_end=draft.time_coverage.end.isoformat())
                copy_raster(source, target, driver='COG', BLOCKSIZE=512, COMPRESS='NONE', RESAMPLING='NEAREST')
        finally:
            source.unlink(missing_ok=True)
        valid, errors, warnings = cog_validate(str(target), strict=True, quiet=True)
        require(valid and not errors and target.stat().st_size > 300 * MIB, 'large file must be a real strict-valid >300 MiB COG')
        draft.assets[role] = 'results/' + target.name
        draft.asset_metadata[role].checksum = sha256_file(target)
    item = approved_fixture(draft, IDENTITY, historical=False)
    engine = create_engine(url)
    try:
        with Session(engine) as session, session.begin():
            datasets = DatasetRepository(session)
            for source in draft.datasets:
                datasets.register(DatasetCreate(dataset_id=source.dataset_id, name='Synthetic large-file input',
                    description='Invented storage reliability fixture, not observations', data_mode='demo'))
                values = source.model_dump()
                values['source_reference'] = store.resolve_uri(root + source.source_reference).as_uri()
                datasets.register_version(DatasetVersionCreate.model_validate(values))
        manifest_uri, _ = store.put('step4-large/approved-test-manifest.json', item.model_dump_json().encode())
        result = subprocess.run([sys.executable, 'scripts/register_published_bundle.py', str(store.resolve_uri(manifest_uri)),
            '--bundle-root', root, '--registered-by', 'synthetic-step4-reliability-operator',
            '--trusted-approver', REVIEWER, '--max-raster-pixels', str(SIZE * SIZE)],
            cwd=ROOT, capture_output=True, text=True, timeout=180)
        require(result.returncode == 0, 'real bounded GIS-aware B1 CLI import failed')
    finally:
        engine.dispose()
    path = store.resolve_uri(root + item.assets['max_depth_cog'])
    facts = {'scenario_id': IDENTITY, 'role': 'max_depth_cog', 'size_bytes': path.stat().st_size,
             'checksum': sha256_file(path), 'width': SIZE, 'height': SIZE, 'strict_cog_valid': True,
             'all_three_aligned_cogs_inspected_by_b1': True, 'synthetic': True, 'scientific_approval': False}
    (store.root / 'step4-large-fixture.json').write_text(json.dumps(facts))
    print(json.dumps(facts), flush=True)


def consume(response, facts):
    require(response.status_code == 200, 'large GET failed')
    digest, size = hashlib.sha256(), 0
    for chunk in response.iter_bytes(chunk_size=MIB):
        digest.update(chunk); size += len(chunk)
    require(size == facts['size_bytes'] and 'sha256:' + digest.hexdigest() == facts['checksum'], 'large GET integrity failed')
    return size


def check():
    store, _ = guard()
    facts = json.loads((store.root / 'step4-large-fixture.json').read_text())
    timings = {}
    with httpx.Client(base_url='http://api:8000', timeout=90, trust_env=False) as client:
        start = time.monotonic()
        with client.stream('GET', URL) as response: consume(response, facts)
        timings['full_get_seconds'] = round(time.monotonic() - start, 3)
        head = client.head(URL)
        require(head.status_code == 200 and not head.content and int(head.headers['content-length']) == facts['size_bytes'], 'large HEAD failed')
        require(head.headers['etag'] == '"' + facts['checksum'] + '"', 'large ETag drift')
        path = store.path_for_key('step4-large/results/large-max_depth_cog.tif')
        for first, last in [(0, 65535), (facts['size_bytes'] // 2, facts['size_bytes'] // 2 + 65535),
                            (facts['size_bytes'] - 65536, facts['size_bytes'] - 1)]:
            response = client.get(URL, headers={'Range': f'bytes={first}-{last}', 'If-Range': head.headers['etag']})
            with path.open('rb') as handle: handle.seek(first); expected = handle.read(last - first + 1)
            require(response.status_code == 206 and response.content == expected
                    and response.headers['content-range'] == f'bytes {first}-{last}/{facts["size_bytes"]}', 'large range failed')
        require(client.get(URL, headers={'Range': f'bytes={facts["size_bytes"]}-'}).status_code == 416, 'large 416 failed')
        # Hold two genuine slow TCP clients; their snapshots must remain alive.
        responses = []
        try:
            for _ in range(2): responses.append(client.send(client.build_request('GET', URL), stream=True))
            require(all(r.status_code == 200 for r in responses), 'two supported slow clients were not admitted')
            saturated = client.get(URL)
            require(saturated.status_code == 503 and saturated.headers['content-type'] == 'application/problem+json', 'capacity saturation did not fail before bytes')
            require(client.get('/api/v1/health').status_code == 200 and client.get('/readyz').status_code == 200, 'saturation blocked health/readiness')
            _, url = guard()
            engine = create_engine(url)
            try:
                with engine.connect() as connection:
                    require(connection.execute(text("SELECT count(*) FROM pg_stat_activity WHERE usename='b2_reader' AND state='idle in transaction'")).scalar_one() == 0,
                            'slow downloads retain database transactions')
            finally:
                engine.dispose()
            with ThreadPoolExecutor(max_workers=2) as pool:
                sizes = list(pool.map(lambda r: consume(r, facts), responses))
            require(sizes == [facts['size_bytes']] * 2, 'concurrent integrity failed')
        finally:
            for response in responses: response.close()
        # A third stream is aborted without consuming its body. Recovered HEAD
        # calls below verify that disconnect cleanup restores enough capacity.
        for _ in range(3):
            response = client.send(client.build_request('GET', URL), stream=True)
            require(response.status_code == 200, 'disconnect test could not start')
            response.close()
            time.sleep(.5)
        require(client.head(URL).status_code == 200, 'capacity did not recover after disconnects')
    return {'large_fixture': facts, 'timings': timings, 'full_head_ranges_416_verified': True,
            'two_slow_clients_integrity_verified': True, 'third_client_safe_503_verified': True,
            'three_client_disconnects_recovered': True, 'slow_clients_do_not_retain_db_transactions': True,
            'capacity_is_a_baseline_not_a_team_a_sla': True}


def failures():
    store, _ = guard()
    path = store.path_for_key('step4-large/results/large-max_depth_cog.tif')
    original_checksum = sha256_file(path)
    results = []
    with httpx.Client(base_url='http://api:8000', timeout=90, trust_env=False) as client:
        def unavailable(label):
            response = client.get(URL)
            require(response.status_code == 503 and response.json()['detail'] == 'The registered artifact is unavailable.'
                    and 'file:' not in response.text and '/objects' not in response.text, label + ' unsafe')
            require(client.get('/api/v1/health').status_code == 200, 'storage failure blocked liveness')
            results.append(label)
        withheld = path.with_suffix('.withheld')
        require(not withheld.exists(), 'withheld fixture already exists')
        try:
            path.rename(withheld); unavailable('missing_large_object')
        finally:
            if withheld.exists(): withheld.rename(path)
        with path.open('r+b') as handle:
            first = handle.read(1)
            try:
                handle.seek(0); handle.write(bytes([first[0] ^ 255])); handle.flush()
                unavailable('corrupt_large_object')
            finally:
                handle.seek(0); handle.write(first); handle.flush()
        size = path.stat().st_size
        with path.open('r+b') as handle:
            handle.seek(size - 65536); tail = handle.read()
            try:
                handle.truncate(size - 65536); unavailable('truncated_large_object')
            finally:
                handle.seek(size - 65536); handle.write(tail); handle.flush()
        mode = path.stat().st_mode & 0o777
        try:
            path.chmod(0); unavailable('unreadable_large_object')
        finally:
            path.chmod(mode)
        require(sha256_file(path) == original_checksum and client.head(URL).status_code == 200, 'large fixture recovery failed')
    return {'actual_large_file_failures': results, 'fixture_restored_checksum_verified': True}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare': prepare()
    elif action == 'check': print(json.dumps(check()), flush=True)
    elif action == 'failures': print(json.dumps(failures()), flush=True)
    else: raise ValueError('unknown large probe action')
