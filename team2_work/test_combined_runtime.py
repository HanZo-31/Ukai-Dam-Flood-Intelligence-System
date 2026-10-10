"""Ownership, collision and cleanup tests for the separate combined supervisor."""
import json
import hashlib
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import combined_runtime as runtime

SOURCE = Path(os.environ.get('UKAI_REFERENCE_ROOT', str(Path(sys.executable).resolve().parents[2])))


def config(tmp_path, **changes):
    return runtime.Config(SOURCE, tmp_path / 'owned-state', **changes)


def test_owner_is_specific_and_different_from_baseline(tmp_path):
    owner = config(tmp_path).owner()
    assert owner['database'].startswith('ukai_b_integration_team2_')
    assert owner['database'] != 'ukai_b_integration_ssd'
    assert owner['ports'] == {'database': 55434, 'api': 8767, 'web': 5176, 'candidate': 8770}
    assert owner['state'] != owner['source']


@pytest.mark.parametrize('changes', [{'api_port': 55434}, {'web_port': 0}, {'candidate_port': 65536}])
def test_invalid_port_profile_rejected_before_resources(tmp_path, changes):
    with pytest.raises(ValueError, match='distinct valid ports'):
        config(tmp_path, **changes).owner()
    assert not (tmp_path / 'owned-state').exists()


def test_baseline_cannot_be_used_as_mutable_state():
    with pytest.raises(ValueError, match='Separate'):
        runtime.Config(SOURCE, SOURCE / 'data').owner()


def test_existing_unowned_state_is_not_adopted(tmp_path):
    cfg = config(tmp_path)
    cfg.state.mkdir()
    (cfg.state / 'do-not-touch.txt').write_text('User data')
    with pytest.raises(ValueError, match='without matching owner'):
        runtime.load_owner(cfg)
    assert (cfg.state / 'do-not-touch.txt').read_text() == 'User data'


def test_changed_owner_or_ports_cannot_be_reused(tmp_path):
    cfg = config(tmp_path)
    cfg.state.mkdir()
    runtime.json_atomic(cfg.state / 'combined-owner.json', cfg.owner())
    assert runtime.load_owner(cfg) == cfg.owner()
    with pytest.raises(ValueError, match='owner/profile differs'):
        runtime.load_owner(config(tmp_path, web_port=5190))


def test_cross_process_instance_lock_rejects_second_owner(tmp_path):
    import subprocess
    cfg = config(tmp_path)
    cfg.state.mkdir()
    script = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
              'from combined_runtime import instance_lock; '
              'ctx=instance_lock(Path(sys.argv[2]));ctx.__enter__()')
    with runtime.instance_lock(cfg.state):
        run = subprocess.run([sys.executable, '-B', '-c', script, str(Path(runtime.__file__).parent), str(cfg.state)],
                             capture_output=True, text=True, timeout=5)
    assert run.returncode != 0 and 'already starting or running' in run.stderr
    with runtime.instance_lock(cfg.state):
        pass


def test_occupied_port_is_not_stopped_or_adopted(tmp_path):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(RuntimeError, match='in use'):
            runtime.check_ports(config(tmp_path, web_port=port))
        assert listener.fileno() != -1


def test_stop_child_acts_only_on_passed_owned_handle():
    events = []
    class Process:
        def poll(self): return None
        def terminate(self): events.append('terminate-owned')
        def wait(self, timeout): events.append(('wait-owned', timeout))
    runtime.stop_child(Process())
    assert events == ['terminate-owned', ('wait-owned', 10)]


def test_shutdown_error_is_not_reported_as_stopped(tmp_path):
    cfg = config(tmp_path)
    cfg.state.mkdir()
    supervisor = runtime.Supervisor(cfg)
    def fail(*args):
        raise RuntimeError('Synthetic owned database failure')
    supervisor.module = SimpleNamespace(stop_database=fail)
    supervisor.database_touched = True
    with pytest.raises(RuntimeError, match='shutdown incomplete'):
        supervisor.close()
    state = json.loads((cfg.state / 'combined-status.json').read_text())
    assert state['status'] == 'shutdown_failed' and state['shutdown_failures'] == ['database']


def test_candidate_failure_preserves_reference_monitor(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    cfg.state.mkdir()
    supervisor = runtime.Supervisor(cfg)
    class Process:
        def __init__(self, code, pid): self.code, self.pid = code, pid
        def poll(self): return self.code
    supervisor.processes = {'api': Process(None, 1), 'candidate': Process(1, 2), 'frontend': Process(None, 3)}
    monkeypatch.setattr(runtime.time, 'sleep', lambda seconds: (cfg.state / 'combined-stop.request').write_text('stop'))
    supervisor.monitor()
    saved = json.loads((cfg.state / 'combined-status.json').read_text())
    assert saved['status'] == 'ready_candidate_unavailable' and not saved['candidate_available']


def test_reference_failure_requires_owned_cleanup(tmp_path):
    cfg = config(tmp_path)
    cfg.state.mkdir()
    supervisor = runtime.Supervisor(cfg)
    supervisor.processes = {name: SimpleNamespace(poll=lambda: 1, pid=index) for index, name in enumerate(('api', 'candidate', 'frontend'))}
    with pytest.raises(RuntimeError, match='Reference API/frontend stopped'):
        supervisor.monitor()


def ready_existing(tmp_path, status='ready'):
    cfg = config(tmp_path)
    cfg.state.mkdir()
    owner = cfg.owner()
    runtime.json_atomic(cfg.state / 'combined-status.json', {'instance': owner['instance'], 'status': status})
    roots = [SOURCE / 'part_a', *[SOURCE / 'receipts' / name for name in ('h01', 'h03', '2006')]]
    items = [json.loads((root / 'prototype-manifest.json').read_text()) for root in roots]
    return cfg, owner, items


@pytest.mark.parametrize('status', ['stopped', 'shutdown_failed', 'initializing'])
def test_stale_duplicate_cannot_report_success(tmp_path, monkeypatch, status):
    cfg, owner, _ = ready_existing(tmp_path, status)
    monkeypatch.setattr(runtime, 'get_json', lambda *args: pytest.fail('Stale status should reject before readiness HTTP'))
    with pytest.raises(RuntimeError, match='not verified ready'):
        runtime.validate_existing_instance(cfg, owner)


@pytest.mark.parametrize('fault', ['unavailable-api', 'wrong-run', 'unavailable-candidate', 'wrong-mode', 'ml-enabled'])
def test_duplicate_rechecks_real_readiness(tmp_path, monkeypatch, fault):
    cfg, owner, items = ready_existing(tmp_path)
    if fault == 'wrong-run':
        items[0]['run_id'] = 'wrong-run'
    def get(port, path):
        if ((fault == 'unavailable-api' and path.endswith('/scenarios'))
                or (fault == 'unavailable-candidate' and path.endswith('/capabilities'))):
            raise OSError('Synthetic unavailable service')
        if path.endswith('/scenarios'):
            return {'items': items}
        return {'supported_modes': ['experimental_ml'] if fault == 'wrong-mode' else ['stored_reference'],
                'experimental_ml_enabled': fault == 'ml-enabled'}
    monkeypatch.setattr(runtime, 'get_json', get)
    with pytest.raises(RuntimeError, match='not verified ready'):
        runtime.validate_existing_instance(cfg, owner)


@pytest.mark.parametrize('status', ['ready', 'ready_candidate_unavailable'])
def test_duplicate_healthy_or_explicitly_degraded_reference(tmp_path, monkeypatch, status):
    cfg, owner, items = ready_existing(tmp_path, status)
    calls = []
    def get(port, path):
        calls.append(path)
        if path.endswith('/scenarios'):
            return {'items': items}
        return {'supported_modes': ['stored_reference'], 'experimental_ml_enabled': False}
    monkeypatch.setattr(runtime, 'get_json', get)
    assert runtime.validate_existing_instance(cfg, owner) == status
    assert ('/api/v1/candidates/capabilities' in calls) == (status == 'ready')


def test_duplicate_main_rejects_matching_proxy_with_failed_status(tmp_path, monkeypatch):
    cfg, owner, _ = ready_existing(tmp_path, 'shutdown_failed')
    runtime.json_atomic(cfg.state / 'combined-owner.json', owner)
    monkeypatch.setattr(sys, 'argv', ['combined_runtime.py', '--source', str(SOURCE), '--state', str(cfg.state)])
    monkeypatch.setattr(runtime, 'get_json', lambda *args: {'instance': owner['instance']})
    monkeypatch.setattr(runtime.subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Must not launch extra services'))
    with pytest.raises(RuntimeError, match='not verified ready'):
        runtime.main()


def alias_fixture(tmp_path, monkeypatch, status='stopped'):
    physical = tmp_path / 'physical-state'
    alias = tmp_path / 'logical-state'
    physical.mkdir()
    original = Path.resolve
    def resolve(path, *args, **kwargs):
        if path.is_relative_to(alias):
            return physical / path.relative_to(alias)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'resolve', resolve)
    cfg = runtime.Config(SOURCE, physical)
    owner = cfg.owner()
    old_id = hashlib.sha256(json.dumps([owner['package_id'], owner['source'].casefold(),
        str(alias).casefold(), [55434, 8767, 5176, 8770]]).encode()).hexdigest()[:16]
    recorded = owner | {'state': str(alias), 'instance': 'team2-' + old_id,
                        'database': 'ukai_b_integration_team2_' + old_id}
    runtime.json_atomic(physical / 'combined-owner.json', recorded)
    runtime.json_atomic(physical / 'combined-status.json', {'instance': owner['instance'], 'status': status})
    target = {'database': owner['database'], 'project': 'Ukai SSD', 'protected_database': 'ukai', 'state': 'created',
        'objects_root': str(physical / 'objects'), 'scratch_root': str(physical / 'scratch'),
        'protected_object_root': str(physical / 'protected-unused')}
    runtime.json_atomic(physical / 'target-marker.json', target)
    return cfg, owner, recorded


def test_verified_alias_transition_preserves_database_without_writing(tmp_path, monkeypatch):
    cfg, owner, recorded = alias_fixture(tmp_path, monkeypatch)
    assert runtime.load_owner(cfg) == owner
    assert json.loads((cfg.state / 'combined-owner.json').read_text()) == recorded


@pytest.mark.parametrize('fault', ['wrong-database', 'wrong-status-instance', 'wrong-object-root', 'altered-old-owner'])
def test_alias_transition_cannot_adopt_unrelated_state(tmp_path, monkeypatch, fault):
    cfg, owner, recorded = alias_fixture(tmp_path, monkeypatch)
    if fault == 'wrong-database':
        path = cfg.state / 'target-marker.json'; value = json.loads(path.read_text()); value['database'] = 'unrelated_database'
    elif fault == 'wrong-status-instance':
        path = cfg.state / 'combined-status.json'; value = {'instance': 'unrelated', 'status': 'stopped'}
    elif fault == 'wrong-object-root':
        path = cfg.state / 'target-marker.json'; value = json.loads(path.read_text()); value['objects_root'] = str(tmp_path / 'other')
    else:
        path = cfg.state / 'combined-owner.json'; value = recorded | {'database': 'unrelated_database'}
    runtime.json_atomic(path, value)
    with pytest.raises(ValueError, match='owner/profile differs'):
        runtime.load_owner(cfg)


def test_live_alias_transition_requires_matching_live_proxy(tmp_path, monkeypatch):
    cfg, owner, _ = alias_fixture(tmp_path, monkeypatch, 'ready')
    monkeypatch.setattr(runtime, 'get_json', lambda *args: {'instance': owner['instance']})
    assert runtime.load_owner(cfg) == owner
    monkeypatch.setattr(runtime, 'get_json', lambda *args: {'instance': 'unrelated'})
    with pytest.raises(ValueError, match='owner/profile differs'):
        runtime.load_owner(cfg)
