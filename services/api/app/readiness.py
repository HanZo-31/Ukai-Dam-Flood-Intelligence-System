"""Read-only dependency probes, isolated from the business connection pool."""
import asyncio
import json
import shutil
import tempfile
from threading import Lock
from typing import TypedDict, cast

import psycopg
from sqlalchemy.engine import make_url
from sqlalchemy.dialects import postgresql
from services.api.app.db.base import Base
from services.api.app.db import models  # noqa: F401 -- registers unchanged B1 metadata


EXPECTED_REVISION = "g05b8eab1001"
MARKER = ".b2-storage-ready.json"
RESPONSE_BUDGET_SECONDS = 4


class TLSParameters(TypedDict, total=False):
    sslmode: str
    sslrootcert: str
    sslcert: str
    sslkey: str
    sslcrl: str


def expected_columns():
    def typename(column):
        value = str(column.type.compile(dialect=postgresql.dialect())).lower()
        return value.replace("varchar", "character varying").replace("float", "double precision")
    return {(table.name, column.name): (typename(column), column.nullable)
            for table in Base.metadata.tables.values() for column in table.columns}


def storage_probe(settings):
    # Only local bind/volume storage is supported in this release. A marker
    # detects wrong/empty mounts; it does not assert scientific asset quality.
    marker = settings.object_root / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("storage unavailable")
    with marker.open("rb") as stream:
        data = stream.read(4097)
    value = json.loads(data) if len(data) <= 4096 else None
    if (not isinstance(value, dict) or type(value.get("schema_version")) is not int
            or value != {"schema_version": 1, "store_id": settings.storage_id}):
        raise ValueError("storage unavailable")
    if shutil.disk_usage(settings.scratch_root).free < settings.scratch_min_bytes:
        raise ValueError("scratch unavailable")
    # Explicit dir avoids tempfile's cached development default. Context exit
    # removes the probe even when a read/write/flush fails.
    with tempfile.TemporaryFile(dir=settings.scratch_root) as stream:
        stream.write(b"b2-ready")
        stream.flush()
        stream.seek(0)
        if stream.read() != b"b2-ready":
            raise ValueError("scratch unavailable")


async def database_probe(settings):
    url = make_url(settings.database_url)
    # production_settings already restricts these to single-string TLS options.
    tls = cast(TLSParameters, dict(url.query))
    connection = await psycopg.AsyncConnection.connect(
        host=url.host, port=url.port or 5432, dbname=url.database, user=url.username,
        password=url.password, **tls, connect_timeout=2, autocommit=True,
        application_name="b2-readiness",
        options="-c default_transaction_read_only=on -c statement_timeout=1000 "
                "-c lock_timeout=500 -c search_path=public,pg_catalog")
    try:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT version_num FROM public.alembic_version")
            if await cursor.fetchall() != [(EXPECTED_REVISION,)]:
                raise ValueError("schema unavailable")
            await cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')")
            if await cursor.fetchone() != (True,):
                raise ValueError("spatial database unavailable")
            await cursor.execute("SELECT public.ST_SRID(public.ST_SetSRID(public.ST_MakePoint(0,0),4326))")
            if await cursor.fetchone() != (4326,):
                raise ValueError("spatial database unavailable")
            # Effective membership includes inherited/SET ROLE privileges:
            # reject powerful parent roles, not just direct role attributes.
            await cursor.execute("""SELECT EXISTS(SELECT 1 FROM pg_roles WHERE
                (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls)
                AND pg_has_role(current_user, oid, 'MEMBER')),
                has_database_privilege(current_database(), 'CREATE'),
                has_schema_privilege('public', 'CREATE')""")
            role_privileges = await cursor.fetchone()
            if role_privileges is None or any(role_privileges):
                raise ValueError("reader privileges unavailable")
            await cursor.execute("""SELECT c.relname, a.attname,
                lower(format_type(a.atttypid, a.atttypmod)), NOT a.attnotnull
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                JOIN pg_attribute a ON a.attrelid=c.oid
                WHERE n.nspname='public' AND a.attnum>0 AND NOT a.attisdropped""")
            columns = {(table, column): (kind, nullable)
                       for table, column, kind, nullable in await cursor.fetchall()}
            if any(columns.get(key) != value for key, value in expected_columns().items()):
                raise ValueError("schema unavailable")
            await cursor.execute("""SELECT c.relname,
                has_table_privilege(c.oid, 'SELECT'),
                has_table_privilege(c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'),
                EXISTS(SELECT 1 FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0
                    AND NOT a.attisdropped AND has_column_privilege(c.oid, a.attnum, 'INSERT,UPDATE,REFERENCES'))
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')""")
            privileges = {name: (read, write or column_write)
                          for name, read, write, column_write in await cursor.fetchall()}
            if any(write for read, write in privileges.values()) or any(privileges.get(name) != (True, False)
                   for name in {*Base.metadata.tables, "alembic_version"}):
                raise ValueError("reader privileges unavailable")
            await cursor.execute("""SELECT EXISTS(SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
                AND CASE WHEN c.relkind='S'
                    THEN has_sequence_privilege(c.oid, 'USAGE,UPDATE') ELSE false END)""")
            if await cursor.fetchone() != (False,):
                raise ValueError("reader privileges unavailable")
    finally:
        # Close directly rather than await rollback on an unresponsive server.
        await connection.close()


class Readiness:
    def __init__(self, settings):
        self.settings = settings
        self._gate = Lock()
        self._task = None

    async def _probe(self):
        try:
            # A stalled mount must not block liveness/event-loop progress. The
            # gate remains held until this one worker finishes; repeated probes
            # cannot accumulate threads/connections after a timeout.
            await asyncio.to_thread(storage_probe, self.settings)
            async with asyncio.timeout(4):
                await database_probe(self.settings)
            return True
        except Exception:
            return False

    def _finished(self, task):
        self._task = None
        self._gate.release()
        if not task.cancelled():
            task.exception()  # consume unexpected failures without secret logs

    async def check(self):
        if self.settings is None or not self._gate.acquire(blocking=False):
            return False
        task = asyncio.create_task(self._probe())
        self._task = task  # keep a strong reference after the response deadline
        task.add_done_callback(self._finished)
        # Do not wait for driver cancellation cleanup or an uninterruptible
        # filesystem syscall. Only one outstanding probe exists per worker.
        done, _ = await asyncio.wait({task}, timeout=RESPONSE_BUDGET_SECONDS)
        return task.result() if done else False
