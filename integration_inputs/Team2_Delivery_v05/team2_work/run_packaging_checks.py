"""Record only new packaging-specific tests; do not rerun the unchanged broad suite."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_delivery import digest  # noqa: E402 -- bundled Python local bootstrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh evidence directory required')
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent
    names = ('package_delivery.py', 'verify_delivery.py', 'test_delivery.py', 'run_packaging_checks.py')
    hashes = {name: digest(root / name) for name in names}
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(), 'source_hashes': hashes}
    command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
               '--basetemp', str((args.output / 'test-temp').resolve()), str(root / 'test_delivery.py')]
    run = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=60)
    log = args.output / 'tests.log'
    log.write_text(run.stdout + run.stderr, encoding='utf-8')
    unchanged = hashes == {name: digest(root / name) for name in names}
    report.update(exit_code=run.returncode, log_sha256=digest(log), source_unchanged=unchanged,
                  passed=run.returncode == 0 and unchanged,
                  finished_at=datetime.now(ZoneInfo('Asia/Calcutta')).isoformat())
    (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(run.stdout + run.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
