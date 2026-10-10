"""Real Node proxy/candidate test; reference upstream is a labelled routing double."""
import argparse
from datetime import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, ProxyHandler, Request
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('New evidence directory required')
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(), 'passed': False,
        'reference_upstream': 'routing test double; no genuine reference API roundtrip claimed',
        'candidate_upstream': 'actual candidate service with real source-byte hashes',
        'baseline_runtime_modified': False}
    class ReferenceDouble(BaseHTTPRequestHandler):
        def do_GET(self):
            payload = json.dumps({'routing_double': True, 'path': self.path}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *args):
            pass
    reference = ThreadingHTTPServer(('127.0.0.1', 0), ReferenceDouble)
    thread = threading.Thread(target=reference.serve_forever, daemon=True)
    thread.start()
    def available_port():
        with socket.socket() as handle:
            handle.bind(('127.0.0.1', 0))
            return handle.getsockname()[1]
    candidate_port, web_port = available_port(), available_port()
    opener = build_opener(ProxyHandler({}))
    def request(path, payload=None):
        req = Request('http://127.0.0.1:' + str(web_port) + path,
            data=json.dumps(payload).encode() if payload else None,
            headers={'Content-Type': 'application/json'} if payload else {})
        try:
            response = opener.open(req, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read()
    processes, logs = [], []
    try:
        for name, command, environment in [
            ('candidate', [sys.executable, '-B', str(root / 'run_candidate_service.py'), '--source', str(args.source.resolve()),
                '--state', str((args.output / 'jobs').resolve()), '--port', str(candidate_port)], os.environ.copy()),
            ('web', [str(args.source / 'runtime/node/node.exe'), str(root / 'assembly/ssd_web_server.cjs')],
                os.environ | {'UKAI_WEB_PORT': str(web_port), 'UKAI_API_PORT': str(reference.server_port),
                    'UKAI_CANDIDATE_PORT': str(candidate_port), 'UKAI_DIST_ROOT': str(args.source / 'frontend/dist')})]:
            handle = (args.output / (name + '.log')).open('w', encoding='utf-8')
            logs.append(handle)
            processes.append(subprocess.Popen(command, env=environment, stdout=handle, stderr=subprocess.STDOUT))
        deadline = time.monotonic() + 15
        while True:
            if any(process.poll() is not None for process in processes):
                raise ValueError('Owned process exited before ready')
            try:
                status, payload = request('/api/v1/candidates/capabilities')
                if status == 200:
                    break
            except (URLError, OSError):
                pass
            if time.monotonic() >= deadline:
                raise ValueError('Proxy startup timeout')
            time.sleep(0.1)
        capability = json.loads(payload)
        if capability['experimental_ml_enabled']:
            raise ValueError('Incorrect ML gate')
        status, payload = request('/api/v1/candidates/jobs', {'request_id': 'proxy-request-001', 'peak_release_m3s': 20000})
        result = json.loads(payload)
        if status != 200 or result['computed'] or result['actual_peak_release_m3s'] != 20000:
            raise ValueError('Candidate POST was not routed correctly')
        for path in ('/api/v1/prototypes/scenarios', '/api/v1/candidates-legacy/test'):
            status, payload = request(path)
            if status != 200 or json.loads(payload) != {'routing_double': True, 'path': path}:
                raise ValueError('Reference route or namespace boundary changed')
        status, payload = request('/')
        if status != 200 or b'<html' not in payload.lower():
            raise ValueError('Actual built frontend not served')
        processes[0].terminate()
        processes[0].wait(timeout=5)
        status, payload = request('/api/v1/candidates/capabilities')
        if status != 503 or 'candidate' not in json.loads(payload)['detail']:
            raise ValueError('Stopped candidate was not explicitly unavailable')
        if request('/')[0] != 200 or not json.loads(request('/api/v1/prototypes/scenarios')[1])['routing_double']:
            raise ValueError('Candidate failure blocked reference/static routes')
        report.update(passed=True, candidate_post_verified=True, prefix_boundary_verified=True,
            actual_built_frontend_served=True, candidate_failure_isolated=True,
            proxy_sha256=hashlib.sha256((root / 'assembly/ssd_web_server.cjs').read_bytes()).hexdigest(),
            candidate_sha256=hashlib.sha256((root / 'candidate_service.py').read_bytes()).hexdigest())
    except Exception as error:
        report['error_type'] = type(error).__name__
        report['passed'] = False
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        for handle in logs:
            handle.close()
        reference.shutdown()
        reference.server_close()
        thread.join(timeout=2)
        report['owned_processes_stopped'] = all(process.poll() is not None for process in processes)
        report['passed'] = report['passed'] and report['owned_processes_stopped']
        report['finished_at'] = datetime.now(ZoneInfo('Asia/Calcutta')).isoformat()
        (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
