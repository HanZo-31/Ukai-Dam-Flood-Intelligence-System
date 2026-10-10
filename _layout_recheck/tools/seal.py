"""Refresh V05 delivery inventory, seal and independently verify; no external writes."""
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'layout_cleanup_evidence'


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    assert ROOT.name == 'UKAI_COMBINED_V05'
    assert json.loads((OUT / 'PRESERVATION.json').read_text())['passed']
    assert json.loads((OUT / 'BROWSER_CHECKS.json').read_text())['passed']
    assert json.loads((OUT / 'RUNTIME_STOPPED.json').read_text())['all_owned_children_exited']
    tests = json.loads((OUT / 'final/report.json').read_text())
    assert tests['passed'] and all(sha(ROOT / key) == value for key, value in tests['source_hashes'].items())
    assert '296 passed (296)' in (OUT / 'final/test.log').read_text(encoding='utf-8')
    assert not any((ROOT / '_layout_recheck' / name).exists()
        for name in ['baseline-source', 'private-runtime', 'npm-cache', 'temp'])
    ignored = {'__pycache__', '.vite', '.pytest_cache'}
    files = sorted(path for path in ROOT.rglob('*') if path.is_file() and
                   path.name != 'SSD_CHECKSUMS.sha256' and path != ROOT / 'FILE_INVENTORY.csv'
                   and not ignored.intersection(path.parts))
    with (ROOT / 'FILE_INVENTORY.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['relative_path', 'bytes', 'sha256'])
        with ThreadPoolExecutor(max_workers=8) as pool:
            for i, (path, digest) in enumerate(zip(files, pool.map(sha, files)), 1):
                writer.writerow([path.relative_to(ROOT).as_posix(), path.stat().st_size, digest])
                if i % 3000 == 0:
                    print(f'Inventory: {i} verified', flush=True)
    subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/seal_ssd_copy.py'),
                    '--root', str(ROOT)], check=True)
    entries = [line.split('  ', 1) for line in (ROOT / 'SSD_CHECKSUMS.sha256').read_text().splitlines()]

    def checked(entry):
        digest, relative = entry
        assert sha(ROOT / relative) == digest, 'Final delivery mismatch: ' + relative

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(checked, entries))
    assert len(entries) == len(files) + 1
    # Print rather than write a post-seal report: no checksum/report self-cycle.
    print(json.dumps({'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
        'project': str(ROOT), 'release': (ROOT / 'INTEGRATION_RELEASE_ID.txt').read_text().strip(),
        'sealed_files': len(entries), 'checksum_mismatches': 0,
        'manifest_sha256': sha(ROOT / 'SSD_CHECKSUMS.sha256'), 'frontend_tests': 296,
        'other_project_folders_modified': False, 'private_test_profile_removed': True}, indent=2), flush=True)


if __name__ == '__main__':
    main()
