"""Internal producer CLI: start/fail a run, or register verified completion."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from services.api.app.db.session import SessionLocal
from services.api.app.result_registration import CompletedBundle, complete_run, fail_run, start_run
from services.api.app.storage import default_store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    start = commands.add_parser("start")
    start.add_argument("scenario_id")
    start.add_argument("run_id")
    finish = commands.add_parser("complete")
    finish.add_argument("bundle", type=Path)
    fail = commands.add_parser("fail")
    fail.add_argument("run_id")
    fail.add_argument("error_code")
    args = parser.parse_args()
    try:
        with SessionLocal.begin() as session:
            if args.action == "start":
                run = start_run(session, args.scenario_id, args.run_id)
            elif args.action == "fail":
                run = fail_run(session, args.run_id, args.error_code)
            else:
                bundle = CompletedBundle.model_validate_json(args.bundle.read_text(encoding="utf-8"))
                run = complete_run(session, bundle, default_store())
            print(f"run={run.run_id}, status={run.status}")
    except (OSError, ValueError, ValidationError):
        # Validation exceptions may echo input values, paths or credentials.
        print("run registration failed: invalid input, state or local artifacts", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("run registration failed: database transaction rolled back", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
