"""Bounded local snapshot admission; Linux reservations coordinate workers."""
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat
import tempfile
from threading import Lock

MIB = 1024 * 1024
_lock = Lock()
_pending: dict[str, int] = {}


@dataclass(frozen=True)
class DownloadPolicy:
    scratch_root: Path
    max_bytes: int = 512 * MIB
    reserve_bytes: int = 8 * MIB
    verification_seconds: int = 60
    stream_seconds: int = 300


def download_policy(environment=None):
    environment = os.environ if environment is None else environment
    try:
        root = Path(environment.get('TMPDIR') or tempfile.gettempdir()).resolve()
        maximum = int(environment.get('B2_DOWNLOAD_MAX_BYTES', str(512 * MIB)))
        reserve = int(environment.get('B2_SCRATCH_MIN_BYTES', str(8 * MIB)))
        seconds = int(environment.get('B2_DOWNLOAD_VERIFY_SECONDS', '60'))
        streaming = int(environment.get('B2_DOWNLOAD_STREAM_SECONDS', '300'))
        if (not root.is_dir() or not MIB <= maximum <= 8 * 1024 * MIB
                or not MIB <= reserve <= 1024 * MIB or not 1 <= seconds <= 300 or not 1 <= streaming <= 3600):
            raise ValueError()
        return DownloadPolicy(root, maximum, reserve, seconds, streaming)
    except (ValueError, TypeError, OSError):
        raise ValueError('Download capacity configuration is invalid.') from None


class SnapshotLease:
    """File-compatible handle with idempotent local reservation cleanup."""
    def __init__(self, handle, key=None, reservation=0):
        self.handle, self.key, self.reservation = handle, key, reservation

    def __getattr__(self, name):
        return getattr(self.handle, name)

    def close(self):
        try:
            self.handle.close()
        finally:
            with _lock:
                if self.reservation:
                    _pending[self.key] -= self.reservation
                    if not _pending[self.key]:
                        del _pending[self.key]
                    self.reservation = 0


@contextmanager
def admission_lock(root):
    # Non-blocking cross-worker serialization: saturation fails safely, not an
    # unbounded waiting queue. The one private lock file contains no metadata.
    if os.name != 'posix':
        yield
        return
    import fcntl
    fd = os.open(root / '.b2-download-admission.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError('invalid admission lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def reserve_snapshot(policy, size):
    if not 0 <= size <= policy.max_bytes:
        raise ValueError('artifact exceeds capacity')
    key = str(policy.scratch_root)
    with _lock, admission_lock(policy.scratch_root):
        if shutil.disk_usage(policy.scratch_root).free - _pending.get(key, 0) < size + policy.reserve_bytes:
            raise OSError('scratch capacity unavailable')
        handle = tempfile.TemporaryFile(mode='w+b', dir=policy.scratch_root)
        try:
            if os.name == 'posix':
                # Real allocation, not sparse truncate. Kernel ENOSPC plus the
                # shared lock prevents concurrent workers oversubscribing tmpfs.
                if size:
                    os.posix_fallocate(handle.fileno(), 0, size)
                return SnapshotLease(handle)
            # Conservative per-process Windows DEVELOPMENT accounting. Linux
            # kernel allocation is the supported multi-worker release profile.
            if size:
                _pending[key] = _pending.get(key, 0) + size
            return SnapshotLease(handle, key, size)
        except BaseException:
            handle.close()
            raise


@contextmanager
def open_local_source(store, uri):
    path = store.resolve_uri(uri)
    if os.name != 'posix':
        if not path.is_file():
            raise ValueError('object must be a regular file')
        with path.open('rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode) or not path.resolve().is_relative_to(store.root):
                raise ValueError('invalid local object')
            yield source
        return
    # Directory descriptors anchor traversal under the configured root, even
    # if a publisher swaps a parent for a symlink between resolve and open.
    parts = path.relative_to(store.root).parts
    if not parts:
        raise ValueError('object must be a file')
    directory = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError('object must be a regular file')
            yield source
    finally:
        os.close(directory)
