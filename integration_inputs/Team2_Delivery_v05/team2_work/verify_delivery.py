"""Read-only plain-folder receiver verification; no database or service startup."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from zoneinfo import ZoneInfo


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def safe_file(root, name):
    parts = PurePosixPath(name)
    if (not name or '\\' in name or ':' in name or parts.is_absolute()
            or '..' in parts.parts or '.' in parts.parts or parts.as_posix() != name):
        raise ValueError('Unsafe or noncanonical delivery path')
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Delivery path escapes root')
    for item in (path, *path.parents):
        if item == root.parent:
            break
        if item.is_symlink() or item.is_junction():
            raise ValueError('Delivery links/junctions are not accepted')
    if not path.is_file():
        raise ValueError('Missing delivered file: ' + name)
    return path


def verify_files(root):
    root = root.resolve()
    expected = {}
    for line in (root / 'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines():
        value, name = line.split('  ', 1)
        if not re.fullmatch('[0-9a-f]{64}', value) or name in expected or name == 'CHECKSUMS.sha256':
            raise ValueError('Malformed, duplicate or self-referential checksum')
        if digest(safe_file(root, name)) != value:
            raise ValueError('Checksum mismatch: ' + name)
        expected[name] = value
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
    if not expected or actual != set(expected) | {'CHECKSUMS.sha256'}:
        raise ValueError('Unexpected, omitted or unlisted delivery files')
    with (root / 'FILE_INVENTORY.csv').open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    row_paths = [row['relative_path'] for row in rows]
    if len(row_paths) != len(set(row_paths)) or set(row_paths) != set(expected) - {'FILE_INVENTORY.csv'}:
        raise ValueError('Inventory membership mismatch')
    for row in rows:
        path = safe_file(root, row['relative_path'])
        if int(row['bytes']) != path.stat().st_size or row['sha256'] != expected[row['relative_path']]:
            raise ValueError('Inventory size/hash mismatch')
    return expected


def verify_links(root):
    checked = 0
    for path in [root / 'START_HERE.md', root / 'DELIVERY.md', *sorted((root / 'team2_work').glob('*.md'))]:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if target.startswith(('http:', 'https:', '#')):
                continue
            link = (path.parent / target.split('#', 1)[0]).resolve()
            if not link.is_relative_to(root.resolve()) or not link.is_file():
                raise ValueError('Broken/escaping Markdown link in ' + path.name)
            checked += 1
    return checked


def verify_evidence(root):
    work = root / 'team2_work'
    index = work / 'DELIVERY_EVIDENCE.json'
    paths = json.loads(index.read_text()) if index.exists() else {
        'regression': 'evidence/final-regression-v01/report.json',
        'quality': 'evidence/final-quality-v05/report.json',
        'packaging': 'evidence/packaging-check-v02/report.json',
        'contract': 'evidence/contract-reconciliation-v02/report.json'}
    if set(paths) != {'regression', 'quality', 'packaging', 'contract'}:
        raise ValueError('Invalid delivery evidence index')
    reports = {key: json.loads(safe_file(work, name).read_text()) for key, name in paths.items()}
    regression, quality, packaging, contract = [reports[key] for key in ('regression', 'quality', 'packaging', 'contract')]
    if not all(report['passed'] for report in (regression, quality, packaging, contract)):
        raise ValueError('Required delivered evidence is not passing')
    if not regression['source_unchanged'] or not regression['clean_shutdown']:
        raise ValueError('Regression ownership/source closure failed')
    matched = 0
    for name, value in regression['source_hashes'].items():
        if name.startswith('team2/'):
            path = safe_file(work, name.removeprefix('team2/'))
            if digest(path) != value:
                raise ValueError('Delivered source differs from final regression: ' + name)
            matched += 1
    for name, value in quality['source_hashes'].items():
        if digest(safe_file(work, name)) != value:
            raise ValueError('Delivered source differs from final quality: ' + name)
    for name, value in packaging['source_hashes'].items():
        if digest(safe_file(work, name)) != value:
            raise ValueError('Delivered source differs from packaging tests: ' + name)
    if digest((work / paths['packaging']).parent / 'tests.log') != packaging['log_sha256']:
        raise ValueError('Packaging log does not match report')
    if digest((work / paths['regression']).parent / 'tests.log') != regression['log_sha256']:
        raise ValueError('Regression log does not match report')
    for check in quality['checks']:
        if digest((work / paths['quality']).parent / (check['check'] + '.log')) != check['log_sha256']:
            raise ValueError('Quality log does not match report')
    for key, name in [('spec_sha256', 'candidate-openapi-v1.json'), ('examples_sha256', 'candidate-examples.json')]:
        if digest(work / ('contract-drop-v02/' + name)) != contract[key]:
            raise ValueError('Frozen contract content differs from evidence')
    if digest(work / 'candidate_service.py') != contract['service_sha256']:
        raise ValueError('Contract tested against different service source')
    return matched


def metadata_checks(root, source):
    work = root / 'team2_work'
    python = source / 'runtime/python/python.exe'
    if (source / 'SSD_PACKAGE_ID.txt').read_text().strip() != '2ccf20b727ac4588a7f3ac39ba68b9ca':
        raise ValueError('Wrong baseline lineage')
    commands = [[str(python), '-B', str(work / name), '--help'] for name in
                ('combined_runtime.py', 'run_candidate_service.py', 'verify_delivery.py', 'package_delivery.py')]
    commands += [[str(source / 'runtime/node/node.exe'), '--check', str(work / 'assembly/ssd_web_server.cjs')]]
    for command in commands:
        run = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise ValueError('Delivered metadata/syntax check failed: ' + Path(command[-2]).name)
    for path in work.glob('*.py'):
        compile(path.read_bytes(), str(path), 'exec')
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('receiver_candidate', work / 'candidate_service.py')
    if spec is None or spec.loader is None:
        raise ValueError('Cannot load delivered service models')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    examples = json.loads((work / 'contract-drop-v02/candidate-examples.json').read_text())
    module.Capabilities.model_validate(examples['capabilities'])
    for pair in examples['examples']:
        module.CandidateRequest.model_validate(pair['request'])
        module.CandidateResult.model_validate(pair['response'])
    for name in ('START_TEAM2.cmd', 'STOP_TEAM2.cmd'):
        text = (work / name).read_text()
        if '%~dp0combined_runtime.py' not in text or 'runtime\\python\\python.exe' not in text:
            raise ValueError('Delivered CMD does not reference actual relative entry point')
    return len(commands)


def verify(root, source):
    expected = verify_files(root)
    links = verify_links(root)
    matched = verify_evidence(root)
    metadata = metadata_checks(root, source)
    return {'passed': True, 'checked_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
        'delivery': str(root.resolve()), 'verified_checksums': len(expected),
        'files_including_checksum': len(expected) + 1, 'markdown_links': links,
        'final_regression_source_matches': matched, 'metadata_commands': metadata,
        'services_started': False, 'database_changed': False, 'browser_rendering_tested': False,
        'checksum_file_sha256': digest(root / 'CHECKSUMS.sha256')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.package.resolve(), args.source.resolve()), indent=2))


if __name__ == '__main__':
    main()
