"""Validate candidate V1 published-manifest metadata; never register/run a model."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError
from services.api.app.published_contract import PublishedScenarioManifest, require_publishable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--allow-draft", action="store_true", help="Validate draft/rejected metadata for review only")
    args = parser.parse_args()
    try:
        manifest = PublishedScenarioManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
        if not args.allow_draft:
            require_publishable(manifest)
    except ValidationError as exc:
        # Report field/type, not payloads, local paths or embedded credentials.
        for error in exc.errors(include_input=False, include_url=False):
            location = ".".join(map(str, error["loc"])) or "manifest"
            print(f"invalid: {location} ({error['type']})", file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("invalid: manifest is unreadable or not approved for publication", file=sys.stderr)
        return 1
    print(f"metadata valid: {manifest.scenario_id}, status={manifest.status}, data_mode={manifest.data_mode}")
    print("Schema/semantic checks only: asset bytes not verified; nothing registered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
