"""Import a local precomputed bundle with explicit provenance and approval trust."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy.exc import SQLAlchemyError
from services.api.app.db.session import SessionLocal
from services.api.app.published_registry import register_published_bundle
from services.api.app.storage import default_store
from services.api.app.gis_validation import GISInspector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--bundle-root", required=True, help="Trusted file:// root ending in /")
    parser.add_argument("--registered-by", required=True)
    parser.add_argument("--trusted-approver", action="append", default=[], help="Operator-controlled allowlist, not manifest input")
    parser.add_argument("--metadata-only-demo", action="store_true", help="Explicit legacy hash/metadata testing only; never production")
    parser.add_argument("--max-raster-pixels", type=int, default=20_000_000,
                        help="Explicit reviewed single-band GIS inspection budget; default remains 20 million pixels")
    args = parser.parse_args()
    if not 1 <= args.max_raster_pixels <= 1_000_000_000:
        parser.error("Raster pixel budget must be between 1 and 1000000000")
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.metadata_only_demo and payload.get("data_mode") != "demo":
            raise ValueError("metadata-only mode is restricted to demo")
        with SessionLocal.begin() as session:
            bundle = register_published_bundle(session, payload, default_store(), bundle_root_uri=args.bundle_root,
                                               registered_by=args.registered_by, trusted_approvers=set(args.trusted_approver),
                                               asset_inspector=None if args.metadata_only_demo else GISInspector(max_pixels=args.max_raster_pixels))
            identity = bundle.scenario_id
        print(f"published bundle registered: {identity}")
        return 0
    except SQLAlchemyError:
        print("registration failed: database operation rolled back", file=sys.stderr)
    except (ValueError, OSError):
        # Do not echo payloads, credentials or connection details on failure.
        print("registration failed: invalid manifest, trust policy, provenance or local artifacts", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
