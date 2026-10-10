"""Run baseline+Team2 regression on retained owned state, then stop all owned services."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from combined_runtime import Config, get_json, load_owner


def frozen_sources(root, baseline):
    files = [*root.glob('*.py'), root / 'assembly/ssd_web_server.cjs', root / 'quality-ruff.toml', root / 'quality-mypy.ini']
    for folder in ('services', 'tests', 'scripts', 'database'):
        files.extend(path for path in (baseline / folder).rglob('*') if path.is_file() and '__pycache__' not in path.parts)
    result = {}
    for path in files:
        key = 'team2/' + path.relative_to(root).as_posix() if path.is_relative_to(root) else 'baseline/' + path.relative_to(baseline).as_posix()
        result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ui-window-seconds', type=int, default=0)
    args = parser.parse_args()
    args.source, args.state, args.output = args.source.resolve(), args.state.resolve(), args.output.resolve()
    if args.output.exists() or not 0 <= args.ui_window_seconds <= 600:
        raise ValueError('Fresh output and bounded UI interval required')
    marker = json.loads((args.state / 'combined-owner.json').read_text())
    ports = marker['ports']
    config = Config(args.source, args.state, ports['database'], ports['api'], ports['web'], ports['candidate'])
    owner = load_owner(config)
    root = Path(__file__).resolve().parent
    args.output.mkdir(parents=True)
    frozen = frozen_sources(root, args.source)
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(), 'passed': False,
              'source_hashes': frozen, 'target_database': owner['database'], 'runtime_exit_code': None,
              'baseline_working_database_used': False}
    flags = ['--source', str(args.source), '--state', str(args.state),
        '--db-port', str(config.db_port), '--api-port', str(config.api_port),
        '--web-port', str(config.web_port), '--candidate-port', str(config.candidate_port)]
    with (args.output / 'runtime.log').open('w', encoding='utf-8') as runtime_log:
        process = subprocess.Popen([sys.executable, '-B', str(root / 'combined_runtime.py'), *flags, '--no-browser'],
                                   stdout=runtime_log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise ValueError('Owned runtime stopped before ready')
                try:
                    status = json.loads((args.state / 'combined-status.json').read_text())
                    if status['status'] == 'ready':
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(0.2)
            else:
                raise ValueError('Warm runtime startup timeout')
            print('Owned combined app ready: http://127.0.0.1:' + str(config.web_port), flush=True)
            before = {(item['scenario_id'], item['run_id']) for item in get_json(config.web_port, '/api/v1/prototypes/scenarios')['items']}
            url = (args.state / 'database-url.txt').read_text().strip()
            password = (args.state / 'db-password.txt').read_text().strip()
            env = os.environ.copy()
            for key in list(env):
                if key.startswith(('B2_', 'PG')) or key in {'DATABASE_URL', 'DATABASE_URL_FILE', 'OBJECT_STORAGE_ROOT'}:
                    env.pop(key, None)
            env.update(DATABASE_URL=url, OBJECT_STORAGE_ROOT=str(args.state / 'objects'),
                TMPDIR=str(args.state / 'scratch'), TMP=str(args.state / 'scratch'), TEMP=str(args.state / 'scratch'),
                UKAI_PG_BIN=str(args.source / 'runtime/pgsql/bin'), UKAI_REFERENCE_ROOT=str(args.source),
                B2_ENV='local', B2_ENABLE_PROTOTYPE_PREVIEW='false', PYTHONDONTWRITEBYTECODE='1')
            tests = [args.source / 'tests', args.source / 'services/api/tests',
                     root / 'test_candidate_service.py', root / 'test_combined_runtime.py']
            command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                       '--basetemp', str(args.output / 'test-temp'), *map(str, tests)]
            print('Running final baseline + Team2 regression on owned target...', flush=True)
            run = subprocess.run(command, cwd=args.source, env=env, capture_output=True, text=True, timeout=900)
            output = (run.stdout + run.stderr).replace(password, '<private-password>')
            output = re.sub(r'postgres(?:ql)?(?:\+[a-z_]+)?://[^\s\"\']+', '<private-database-url>', output)
            log = args.output / 'tests.log'
            log.write_text(output, encoding='utf-8')
            report.update(test_exit_code=run.returncode, command=['bundled Python3.12.4', *command[1:]],
                summary=(re.findall(r'\d+ passed[^\r\n]*', output) or ['No passing summary'])[ -1],
                log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
            print(report['summary'], flush=True)
            if run.returncode:
                raise ValueError('Final regression failed; inspect retained tests.log')
            after = {(item['scenario_id'], item['run_id']) for item in get_json(config.web_port, '/api/v1/prototypes/scenarios')['items']}
            report['actual_reference_catalog_unchanged'] = before == after and len(after) == 4
            if args.ui_window_seconds:
                print('Keeping owned app available briefly for UI verification...', flush=True)
                deadline = time.monotonic() + args.ui_window_seconds
                while time.monotonic() < deadline and not (args.output / 'finish-ui.request').exists():
                    time.sleep(0.2)
            report['passed'] = report['actual_reference_catalog_unchanged']
        except Exception as error:
            report['failure_type'] = type(error).__name__
            report['reason'] = str(error) if isinstance(error, ValueError) else 'Execution failed; private details suppressed'
        finally:
            if process.poll() is None:
                stopped = subprocess.run([sys.executable, '-B', str(root / 'combined_runtime.py'), *flags, '--stop'],
                                         capture_output=True, text=True, timeout=10)
                report['stop_command_exit_code'] = stopped.returncode
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=10)
                    report['passed'] = False
                    report['forced_cleanup'] = True
            report['runtime_exit_code'] = process.returncode
            report['clean_shutdown'] = process.returncode == 0 and not (args.state / 'pgdata/postmaster.pid').exists()
            report['source_unchanged'] = frozen == frozen_sources(root, args.source)
            report['passed'] = report['passed'] and report['clean_shutdown'] and report['source_unchanged']
            report['finished_at'] = datetime.now(ZoneInfo('Asia/Calcutta')).isoformat()
            (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report.get(key) for key in ('passed', 'summary', 'clean_shutdown', 'source_unchanged', 'reason')}), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
