"""Targeted naming/startup unit checks. No imports, approval or model jobs."""
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'simulation_polish_evidence'


def main():
    output = OUT / (sys.argv[1] if len(sys.argv) > 1 else 'backend-checks')
    output.mkdir(exist_ok=False)
    temp = OUT / '_temporary'
    temp.mkdir(exist_ok=True)
    # Ownership tests require source and mutable test state to be disjoint.
    # A tiny, non-executable source fixture keeps both inside V05 without
    # weakening the production prohibition on writing into the app folder.
    fixture = temp / 'reference-fixture'
    fixture.mkdir(exist_ok=True)
    (fixture / 'SIMULATION_PACKAGE_ID.txt').write_bytes((ROOT / 'SIMULATION_PACKAGE_ID.txt').read_bytes())
    control = fixture / 'runtime/pgsql/bin/pg_ctl.exe'
    control.parent.mkdir(parents=True, exist_ok=True)
    control.write_bytes(b'Unit-test existence fixture only; not an executable.')
    for relative in ['part_a', 'receipts/h01', 'receipts/h03', 'receipts/2006']:
        destination = fixture / relative
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'prototype-manifest.json').write_bytes((ROOT / relative / 'prototype-manifest.json').read_bytes())
    env = os.environ | {'TEMP': str(temp), 'TMP': str(temp),
        'PYTHONDONTWRITEBYTECODE': '1', 'UKAI_REFERENCE_ROOT': str(fixture)}
    commands = [
        ('startup-unit-tests', [sys.executable, '-B', '-m', 'pytest', 'tests/test_simulation_runtime.py',
            'team2_work/test_combined_runtime.py', '-q', '--basetemp', str(temp / 'pytest'),
            '-o', 'cache_dir=' + str(temp / 'pytest-cache')]),
        ('syntax-baseline-proxy', [str(ROOT / 'runtime/node/node.exe'), '--check', 'scripts/simulation_web_server.cjs']),
        ('syntax-combined-proxy', [str(ROOT / 'runtime/node/node.exe'), '--check', 'team2_work/assembly/simulation_web_server.cjs']),
        ('syntax-browser-helper', [str(ROOT / 'runtime/node/node.exe'), '--check', 'scripts/check_simulation_browser.cjs']),
        ('python-lint', [str(ROOT / 'runtime/quality/python.exe'), '-B', '-m', 'ruff', 'check', '--no-cache',
            '--select', 'E4,E9,F', 'scripts/simulation_runtime.py', 'scripts/seal_simulation_copy.py',
            'scripts/build_simulation_copy.py', 'team2_work/combined_runtime.py',
            'simulation_polish_evidence/tools']),
    ]
    report = {'started_at': datetime.now().astimezone().isoformat(), 'passed': True, 'commands': []}
    for task, command in commands:
        with (output / (task + '.log')).open('w', encoding='utf-8') as handle:
            run = subprocess.run(command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, timeout=180)
        report['commands'].append({'task': task, 'exit_code': run.returncode})
        print(task + ': ' + str(run.returncode), flush=True)
        print((output / (task + '.log')).read_text(encoding='utf-8', errors='replace'), flush=True)
        if run.returncode:
            report['passed'] = False
    report['finished_at'] = datetime.now().astimezone().isoformat()
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
