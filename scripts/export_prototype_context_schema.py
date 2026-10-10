"""Print or check context schema; no file writes, DB, GIS or HTTP startup."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.api.app.prototype_context import prototype_context_json_schema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    schema = prototype_context_json_schema()
    if args.check:
        try:
            stored = json.loads(args.check.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print("Context schema is unreadable or invalid.", file=sys.stderr)
            return 1
        if stored != schema:
            print("Context schema differs from executable contract.", file=sys.stderr)
            return 1
        print("Context schema matches executable contract.")
        return 0
    print(json.dumps(schema, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
