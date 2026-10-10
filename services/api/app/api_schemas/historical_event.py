from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, HttpUrl
from services.api.app.api_schemas.scenario import DatasetProvenance, OffsetPagination, ScenarioSummary


class ReplayAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool
    scenarios_url: str
    example: ScenarioSummary | None


class HistoricalEventSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    name: str
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    observed_coverage: str
    source_urls: list[HttpUrl]
    data_mode: Literal["demo", "production"]
    source_labels: list[Literal["observed", "simulated", "assumed", "demo"]]
    datasets: list[DatasetProvenance]
    replay: ReplayAvailability


class HistoricalEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[HistoricalEventSummary]
    pagination: OffsetPagination
