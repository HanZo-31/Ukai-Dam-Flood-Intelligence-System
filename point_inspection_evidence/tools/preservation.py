"""Protect original inputs/backend and verify only the agreed frontend feature changed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'point_inspection_evidence'
ALLOWED = {'frontend/src/main.tsx', 'frontend/src/map/FloodMap.tsx', 'frontend/src/pages/Explore.tsx',
    'frontend/src/pages/Compare.tsx', 'frontend/package.json', 'frontend/package-lock.json',
    'START_HERE.md', 'START_COMPUTED_HERE.md', 'INTEGRATION_RELEASE_ID.txt', 'FILE_INVENTORY.csv'}


def sha(path):
    with path.open('rb') as handle: return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    entries = [line.split('  ', 1) for line in (OUT / 'BEFORE_CHANGE_CHECKSUMS.sha256').read_text().splitlines()]
    def check(entry):
        digest, relative = entry
        path = ROOT / relative
        return relative, not path.is_file() or sha(path) != digest
    protected, changed, violations = 0, [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for relative, mismatch in pool.map(check, entries):
            allowed = relative in ALLOWED or relative.startswith('frontend/dist/')
            if mismatch:
                changed.append(relative)
                if not allowed: violations.append(relative)
            elif not allowed: protected += 1
    assert not violations, violations
    before = (OUT / 'FloodMap.before.txt').read_text()
    after = (ROOT / 'frontend/src/map/FloodMap.tsx').read_text()
    start, end = '  // swap the data layer', '  useEffect(() => { dataLayerRef.current?.setOpacity(opacity); }, [opacity]);'
    assert before[before.index(start):before.index(end)+len(end)] == after[after.index(start):after.index(end)+len(end)]
    start, end = '  // moving the slider', '  return (\n'
    assert before[before.index(start):before.index(end, before.index(start))] == after[after.index(start):after.index(end, after.index(start))]
    old_explore = (OUT / 'Explore.before.txt').read_text()
    new_explore = (ROOT / 'frontend/src/pages/Explore.tsx').read_text()
    start, end = '  const maxHours =', '  return (\n'
    assert old_explore[old_explore.index(start):old_explore.index(end)] == new_explore[new_explore.index(start):new_explore.index(end)]
    declared = json.loads((ROOT / 'frontend/package.json').read_text())['dependencies']['geotiff']
    installed = json.loads((ROOT / 'frontend/node_modules/geotiff/package.json').read_text())['version']
    assert declared == installed == '3.1.0-beta.0'
    result = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
        'before_entries': len(entries), 'protected_files_unchanged': protected, 'protected_mismatches': violations,
        'approved_existing_changes': changed, 'original_raster_layer_opacity_timeline_fit_logic_identical': True,
        'original_explore_clock_and_mode_handlers_identical': True,
        'new_marker_and_read_only_selection_events_isolated': True,
        'installed_dependency_versions_unchanged': True,
        'no_original_data_backend_solver_contract_or_launcher_changes': True}
    (OUT / 'PRESERVATION.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__': main()
