"""Compare the pre-terrain package; only the requested display changes may differ."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWED = {'frontend/src/map/FloodMap.tsx', 'frontend/src/pages/Explore.tsx', 'FILE_INVENTORY.csv'}


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    entries = [line.split('  ', 1) for line in (ROOT / 'simulation_polish_evidence/BEFORE_TERRAIN_CHECKSUMS.sha256').read_text().splitlines()]
    def check(entry):
        expected, name = entry
        allowed = name in ALLOWED or name.startswith('frontend/dist/')
        path = ROOT / name
        return name, allowed, path.is_file() and sha(path) == expected
    changed, violations, protected = [], [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, allowed, unchanged in pool.map(check, entries):
            if not unchanged:
                changed.append(name)
                if not allowed:
                    violations.append(name)
            elif not allowed:
                protected += 1
    assert not violations, violations
    old = (ROOT / 'simulation_polish_evidence/FloodMap.before-terrain.txt').read_text()
    new = (ROOT / 'frontend/src/map/FloodMap.tsx').read_text()
    start, end = '  // swap the data layer', '  return ('
    assert old.split(start)[1].split(end)[0] == new.split(start)[1].split(end)[0]
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
              'protected_original_files_unchanged': protected, 'unauthorized_changes': violations,
              'approved_changed_existing_files': changed,
              'flood_swap_opacity_point_marker_timeline_and_fit_code_identical': True,
              'original_terrain_flood_rasters_solver_api_database_code_and_config_unchanged': True}
    (ROOT / 'simulation_polish_evidence/TERRAIN_PRESERVATION.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
