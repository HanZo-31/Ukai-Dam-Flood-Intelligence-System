"""Verified synthetic fixture used by seed_db.py and integration tests."""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from services.api.app.db.models import ScenarioInput, StatusReading
from services.api.app.manifest_registry import register_manifest, verify_manifest
from services.api.app.repositories.scenario_repository import ScenarioRepository
from services.api.app.repositories.status_repository import StatusRepository
from services.api.app.result_registration import CompletedBundle, complete_run, start_run
from services.api.app.schemas import ScenarioManifest

ROOT = Path(__file__).resolve().parents[1]


def build_demo(store) -> tuple[ScenarioManifest, CompletedBundle]:
    source = ROOT / "database" / "seeds"
    template = json.loads((source / "demo_scenarios.json").read_text(encoding="utf-8"))[0]
    scenario_id = "demo-monsoon-local-002"
    template.update(scenario_id=scenario_id, input_dataset_version="synthetic-demo-v2")
    inputs = []
    for input_type, filename in [("rainfall_forecast", "rainfall-demo.csv"), ("reservoir_curve", "reservoir-curve-demo.csv")]:
        uri, checksum = store.put(f"scenarios/{scenario_id}/inputs/{filename}", (source / filename).read_bytes())
        inputs.append(dict(input_type=input_type, storage_uri=uri, checksum=checksum, dataset_version="synthetic-demo-v2"))
    assumptions, _ = store.put(f"scenarios/{scenario_id}/inputs/assumptions.md", (source / "assumptions-demo.md").read_bytes())
    template.update(inputs=inputs, assumptions_url=assumptions)
    manifest = ScenarioManifest.model_validate(template)
    run_id = "demo-local-002-run-001"
    uri, checksum = store.put(f"scenarios/{scenario_id}/runs/{run_id}/outputs/depth-demo.csv", (source / "depth-demo.csv").read_bytes())
    bundle = CompletedBundle.model_validate(dict(run_id=run_id, assets=[dict(asset_type="depth_csv", storage_uri=uri, checksum=checksum, crs=manifest.crs)], impact=dict(max_depth_m=1.2, flooded_area_km2=0.02, population_exposed=0, buildings_exposed=0)))
    return manifest, bundle


def seed(session, store):
    manifest, bundle = build_demo(store)
    verify_manifest(manifest, store)
    repository = ScenarioRepository(session)
    scenario = repository.get(manifest.scenario_id)
    if scenario:
        expected = manifest.model_dump(exclude={"inputs"})
        if any(getattr(scenario, key) != value for key, value in expected.items()):
            raise ValueError("existing demo metadata differs; create a new version instead of replacing it")
        rows = session.scalars(select(ScenarioInput).where(ScenarioInput.scenario_id == manifest.scenario_id)).all()
        actual = {(row.input_type, row.storage_uri, row.checksum, row.dataset_version) for row in rows}
        wanted = {(i.input_type, i.storage_uri, i.checksum, i.dataset_version) for i in manifest.inputs}
        if actual != wanted:
            raise ValueError("existing demo inputs differ")
    else:
        scenario = register_manifest(session, manifest, store)
    store.put(f"scenarios/{manifest.scenario_id}/manifest.json", manifest.model_dump_json(indent=2).encode("utf-8"))
    if scenario.status != "completed":
        start_run(session, scenario.scenario_id, bundle.run_id, stage="synthetic_contract_test")
        complete_run(session, bundle, store)
    else:
        from services.api.app.repositories.asset_repository import AssetRepository
        from services.api.app.repositories.impact_repository import ImpactRepository
        from services.api.app.repositories.run_repository import RunRepository
        assets = AssetRepository(session).list_for_scenario(scenario.scenario_id)
        actual = {(a.asset_type, a.storage_uri, a.checksum, a.crs) for a in assets}
        wanted = {(a.asset_type, a.storage_uri, a.checksum, a.crs) for a in bundle.assets}
        impact = ImpactRepository(session).get(scenario.scenario_id)
        run = RunRepository(session).get(bundle.run_id)
        if actual != wanted or impact is None or run is None or run.status != "completed":
            raise ValueError("existing completed demo is inconsistent")
        if any(getattr(impact, key) != value for key, value in bundle.impact.model_dump().items()):
            raise ValueError("existing demo impact differs")
        for asset in bundle.assets:
            store.verify(asset.storage_uri, asset.checksum)
    reading_time = datetime(2026, 10, 2, tzinfo=timezone.utc)
    if session.scalar(select(StatusReading).where(StatusReading.reading_time == reading_time, StatusReading.data_mode == "demo")) is None:
        StatusRepository(session).add(reading_time=reading_time, reservoir_level_m=101.0, inflow_m3s=20.0, release_m3s=15.0, data_mode="demo")
    return scenario.scenario_id, scenario.status
