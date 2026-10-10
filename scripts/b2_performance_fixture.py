"""Owned synthetic catalogue scale and read-only performance fingerprints."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from scripts.backup_db import snapshot
from scripts.b2_large_asset_probe import guard, URL
from scripts.rehearse_b1_handoff import REVIEWER, require
from services.api.app.db.models import PublishedBundle, Scenario
from services.api.app.gis_validation import GISInspector
from services.api.app.published_contract import PublishedScenarioManifest
from services.api.app.published_registry import register_published_bundle
from services.api.app.storage import sha256_file


def fingerprint(engine, store):
    database = json.dumps(snapshot(engine), sort_keys=True, separators=(',', ':')).encode()
    objects = {p.relative_to(store.root).as_posix(): sha256_file(p) for p in store.root.rglob('*') if p.is_file()}
    return {'database_sha256': hashlib.sha256(database).hexdigest(),
            'objects_sha256': hashlib.sha256(json.dumps(objects, sort_keys=True).encode()).hexdigest(),
            'object_files': len(objects)}


def prepare(count):
    store, url = guard()
    require(1 <= count <= 500, 'bounded synthetic catalogue size required')
    engine = create_engine(url)
    try:
        fixture = json.loads((store.root / 'container-fixture.json').read_text())
        identity = fixture['items'][1]['scenario_id']
        with Session(engine) as session, session.begin():
            bundle = session.scalar(select(PublishedBundle).where(PublishedBundle.scenario_id == identity))
            require(bundle is not None, 'small GIS-aware fixture required')
            original = PublishedScenarioManifest.model_validate(bundle.manifest_json)
            for index in range(count):
                item = original.model_copy(deep=True)
                item.scenario_id = f'b2-perf-synthetic-{index:04d}'
                item.run_id = item.scenario_id + '-run'
                register_published_bundle(session, item, store, bundle_root_uri=bundle.bundle_root_uri,
                    registered_by='synthetic-performance-operator', trusted_approvers={REVIEWER}, asset_inspector=GISInspector())
        facts = json.loads((store.root / 'step4-large-fixture.json').read_text())
        path = store.path_for_key('step4-large/results/large-max_depth_cog.tif')
        start = facts['size_bytes'] // 2
        with path.open('rb') as stream:
            stream.seek(start); chunk = stream.read(65536)
        with Session(engine) as session:
            approved = len(session.scalars(select(Scenario.scenario_id).where(Scenario.publication_status == 'approved')).all())
        return {'small_scenario_id': identity, 'large_url': URL, 'large': facts,
                'range': {'start': start, 'length': len(chunk), 'sha256': hashlib.sha256(chunk).hexdigest()},
                'approved_catalogue_rows': approved, 'extra_catalogue_rows': count,
                'synthetic': True, 'scientific_approval': False, 'fingerprint': fingerprint(engine, store)}
    finally:
        engine.dispose()


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        result = prepare(int(sys.argv[2]))
    elif sys.argv[1] == 'fingerprint':
        store, url = guard(); engine = create_engine(url)
        try: result = fingerprint(engine, store)
        finally: engine.dispose()
    else:
        raise ValueError('unknown performance fixture action')
    print(json.dumps(result, sort_keys=True), flush=True)
