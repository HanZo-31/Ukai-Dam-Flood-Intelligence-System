"""Transactional internal B1 producer adapter; not B2's public API."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.db.models import ProcessingRun, Scenario
from services.api.app.repositories.asset_repository import AssetRepository
from services.api.app.repositories.impact_repository import ImpactRepository
from services.api.app.repositories.run_repository import RunRepository
from services.api.app.schemas import validate_storage_uri
from services.api.app.storage import LocalObjectStore


class OutputAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_type: str = Field(min_length=1, max_length=100)
    storage_uri: str
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    crs: str | None = Field(default=None, pattern=r"^EPSG:\d+$")

    @field_validator("storage_uri")
    @classmethod
    def validate_uri(cls, value: str) -> str:
        return validate_storage_uri(value)


class ImpactValues(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    max_depth_m: float | None = Field(default=None, ge=0)
    flooded_area_km2: float | None = Field(default=None, ge=0)
    population_exposed: int | None = Field(default=None, ge=0)
    buildings_exposed: int | None = Field(default=None, ge=0)


class CompletedBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(min_length=1, max_length=150)
    assets: list[OutputAsset] = Field(min_length=1)
    impact: ImpactValues

    @field_validator("assets")
    @classmethod
    def require_distinct_assets(cls, assets):
        if len({asset.storage_uri for asset in assets}) != len(assets):
            raise ValueError("output storage URIs must be distinct")
        return assets


def start_run(session: Session, scenario_id: str, run_id: str, stage: str = "model"):
    scenario = session.scalar(select(Scenario).where(Scenario.scenario_id == scenario_id).with_for_update())
    if scenario is None or scenario.status not in {"registered", "queued", "failed"}:
        raise ValueError("scenario is missing or cannot start a new run in its current state")
    run = RunRepository(session).start(scenario_id=scenario_id, run_id=run_id, stage=stage)
    scenario.status = "running"
    session.flush()
    return run


def complete_run(session: Session, bundle: CompletedBundle, store: LocalObjectStore):
    bundle = CompletedBundle.model_validate(bundle.model_dump())
    # Prevent partial completion even if callers catch a late error and commit.
    with session.begin_nested():
        return _complete_run(session, bundle, store)


def _complete_run(session: Session, bundle: CompletedBundle, store: LocalObjectStore):
    run = session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == bundle.run_id).with_for_update())
    if run is None or run.status != "running":
        raise ValueError("run must exist and be running before completion")
    scenario = session.scalar(select(Scenario).where(Scenario.scenario_id == run.scenario_id).with_for_update())
    if scenario.status != "running":
        raise ValueError("scenario must be running before completion")
    for asset in bundle.assets:
        store.verify(asset.storage_uri, asset.checksum)
        if asset.crs and asset.crs != scenario.crs:
            raise ValueError("output CRS must match the registered scenario CRS")
    for asset in bundle.assets:
        AssetRepository(session).add(scenario_id=scenario.scenario_id, data_mode=scenario.data_mode, **asset.model_dump())
    ImpactRepository(session).upsert(scenario.scenario_id, data_mode=scenario.data_mode, **bundle.impact.model_dump())
    RunRepository(session).finish(run, status="completed", metadata_json={"output_count": len(bundle.assets)})
    scenario.status = "completed"
    session.flush()
    return run


def fail_run(session: Session, run_id: str, error_code: str):
    run = session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == run_id).with_for_update())
    if run is None or run.status != "running":
        raise ValueError("run must exist and be running before failure")
    scenario = session.scalar(select(Scenario).where(Scenario.scenario_id == run.scenario_id).with_for_update())
    if scenario.status != "running":
        raise ValueError("scenario must be running before failure")
    RunRepository(session).finish(run, status="failed", metadata_json={"error_code": error_code})
    scenario.status = "failed"
    session.flush()
    return run
