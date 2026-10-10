# Local setup

1. Create a virtual environment if missing and install the pinned requirements. Copy `.env.example` to `.env` only if `.env` is absent; preserve existing configuration and keep `DATABASE_URL` pointed at the Docker database.
2. Start the database with `docker compose up -d --build`; wait for its health check to pass.

The database port binds only to 127.0.0.1 for local testing. Application,
migration and backup connections normalize localhost to IPv4 and default to a
five-second connection timeout; an explicitly configured timeout is preserved.
Remote access requires a separately reviewed deployment configuration.
3. Apply the complete schema with `.\.venv\Scripts\python.exe -m alembic upgrade head`.
4. Load the safe-to-rerun B1 demo data with `.\.venv\Scripts\python.exe scripts\seed_db.py`.
5. Run `.\.venv\Scripts\python.exe -m pytest` before accepting a schema or manifest-contract change. Git/CI is deferred; no commit is required for local testing.

For a new environment only:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The currently tested environment uses Python 3.13; the blueprint names 3.12.
Python 3.12 compatibility has not been verified in this batch. Do not replace a
working environment merely to run this guide. For daily checks, failures and
recovery boundaries use [B1 operations](b1-operations.md).

To register a new scenario, create a JSON document matching `tests/fixtures/scenario_manifest.json` and run:

```powershell
.\.venv\Scripts\python.exe scripts\register_scenario.py path\to\manifest.json
```

The command validates the manifest and checks actual files and SHA-256 hashes
under `OBJECT_STORAGE_ROOT` before writing the scenario and its immutable input
references in one transaction. Duplicate scenario IDs are rejected. The JSON
test fixture only exercises schema parsing; its placeholder file does not exist
and is therefore rejected by the registration CLI.

The seed publishes actual synthetic demo files and registers inputs, a run,
result asset, impact summary, and one status reading. Repeating it verifies
existing data without adding duplicates. It preserves the original legacy demo.

Run `.\.venv\Scripts\python.exe -m alembic check` to detect model/schema drift.
The integration tests create and remove a unique `b1_verify_<uuid>` schema.
Migration downgrade tests never target the active `public` schema.
