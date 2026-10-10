"""Local verification facts for the supported hardened runtime, no secrets."""
import ctypes
import importlib.util
import json
import os
import pyexpat
from pathlib import Path
import stat


ABSENT_EXECUTABLES = ('/usr/bin/infocmp', '/usr/bin/nsenter', '/usr/bin/mount', '/usr/bin/umount',
                      '/usr/bin/perl', '/usr/lib/systemd/systemd-homed')


def runtime_inventory():
    if os.name != 'posix':
        raise ValueError('Runtime inventory is for the Linux API image only.')
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    library = ctypes.CDLL('libexpat.so.1')
    library.XML_ExpatVersion.restype = ctypes.c_char_p
    privileged = [str(path) for directory in ('/usr/bin', '/usr/sbin') for path in Path(directory).rglob('*')
                  if path.is_file() and path.stat().st_mode & (stat.S_ISUID | stat.S_ISGID)]
    return {'uid': os.getuid(), 'effective_capabilities': status['CapEff'].strip(),
            'no_new_privileges': status['NoNewPrivs'].strip() == '1',
            'expat_version': library.XML_ExpatVersion().decode('ascii'),
            'python_expat_version': pyexpat.EXPAT_VERSION,
            'expat_binary_sha256': __import__('hashlib').sha256(Path('/usr/local/lib/libexpat.so.1').read_bytes()).hexdigest(),
            'absent_executables': {path: not Path(path).exists() for path in ABSENT_EXECUTABLES},
            'privileged_executables': privileged,
            'perl_interpreters': [str(path) for path in Path('/usr/bin').glob('perl*') if path.is_file()],
            'pip_absent': importlib.util.find_spec('pip') is None,
            'ensurepip_absent': importlib.util.find_spec('ensurepip') is None,
            'telemetry_exporter_absent': importlib.util.find_spec('opentelemetry.sdk') is None}


if __name__ == '__main__':
    print(json.dumps(runtime_inventory(), sort_keys=True))
