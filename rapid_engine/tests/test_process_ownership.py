"""Real Windows lifecycle check using owned sleeping children, not a solver."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import pytest

@pytest.mark.skipif(os.name != 'nt', reason='Windows portable runtime lifecycle')
def test_abrupt_owner_exit_stops_exact_owned_child():
    root = Path(__file__).resolve().parents[2]
    script = (
        'import subprocess,sys,time; from rapid_engine.process_ownership import own_child; '
        'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"],creationflags=subprocess.CREATE_NO_WINDOW); '
        'lease=own_child(child); print(child.pid,flush=True); time.sleep(60)'
    )
    parent = subprocess.Popen([sys.executable, '-B', '-c', script], cwd=root, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    handle = None
    try:
        line = parent.stdout.readline().strip()
        assert line.isdigit(), parent.stderr.read() if parent.poll() is not None else line
        handle = kernel.OpenProcess(0x100000 | 0x1000 | 0x0001, False, int(line))
        assert handle
        parent.terminate(); parent.wait(timeout=10)
        assert kernel.WaitForSingleObject(handle, 5000) == 0, 'Owned child survived abrupt service termination'
    finally:
        if parent.poll() is None:parent.terminate(); parent.wait(timeout=10)
        if handle:
            if kernel.WaitForSingleObject(handle, 0) != 0:kernel.TerminateProcess(handle, 1)
            kernel.CloseHandle(handle)
