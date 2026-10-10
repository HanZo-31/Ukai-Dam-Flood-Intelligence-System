"""Start the already-imported local backend using this workspace's own settings."""
import os
import json
from pathlib import Path
import subprocess
import sys
import time
import webbrowser
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'http://127.0.0.1:8765'


def catalog_ready(expected, opener=None):
    """Check the actual admitted catalog, bypassing external proxy settings."""
    opener = opener or build_opener(ProxyHandler({}))
    try:
        with opener.open(BASE_URL + '/api/v1/prototypes/scenarios', timeout=3) as response:
            payload = json.loads(response.read(1024 * 1024))
            if response.status != 200:
                return False
        return {(item['scenario_id'], item['run_id']) for item in payload['items']} == expected
    except (OSError, ValueError, KeyError, TypeError):
        return False


def main():
    os.chdir(ROOT)
    admission = json.loads((ROOT / 'runtime/admission.json').read_text())
    expected = {(item['scenario_id'], item['run_id']) for item in admission['entries']}
    if not expected:
        raise ValueError('No scenarios are admitted for this local preview.')
    show_browser = '--no-browser' not in sys.argv
    if catalog_ready(expected):
        print('Ukai is already running. Keep its original server window open.', flush=True)
        if show_browser:
            webbrowser.open(BASE_URL + '/docs')
        return
    os.environ['DATABASE_URL'] = (ROOT / 'runtime/database-url.txt').read_text().strip()
    os.environ['OBJECT_STORAGE_ROOT'] = str(ROOT / 'objects')
    os.environ['TMPDIR'] = str(ROOT / 'scratch')
    os.environ['TEMP'] = str(ROOT / 'temp')
    os.environ['TMP'] = str(ROOT / 'temp')
    os.environ['B2_ENV'] = 'local'
    pg = ROOT / 'runtime/pgsql/bin/pg_ctl.exe'
    data = ROOT / 'runtime/pgdata2'
    status = subprocess.run([str(pg), '-D', str(data), 'status'], capture_output=True)
    if status.returncode:
        print('Starting the local database. Please wait...', flush=True)
        subprocess.run([str(pg), '-D', str(data), '-l', str(ROOT/'runtime/postgresql.log'), '-w', 'start'], check=True,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    log_path = ROOT / 'runtime/host-api.log'
    with log_path.open('w', encoding='utf-8') as log:
        api = subprocess.Popen([sys.executable, 'scripts/run_prototype_preview.py', '--admission', 'runtime/admission.json',
            '--expected-database', 'ukai_b_integration_combined_20261008', '--port', '8765'],
            stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if api.poll() is not None:
                    raise RuntimeError('The API could not start. Details are in runtime/host-api.log.')
                if catalog_ready(expected):
                    break
                time.sleep(1)
            else:
                raise RuntimeError('The API did not respond within 60 seconds. Details are in runtime/host-api.log.')
            print(f'READY: {len(expected)} scenarios verified. {BASE_URL}/docs', flush=True)
            print('Keep this window open. Press Ctrl+C here to stop the API.', flush=True)
            if show_browser:
                webbrowser.open(BASE_URL + '/docs')
            api.wait()
        except KeyboardInterrupt:
            print('\nStopping the API...', flush=True)
        finally:
            if api.poll() is None:
                api.terminate()
                try:
                    api.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    api.kill()
                    api.wait()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        message = str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
        print('START FAILED: ' + message, file=sys.stderr)
        raise SystemExit(1)
