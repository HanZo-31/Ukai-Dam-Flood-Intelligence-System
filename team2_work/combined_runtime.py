"""Owned local reference/candidate supervisor; no edits to the prepared package."""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
import webbrowser

HERE = Path(__file__).resolve().parent
OPENER = build_opener(ProxyHandler({}))


@dataclass(frozen=True)
class Config:
    source: Path
    state: Path
    db_port: int = 55434
    api_port: int = 8767
    web_port: int = 5176
    candidate_port: int = 8770

    def owner(self):
        source, state = self.source.resolve(), self.state.resolve()
        if (state.is_relative_to(source) or source.is_relative_to(state)
                or len(state.parts) < 3 or source == state):
            raise ValueError('Separate specific local state directory required')
        ports = [self.db_port, self.api_port, self.web_port, self.candidate_port]
        if any(type(port) is not int or not 1 <= port <= 65535 for port in ports) or len(set(ports)) != 4:
            raise ValueError('Four distinct valid ports required')
        package = (source / 'SIMULATION_PACKAGE_ID.txt').read_text().strip()
        if not package or not (source / 'runtime/pgsql/bin/pg_ctl.exe').is_file():
            raise ValueError('Complete portable baseline required')
        identity = hashlib.sha256(json.dumps([package, str(source).casefold(), str(state).casefold(), ports]).encode()).hexdigest()[:16]
        return {'schema_version': '1.0.0', 'kind': 'ukai_team2_combined_runtime',
            'instance': 'team2-' + identity, 'package_id': package, 'source': str(source),
            'state': str(state), 'ports': {'database': self.db_port, 'api': self.api_port,
            'web': self.web_port, 'candidate': self.candidate_port},
            'database': 'ukai_b_integration_team2_' + identity}


def json_atomic(path, payload):
    temporary = path.with_name(path.name + '.pending')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_owner(config):
    expected = config.owner()
    state = config.state.resolve()
    marker = state / 'combined-owner.json'
    if marker.exists():
        recorded = json.loads(marker.read_text())
        if recorded != expected and not verified_path_transition(config, recorded, expected):
            raise ValueError('State owner/profile differs; choose a separate state directory')
    elif state.exists() and any(path.name != 'combined-instance.lock' for path in state.iterdir()):
        raise ValueError('Existing state without matching owner is not a disposable target')
    return expected


def verified_path_transition(config, recorded, expected):
    """Recognize only our pre-creation path-alias bug, never adopt a different DB."""
    try:
        old_path = recorded['state']
        if old_path == expected['state'] or Path(old_path).resolve() != config.state.resolve():
            return False
        ports = [config.db_port, config.api_port, config.web_port, config.candidate_port]
        old_identity = hashlib.sha256(json.dumps([
            expected['package_id'], expected['source'].casefold(), old_path.casefold(), ports]).encode()).hexdigest()[:16]
        old_expected = expected | {'state': old_path, 'instance': 'team2-' + old_identity,
                                   'database': 'ukai_b_integration_team2_' + old_identity}
        if recorded != old_expected:
            return False
        status = json.loads((config.state / 'combined-status.json').read_text())
        target = json.loads((config.state / 'target-marker.json').read_text())
        if (status['instance'] != expected['instance']
                or status['status'] not in {'ready', 'ready_candidate_unavailable', 'stopped'}
                or target['database'] != expected['database'] or target['project'] != 'Ukai SSD'
                or target['protected_database'] != 'ukai' or target['state'] != 'created'):
            return False
        for field, folder in [('objects_root', 'objects'), ('scratch_root', 'scratch'),
                              ('protected_object_root', 'protected-unused')]:
            if Path(target[field]).resolve() != (config.state / folder).resolve():
                return False
        if status['status'] != 'stopped' and get_json(config.web_port, '/__ukai_instance').get('instance') != expected['instance']:
            return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


@contextmanager
def instance_lock(state):
    import msvcrt
    handle = (state / 'combined-instance.lock').open('a+b')
    try:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('This combined instance is already starting or running') from None
        yield
    finally:
        handle.close()


def get_json(port, path):
    with OPENER.open('http://127.0.0.1:' + str(port) + path, timeout=3) as response:
        return json.load(response)


def check_ports(config):
    for name, port in config.owner()['ports'].items():
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                raise RuntimeError(name + ' port ' + str(port) + ' is in use; no unrelated process was stopped') from None


def validate_existing_instance(config, owner):
    """Matching proxy identity alone is not proof of a healthy owned runtime."""
    try:
        status = json.loads((config.state / 'combined-status.json').read_text())
        if (status.get('instance') != owner['instance']
                or status.get('status') not in {'ready', 'ready_candidate_unavailable'}):
            raise ValueError('stale status')
        roots = [config.source / 'part_a', *[config.source / 'receipts' / name for name in ('h01', 'h03', '2006')]]
        expected = set()
        for root in roots:
            manifest = json.loads((root / 'prototype-manifest.json').read_text())
            expected.add((manifest['scenario_id'], manifest['run_id']))
        items = get_json(config.web_port, '/api/v1/prototypes/scenarios')['items']
        if len(items) != 4 or {(item['scenario_id'], item['run_id']) for item in items} != expected:
            raise ValueError('reference catalog differs')
        if status['status'] == 'ready':
            capability = get_json(config.web_port, '/api/v1/candidates/capabilities')
            if capability['supported_modes'] != ['stored_reference'] or capability['experimental_ml_enabled']:
                raise ValueError('candidate capability differs')
        return status['status']
    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError('Matching instance is not verified ready. Inspect its owned status/logs; no unrelated process was stopped.') from None


def baseline_module(config, owner):
    source = config.source.resolve()
    sys.path.insert(0, str(source))
    spec = importlib.util.spec_from_file_location('team2_baseline_runtime', source / 'scripts/simulation_runtime.py')
    if spec is None or spec.loader is None:
        raise ValueError('Portable runtime module cannot be loaded')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, value in {'DB': owner['database'], 'DB_PORT': config.db_port,
                        'API_PORT': config.api_port, 'WEB_PORT': config.web_port}.items():
        setattr(module, name, value)
    return module


def stop_child(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


class Supervisor:
    def __init__(self, config):
        self.config = config
        self.owner = config.owner()
        self.processes, self.logs = {}, []
        self.module = None
        self.database_touched = False
        self.previous_environment = os.environ.copy()

    def write_status(self, status, **values):
        json_atomic(self.config.state / 'combined-status.json', {
            'instance': self.owner['instance'], 'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'processes': {name: process.pid for name, process in self.processes.items()}, **values})

    def start_child(self, name, command, env):
        output = (self.config.state / (name + '.log')).open('a', encoding='utf-8')
        self.logs.append(output)
        self.processes[name] = subprocess.Popen(command, cwd=self.config.source,
            env=env, stdout=output, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def start(self, timeout=240):
        config, state = self.config, self.config.state
        self.module = baseline_module(config, self.owner)
        manifest = config.source / 'SIMULATION_CHECKSUMS.sha256'
        seal = hashlib.sha256(manifest.read_bytes()).hexdigest()
        verified = state / 'combined-copy-verified.json'
        if not verified.exists() or json.loads(verified.read_text()).get('inventory_sha256') != seal:
            self.module.verify_copy()
            json_atomic(verified, {'inventory_sha256': seal, 'source': str(config.source)})
        # No inherited profile can override the explicitly owned target.
        for key in list(os.environ):
            if key.startswith(('B2_', 'PG')) or key in {'DATABASE_URL', 'DATABASE_URL_FILE', 'OBJECT_STORAGE_ROOT'}:
                os.environ.pop(key, None)
        self.write_status('initializing')
        self.database_touched = True
        _, _, admission, entries = self.module.configure(state, state / 'setup.log')
        api_env = os.environ.copy()
        safe_env = {key: value for key, value in api_env.items()
                    if not key.startswith(('B2_', 'PG')) and key not in {'DATABASE_URL', 'DATABASE_URL_FILE'}}
        python = str(config.source / 'runtime/python/python.exe')
        self.start_child('api', [python, '-B', 'scripts/run_prototype_preview.py', '--admission', str(admission),
            '--expected-database', self.owner['database'], '--port', str(config.api_port)], api_env)
        self.start_child('candidate', [python, '-B', str(HERE / 'run_candidate_service.py'),
            '--source', str(config.source), '--state', str(state / 'candidate-jobs'),
            '--port', str(config.candidate_port)], safe_env)
        self.start_child('frontend', [str(config.source / 'runtime/node/node.exe'),
            str(HERE / 'assembly/simulation_web_server.cjs')], safe_env | {
                'UKAI_INSTANCE': self.owner['instance'], 'UKAI_WEB_PORT': str(config.web_port),
                'UKAI_API_PORT': str(config.api_port), 'UKAI_CANDIDATE_PORT': str(config.candidate_port),
                'UKAI_DIST_ROOT': str(config.source / 'frontend/dist')})
        expected = {(item['scenario_id'], item['run_id']) for item in entries}
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in self.processes.values()):
                raise RuntimeError('An owned service exited during startup; see the local role log')
            try:
                catalog = get_json(config.web_port, '/api/v1/prototypes/scenarios')['items']
                capability = get_json(config.web_port, '/api/v1/candidates/capabilities')
                if {(item['scenario_id'], item['run_id']) for item in catalog} == expected and not capability['experimental_ml_enabled']:
                    self.write_status('ready', reference_count=4, candidate_available=True,
                                      ml_enabled=False, new_hydraulic_scenarios=0)
                    return
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(0.2)
        raise RuntimeError('Combined startup did not reach the four-reference/candidate checks')

    def monitor(self):
        stop = self.config.state / 'combined-stop.request'
        degraded = False
        while not stop.exists():
            if any(self.processes[name].poll() is not None for name in ('api', 'frontend')):
                raise RuntimeError('Reference API/frontend stopped; shutting down owned resources')
            if self.processes['candidate'].poll() is not None and not degraded:
                degraded = True
                self.write_status('ready_candidate_unavailable', reference_count=4, candidate_available=False, ml_enabled=False)
                print('Candidate service stopped; reference pages remain available. Restart to recover it.', flush=True)
            time.sleep(0.2)

    def close(self):
        failures = []
        for name, process in reversed(list(self.processes.items())):
            try:
                stop_child(process)
            except Exception:
                failures.append(name)
        for output in self.logs:
            output.close()
        if self.module is not None and self.database_touched:
            try:
                self.module.stop_database(self.config.source / 'runtime/pgsql/bin',
                    self.config.state / 'pgdata', self.config.state / 'setup.log')
            except Exception:
                failures.append('database')
        os.environ.clear()
        os.environ.update(self.previous_environment)
        self.write_status('stopped' if not failures else 'shutdown_failed', shutdown_failures=failures)
        if failures:
            raise RuntimeError('Owned resource shutdown incomplete; retained logs identify the roles')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--state', type=Path)
    for name, default in [('db', 55434), ('api', 8767), ('web', 5176), ('candidate', 8770)]:
        parser.add_argument('--' + name + '-port', type=int, default=default)
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve()
    default_state = Path(os.environ.get('LOCALAPPDATA', str(HERE))) / 'UkaiTeam2' / hashlib.sha256(str(source).casefold().encode()).hexdigest()[:16]
    config = Config(source, (args.state or default_state).resolve(), args.db_port, args.api_port, args.web_port, args.candidate_port)
    owner = load_owner(config)
    if args.stop:
        if (config.state / 'combined-owner.json').is_file():
            json_atomic(config.state / 'combined-stop.request', {'instance': owner['instance']})
            print('Stop requested for this owned combined instance. Wait for Stopped.', flush=True)
        else:
            print('No matching combined instance has been initialized.', flush=True)
        return 0
    try:
        existing = get_json(config.web_port, '/__ukai_instance')
    except (OSError, ValueError):
        existing = None
    if isinstance(existing, dict) and existing.get('instance') == owner['instance']:
        status = validate_existing_instance(config, owner)
        print('This combined copy is already running: ' + status, flush=True)
        if status == 'ready_candidate_unavailable':
            print('Reference API verified; candidate unavailable. Stop/restart this owned profile to recover it.', flush=True)
        return 0
    config.state.mkdir(parents=True, exist_ok=True)
    # Canonicalize after creation: Windows package redirection/junctions may only
    # become resolvable once the state folder exists. Marker and supervisor agree.
    config = replace(config, state=config.state.resolve())
    with instance_lock(config.state):
        owner = load_owner(config)
        check_ports(config)
        owner_file = config.state / 'combined-owner.json'
        if not owner_file.exists():
            json_atomic(owner_file, owner)
        elif json.loads(owner_file.read_text()) != owner:
            # load_owner already validated exact alias + status + existing DB.
            backup = config.state / 'combined-owner-precanonical.json'
            if not backup.exists():
                json_atomic(backup, json.loads(owner_file.read_text()))
            json_atomic(owner_file, owner)
            print('Normalized verified state path ownership; existing database/imports preserved.', flush=True)
        (config.state / 'combined-stop.request').unlink(missing_ok=True)
        supervisor = Supervisor(config)
        try:
            supervisor.start()
            print('READY: 4 references and candidate fallback. http://127.0.0.1:' + str(config.web_port), flush=True)
            print('Local state: ' + str(config.state) + '. Ctrl+C or STOP_TEAM2 stops this instance.', flush=True)
            if not args.no_browser:
                webbrowser.open('http://127.0.0.1:' + str(config.web_port))
            supervisor.monitor()
        except KeyboardInterrupt:
            print('Stopping owned services...', flush=True)
        finally:
            supervisor.close()
        print('Stopped.', flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        detail = str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
        print('TEAM2 START FAILED: ' + detail, file=sys.stderr)
        raise SystemExit(1)
