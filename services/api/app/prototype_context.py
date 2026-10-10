"""Pure prototype-context metadata contract; no DB, GIS, environment or HTTP imports."""
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BeforeValidator, Field, StringConstraints, model_validator

from services.api.app.published_contract import (
    Checksum, ContractModel, Identifier, PublishedScenarioManifest,
    TimeCoverage, Timestamp, Version, CORE_ROLES, validate_reference,
)

MAX_CONTEXT_BYTES = 64 * 1024


def _plain(value):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value) or "<" in value or ">" in value:
        raise ValueError("context_text_invalid")
    return value


def _portable(value):
    value = validate_reference(value)
    if urlsplit(value).scheme:
        raise ValueError("context_reference_must_be_relative")
    return value


def _true(value):
    if type(value) is not bool or value is not True:
        raise ValueError("prototype_flag_required")
    return value


Text = Annotated[str, BeforeValidator(_plain), StringConstraints(min_length=1, max_length=1000, pattern=r"^\S(?:.*\S)?$")]
PortableKey = Annotated[str, BeforeValidator(_portable), StringConstraints(min_length=1, max_length=512)]
Texts = Annotated[list[Text], Field(min_length=1, max_length=32)]
References = Annotated[list[PortableKey], Field(min_length=1, max_length=32)]
PositiveNumber = Annotated[float, Field(gt=0, strict=True, allow_inf_nan=False)]
PositiveInteger = Annotated[int, Field(gt=0, strict=True)]
PrototypeFlag = Annotated[Literal[True], BeforeValidator(_true)]
ImpactField = Literal["max_depth_m", "flooded_area_km2", "population_exposed", "buildings_exposed", "roads_affected_km", "critical_facilities_exposed"]
Product = Literal["max_depth_m", "flooded_area_km2", "population_exposed", "buildings_exposed", "roads_affected_km", "critical_facilities_exposed", "duration_cog", "hazard_cog", "exposure_geojson", "breach_width_m", "breach_formation_minutes", "max_wse_cog"]


class Engine(ContractModel):
    name: Text
    software_version: Version
    build: Text | None
    build_unavailable_reason: Text | None
    source_checksum: Checksum | None
    source_checksum_unavailable_reason: Text | None

    @model_validator(mode="after")
    def check_unavailable(self):
        for value, reason in ((self.build, self.build_unavailable_reason),
                              (self.source_checksum, self.source_checksum_unavailable_reason)):
            if (value is None) != (reason is not None):
                raise ValueError("engine_missing_value_reason_mismatch")
        return self


class Original(ContractModel):
    scenario_id: Identifier
    status: Literal["draft"]
    scenario_type: Literal["hypothetical_release", "hypothetical", "historical_replay"]
    validation_status: Literal["not_validated"]
    manifest_reference: PortableKey
    manifest_checksum: Checksum
    asset_checksums: dict[PortableKey, Checksum] = Field(min_length=1, max_length=64)


class DatasetIdentity(ContractModel):
    dataset_id: Identifier
    version: Version


class Forcing(ContractModel):
    kind: Literal["hypothetical_assumption", "reconstructed_historical"]
    source_label: Literal["assumed"]
    description: Text
    datasets: list[DatasetIdentity] = Field(min_length=1, max_length=32)
    provenance_references: References
    uncertainties: Texts

    @model_validator(mode="after")
    def unique_datasets(self):
        if len({(d.dataset_id, d.version) for d in self.datasets}) != len(self.datasets):
            raise ValueError("duplicate_forcing_dataset")
        return self


class Arrival(ContractModel):
    unit: Literal["min"]
    origin: Literal["simulation_start"]
    reference_timestamp: Timestamp
    threshold_m: Annotated[float, Field(strict=True, allow_inf_nan=False)]
    temporal_resolution_minutes: PositiveNumber
    original_unit: Literal["h"]
    conversion_factor: Annotated[int, Field(strict=True)]
    conversion: Literal["valid_cells_times_60_nodata_preserved"]
    original_reference: PortableKey
    original_checksum: Checksum
    evidence_references: References

    @model_validator(mode="after")
    def check_conversion(self):
        if self.threshold_m != 0.1 or self.conversion_factor != 60:
            raise ValueError("arrival_definition_mismatch")
        return self


IntervalField = Literal["computation_step_seconds", "forcing_interval_minutes", "mapping_interval_minutes"]


class Timing(ContractModel):
    time_step_meaning: Literal["result_output_interval"]
    result_output_interval_minutes: PositiveInteger
    computation_step_seconds: PositiveNumber | None
    forcing_interval_minutes: PositiveNumber | None
    mapping_interval_minutes: PositiveNumber | None
    unavailable_reasons: dict[IntervalField, Text] = Field(max_length=3)
    coverage_clock_kind: Literal["model_clock", "observed_event"]
    timezone_convention: Text
    evidence_references: References

    @model_validator(mode="after")
    def check_reasons(self):
        expected = {key for key in ("computation_step_seconds", "forcing_interval_minutes", "mapping_interval_minutes") if getattr(self, key) is None}
        if set(self.unavailable_reasons) != expected:
            raise ValueError("timing_unavailable_reason_mismatch")
        return self


class Limitations(ContractModel):
    calibration: Text
    terrain_bathymetry: Text
    vertical_datum: Text
    exposure: Text
    source_uncertainties: Texts


class PreservedWSE(ContractModel):
    reference: PortableKey
    checksum: Checksum
    vertical_datum: Literal["unknown"]
    reason_not_registered: Text


OperationName = Literal["arrival_hours_to_minutes", "coordinate_window_alignment", "strict_cog_packaging", "band_metadata", "extent_geojson_normalization", "identity_correction"]


class Operation(ContractModel):
    name: OperationName
    parameters_and_method: Text
    evidence_references: References


class Derivation(ContractModel):
    processor: Text
    processor_version: Version
    source_scenario_id: Identifier
    derivative_scenario_id: Identifier
    derivative_run_id: Identifier
    operations: list[Operation] = Field(min_length=1, max_length=16)
    evidence_references: References

    @model_validator(mode="after")
    def operations_unique(self):
        names = [item.name for item in self.operations]
        if len(set(names)) != len(names):
            raise ValueError("duplicate_derivation_operation")
        if not {"arrival_hours_to_minutes", "coordinate_window_alignment"} <= set(names):
            raise ValueError("required_derivation_operations_missing")
        return self


class PrototypeContext(ContractModel):
    schema_version: Literal["1.0.0"]
    scenario_id: Identifier
    run_id: Identifier
    model_version: Version
    input_dataset_version: Version
    time_coverage: TimeCoverage
    engine: Engine
    scenario_family: Identifier
    calibration_status: Literal["uncalibrated"]
    scientific_validation_status: Literal["not_validated"]
    prototype: PrototypeFlag
    original: Original
    forcing: Forcing
    arrival: Arrival
    timing: Timing
    limitations: Limitations
    assumptions: Texts
    unavailable_products: dict[Product, Text] = Field(max_length=32)
    preserved_wse: PreservedWSE | None
    derivation: Derivation


class ContextBindingError(ValueError):
    """Safe static field path for metadata-checker diagnostics."""


def _require(condition, field):
    if not condition:
        raise ContextBindingError(field)


def validate_bound_context(context, manifest, *, synthetic_example=False):
    """Revalidate values and cross-bind metadata; does not inspect GIS or approve data.

    synthetic_example is ONLY a metadata-example/checker mode. Actual preview
    callers must use the default production/simulated profile and admission gate.
    """
    manifest = PublishedScenarioManifest.model_validate(manifest.model_dump())
    context = PrototypeContext.model_validate(context.model_dump())
    expected = ("demo", "demo") if synthetic_example else ("production", "simulated")
    _require((manifest.data_mode, manifest.data_kind) == expected, "manifest.data_mode")
    _require(manifest.status == "draft" and manifest.quality.validation_status == "pending", "manifest.quality")
    _require(manifest.quality.approved_by is None and manifest.quality.approved_at is None, "manifest.quality")
    _require(CORE_ROLES <= set(manifest.assets), "manifest.assets")
    supported = CORE_ROLES | {"duration_cog", "hazard_cog", "exposure_geojson"}
    _require(set(manifest.assets) <= supported, "manifest.assets")
    for field in ("scenario_id", "run_id", "model_version", "input_dataset_version", "time_coverage"):
        _require(getattr(context, field) == getattr(manifest, field), "context." + field)
    _require(context.original.scenario_id != manifest.scenario_id, "context.original.scenario_id")
    target_type = "historical_replay" if context.original.scenario_type == "historical_replay" else "hypothetical"
    _require(target_type == manifest.scenario_type, "context.original.scenario_type")
    expected_forcing = "reconstructed_historical" if target_type == "historical_replay" else "hypothetical_assumption"
    _require(context.forcing.kind == expected_forcing, "context.forcing.kind")
    if target_type == "hypothetical":
        _require(context.timing.coverage_clock_kind == "model_clock", "context.timing.coverage_clock_kind")
    _require(context.arrival.reference_timestamp == manifest.time_coverage.start, "context.arrival.reference_timestamp")
    _require(context.timing.result_output_interval_minutes == manifest.time_step_minutes, "context.timing.result_output_interval_minutes")
    _require(context.derivation.source_scenario_id == context.original.scenario_id, "context.derivation.source_scenario_id")
    _require(context.derivation.derivative_scenario_id == manifest.scenario_id, "context.derivation.derivative_scenario_id")
    _require(context.derivation.derivative_run_id == manifest.run_id, "context.derivation.derivative_run_id")
    _require(context.original.asset_checksums.get(context.arrival.original_reference) == context.arrival.original_checksum, "context.arrival.original_checksum")
    registered = {(d.dataset_id, d.version): d for d in manifest.datasets}
    for item in context.forcing.datasets:
        source = registered.get((item.dataset_id, item.version))
        if source is None:
            raise ContextBindingError("context.forcing.datasets")
        _require(source.source_label == ("demo" if synthetic_example else "assumed"), "context.forcing.source_label")
    if context.preserved_wse is not None:
        _require(context.original.asset_checksums.get(context.preserved_wse.reference) == context.preserved_wse.checksum, "context.preserved_wse.checksum")
        _require("max_wse_cog" in context.unavailable_products, "context.unavailable_products")
    for field in type(manifest.summary).model_fields:
        value = getattr(manifest.summary, field)
        _require((value is None) == (field in context.unavailable_products), "context.unavailable_products")
    for field in ("breach_width_m", "breach_formation_minutes"):
        _require((getattr(manifest.parameters, field) is None) == (field in context.unavailable_products), "context.unavailable_products")
    for role in ("duration_cog", "hazard_cog", "exposure_geojson"):
        _require((role not in manifest.assets) == (role in context.unavailable_products), "context.unavailable_products")
    return context


def prototype_context_json_schema():
    schema = PrototypeContext.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:ukai:contracts:prototype-context:1.0.0"
    schema["description"] = "Local uncalibrated prototype context. Runtime binding, byte/GIS verification and operator admission are additional gates."
    return schema
