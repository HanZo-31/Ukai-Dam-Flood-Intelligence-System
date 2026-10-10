"""Probe the real owned loopback process and clean shutdown, no baseline services changed."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import build_opener, ProxyHandler, Request
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh probe directory required')
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in root.glob('*.py')}
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(), 'passed': False,
              'source_hashes': hashes, 'baseline_database_changed': False, 'ml_prediction_performed': False}
    opener = build_opener(ProxyHandler({}))
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0))
        port = available.getsockname()[1]
    base = 'http://127.0.0.1:' + str(port)
    def get(path):
        with opener.open(base + path, timeout=3) as response:
            return json.loads(response.read())
    with (args.output / 'service.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-B', str(root / 'run_candidate_service.py'),
            '--source', str(args.source.resolve()), '--state', str((args.output / 'jobs').resolve()),
            '--port', str(port)], stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise ValueError('Owned service exited before ready')
                try:
                    capability = get('/api/v1/candidates/capabilities')
                    break
                except (URLError, OSError):
                    if time.monotonic() >= deadline:
                        raise ValueError('Local startup timed out')
                    time.sleep(0.1)
            if capability['experimental_ml_enabled'] or capability['supported_modes'] != ['stored_reference']:
                raise ValueError('Capability gate incorrect')
            durations = []
            results = []
            for number, peak in enumerate((15000, 20000, 30000)):
                request = {'request_id': 'tcp-check-' + str(number), 'peak_release_m3s': peak}
                started = time.perf_counter()
                req = Request(base + '/api/v1/candidates/jobs', data=json.dumps(request).encode(),
                              headers={'Content-Type': 'application/json'}, method='POST')
                with opener.open(req, timeout=5) as response:
                    result = json.loads(response.read())
                durations.append(time.perf_counter() - started)
                if result['computed'] or result['actual_peak_release_m3s'] != peak or result['scientifically_validated']:
                    raise ValueError('Reference identity or scientific label incorrect')
                if get('/api/v1/candidates/jobs/' + result['job_id'])['source_run_id'] != result['source_run_id']:
                    raise ValueError('Saved job identity incorrect')
                results.append(result)
            report.update(base_url=base, capabilities=capability, reference_results=results,
                          request_complete_seconds=durations, timing_scope='HTTP stored selection; no browser render or model run',
                          cold_warm_claim='three distinct reference lookups, no SLA/percentile inference', passed=True)
        except Exception as error:
            report['error_type'] = type(error).__name__
            report['passed'] = False
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            deadline = time.monotonic() + 3
            while True:
                with socket.socket() as probe:
                    probe.settimeout(0.1)
                    closed = probe.connect_ex(('127.0.0.1', port)) != 0
                if closed or time.monotonic() >= deadline:
                    break
                time.sleep(0.1)
            report['clean_stop'] = closed
            report['source_unchanged'] = hashes == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in root.glob('*.py')}
            report['passed'] = report['passed'] and closed and report['source_unchanged']
            report['finished_at'] = datetime.now(ZoneInfo('Asia/Calcutta')).isoformat()
            (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report.get(key) for key in ('passed', 'clean_stop', 'source_unchanged', 'request_complete_seconds', 'error_type')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
