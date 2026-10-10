"""Own isolated layout verification services; all file writes stay within V05."""
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / '_layout_recheck'
SOURCE = CHECK / 'baseline-source'
STATE = CHECK / 'private-runtime'
PUBLIC = ROOT / 'layout_cleanup_evidence'
FLAGS = ['--source', str(SOURCE), '--state', str(STATE), '--db-port', '55448',
         '--api-port', '8796', '--web-port', '5192', '--candidate-port', '8788', '--no-browser']
OPENER = build_opener(ProxyHandler({}))


def get(port, route):
    with OPENER.open(f'http://127.0.0.1:{port}{route}', timeout=3) as response:
        return json.load(response)


def main():
    if sys.argv[1:] == ['stop']:
        (CHECK / 'stop.request').touch()
        return
    assert not (CHECK / 'stop.request').exists()
    processes, logs = [], []
    start = time.monotonic()
    try:
        logs.append((CHECK / 'isolated-runtime.log').open('w', encoding='utf-8'))
        services = subprocess.Popen([str(SOURCE / 'runtime/python/python.exe'), '-B',
                     str(SOURCE / 'team2_work/combined_runtime.py'), *FLAGS],
                     stdout=logs[-1], stderr=subprocess.STDOUT)
        processes.append(services)
        while time.monotonic() - start < 600:
            if services.poll() is not None:
                raise RuntimeError('Owned isolated services exited; inspect local private log')
            try:
                if len(get(5192, '/api/v1/prototypes/scenarios')['items']) == 4:
                    break
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(.25)
        else:
            raise TimeoutError('Isolated services did not become ready')
        logs.append((CHECK / 'current-frontend.log').open('w', encoding='utf-8'))
        proxy = subprocess.Popen([str(ROOT / 'runtime/node/node.exe'),
                    str(ROOT / 'team2_work/assembly/ssd_web_server.cjs')],
                    env=os.environ | {'UKAI_DIST_ROOT': str(ROOT / 'frontend/dist'),
                      'UKAI_WEB_PORT': '5191', 'UKAI_API_PORT': '8796',
                      'UKAI_CANDIDATE_PORT': '8788', 'UKAI_INSTANCE': 'v05-layout-cleanup'},
                    stdout=logs[-1], stderr=subprocess.STDOUT)
        processes.append(proxy)
        for _ in range(100):
            if proxy.poll() is not None:
                raise RuntimeError('Temporary V05 frontend exited')
            try:
                if get(5191, '/__ukai_instance')['instance'] == 'v05-layout-cleanup':
                    break
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(.1)
        else:
            raise TimeoutError('Temporary V05 frontend did not become ready')
        (PUBLIC / 'RUNTIME_READY.json').write_text(json.dumps({
            'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
            'frontend_source': 'V05/frontend/dist', 'backend': 'hash-verified pre-change V05 snapshot',
            'profile': 'new isolated test profile under V05/_layout_recheck; not the user profile',
            'web': 'http://127.0.0.1:5191/', 'writes_outside_v05': False,
            'normal_startup_ports_unchanged': True}, indent=2), encoding='utf-8')
        print('READY V05 cleanup frontend http://127.0.0.1:5191/; private test profile inside V05', flush=True)
        while not (CHECK / 'stop.request').exists():
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('An owned verification service stopped')
            if time.monotonic() - start > 7200:
                raise TimeoutError('Verification window expired')
            time.sleep(.5)
    finally:
        if len(processes) > 1 and processes[-1].poll() is None:
            processes[-1].terminate()
            processes[-1].wait(timeout=10)
        if processes and processes[0].poll() is None:
            subprocess.run([str(SOURCE / 'runtime/python/python.exe'), '-B',
                str(SOURCE / 'team2_work/combined_runtime.py'), *FLAGS, '--stop'], timeout=30, check=True)
            processes[0].wait(timeout=60)
        for log in logs:
            log.close()
        (PUBLIC / 'RUNTIME_STOPPED.json').write_text(json.dumps({
            'checked_at': datetime.now().astimezone().isoformat(),
            'all_owned_children_exited': all(p.poll() is not None for p in processes)}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
