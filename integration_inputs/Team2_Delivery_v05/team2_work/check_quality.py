"""Local Team2 correctness/type/OpenAPI gate with hashes; no dependency installation."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo


def sources(root):
    files = [*root.glob('*.py'), root / 'assembly/ssd_web_server.cjs', root / 'quality-ruff.toml', root / 'quality-mypy.ini']
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh quality evidence directory required')
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent
    frozen = sources(root)
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
              'source_hashes': frozen, 'passed': False, 'checks': [], 'dependencies_installed': False}
    quality = args.source / 'runtime/quality/python.exe'
    runtime = args.source / 'runtime/python/python.exe'
    commands = [
        ('dependency-consistency', [str(runtime), '-B', '-m', 'pip', 'check']),
        ('correctness-lint', [str(quality), '-B', '-m', 'ruff', 'check', '--no-cache',
            '--config', str(root / 'quality-ruff.toml'), *[str(root / name) for name in sorted(frozen) if name.endswith('.py')]]),
        ('gradual-types', [str(quality), '-B', '-m', 'mypy', '--config-file', str(root / 'quality-mypy.ini'),
            '--python-executable', str(runtime), '--cache-dir', str(args.output / 'mypy-cache'),
            *[str(root / name) for name in ('candidate_service.py', 'combined_runtime.py', 'run_candidate_service.py')]]),
        ('proxy-syntax', [str(args.source / 'runtime/node/node.exe'), '--check', str(root / 'assembly/ssd_web_server.cjs')]),
        ('openapi-conformance', [str(runtime), '-B', '-m', 'openapi_spec_validator', str(root / 'contract-drop-v02/candidate-openapi-v1.json')]),
    ]
    try:
        for name, command in commands:
            run = subprocess.run(command, capture_output=True, text=True, timeout=90)
            log = args.output / (name + '.log')
            log.write_text(run.stdout + run.stderr, encoding='utf-8')
            report['checks'].append({'check': name, 'exit_code': run.returncode, 'passed': run.returncode == 0,
                                    'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
            print(name + ': ' + (run.stdout.strip() or run.stderr.strip()), flush=True)
            if run.returncode:
                return 1
        report['passed'] = True
    finally:
        report['source_unchanged'] = frozen == sources(root)
        report['passed'] = report['passed'] and report['source_unchanged']
        report['finished_at'] = datetime.now(ZoneInfo('Asia/Calcutta')).isoformat()
        (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
