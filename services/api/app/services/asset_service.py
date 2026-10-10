"""Verify a local registered object into a disk-backed snapshot before serving."""
from dataclasses import dataclass
import hashlib
import re
import os
import time
from typing import BinaryIO

from fastapi import HTTPException
from services.api.app.storage import LocalObjectStore
from services.api.app.services.download_policy import download_policy, reserve_snapshot, open_local_source

CHUNK_SIZE = 1024 * 1024


@dataclass
class VerifiedDownload:
    handle: BinaryIO
    size: int
    checksum: str
    media_type: str
    filename: str
    stream_seconds: int = 300

    def chunks(self, start: int, length: int):
        try:
            self.handle.seek(start)
            while length:
                chunk = self.handle.read(min(CHUNK_SIZE, length))
                if not chunk:
                    raise OSError("Verified snapshot ended before its declared length")
                length -= len(chunk)
                yield chunk
        finally:
            self.handle.close()


def verified_download(store: LocalObjectStore, uri: str, checksum: str,
                      *, media_type: str, filename: str, policy=None) -> VerifiedDownload:
    """Copy/hash once, avoiding a verify-then-reopen race or loading a raster in RAM.

    The configured local store constrains the path. The response reads only this
    verified temporary snapshot, never the original filename. Remote storage
    requires a separately implemented adapter.
    """
    snapshot = None
    try:
        if not isinstance(checksum, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", checksum):
            raise ValueError("Missing registered checksum")
        policy = policy or download_policy()
        deadline = time.monotonic() + policy.verification_seconds
        digest = hashlib.sha256()
        size = 0
        with open_local_source(store, uri) as source:
            original = os.fstat(source.fileno())
            snapshot = reserve_snapshot(policy, original.st_size)
            for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
                if time.monotonic() > deadline or size + len(chunk) > original.st_size:
                    raise ValueError("Object changed or verification budget exceeded")
                digest.update(chunk)
                if snapshot.write(chunk) != len(chunk):
                    raise OSError("Snapshot write incomplete")
                size += len(chunk)
            current = os.fstat(source.fileno())
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if (size != original.st_size or any(getattr(original, f) != getattr(current, f) for f in fields)
                    or time.monotonic() > deadline):
                raise ValueError("Object changed or verification budget exceeded")
        if "sha256:" + digest.hexdigest() != checksum:
            raise ValueError("Object checksum mismatch")
        snapshot.flush()
        snapshot.seek(0)
        return VerifiedDownload(snapshot, size, checksum, media_type, filename, policy.stream_seconds)
    except (ValueError, OSError, TypeError) as error:
        if snapshot is not None:
            snapshot.close()
        raise HTTPException(503, "The registered artifact is unavailable.") from error


def byte_range(value: str | None, size: int) -> tuple[int, int, int]:
    """Return start, length and response status; support one RFC-style byte range."""
    if value is None:
        return 0, size, 200
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value)
    if not match or size == 0 or len(value) > 100:
        raise HTTPException(416, "Requested range is not satisfiable.", headers={"Content-Range": f"bytes */{size}"})
    first, last = match.groups()
    if not first and not last:
        raise HTTPException(416, "Requested range is not satisfiable.", headers={"Content-Range": f"bytes */{size}"})
    if first:
        start, end = int(first), int(last) if last else size - 1
    else:
        suffix = int(last)
        start, end = max(0, size - suffix), size - 1
        if suffix == 0:
            start = size
    if start >= size or end < start:
        raise HTTPException(416, "Requested range is not satisfiable.", headers={"Content-Range": f"bytes */{size}"})
    end = min(end, size - 1)
    return start, end - start + 1, 206
