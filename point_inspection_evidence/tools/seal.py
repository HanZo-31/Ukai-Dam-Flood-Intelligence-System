"""Seal the current V05 files without bypassing the startup copy-integrity gate."""
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open('rb') as handle: return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    ignored = {'__pycache__', '.vite', '.pytest_cache'}
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name != 'SSD_CHECKSUMS.sha256'
                   and p != ROOT / 'FILE_INVENTORY.csv' and not ignored.intersection(p.parts))
    with (ROOT / 'FILE_INVENTORY.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle); writer.writerow(['relative_path', 'bytes', 'sha256'])
        with ThreadPoolExecutor(max_workers=8) as pool:
            for i, (p, digest) in enumerate(zip(files, pool.map(sha, files)), 1):
                writer.writerow([p.relative_to(ROOT).as_posix(), p.stat().st_size, digest])
                if i % 3000 == 0: print(f'Inventory: {i}', flush=True)
    subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/seal_ssd_copy.py'), '--root', str(ROOT)], check=True)
    entries = [line.split('  ', 1) for line in (ROOT / 'SSD_CHECKSUMS.sha256').read_text().splitlines()]
    def check(entry):
        digest, relative = entry
        assert sha(ROOT / relative) == digest, relative
    with ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(check, entries))
    assert len(entries) == len(files) + 1
    print(json.dumps({'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
        'sealed_entries': len(entries), 'checksum_mismatches': 0,
        'manifest_sha256': sha(ROOT / 'SSD_CHECKSUMS.sha256')}, indent=2), flush=True)


if __name__ == '__main__': main()
