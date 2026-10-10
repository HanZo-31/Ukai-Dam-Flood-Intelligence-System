from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from services.api.app.api_schemas.status import CurrentStatusResponse
from services.api.app.api.v1.responses import ERRORS
from services.api.app.services.status_service import StatusService, get_status_service

router = APIRouter(tags=["status"])


@router.get("/status/current", response_model=CurrentStatusResponse, responses=ERRORS,
            summary="Read the latest demo status",
            description="Seeded/dummy V1 readings only. Always labelled demo; timestamp is the persisted reading time, not a claim of live telemetry.")
def current_status(service: Annotated[StatusService, Depends(get_status_service)],
                   data_mode: Literal["demo"] = "demo") -> CurrentStatusResponse:
    return service.current()
