"""Read-only local bundle integrity check; no DB writes or approval claims."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from services.api.app.gis_validation import GISInspector
from services.api.app.published_contract import PublishedScenarioManifest, resolve_reference
from services.api.app.storage import default_store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--bundle-root", required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    try:
        manifest = PublishedScenarioManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
        store = default_store()
        store.resolve_uri(resolve_reference(args.bundle_root, "root-validation"))
        for reference, checksum in [(manifest.assumptions_url, manifest.assumptions_checksum),
                                    (manifest.quality.report_reference, manifest.quality.report_checksum),
                                    *((item.source_reference, item.checksum) for item in manifest.datasets)]:
            store.verify(resolve_reference(args.bundle_root, reference), checksum)
        inspector = GISInspector()
        seen = set()
        for role in sorted(manifest.assets, key=lambda role: (not role.endswith("_cog"), role)):
            metadata = manifest.asset_metadata[role]
            uri = resolve_reference(args.bundle_root, manifest.assets[role])
            store.verify(uri, metadata.checksum)
            path = store.resolve_uri(uri)
            if path in seen:
                raise ValueError("asset aliases resolve to one object")
            seen.add(path)
            report = inspector(path, role, metadata)
            if manifest.data_mode == "production" and report.synthetic:
                raise ValueError("synthetic assets cannot claim production")
        print(f"GIS integrity verified: {manifest.scenario_id}; assets={len(seen)}; status={manifest.status}; no database writes or scientific approval")
        return 0
    except (ValueError, OSError):
        print("GIS integrity failed: invalid metadata, local references, bytes or GIS content", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
