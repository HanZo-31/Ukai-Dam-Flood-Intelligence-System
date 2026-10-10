from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class CurrentStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    reservoir_level_m: float | None
    inflow_m3s: float | None = Field(ge=0)
    release_m3s: float | None = Field(ge=0)
    timestamp: AwareDatetime
    data_mode: Literal["demo"]
    data_kind: Literal["demo"] = "demo"
    is_live: Literal[False] = False
