"""Explicit local-only prototype enablement and bounded operator admission."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat

from pydantic import Field, model_validator
from typing import Literal
from services.api.app.published_contract import Checksum, ContractModel, Identifier

MAX_ADMISSION_BYTES = 1024 * 1024


def parse_json_bytes(raw, maximum):
    if len(raw) > maximum:
        raise ValueError("JSON size exceeds limit")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def bad_constant(value):
        raise ValueError("Nonfinite JSON value")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)


def regular_json(path, maximum):
    """Bounded unchanged regular-file snapshot; never block opening a FIFO."""
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or path.is_symlink()
            or getattr(before, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)):
        raise ValueError("Regular local file required")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > maximum:
            raise ValueError("Regular bounded file required")
        raw = handle.read(maximum + 1)
        after = os.fstat(handle.fileno())
    current = path.lstat()
    # Windows path stat reports creation time while fd stat can report change
    # time. Compare ctime within each API, never across those two meanings.
    keys = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, key) != getattr(opened, key) or getattr(opened, key) != getattr(after, key)
           or getattr(after, key) != getattr(current, key) for key in keys):
        raise ValueError("File changed during read")
    if opened.st_ctime_ns != after.st_ctime_ns or before.st_ctime_ns != current.st_ctime_ns:
        raise ValueError("File changed during read")
    return parse_json_bytes(raw, maximum)


class AdmissionEntry(ContractModel):
    scenario_id: Identifier
    run_id: Identifier
    manifest_checksum: Checksum


class Admission(ContractModel):
    schema_version: Literal["1.0.0"]
    entries: list[AdmissionEntry] = Field(max_length=1000)

    @model_validator(mode="after")
    def unique(self):
        if len({entry.scenario_id for entry in self.entries}) != len(self.entries):
            raise ValueError("Duplicate admission identity")
        return self


@dataclass(frozen=True)
class PrototypeSettings:
    admission_file: Path

    def admission(self):
        try:
            return Admission.model_validate(regular_json(self.admission_file, MAX_ADMISSION_BYTES))
        except (ValueError, OSError, RecursionError, TypeError) as error:
            raise ValueError("Prototype admission is unavailable or invalid.") from error


def prototype_settings(environment=None):
    env = os.environ if environment is None else environment
    try:
        flag = env.get("B2_ENABLE_PROTOTYPE_PREVIEW", "false")
        if flag not in {"false", "0", "true", "1"}:
            raise ValueError()
        if flag in {"false", "0"}:
            return None
        if env.get("B2_ENV", "local") != "local" or env.get("B2_PROTOTYPE_LAUNCH_BOUND") != "127.0.0.1":
            raise ValueError()
        raw = env.get("B2_PROTOTYPE_ADMISSION_FILE", "")
        path = Path(raw)
        if not raw or not path.is_absolute():
            raise ValueError()
        settings = PrototypeSettings(path)
        settings.admission()
        return settings
    except (ValueError, TypeError, OSError):
        raise ValueError("Prototype preview configuration is invalid.") from None
