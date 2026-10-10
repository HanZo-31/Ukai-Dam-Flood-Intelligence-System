"""Immutable local object store for reproducible B1 demos and integration tests."""
import hashlib
import os
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import url2pathname
import tempfile
from threading import Lock

_DIRECTORY_LOCK = Lock()


def publish_no_replace(temporary_path: Path, path: Path) -> None:
    """Atomically publish without replacement, including restricted Windows."""
    try:
        os.link(temporary_path, path)
    except PermissionError:
        if os.name != "nt":
            raise
        try:
            os.rename(temporary_path, path)
        except PermissionError:
            # Windows may report access denied rather than file-exists when a
            # concurrent publisher owns the destination. Caller verifies bytes.
            if path.exists():
                raise FileExistsError("immutable destination exists") from None
            raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


class LocalObjectStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path_for_key(self, key: str) -> Path:
        parts = PurePosixPath(key)
        if not key or parts.is_absolute() or "\\" in key or ":" in key or any(p in {"..", "."} for p in key.split("/")):
            raise ValueError("object key must be a relative path without traversal")
        target = (self.root / Path(*parts.parts)).resolve()
        if not target.is_relative_to(self.root) or target == self.root:
            raise ValueError("object key escapes storage root")
        return target

    def put(self, key: str, content: bytes) -> tuple[str, str]:
        path = self.path_for_key(key)
        checksum = "sha256:" + hashlib.sha256(content).hexdigest()
        with _DIRECTORY_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if sha256_file(path) != checksum:
                raise ValueError("immutable object already exists with different content")
        else:
            temporary_path = None
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as handle:
                    temporary_path = Path(handle.name)
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                # Hard-link publication is atomic and never overwrites a key.
                publish_no_replace(temporary_path, path)
            except FileExistsError:
                if sha256_file(path) != checksum:
                    raise ValueError("concurrent immutable object conflict")
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
        return path.as_uri(), checksum

    def resolve_uri(self, uri: str) -> Path:
        parsed = urlsplit(uri)
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"} or parsed.query or parsed.fragment:
            raise ValueError("local demo verification requires a local file:// URI; S3 needs a configured adapter")
        path = Path(url2pathname(parsed.path)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("object URI is outside the configured storage root")
        return path

    def verify(self, uri: str, checksum: str) -> None:
        path = self.resolve_uri(uri)
        if not path.is_file():
            raise ValueError("referenced object does not exist")
        if sha256_file(path) != checksum:
            raise ValueError("object SHA-256 checksum mismatch")


def default_store() -> LocalObjectStore:
    project = Path(__file__).resolve().parents[3]
    return LocalObjectStore(Path(os.getenv("OBJECT_STORAGE_ROOT", str(project / "data" / "object-store"))))
