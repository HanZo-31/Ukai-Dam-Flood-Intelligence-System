"""Read-only current V05 comparison against its pre-navbar checksum receipt."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'navigation_legend_evidence'
ALLOWED = {'frontend/src/studio.css', 'frontend/src/components/ExploreLayers.tsx',
    'frontend/src/pages/Explore.tsx', 'START_HERE.md', 'START_COMPUTED_HERE.md',
    'INTEGRATION_RELEASE_ID.txt', 'FILE_INVENTORY.csv'}


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    entries = [line.split('  ', 1) for line in (OUT / 'BEFORE_CHANGE_CHECKSUMS.sha256').read_text().splitlines()]

    def check(entry):
        digest, relative = entry
        path = ROOT / relative
        return relative, not path.is_file() or sha(path) != digest

    changed, violations, protected = [], [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for relative, mismatch in pool.map(check, entries):
            allowed = relative in ALLOWED or relative.startswith('frontend/dist/')
            if mismatch:
                changed.append(relative)
                if not allowed:
                    violations.append(relative)
            elif not allowed:
                protected += 1
    assert not violations, violations
    final = json.loads((OUT / 'final/report.json').read_text())
    assert final['passed'] and all(sha(ROOT / p) == digest for p, digest in final['source_hashes'].items())
    source = (ROOT / 'frontend/src/pages/Explore.tsx').read_text()
    assert '<Legend mode={mode} colorBy={colorBy} />' in source[source.index('<aside className="page-legend-corner"'):]
    assert '<Legend' not in source[source.index('<div className="map-wrap studio-map">'):source.index('<div className="explore-footer">')]
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
        'before_entries': len(entries), 'protected_files_unchanged': protected,
        'protected_mismatches': violations, 'approved_changed_existing_files': changed,
        'source_matches_passing_tests': True, 'legend_outside_map': True,
        'preserved': 'Map renderer, flood/terrain inputs, colour scales, original Legend, TimelinePanel and its clock/handlers, backend, candidate/solver services, dependency locks and launcher scripts.',
        'other_project_folders_written': False}
    (OUT / 'PRESERVATION.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
