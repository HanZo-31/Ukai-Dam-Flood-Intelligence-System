"""Record the terrain generator regression tests and correctness lint inside V05."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    out = ROOT / 'simulation_polish_evidence/terrain-checks'
    out.mkdir(exist_ok=False)
    commands = [
        ('terrain-unit-tests', [sys.executable, '-B', '-m', 'unittest', 'tests/test_local_terrain.py']),
        ('terrain-lint', [str(ROOT / 'runtime/quality/python.exe'), '-B', '-m', 'ruff', 'check', '--no-cache',
                          '--select', 'E4,E9,F', 'scripts/build_local_terrain.py', 'tests/test_local_terrain.py',
                          'simulation_polish_evidence/tools/verify_terrain.py', 'simulation_polish_evidence/tools/terrain_checks.py']),
    ]
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True, 'commands': []}
    for name, command in commands:
        with (out / (name + '.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        report['commands'].append({'name': name, 'command': command, 'exit_code': result.returncode})
        report['passed'] &= result.returncode == 0
        print((out / (name + '.log')).read_text(), flush=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
