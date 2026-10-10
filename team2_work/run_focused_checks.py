"""Capture current Team2 tests with source hashes, exit status and retained logs."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo


def sources(root):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.glob('*.py'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('New evidence directory required')
    root = Path(__file__).resolve().parent
    args.output.mkdir(parents=True)
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(), 'source_hashes': sources(root)}
    tests = [root / 'test_candidate_service.py']
    if (root / 'test_combined_runtime.py').is_file():
        tests.append(root / 'test_combined_runtime.py')
    command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--basetemp', str((args.output / 'test-temp').resolve()), *map(str, tests)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=60)
    log = args.output / 'tests.log'
    log.write_text(run.stdout + run.stderr, encoding='utf-8')
    report.update(command=['bundled Python3.12.4', *command[1:]], exit_code=run.returncode,
        source_unchanged=sources(root) == report['source_hashes'],
        finished_at=datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
        log_checksum=hashlib.sha256(log.read_bytes()).hexdigest(),
        passed=run.returncode == 0 and sources(root) == report['source_hashes'])
    (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(run.stdout)
    print(json.dumps({key: report[key] for key in ('exit_code', 'source_unchanged', 'passed')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
