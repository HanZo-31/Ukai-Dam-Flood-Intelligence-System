"""Portable copy integrity and lifecycle checks without touching any database."""
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import simulation_runtime as ssd


def inventory(root,entries):
    (root/'SIMULATION_CHECKSUMS.sha256').write_text(''.join(
        hashlib.sha256(value).hexdigest()+'  '+key+'\n' for key,value in entries.items()))


@pytest.mark.parametrize('kind',['empty','truncated','modified','duplicate','traversal'])
def test_checksum_verification_refuses_bad_copy(tmp_path,monkeypatch,kind):
    monkeypatch.setattr(ssd,'ROOT',tmp_path)
    (tmp_path/'a.txt').write_bytes(b'a')
    (tmp_path/'b.txt').write_bytes(b'b')
    inventory(tmp_path,{'a.txt':b'a','b.txt':b'b'})
    if kind=='empty':
        (tmp_path/'SIMULATION_CHECKSUMS.sha256').write_text('')
    elif kind=='truncated':
        inventory(tmp_path,{'a.txt':b'a'})
    elif kind=='modified':
        (tmp_path/'a.txt').write_bytes(b'changed')
    elif kind=='duplicate':
        line=(tmp_path/'SIMULATION_CHECKSUMS.sha256').read_text().splitlines()[0]
        (tmp_path/'SIMULATION_CHECKSUMS.sha256').write_text(line+'\n'+line+'\n')
    else:
        inventory(tmp_path,{'../a.txt':b'a'})
    with pytest.raises(RuntimeError):
        ssd.verify_copy()


def test_copy_check_performs_no_network_requests(tmp_path,monkeypatch):
    monkeypatch.chdir(Path.cwd())
    monkeypatch.setattr(ssd,'ROOT',tmp_path)
    (tmp_path/'SIMULATION_PACKAGE_ID.txt').write_text('test')
    inventory(tmp_path,{'SIMULATION_PACKAGE_ID.txt':b'test'})
    monkeypatch.setattr(sys,'argv',['simulation_runtime.py','--verify-copy'])
    monkeypatch.setattr(ssd,'json_get',lambda *args:pytest.fail('Network used during offline copy verification'))
    ssd.main()


def test_check_only_does_not_silently_skip_running_app(tmp_path,monkeypatch):
    monkeypatch.chdir(Path.cwd())
    monkeypatch.setattr(ssd,'ROOT',tmp_path)
    (tmp_path/'SIMULATION_PACKAGE_ID.txt').write_text('test')
    instance=hashlib.sha256(('test|'+str(tmp_path).casefold()).encode()).hexdigest()[:16]
    monkeypatch.setattr(sys,'argv',['simulation_runtime.py','--check-only'])
    monkeypatch.setattr(ssd,'json_get',lambda *args:{'instance':instance})
    with pytest.raises(RuntimeError,match='Stop the Simulation server'):
        ssd.main()


def test_another_process_cannot_acquire_live_instance_lock(tmp_path):
    lock=ssd.take_lock(tmp_path)
    try:
        child="import msvcrt,sys; f=open(sys.argv[1],'r+b'); msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)"
        result=subprocess.run([sys.executable,'-c',child,str(tmp_path/'instance.lock')],capture_output=True,check=False)
        assert result.returncode!=0
    finally:
        lock.close()
    ssd.take_lock(tmp_path).close()


def test_shutdown_error_is_not_reported_as_stopped(tmp_path,monkeypatch):
    (tmp_path/'postmaster.pid').write_text('1')
    def failure(*args,**kwargs):
        raise subprocess.CalledProcessError(1,['pg_ctl'])
    monkeypatch.setattr(ssd,'pg',failure)
    with pytest.raises(subprocess.CalledProcessError):
        ssd.stop_database(Path('.'),tmp_path,Path('.'))


def test_relative_state_path_is_resolved_from_caller_folder(tmp_path,monkeypatch):
    package=tmp_path/'package'
    package.mkdir()
    (package/'SIMULATION_PACKAGE_ID.txt').write_text('test')
    receiving=tmp_path/'receiving'
    receiving.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ssd,'ROOT',package)
    monkeypatch.setattr(sys,'argv',['simulation_runtime.py','--stop','--state-dir','receiving'])
    ssd.main()
    assert (receiving/'stop.request').is_file()
    assert not (package/'receiving').exists()
