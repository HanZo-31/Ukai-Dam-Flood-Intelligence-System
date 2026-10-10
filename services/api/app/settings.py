"""B2-only production configuration. Never loads B1's development .env."""
from dataclasses import dataclass, field
import ipaddress
import os
from pathlib import Path
import re

from sqlalchemy.engine import make_url


CONFIG_ERROR = "Production database, storage, scratch or worker configuration is invalid."


@dataclass(frozen=True)
class ProductionSettings:
    database_url: str = field(repr=False)
    object_root: Path = field(repr=False)
    scratch_root: Path = field(repr=False)
    storage_id: str
    workers: int
    scratch_min_bytes: int


def production_settings(environment=None, *, required=False):
    environment = os.environ if environment is None else environment
    try:
        mode = environment.get("B2_ENV", "local")
        if mode not in {"local", "production"} or (required and mode != "production"):
            raise ValueError()
        if mode == "local":
            return None
        direct, secret = environment.get("DATABASE_URL"), environment.get("DATABASE_URL_FILE")
        if bool(direct) == bool(secret):
            raise ValueError()
        if secret:
            with Path(secret).open("rb") as stream:
                raw = stream.read(8193)
                if len(raw) > 8192:
                    raise ValueError()
                value = raw.decode("utf-8").strip()
        else:
            value = direct
        if not value or len(value.encode("utf-8")) > 8192 or any(ord(c) < 32 for c in value):
            raise ValueError()
        url = make_url(value)
        if (url.drivername != "postgresql+psycopg" or not url.host or not url.database
                or not url.username or not url.password
                or not 1 <= (5432 if url.port is None else url.port) <= 65535):
            raise ValueError()
        # A container must never silently connect to itself or permit libpq
        # multi-host, socket, service-file or query-string host overrides.
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", url.host) or url.host.rstrip(".").lower() == "localhost":
            raise ValueError()
        try:
            address = ipaddress.ip_address(url.host)
        except ValueError:
            address = None
        mapped = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) else None
        if address and (address.is_loopback or address.is_unspecified
                        or (mapped is not None and mapped.is_loopback)):
            raise ValueError()
        allowed = {"sslmode", "sslrootcert", "sslcert", "sslkey", "sslcrl"}
        if set(url.query) - allowed or any(not isinstance(v, str) or not v for v in url.query.values()):
            raise ValueError()
        if "sslmode" in url.query and url.query["sslmode"] not in {
                "disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
            raise ValueError()
        root, scratch = (Path(environment.get(key, "")) for key in ("OBJECT_STORAGE_ROOT", "TMPDIR"))
        if not all(p.is_absolute() and p.is_dir() for p in (root, scratch)):
            raise ValueError()
        root, scratch = root.resolve(), scratch.resolve()
        if scratch.is_relative_to(root) or root.is_relative_to(scratch):
            raise ValueError()
        if not os.access(root, os.R_OK | os.X_OK) or not os.access(scratch, os.R_OK | os.W_OK | os.X_OK):
            raise ValueError()
        storage_id = environment.get("B2_STORAGE_ID", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", storage_id):
            raise ValueError()
        workers = int(environment.get("B2_WORKERS", "1"))
        minimum = int(environment.get("B2_SCRATCH_MIN_BYTES", str(8 * 1024 * 1024)))
        if not 1 <= workers <= 8 or not 1024 * 1024 <= minimum <= 1024 * 1024 * 1024:
            raise ValueError()
        return ProductionSettings(value, root, scratch, storage_id, workers, minimum)
    except Exception:
        # Never include rejected values, paths, credentials or parser exceptions.
        raise ValueError(CONFIG_ERROR) from None


def business_database_url(settings):
    """Enforce bounded, read-only defaults without changing B1's DB loader."""
    return make_url(settings.database_url).update_query_dict({
        "connect_timeout": "2", "options": "-c default_transaction_read_only=on "
        "-c statement_timeout=10000 -c lock_timeout=1000 -c search_path=public,pg_catalog",
    }).render_as_string(hide_password=False)
