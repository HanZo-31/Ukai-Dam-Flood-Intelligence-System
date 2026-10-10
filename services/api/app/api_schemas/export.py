"""Public metadata for an existing, registered export; never a storage URI."""
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict
from services.api.app.published_contract import Checksum, CRS


class ScenarioExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    model_version: str
    input_dataset_version: str
    data_mode: Literal["demo", "production"]
    data_kind: Literal["observed", "simulated", "assumed", "demo"]
    asset_type: Literal["export_geojson", "export_kml"]
    format: Literal["geojson", "kml"]
    crs: CRS
    unit: Literal["1"]
    checksum: Checksum
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    download_url: str
