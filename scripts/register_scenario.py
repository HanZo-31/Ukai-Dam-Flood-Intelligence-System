"""Register a validated B1 scenario manifest in PostgreSQL."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.db.session import SessionLocal
from services.api.app.manifest_registry import register_manifest
from services.api.app.storage import default_store
from services.api.app.schemas import ScenarioManifest


def register(path: Path) -> str:
    manifest = ScenarioManifest.model_validate_json(path.read_text(encoding="utf-8"))
    with SessionLocal.begin() as session:
        register_manifest(session, manifest, default_store())
    return manifest.scenario_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        print(f"registered scenario: {register(args.manifest)}")
    except (OSError, ValidationError, ValueError) as exc:
        print(f"registration failed: {exc}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("registration failed: database transaction rolled back", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
