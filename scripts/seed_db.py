"""Load idempotent B1 demo manifests after running Alembic migrations."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.app.db.session import SessionLocal
from services.api.app.repositories.scenario_repository import ScenarioRepository
from services.api.app.schemas import ScenarioManifest
from scripts.demo_seed import seed
from services.api.app.storage import default_store


def main() -> int:
    with SessionLocal.begin() as session:
        scenario_id, status = seed(session, default_store())
    print(f"verified demo ready: {scenario_id}, status={status}; safe to rerun")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
