from typing import Literal

from pydantic import BaseModel, ConfigDict, AwareDatetime
from services.api.app.published_contract import AssetRole, Checksum, CRS


class Layer(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    asset_type: AssetRole
    format: Literal["cog", "geojson"]
    crs: CRS
    unit: str
    nodata: float | None
    checksum: Checksum
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    url: str


class ScenarioLayersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    model_version: str
    input_dataset_version: str
    data_mode: Literal["demo", "production"]
    data_kind: Literal["observed", "simulated", "assumed", "demo"]
    layers: list[Layer]
