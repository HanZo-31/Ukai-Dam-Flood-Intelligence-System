"""Quality-tool checks stay local, pinned and separate from runtime packages."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from scripts import check_b2_quality as quality


def fake_run(args, **kwargs):
    if args[1:] == ['--version']:
        return SimpleNamespace(returncode=0, stdout='Python 3.13.15', stderr='')
    if '--version' in args:
        text = 'ruff 0.16.10' if args[2] == 'ruff' else 'mypy 2.4.0 (compiled: yes)'
    else:
        text = 'All checks passed!' if args[2] == 'ruff' else 'Success: no issues found in 31 source files'
    return SimpleNamespace(returncode=0, stdout=text, stderr='')


def test_quality_report_pinned_local_and_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(quality.subprocess, 'run', fake_run)
    monkeypatch.setattr(quality, 'sources', lambda: {'source.py': 'hash'})
    result = quality.check(sys.executable, sys.executable, tmp_path / 'result.json')
    assert result['result'] == 'passed' and result['source_unchanged_during_checks']
    assert not result['git_or_ci_used'] and not result['strict_typing_or_all_rules_claimed']
    assert len(result['checks']) == 2


def test_quality_existing_report_not_overwritten(tmp_path):
    output = tmp_path / 'existing.json'
    output.write_text('keep')
    with pytest.raises(ValueError, match='new report'):
        quality.check(sys.executable, sys.executable, output)
    assert output.read_text() == 'keep'


def test_failed_quality_command_retains_failed_report(tmp_path, monkeypatch):
    def fail(args, **kwargs):
        if '--version' in args:
            return fake_run(args, **kwargs)
        return SimpleNamespace(returncode=1, stdout='lint failed', stderr='')
    monkeypatch.setattr(quality.subprocess, 'run', fail)
    monkeypatch.setattr(quality, 'sources', lambda: {'source.py': 'hash'})
    output = tmp_path / 'failed.json'
    with pytest.raises(ValueError, match='gate failed'):
        quality.check(sys.executable, sys.executable, output)
    assert json.loads(output.read_text())['result'] == 'failed'


def test_source_mutation_fails_quality_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(quality.subprocess, 'run', fake_run)
    snapshots = iter([{'source.py': 'before'}, {'source.py': 'after'}])
    monkeypatch.setattr(quality, 'sources', lambda: next(snapshots))
    with pytest.raises(ValueError, match='source changed'):
        quality.check(sys.executable, sys.executable, tmp_path / 'changed.json')
    result = json.loads((tmp_path / 'changed.json').read_text())
    assert result['result'] == 'failed' and not result['source_unchanged_during_checks']


def test_quality_scope_preserves_b1_ownership():
    assert [name for name in quality.APPLICATION if 'repositories' in name] == [
        'services/api/app/repositories/prototype_repository.py']
    assert not any('app/db' in name for name in quality.APPLICATION)
    assert all(Path(quality.ROOT / name).exists() for name in quality.APPLICATION + quality.SCRIPTS + quality.CONFIGS)


@pytest.mark.parametrize('module', ['ruff', 'mypy'])
def test_unpinned_tool_version_refused(tmp_path, monkeypatch, module):
    def wrong(args, **kwargs):
        if len(args) > 2 and args[2] == module and '--version' in args:
            return SimpleNamespace(returncode=0, stdout=module + ' 0.0.1', stderr='')
        return fake_run(args, **kwargs)
    monkeypatch.setattr(quality.subprocess, 'run', wrong)
    monkeypatch.setattr(quality, 'sources', lambda: {'source.py': 'hash'})
    with pytest.raises(ValueError, match='Pinned quality'):
        quality.check(sys.executable, sys.executable, tmp_path / (module + '.json'))


def test_wrong_runtime_version_refused(tmp_path, monkeypatch):
    def wrong(args, **kwargs):
        if args[1:] == ['--version']:
            return SimpleNamespace(returncode=0, stdout='Python 3.11.0', stderr='')
        return fake_run(args, **kwargs)
    monkeypatch.setattr(quality.subprocess, 'run', wrong)
    monkeypatch.setattr(quality, 'sources', lambda: {'source.py': 'hash'})
    with pytest.raises(ValueError, match='runtime must use Python 3.12 or 3.13'):
        quality.check(sys.executable, sys.executable, tmp_path / 'bad-runtime.json')


def test_benchmark_scope_is_not_all_handoff_documents():
    from scripts.verify_b2_handoff_source import BENCHMARK_FILES, benchmark_fingerprints
    hashes = {n: 'sha256:verified' for n in BENCHMARK_FILES}
    hashes['docs/b1-status.md'] = 'changed-document'
    assert benchmark_fingerprints({'source_hashes': hashes}) == {n: 'verified' for n in BENCHMARK_FILES}


def test_missing_benchmark_file_refused():
    from scripts.verify_b2_handoff_source import benchmark_fingerprints
    with pytest.raises(ValueError, match='coverage missing'):
        benchmark_fingerprints({'source_hashes': {}})
