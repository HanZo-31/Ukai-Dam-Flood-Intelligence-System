"""Validated catalog writes; scientific observations/results are supplied by Team A."""
from typing import Annotated, Literal
import json

from pydantic import AfterValidator, ConfigDict, Field, HttpUrl, model_validator

from services.api.app.published_contract import (
    ContractModel, Identifier, Version, TextValue, Checksum, CRS, Reference,
    Timestamp, TimeCoverage,
)


def public_source_url(url):
    if url.username is not None or url.password is not None:
        raise ValueError("source URLs must not contain credentials")
    return url


SourceURL = Annotated[HttpUrl, AfterValidator(public_source_url)]


class CatalogModel(ContractModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, revalidate_instances="always")


class DatasetCreate(CatalogModel):
    dataset_id: Identifier
    name: TextValue
    description: TextValue
    data_mode: Literal["demo", "production"] = "demo"


class DatasetVersionCreate(CatalogModel):
    dataset_id: Identifier
    version: Version
    source_reference: Reference
    source_url: SourceURL | None = None
    source_label: Literal["observed", "simulated", "assumed", "demo"]
    license: TextValue
    checksum: Checksum
    crs: CRS | None
    time_coverage: TimeCoverage | None
    quality_notes: TextValue
    units: dict[str, TextValue] = Field(default_factory=dict)


class HistoricalEventCreate(CatalogModel):
    event_id: Identifier
    name: TextValue
    time_coverage: TimeCoverage
    observed_coverage: TextValue
    quality_notes: TextValue
    source_urls: list[SourceURL] = Field(min_length=1)
    data_mode: Literal["demo", "production"] = "demo"


class ValidationMetricCreate(CatalogModel):
    metric_id: Identifier
    event_id: Identifier
    dataset_id: Identifier
    dataset_version: Version
    model_version: Version
    run_id: str | None = Field(default=None, min_length=1, max_length=150)
    station_id: str | None = Field(default=None, min_length=1, max_length=150)
    metric_name: Literal["rmse", "mae", "peak_stage_error", "timing_error", "iou", "flood_area_agreement"]
    value: float = Field(strict=True, allow_inf_nan=False)
    unit: TextValue
    sample_count: int | None = Field(default=None, strict=True, gt=0)
    computed_at: Timestamp
    calculation_config: dict = Field(min_length=1)
    report_reference: Reference
    report_checksum: Checksum

    @model_validator(mode="after")
    def metric_domain(self):
        try:
            json.dumps(self.calculation_config, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("calculation configuration must contain finite JSON values") from exc
        if self.metric_name in {"rmse", "mae"} and self.value < 0:
            raise ValueError("RMSE and MAE must be nonnegative")
        if self.metric_name in {"iou", "flood_area_agreement"}:
            if not 0 <= self.value <= 1 or self.unit != "fraction":
                raise ValueError("overlap metrics require a fraction in [0, 1]")
        return self
