"""Explicit draft response models; no inheritance of approved status/quality."""
from typing import Literal
from pydantic import Field
from services.api.app.published_contract import (
    ContractModel, Identifier, Version, CRS, Checksum, Timestamp, ImpactSummary, ScenarioParameters, ParameterUnits,
)
from services.api.app.prototype_context import Engine, Timing, Arrival
from .scenario import DatasetProvenance


LABEL: Literal["Uncalibrated prototype — simulated"] = "Uncalibrated prototype — simulated"
WARNINGS: tuple[Literal["uncalibrated"], Literal["not_scientifically_validated"], Literal["simulated"]] = ("uncalibrated", "not_scientifically_validated", "simulated")
PrototypeMapRole = Literal["max_depth_cog", "max_velocity_cog", "arrival_time_cog", "extent_geojson", "duration_cog", "hazard_cog", "exposure_geojson"]


class PrototypeLayer(ContractModel):
    asset_type: PrototypeMapRole
    format: Literal["cog", "geojson"]
    crs: CRS
    unit: str
    nodata: float | None
    checksum: Checksum
    coverage_start: Timestamp
    coverage_end: Timestamp
    url: str


class PrototypeSummary(ContractModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    scenario_id: Identifier
    run_id: Identifier
    scenario_type: Literal["historical_replay", "hypothetical"]
    model_version: Version
    input_dataset_version: Version
    status: Literal["draft"] = "draft"
    validation_status: Literal["pending"] = "pending"
    approved_by: None = None
    approved_at: None = None
    data_mode: Literal["production"] = "production"
    data_kind: Literal["simulated"] = "simulated"
    calibration_status: Literal["uncalibrated"] = "uncalibrated"
    prototype: Literal[True] = True
    scientifically_validated: Literal[False] = False
    label: Literal["Uncalibrated prototype — simulated"] = LABEL
    warnings: tuple[Literal["uncalibrated"], Literal["not_scientifically_validated"], Literal["simulated"]] = WARNINGS


class PrototypePagination(ContractModel):
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    next_offset: int | None = Field(ge=0)


class PrototypeList(ContractModel):
    items: list[PrototypeSummary]
    pagination: PrototypePagination


class PrototypeLinks(ContractModel):
    self: str
    layers: str
    impact: str
    assumptions: str
    quality_report: str


class PublicTiming(ContractModel):
    time_step_meaning: Literal["result_output_interval"]
    result_output_interval_minutes: int = Field(gt=0)
    computation_step_seconds: float | None
    forcing_interval_minutes: float | None
    mapping_interval_minutes: float | None
    unavailable_reasons: dict[str, str]
    coverage_clock_kind: Literal["model_clock", "observed_event"]
    timezone_convention: str

    @classmethod
    def from_context(cls, value: Timing):
        return cls.model_validate(value.model_dump(exclude={"evidence_references"}))


class PublicArrival(ContractModel):
    unit: Literal["min"]
    origin: Literal["simulation_start"]
    reference_timestamp: Timestamp
    threshold_m: float
    temporal_resolution_minutes: float
    original_unit: Literal["h"]
    conversion_factor: int

    @classmethod
    def from_context(cls, value: Arrival):
        names = cls.model_fields
        return cls.model_validate({name: getattr(value, name) for name in names})


class PublicProvenance(ContractModel):
    source_scenario_id: Identifier
    source_manifest_checksum: Checksum
    scenario_family: Identifier
    derivation_processor: str
    derivation_version: Version


class PrototypeDetail(PrototypeSummary):
    crs: CRS
    historical_event_id: Identifier | None
    run_timestamp: Timestamp | None
    run_timestamp_unknown_reason: str | None = None
    coverage_start: Timestamp
    coverage_end: Timestamp
    time_step_minutes: int = Field(gt=0)
    parameters: ScenarioParameters
    parameter_units: ParameterUnits
    summary: ImpactSummary
    engine: Engine
    provenance: PublicProvenance
    timing: PublicTiming
    arrival: PublicArrival
    datasets: list[DatasetProvenance]
    limitations: list[str]
    assumptions: list[str]
    unavailable_reasons: dict[str, str]
    links: PrototypeLinks


class PrototypeLayers(PrototypeSummary):
    layers: list[PrototypeLayer]


class PrototypeImpact(PrototypeSummary, ImpactSummary):
    unavailable_reasons: dict[str, str]
