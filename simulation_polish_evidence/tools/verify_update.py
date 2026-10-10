"""Read-only guard for V05 Simulation naming and presentation changes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'simulation_polish_evidence'


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    scope = json.loads((OUT / 'CHANGE_SCOPE.json').read_text())
    renames = scope['renames']
    allowed = set(scope['approved_existing_changes'])
    entries = [line.split('  ', 1) for line in (OUT / 'BEFORE_CHANGE_CHECKSUMS.sha256').read_text().splitlines()]

    def check(entry):
        expected, original = entry
        current = renames.get(original, original)
        path = ROOT / current
        different = not path.is_file() or digest(path) != expected
        editable = current in allowed or current.startswith('frontend/dist/')
        return original, current, different, editable

    violations, changed, unchanged = [], [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for original, current, different, editable in pool.map(check, entries):
            if different:
                changed.append(current)
                if not editable:
                    violations.append({'original': original, 'current': current})
            elif not editable:
                unchanged += 1
    assert not violations, violations
    for original, current in renames.items():
        assert not (ROOT / original).exists(), original
        assert (ROOT / current).is_file(), current
    assert (ROOT / 'SIMULATION_PACKAGE_ID.txt').read_text().strip() == '7e9432a8165f49da89b093fde5845c61'
    runtime = (ROOT / 'scripts/simulation_runtime.py').read_text()
    for value in scope['preserved_internal_identifiers']:
        assert value in runtime, value
    combined = (ROOT / 'team2_work/combined_runtime.py').read_text()
    assert "'Ukai SSD'" in combined
    assert 'SIMULATION_PACKAGE_ID.txt' in combined
    assert 'SIMULATION_CHECKSUMS.sha256' in combined
    assert 'simulation_runtime.py' in combined
    assert 'assembly/simulation_web_server.cjs' in combined
    for path in [ROOT / 'scripts', ROOT / 'tests', ROOT / 'team2_work']:
        for source in path.glob('*.py'):
            # Syntax validation without generating bytecode or invoking programs.
            compile(source.read_text(encoding='utf-8-sig'), str(source), 'exec')
    for source in ROOT.glob('*.cmd'):
        text = source.read_text()
        assert not re.search(r'(?:START|STOP|CHECK)_SSD|scripts\\(?:ssd_runtime|seal_ssd_copy)', text), source
    css = (ROOT / 'frontend/src/simulation-polish.css').read_text()
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    assert not re.search(r'\.(?:map[\w-]*|ol-[\w-]*|legend[\w-]*|timeline[\w-]*)\b|url\(|@import', css)
    assert 'prefers-reduced-motion' in css
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
              'before_entries': len(entries), 'protected_files_unchanged': unchanged,
              'protected_mismatches': violations, 'approved_existing_changes': changed,
              'active_renames_checked': len(renames), 'package_identity_preserved': True,
              'original_map_data_clock_layers_backend_solver_bytes_unchanged': True,
              'historical_evidence_and_package_report_preserved': True,
              'database_and_profile_identifiers_preserved': True}
    (OUT / 'PRESERVATION.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
