from typing import Literal
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"] = "ok"
    service: Literal["ukai-flood-api"] = "ukai-flood-api"
    api_version: Literal["v1"] = "v1"
