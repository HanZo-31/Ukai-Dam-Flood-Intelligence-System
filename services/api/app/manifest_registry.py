from pathlib import Path

from sqlalchemy.orm import Session

from services.api.app.repositories.scenario_repository import ScenarioRepository
from services.api.app.schemas import ScenarioManifest
from services.api.app.storage import LocalObjectStore


def verify_manifest(manifest: ScenarioManifest, store: LocalObjectStore) -> None:
    for item in manifest.inputs:
        store.verify(item.storage_uri, item.checksum)
    if manifest.assumptions_url:
        if not store.resolve_uri(manifest.assumptions_url).is_file():
            raise ValueError("assumptions object is missing")


def register_manifest(session: Session, manifest: ScenarioManifest, store: LocalObjectStore):
    manifest = ScenarioManifest.model_validate(manifest.model_dump())
    verify_manifest(manifest, store)
    repository = ScenarioRepository(session)
    if repository.get(manifest.scenario_id):
        raise ValueError(f"scenario already exists: {manifest.scenario_id}")
    # Storage cannot share a DB transaction: a failed DB write may leave an
    # immutable manifest object, which is safe to retry with identical bytes.
    store.put(f"scenarios/{manifest.scenario_id}/manifest.json", manifest.model_dump_json(indent=2).encode("utf-8"))
    return repository.register(manifest)
