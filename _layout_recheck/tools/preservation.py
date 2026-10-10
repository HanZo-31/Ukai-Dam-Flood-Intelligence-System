"""Read-only check: only requested V05 presentation/doc/rebuild changes are allowed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '_layout_recheck/baseline-source'
OUT = ROOT / 'layout_cleanup_evidence'
ALLOWED = {'frontend/src/studio.css', 'frontend/src/components/ExploreLayers.tsx',
    'frontend/src/components/ExploreTimeline.tsx', 'frontend/src/components/TimelinePanel.tsx',
    'START_HERE.md', 'START_COMPUTED_HERE.md', 'STUDIO_FRONTEND_STATUS.md',
    'INTEGRATION_RELEASE_ID.txt', 'FILE_INVENTORY.csv'}


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    entries = [line.split('  ', 1) for line in (BASE / 'SSD_CHECKSUMS.sha256').read_text().splitlines()]

    def check(entry):
        digest, relative = entry
        assert sha(BASE / relative) == digest, 'Test baseline changed: ' + relative
        path = ROOT / relative
        return relative, not path.is_file() or sha(path) != digest

    changed, protected, violations = [], 0, []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for relative, different in pool.map(check, entries):
            allowed = relative in ALLOWED or relative.startswith('frontend/dist/')
            if different:
                changed.append(relative)
                if not allowed:
                    violations.append(relative)
            elif not allowed:
                protected += 1
    assert not violations, violations
    old = (BASE / 'frontend/src/components/TimelinePanel.tsx').read_text()
    new = (ROOT / 'frontend/src/components/TimelinePanel.tsx').read_text()
    start = old.index('const STEP_MS')
    old_clock = old[start:old.index('  return (\n', start)]
    new_clock = new[new.index('const STEP_MS'):new.index('  const explanation =')]
    assert old_clock == new_clock, 'Timeline effect/state/availability logic changed'
    handlers = ['onClick={() => onPlaying(!playing)}', 'onClick={p.onReset}',
        'onChange={(e) => { onPlaying(false); onHours(Number(e.target.value)); }}',
        'onChange={(e) => p.onColorBy(e.target.value as TimelineColorBy)}']
    assert all(handler in old and handler in new for handler in handlers)
    tests = json.loads((OUT / 'final/report.json').read_text())
    assert tests['passed'] and all(sha(ROOT / key) == value for key, value in tests['source_hashes'].items())
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
        'original_v05_entries': len(entries), 'protected_files_unchanged': protected,
        'protected_mismatches': violations, 'changed_existing_files': changed,
        'timeline_timer_state_availability_and_handlers_identical': True,
        'final_source_matches_passing_tests': True,
        'scope': 'Map renderer, palettes, original styles, scientific data, Explore state/map props, backend, solver, routes/integrations, dependency locks and startup scripts unchanged.',
        'layout_geometry_not_pixel_identical': True}
    (OUT / 'PRESERVATION.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
