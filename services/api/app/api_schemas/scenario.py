"""Stable public response schemas for the scenario catalogue."""
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from services.api.app.published_contract import (
    Checksum, ImpactSummary, ParameterUnits, ScenarioParameters, TextValue,
)


class ScenarioSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    scenario_type: str
    status: Literal["approved"] = "approved"
    model_version: str
    input_dataset_version: str
    crs: str
    data_mode: Literal["demo", "production"]
    data_kind: Literal["observed", "simulated", "assumed", "demo"] | None = None
    historical_event_id: str | None = None
    coverage_start: AwareDatetime | None = None
    coverage_end: AwareDatetime | None = None


class OffsetPagination(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(ge=1, le=999)
    offset: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)


class ScenarioListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ScenarioSummary]
    pagination: OffsetPagination


class DatasetProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str
    version: str
    source_label: Literal["observed", "simulated", "assumed", "demo"]
    license: str
    checksum: Checksum
    crs: str | None
    coverage_start: AwareDatetime | None
    coverage_end: AwareDatetime | None


class ApprovedQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validation_status: Literal["pass"]
    approved_by: TextValue
    approved_at: AwareDatetime


class AssumptionsLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    checksum: Checksum


class ScenarioLinks(BaseModel):
    model_config = ConfigDict(extra="forbid")
    self: str
    layers: str


class ScenarioDetail(ScenarioSummary):
    schema_version: Literal["1.0.0"]
    data_kind: Literal["observed", "simulated", "assumed", "demo"]
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    time_step_minutes: int = Field(gt=0)
    parameters: ScenarioParameters
    parameter_units: ParameterUnits
    summary: ImpactSummary
    run_id: str
    run_timestamp: AwareDatetime
    quality: ApprovedQuality
    datasets: list[DatasetProvenance]
    assumptions: AssumptionsLink
    links: ScenarioLinks
