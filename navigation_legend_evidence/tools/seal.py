"""Inventory/seal the UI-only V05 update and independently check every hash."""
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'navigation_legend_evidence'


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    assert ROOT.name == 'UKAI_COMBINED_V05'
    assert json.loads((OUT / 'PRESERVATION.json').read_text())['passed']
    assert json.loads((OUT / 'BROWSER_CHECKS.json').read_text())['passed']
    report = json.loads((OUT / 'final/report.json').read_text())
    assert report['passed'] and all(sha(ROOT / p) == digest for p, digest in report['source_hashes'].items())
    assert '294 passed | 8 skipped (302)' in (OUT / 'final/test.log').read_text(encoding='utf-8')
    assert not (OUT / '_temporary').exists()
    ignored = {'__pycache__', '.vite', '.pytest_cache'}
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name != 'SSD_CHECKSUMS.sha256'
                   and p != ROOT / 'FILE_INVENTORY.csv' and not ignored.intersection(p.parts))
    with (ROOT / 'FILE_INVENTORY.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['relative_path', 'bytes', 'sha256'])
        with ThreadPoolExecutor(max_workers=8) as pool:
            for i, (p, digest) in enumerate(zip(files, pool.map(sha, files)), 1):
                writer.writerow([p.relative_to(ROOT).as_posix(), p.stat().st_size, digest])
                if i % 3000 == 0:
                    print(f'Inventory: {i} verified', flush=True)
    subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/seal_ssd_copy.py'),
                    '--root', str(ROOT)], check=True)
    entries = [line.split('  ', 1) for line in (ROOT / 'SSD_CHECKSUMS.sha256').read_text().splitlines()]

    def check(entry):
        digest, relative = entry
        assert sha(ROOT / relative) == digest, 'Delivery mismatch: ' + relative

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(check, entries))
    assert len(entries) == len(files) + 1
    print(json.dumps({'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
        'sealed_files': len(entries), 'checksum_mismatches': 0,
        'manifest_sha256': sha(ROOT / 'SSD_CHECKSUMS.sha256'),
        'frontend_tests_passed': 294, 'live_job_tests_not_repeated': 8,
        'active_user_services_not_stopped': True, 'terrain_contours_not_implemented': True}, indent=2), flush=True)


if __name__ == '__main__':
    main()
