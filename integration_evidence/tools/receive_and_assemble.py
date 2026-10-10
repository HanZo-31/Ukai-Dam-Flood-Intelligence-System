"""Verify immutable inputs and create a fresh complete local integration copy."""
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
from datetime import datetime

BASE = Path(r'D:\Window C2\Projects Works\Ukai_SSD_Ready')
TEAM1 = Path(r'D:\Window C2\Projects Works\Team1_Delivery_v1_for_Team2')
WORK = Path(__file__).resolve().parents[1]
TEAM2 = WORK / 'team2_work/deliveries/TEAM2_ENGINEERING_DELIVERY_V05'
OUT = WORK / 'integrated/UKAI_COMBINED_V01'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe(root, name):
    p = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or '..' in p.parts or p.as_posix() != name:
        raise ValueError('Unsafe path: ' + name)
    target = root / name
    if not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError('Missing/escaping file: ' + name)
    for item in (target, *target.parents):
        if item == root.parent:
            break
        if item.is_symlink() or item.is_junction():
            raise ValueError('Linked input: ' + name)
    return target


def receive_team1():
    checks = {}
    for line in (TEAM1 / 'CHECKSUMS.sha256').read_text(encoding='utf-8-sig').splitlines():
        digest, name = line.split('  ', 1)
        if name in checks or sha(safe(TEAM1, name)) != digest:
            raise ValueError('Team 1 checksum mismatch/duplicate: ' + name)
        checks[name] = digest
    listed = set(checks) | {'CHECKSUMS.sha256', 'DELIVERY_ID.txt', 'FILE_INVENTORY.csv'}
    actual = {p.relative_to(TEAM1).as_posix() for p in TEAM1.rglob('*') if p.is_file()}
    if actual != listed:
        raise ValueError('Team 1 unlisted/missing files: ' + str(actual ^ listed))
    if (TEAM1 / 'DELIVERY_ID.txt').read_text().strip() != sha(TEAM1 / 'CHECKSUMS.sha256'):
        raise ValueError('Team 1 delivery ID mismatch')
    rows = list(csv.DictReader((TEAM1 / 'FILE_INVENTORY.csv').open(encoding='utf-8-sig', newline='')))
    names = [r['path'] for r in rows]
    if len(set(names)) != len(names) or set(names) != set(checks) - {'FILE_INVENTORY.csv'}:
        raise ValueError('Team 1 inventory membership mismatch')
    for row in rows:
        target = safe(TEAM1, row['path'])
        if int(row['bytes']) != target.stat().st_size or row['sha256'] != checks[row['path']]:
            raise ValueError('Team 1 inventory mismatch: ' + row['path'])
    originals = []
    for p in (TEAM1 / 'baseline_originals').rglob('*'):
        if p.is_file():
            name = p.relative_to(TEAM1 / 'baseline_originals').as_posix()
            if sha(p) != sha(safe(BASE, name)):
                raise ValueError('Team 1 baseline mismatch: ' + name)
            originals.append(name)
    for a, b in [('candidate_openapi_v1.json', 'candidate-openapi-v1.json'),
                 ('candidate_examples.json', 'candidate-examples.json')]:
        if sha(TEAM1 / ('source_overlay/frontend/src/lib/fixtures/' + a)) != sha(TEAM2 / ('team2_work/contract-drop-v02/' + b)):
            raise ValueError('Frozen contract mismatch: ' + a)
    return {'checksums': len(checks), 'files': len(actual), 'baseline_originals_matched': originals,
            'delivery_id': sha(TEAM1 / 'CHECKSUMS.sha256'), 'contract_files_identical': True,
            'inventory_sha256_at_receipt': sha(TEAM1 / 'FILE_INVENTORY.csv'),
            'metadata_note': 'Team 1 excludes its inventory from checksums. All inventory rows were independently matched to the authenticated payload list; new assembly seal will cover the copied inventory.'}


def main():
    if OUT.exists():
        raise ValueError('Refusing to overwrite assembly: ' + str(OUT))
    sys.path.insert(0, str(TEAM2 / 'team2_work'))
    from verify_delivery import verify
    t2 = verify(TEAM2, BASE)
    t1 = receive_team1()
    baseline_count = 0
    for line in (BASE / 'SSD_CHECKSUMS.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        if sha(safe(BASE, name)) != digest:
            raise ValueError('Baseline corruption: ' + name)
        baseline_count += 1
        if baseline_count % 5000 == 0:
            print(f'Baseline: {baseline_count} hashes matched', flush=True)
    ignore = shutil.ignore_patterns('__pycache__', '.pytest_cache', '.vite')
    print('Verified inputs; copying complete baseline into new assembly.', flush=True)
    shutil.copytree(BASE, OUT, ignore=ignore)
    for path in (TEAM1 / 'source_overlay').rglob('*'):
        if path.is_file():
            dst = OUT / path.relative_to(TEAM1 / 'source_overlay')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)
    shutil.copytree(TEAM2 / 'team2_work', OUT / 'team2_work', ignore=ignore)
    shutil.copytree(TEAM1, OUT / 'integration_inputs/Team1_Delivery_v1', ignore=ignore)
    shutil.copytree(TEAM2, OUT / 'integration_inputs/Team2_Delivery_v05', ignore=ignore)
    shutil.copytree(TEAM1 / 'rebuilt_frontend/dist', OUT / 'frontend/dist', dirs_exist_ok=True)
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'baseline': str(BASE),
              'baseline_hashes_matched': baseline_count, 'team1': t1, 'team2': t2,
              'assembly': str(OUT), 'originals_modified': False, 'integration_accepted': False,
              'remaining': ['fresh frontend build/tests', 'combined runtime real-service checks', 'browser acceptance']}
    evidence = OUT / 'integration_evidence'
    evidence.mkdir()
    (evidence / 'RECEIVING_VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
