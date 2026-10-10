"""Fresh local DB/reference/candidate rehearsal, duplicate launch, failure and restart."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler, Request
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from combined_runtime import Config, stop_child


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def source_hashes(source):
    paths = [source / 'SSD_PACKAGE_ID.txt', source / 'SSD_CHECKSUMS.sha256',
             source / 'scripts/ssd_runtime.py', source / 'scripts/ssd_web_server.cjs']
    for root in [source / 'part_a', *[source / 'receipts' / name for name in ('h01', 'h03', '2006')]]:
        paths.extend(path for path in root.rglob('*') if path.is_file())
    return {path.relative_to(source).as_posix(): digest(path) for path in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.source, args.output = args.source.resolve(), args.output.resolve()
    if args.output.exists():
        raise ValueError('Fresh evidence/state required')
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent
    source_before = source_hashes(args.source)
    ports = []
    reservations = []
    try:
        for _ in range(4):
            handle = socket.socket()
            handle.bind(('127.0.0.1', 0))
            ports.append(handle.getsockname()[1])
            reservations.append(handle)
    finally:
        for handle in reservations:
            handle.close()
    state = args.output / 'local-runtime-state'
    config = Config(args.source, state, *ports)
    owner = config.owner()
    flags = ['--source', str(args.source), '--state', str(state),
        '--db-port', str(ports[0]), '--api-port', str(ports[1]),
        '--web-port', str(ports[2]), '--candidate-port', str(ports[3])]
    command = [sys.executable, '-B', str(root / 'combined_runtime.py'), *flags, '--no-browser']
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
        'passed': False, 'checks': [], 'target_database': owner['database'], 'ports': owner['ports'],
        'state': str(state), 'source_hashes': source_before, 'ml_prediction_enabled': False,
        'new_physical_scenarios_generated': 0, 'genuine_browser_rendering': False}
    opener = build_opener(ProxyHandler({}))
    process = None
    logs = []
    def check(label, passed):
        report['checks'].append({'check': label, 'passed': bool(passed)})
        print(label + ': ' + ('passed' if passed else 'FAILED'), flush=True)
        if not passed:
            raise ValueError(label + ' failed')
    def status():
        return json.loads((state / 'combined-status.json').read_text())
    def call(path, payload=None):
        request = Request('http://127.0.0.1:' + str(config.web_port) + path,
            data=json.dumps(payload).encode() if payload else None,
            headers={'Content-Type': 'application/json'} if payload else {})
        try:
            response = opener.open(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read()
    def wait_ready(timeout=300):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ValueError('Owned supervisor exited before ready')
            try:
                current = status()
                if current['status'] == 'ready':
                    return current
            except (OSError, ValueError):
                pass
            time.sleep(0.2)
        raise ValueError('Owned runtime startup timeout')
    def start(name):
        nonlocal process
        handle = (args.output / (name + '.log')).open('w', encoding='utf-8')
        logs.append(handle)
        process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT)
        print('Starting owned ' + name + '...', flush=True)
        return wait_ready()
    def stop():
        run = subprocess.run([sys.executable, '-B', str(root / 'combined_runtime.py'), *flags, '--stop'],
                             capture_output=True, text=True, timeout=10)
        if run.returncode:
            raise ValueError('Owned stop command failed')
        process.wait(timeout=30)
        check('supervisor clean exit', process.returncode == 0)
        check('status stopped', status()['status'] == 'stopped')
        check('database marker removed', not (state / 'pgdata/postmaster.pid').exists())
        closed = []
        for port in ports:
            with socket.socket() as probe:
                probe.settimeout(0.2)
                closed.append(probe.connect_ex(('127.0.0.1', port)) != 0)
        check('all owned listeners stopped', all(closed))
    try:
        first = start('cold-start')
        check('fresh owned database imported four references', len(json.loads(call('/api/v1/prototypes/scenarios')[1])['items']) == 4)
        check('actual frontend served', b'<div id="root"></div>' in call('/')[1])
        check('candidate capability through same origin', json.loads(call('/api/v1/candidates/capabilities')[1])['supported_modes'] == ['stored_reference'])
        imported_before = digest(state / 'import-complete.json')
        import_reports_before = sorted(path.name for path in (state / 'evidence').glob('import-*'))
        duplicate = subprocess.run(command, capture_output=True, text=True, timeout=10)
        check('duplicate launch reuses instance', duplicate.returncode == 0 and 'already running' in duplicate.stdout)
        check('duplicate creates no extra child', status()['processes'] == first['processes'])
        request = {'request_id': 'combined-smoke-job-001', 'peak_release_m3s': 20000}
        code, body = call('/api/v1/candidates/jobs', request)
        job = json.loads(body)
        check('actual candidate POST/reference selection', code == 200 and not job['computed'] and job['actual_peak_release_m3s'] == 20000)
        code, body = call(job['reference_resources']['detail'])
        detail = json.loads(body)
        check('returned reference link matches actual API run', code == 200 and detail['run_id'] == job['source_run_id'])
        layers = json.loads(call(job['reference_resources']['layers'])[1])['layers']
        depth = next(item for item in layers if item['asset_type'] == 'max_depth_cog')
        with opener.open('http://127.0.0.1:' + str(config.web_port) + depth['url'], timeout=10) as download:
            raw = download.read()
            check('actual asset download hash through proxy', 'sha256:' + hashlib.sha256(raw).hexdigest() == depth['checksum'])
        candidate_pid = first['processes']['candidate']
        if sys.platform == 'win32':
            killed = subprocess.run(['taskkill', '/PID', str(candidate_pid), '/T', '/F'], capture_output=True, timeout=5)
            check('owned candidate interrupted for recovery test', killed.returncode == 0)
        else:
            import signal
            __import__('os').kill(candidate_pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and status()['status'] != 'ready_candidate_unavailable':
            time.sleep(0.1)
        check('degraded candidate is explicit', status()['status'] == 'ready_candidate_unavailable' and call('/api/v1/candidates/capabilities')[0] == 503)
        check('actual reference API survives candidate failure', len(json.loads(call('/api/v1/prototypes/scenarios')[1])['items']) == 4)
        stop()
        second = start('warm-restart')
        check('warm restart has new owned children', second['processes'] != first['processes'])
        check('warm restart does not reimport references', digest(state / 'import-complete.json') == imported_before and
            sorted(path.name for path in (state / 'evidence').glob('import-*')) == import_reports_before)
        code, body = call('/api/v1/candidates/jobs', request)
        resumed = json.loads(body)
        check('saved job recovers across restart', code == 200 and resumed['cache_hit'] and resumed['source_run_id'] == job['source_run_id'])
        stop()
        report['passed'] = True
    except Exception as error:
        report['failure_type'] = type(error).__name__
        report['reason'] = str(error) if isinstance(error, ValueError) else 'Owned runtime probe failed; inspect local logs'
    finally:
        if process is not None and process.poll() is None:
            try:
                subprocess.run([sys.executable, '-B', str(root / 'combined_runtime.py'), *flags, '--stop'],
                               capture_output=True, timeout=10)
                process.wait(timeout=30)
            except Exception:
                # Forced supervisor termination is never a clean database-stop claim.
                stop_child(process)
                report['passed'] = False
                report['cleanup_requires_review'] = True
        for handle in logs:
            handle.close()
        report['source_files_unchanged'] = source_hashes(args.source) == source_before
        report['passed'] = report['passed'] and report['source_files_unchanged']
        report['finished_at'] = datetime.now(ZoneInfo('Asia/Calcutta')).isoformat()
        report['supervisor_sha256'] = digest(root / 'combined_runtime.py')
        (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report.get(key) for key in ('passed', 'source_files_unchanged', 'failure_type', 'reason', 'cleanup_requires_review')}), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
