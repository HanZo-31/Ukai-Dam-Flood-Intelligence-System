"""Generate or check the deterministic B2 OpenAPI artifact without DB queries."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preview", action="store_true", help="Generate separate preview-inclusive documentation, not enable a server")
    parser.add_argument("--check", action="store_true", help="Fail on drift; do not modify the artifact.")
    args = parser.parse_args()
    # Contract export is independent of operator admission; no service/query is
    # started. A default export can never accidentally include inherited preview.
    os.environ["B2_ENABLE_PROTOTYPE_PREVIEW"] = "false"
    from services.api.app.main import app
    if args.preview:
        from fastapi import FastAPI
        from services.api.app.api.v1.prototypes import router
        from services.api.app.prototype_runtime import build_preview_openapi
        if not isinstance(app, FastAPI):
            raise ValueError("Export in the documented local profile")
        app.include_router(router)
        payload = build_preview_openapi(app)
    else:
        payload = app.openapi()
    args.output = args.output or ROOT / ("docs/contracts/b2-prototype-openapi-v1.json" if args.preview else "docs/contracts/b2-openapi-v1.json")
    payload = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            print("B2 OpenAPI artifact is missing or stale; regenerate and review it.", file=sys.stderr)
            return 1
        print("B2 OpenAPI artifact matches the live documentation contract.")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print("B2 OpenAPI artifact generated; review the candidate before handoff.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
