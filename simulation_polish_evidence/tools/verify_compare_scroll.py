"""Verify the narrow Compare-only CSS fix against its sealed baseline."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    entries = [line.split('  ', 1) for line in (ROOT / 'simulation_polish_evidence/BEFORE_COMPARE_SCROLL_CHECKSUMS.sha256').read_text().splitlines()]
    allowed = {'frontend/src/pages/Compare.tsx', 'FILE_INVENTORY.csv'}
    def check(entry):
        digest, name = entry
        permitted = name in allowed or name.startswith('frontend/dist/')
        path = ROOT / name
        return name, permitted, path.is_file() and sha(path) == digest
    changed, violations, protected = [], [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, permitted, unchanged in pool.map(check, entries):
            if not unchanged:
                changed.append(name)
                if not permitted:
                    violations.append(name)
            elif not permitted:
                protected += 1
    assert not violations, violations
    expected = dict((name, digest) for digest, name in entries)['frontend/src/pages/Compare.tsx']
    source = (ROOT / 'frontend/src/pages/Compare.tsx').read_bytes()
    added = b'import "../compare-scroll.css";'
    assert source.count(added) == 1
    # Preserve inherited mixed line endings; read_text would normalize them.
    originals = [source.replace(added + ending, b'', 1) for ending in (b'\n', b'\r\n')]
    assert expected in {hashlib.sha256(text).hexdigest() for text in originals}, 'Compare logic changed beyond the stylesheet import'
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
              'protected_original_files_unchanged': protected, 'unauthorized_changes': violations,
              'approved_changed_existing_files': changed, 'compare_implementation_unchanged_except_css_import': True,
              'map_terrain_timing_solver_backend_and_data_files_unchanged': True}
    (ROOT / 'simulation_polish_evidence/COMPARE_SCROLL_PRESERVATION.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
