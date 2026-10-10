"""Repeatable local B2 correctness lint/type gate, independent of Git/CI."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
APPLICATION = [
    'services/api/app/api', 'services/api/app/api_schemas', 'services/api/app/services',
    *['services/api/app/' + name + '.py' for name in (
        'main', 'openapi', 'settings', 'security', 'readiness', 'runtime_inventory', 'container_runtime',
        'prototype_context', 'prototype_settings', 'prototype_runtime', 'receiving', 'receiving_db', 'receiving_http')],
    'services/api/app/repositories/prototype_repository.py',
]
SCRIPTS = ['scripts/' + name + '.py' for name in (
    'b2_container_fixture', 'b2_large_asset_probe', 'b2_performance_fixture', 'b2_performance_probe',
    'b2_receiving_probe', 'check_b2_quality', 'check_b2_vulnerability_gate', 'export_b2_openapi',
    'package_b2_handoff', 'rehearse_b2_container', 'rehearse_b2_receiving', 'verify_b2_handoff_source',
    'check_prototype_metadata', 'export_prototype_context_schema', 'receive_part_a', 'run_prototype_preview')]
NEW_TESTS = ['tests/test_prototype_contracts.py', 'tests/test_receiving_runner.py']
CONFIGS = ['services/api/ruff.toml', 'services/api/mypy.ini', 'services/api/requirements-quality.txt']


def sources():
    files = set()
    for name in [*APPLICATION, 'services/api/tests', *NEW_TESTS, *SCRIPTS, *CONFIGS]:
        path = ROOT / name
        files.update(path.rglob('*.py') if path.is_dir() else [path])
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files) if '__pycache__' not in p.parts}


def check(quality_python, runtime_python, output, *, cache_dir=None):
    quality_python, runtime_python = Path(quality_python).resolve(), Path(runtime_python).resolve()
    output = Path(output).resolve()
    if output.exists() or sys.version_info[:2] not in {(3, 12), (3, 13)}:
        raise ValueError('Choose a new report path and Python 3.12/3.13.')
    if not quality_python.is_file() or not runtime_python.is_file():
        raise ValueError('Quality and verified runtime interpreters are required.')
    frozen = sources()
    report = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'result': 'failed',
              'scope': 'B2 correctness lint including tests/CLIs; gradual application typing, local Python 3.12/3.13 runtime',
              'source_hashes': frozen, 'checks': [], 'git_or_ci_used': False,
              'strict_typing_or_all_rules_claimed': False}
    try:
        runtime = subprocess.run([str(runtime_python), '--version'], cwd=ROOT,
                                 capture_output=True, text=True, timeout=30)
        parts = runtime.stdout.strip().split()
        if runtime.returncode or len(parts) != 2 or parts[0] != 'Python' or not parts[1].startswith(('3.12.', '3.13.')):
            raise ValueError('Verified runtime must use Python 3.12 or 3.13.')
        report['runtime_python'] = parts[1]
        for module, expected in [('ruff', '0.16.10'), ('mypy', '2.4.0')]:
            version = subprocess.run([str(quality_python), '-m', module, '--version'],
                                     cwd=ROOT, capture_output=True, text=True, timeout=30)
            if version.returncode or expected not in version.stdout.split():
                raise ValueError('Pinned quality tool version required.')
        commands = [
            ('correctness lint', ['ruff', 'check', '--config', 'services/api/ruff.toml', '--no-cache',
                                  *APPLICATION, 'services/api/tests', *NEW_TESTS, *SCRIPTS]),
            ('gradual application type check', ['mypy', '--config-file', 'services/api/mypy.ini',
                 '--python-executable', str(runtime_python),
                 '--cache-dir', str(cache_dir or output.parent / 'mypy-cache'), *APPLICATION,
                 *SCRIPTS[-4:], *NEW_TESTS, 'services/api/tests/test_prototype_preview.py']),
        ]
        for label, args in commands:
            print('Checking: ' + label, flush=True)
            run = subprocess.run([str(quality_python), '-m', *args], cwd=ROOT,
                                 capture_output=True, text=True, timeout=180)
            summary = (run.stdout.strip().splitlines()[-1:] or ['No stdout summary'])[0]
            report['checks'].append({'check': label, 'passed': run.returncode == 0, 'summary': summary})
            print(summary, flush=True)
            if run.returncode:
                print(run.stdout, flush=True)
                raise ValueError('Quality gate failed; no source changed by checker.')
        report['result'] = 'passed'
    finally:
        report['source_unchanged_during_checks'] = frozen == sources()
        if not report['source_unchanged_during_checks']:
            report['result'] = 'failed'
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if report['result'] != 'passed':
        raise ValueError('Quality source changed during checks.')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quality-python', type=Path, required=True)
    parser.add_argument('--runtime-python', type=Path, default=Path(sys.executable))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache-dir', type=Path)
    args = parser.parse_args()
    check(args.quality_python, args.runtime_python, args.output, cache_dir=args.cache_dir)
