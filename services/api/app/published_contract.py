"""Candidate V1 Part A -> B published-result contract; no database writes."""
from datetime import datetime
import re
from typing import Annotated, Literal
from urllib.parse import quote, unquote, urlsplit

from pydantic import (
    AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field,
    StringConstraints, model_validator,
    WithJsonSchema, JsonValue,
)

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]{2,149}$")]
Version = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r"^\S(?:.*\S)?$")]
TextValue = Annotated[str, StringConstraints(min_length=1, max_length=500, pattern=r"^\S(?:.*\S)?$")]
Checksum = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
CRS = Annotated[str, StringConstraints(pattern=r"^EPSG:[1-9][0-9]*$")]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]
Count = Annotated[int, Field(ge=0, strict=True)]


TIMESTAMP_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"


def _timestamp(value):
    if not isinstance(value, (str, datetime)):
        raise ValueError("timestamps must be ISO 8601 strings with timezone")
    if isinstance(value, str) and re.fullmatch(TIMESTAMP_PATTERN, value) is None:
        raise ValueError("timestamps must include ISO date/time, seconds and explicit timezone")
    return value


Timestamp = Annotated[AwareDatetime, BeforeValidator(_timestamp), WithJsonSchema({"type": "string", "format": "date-time", "pattern": TIMESTAMP_PATTERN})]


def validate_reference(value: str) -> str:
    """Allow immutable local/S3 references or bundle-relative POSIX keys."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("artifact reference must be a nonempty unpadded string")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("artifact reference contains control characters")
    parsed = urlsplit(value)
    if parsed.query or parsed.fragment or "?" in value or "#" in value or parsed.username or parsed.password:
        raise ValueError("artifact reference must not contain credentials, query or fragment")
    decoded = unquote(parsed.path)
    if "%" in decoded or "\\" in decoded or any(p in {".", "..", ""} for p in decoded.lstrip("/").split("/")):
        raise ValueError("artifact reference contains traversal, empty segments or nested encoding")
    if parsed.scheme == "s3":
        if not parsed.netloc or ":" in parsed.netloc or not decoded.startswith("/"):
            raise ValueError("S3 reference requires a bucket and key")
    elif parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"} or not decoded.startswith("/"):
            raise ValueError("file reference requires an absolute local path")
    elif parsed.scheme or parsed.netloc or decoded.startswith("/") or ":" in decoded:
        raise ValueError("relative reference must be a bundle-relative POSIX key")
    return value


Reference = Annotated[str, StringConstraints(min_length=1, max_length=2048), BeforeValidator(validate_reference)]


def resolve_reference(base_uri: str, reference: str) -> str:
    """The caller supplies the trusted bundle root; payloads cannot select it."""
    reference = validate_reference(reference)
    if urlsplit(reference).scheme:
        return reference
    if not base_uri.endswith("/") or urlsplit(base_uri).scheme not in {"file", "s3"}:
        raise ValueError("bundle root must be an absolute file:// or s3:// URI ending in /")
    validate_reference(base_uri + "root-validation")
    return base_uri + quote(unquote(reference), safe="/-_.~")


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class TimeCoverage(ContractModel):
    start: Timestamp
    end: Timestamp

    @model_validator(mode="after")
    def check_order(self):
        if self.end < self.start:
            raise ValueError("coverage end must not precede start")
        return self


class ScenarioParameters(ContractModel):
    # Explicit null means unavailable/not applicable; no scientific zero defaults.
    reservoir_level_m: Annotated[float, Field(allow_inf_nan=False, strict=True)] | None
    peak_inflow_m3s: NonNegative | None
    peak_release_m3s: NonNegative | None
    breach_width_m: Positive | None
    breach_formation_minutes: Positive | None


class ParameterUnits(ContractModel):
    reservoir_level_m: Literal["m"]
    peak_inflow_m3s: Literal["m3/s"]
    peak_release_m3s: Literal["m3/s"]
    breach_width_m: Literal["m"]
    breach_formation_minutes: Literal["min"]


class ImpactSummary(ContractModel):
    max_depth_m: NonNegative | None
    flooded_area_km2: NonNegative | None
    population_exposed: Count | None
    buildings_exposed: Count | None
    roads_affected_km: NonNegative | None = None
    critical_facilities_exposed: Count | None = None


class DatasetVersionReference(ContractModel):
    dataset_id: Identifier
    version: Version
    source_reference: Reference
    source_label: Literal["observed", "simulated", "assumed", "demo"]
    license: TextValue
    checksum: Checksum
    crs: CRS | None
    time_coverage: TimeCoverage | None
    quality_notes: TextValue


class QualityReview(ContractModel):
    validation_status: Literal["pending", "pass", "fail"]
    approved_by: TextValue | None
    approved_at: Timestamp | None
    report_reference: Reference
    report_checksum: Checksum


AssetRole = Literal[
    "max_depth_cog", "max_velocity_cog", "arrival_time_cog", "extent_geojson",
    "duration_cog", "hazard_cog", "exposure_geojson", "export_geojson", "export_kml",
]
CORE_ROLES = {"max_depth_cog", "max_velocity_cog", "arrival_time_cog", "extent_geojson"}
ROLE_UNITS = {
    "max_depth_cog": "m", "max_velocity_cog": "m/s", "arrival_time_cog": "min",
    "duration_cog": "min", "hazard_cog": "class", "extent_geojson": "1",
    "exposure_geojson": "count", "export_geojson": "1", "export_kml": "1",
}


class AssetMetadata(ContractModel):
    checksum: Checksum
    format: Literal["cog", "geojson", "kml"]
    crs: CRS
    unit: TextValue
    time_coverage: TimeCoverage
    nodata: Annotated[float, Field(allow_inf_nan=False, strict=True)] | None


CORE_ROLE_SCHEMA: list[JsonValue] = [role for role in sorted(CORE_ROLES)]
APPROVED_RULE: dict[str, JsonValue] = {
    "if": {"properties": {"status": {"const": "approved"}}, "required": ["status"]},
    "then": {"properties": {
        "schema_version": {"const": "1.0.0"},
        "run_timestamp": {"type": "string", "format": "date-time"},
        "quality": {"properties": {
            "validation_status": {"const": "pass"},
            "approved_by": {"type": "string", "minLength": 1},
            "approved_at": {"type": "string", "format": "date-time"},
        }},
        "assets": {"required": CORE_ROLE_SCHEMA},
    }},
}


V1_METADATA_RULE: dict[str, JsonValue] = {
    "if": {"properties": {"schema_version": {"const": "1.0.0"}}, "required": ["schema_version"]},
    "then": {"properties": {"run_timestamp": {"type": "string", "format": "date-time"},
                            "run_timestamp_unknown_reason": {"type": "null"}}},
}
LOCAL_DRAFT_RULE: dict[str, JsonValue] = {
    "if": {"properties": {"schema_version": {"const": "1.1.0-local-draft"}}, "required": ["schema_version"]},
    "then": {"properties": {"status": {"const": "draft"},
                            "quality": {"properties": {"validation_status": {"const": "pending"}}}},
             "if": {"properties": {"run_timestamp": {"type": "null"}}, "required": ["run_timestamp"]},
             "then": {"properties": {"run_timestamp_unknown_reason": {"type": "string", "minLength": 1}},
                      "required": ["run_timestamp_unknown_reason"]},
             "else": {"properties": {"run_timestamp_unknown_reason": {"type": "null"}}}},
}


class PublishedScenarioManifest(ContractModel):
    """Approved precomputed outputs; distinct from the legacy input/run DTOs."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False,
                             json_schema_extra={"allOf": [APPROVED_RULE, V1_METADATA_RULE, LOCAL_DRAFT_RULE]})

    schema_version: Literal["1.0.0", "1.1.0-local-draft"]
    scenario_id: Identifier
    scenario_type: Literal["historical_replay", "hypothetical"]
    status: Literal["draft", "approved", "rejected"]
    model_version: Version
    input_dataset_version: Version
    crs: CRS
    time_step_minutes: Annotated[int, Field(gt=0, strict=True)]
    data_mode: Literal["demo", "production"]
    data_kind: Literal["observed", "simulated", "assumed", "demo"]
    run_id: Identifier
    run_timestamp: Timestamp | None
    run_timestamp_unknown_reason: TextValue | None = Field(default=None, exclude_if=lambda value: value is None)
    time_coverage: TimeCoverage
    historical_event_id: Identifier | None = None
    parameters: ScenarioParameters
    parameter_units: ParameterUnits
    datasets: list[DatasetVersionReference] = Field(min_length=1)
    assets: dict[AssetRole, Reference] = Field(min_length=1)
    asset_metadata: dict[AssetRole, AssetMetadata] = Field(min_length=1)
    summary: ImpactSummary
    assumptions_url: Reference
    assumptions_checksum: Checksum
    quality: QualityReview

    @model_validator(mode="after")
    def check_bundle_semantics(self):
        if self.schema_version == "1.0.0":
            if self.run_timestamp is None or self.run_timestamp_unknown_reason is not None:
                raise ValueError("V1 requires a verified producing-run timestamp")
        else:
            if self.status != "draft" or self.quality.validation_status != "pending":
                raise ValueError("local draft extension cannot be scientifically approved")
            if (self.run_timestamp is None) != (self.run_timestamp_unknown_reason is not None):
                raise ValueError("unknown producing-run timestamp requires an explicit reason")
        if (self.data_mode == "demo") != (self.data_kind == "demo"):
            raise ValueError("demo mode requires demo data_kind; production cannot claim demo data")
        if self.schema_version == "1.0.0" and self.scenario_type == "historical_replay" and self.historical_event_id is None:
            raise ValueError("historical replay requires historical_event_id")
        if self.scenario_type == "hypothetical" and self.historical_event_id is not None:
            raise ValueError("hypothetical scenario cannot claim a historical event")
        if len({(d.dataset_id, d.version) for d in self.datasets}) != len(self.datasets):
            raise ValueError("dataset/version references must be unique")
        if self.data_mode == "production" and any(d.source_label == "demo" for d in self.datasets):
            raise ValueError("production cannot use demo-labelled datasets")
        if self.assets.keys() != self.asset_metadata.keys():
            raise ValueError("assets and asset_metadata must have exactly matching roles")
        if len({unquote(p) for p in self.assets.values()}) != len(self.assets):
            raise ValueError("asset references must be distinct")
        for role, asset in self.asset_metadata.items():
            expected_format = "cog" if role.endswith("_cog") else "kml" if role.endswith("_kml") else "geojson"
            if asset.format != expected_format or asset.unit != ROLE_UNITS[role]:
                raise ValueError(f"invalid format or unit for {role}")
            if asset.format == "cog" and asset.crs != self.crs:
                raise ValueError("raster CRS must match the scenario CRS")
            if asset.time_coverage.start < self.time_coverage.start or asset.time_coverage.end > self.time_coverage.end:
                raise ValueError("asset coverage must lie within scenario coverage")
        if self.status == "approved":
            if self.run_timestamp is None:
                raise ValueError("approved scenario requires a producing-run timestamp")
            if not CORE_ROLES <= self.assets.keys():
                raise ValueError("approved scenario requires the four core result roles")
            if self.quality.validation_status != "pass" or self.quality.approved_by is None or self.quality.approved_at is None:
                raise ValueError("approved scenario requires passing quality review and approver/time")
            if self.quality.approved_at < self.run_timestamp:
                raise ValueError("approval cannot precede the published simulation run")
        elif self.quality.approved_by is not None or self.quality.approved_at is not None:
            raise ValueError("draft/rejected scenarios cannot carry approval metadata")
        return self


def require_publishable(manifest: PublishedScenarioManifest) -> PublishedScenarioManifest:
    # Nested dictionaries/models can be mutated after parsing. Revalidate the
    # whole snapshot at the publication boundary, not just the status string.
    manifest = PublishedScenarioManifest.model_validate(manifest.model_dump())
    if manifest.status != "approved":
        raise ValueError("only approved published bundles may enter the approved catalog")
    return manifest


def published_json_schema() -> dict:
    schema = PublishedScenarioManifest.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:ukai:contracts:published-scenario:combined-local-draft:1.1.0"
    schema["description"] = "Strict V1 publication plus an explicitly unapproved local draft extension. Runtime semantic and object verification gates also apply."
    return schema
