from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from services.api.app.api_schemas.historical_event import HistoricalEventListResponse
from services.api.app.api.v1.responses import ERRORS
from services.api.app.published_contract import Timestamp
from services.api.app.repositories.query_filters import time_window
from services.api.app.services.historical_event_service import HistoricalEventService, get_historical_event_service

router = APIRouter(tags=["historical-events"])


@router.get("/historical-events", response_model=HistoricalEventListResponse,
            responses={code: ERRORS[code] for code in (422, 500, 503)}, summary="List registered historical events",
            description="Returns catalogued event coverage/provenance and separately identifies approved replay availability.")
def historical_events(
    service: Annotated[HistoricalEventService, Depends(get_historical_event_service)],
    data_mode: Literal["demo", "production"] = "demo",
    limit: Annotated[int, Query(ge=1, le=999)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    start: Timestamp | None = None,
    end: Timestamp | None = None,
) -> HistoricalEventListResponse:
    try:
        start, end = time_window(start, end)
    except ValueError as error:
        raise HTTPException(422, "Invalid historical-event query.") from error
    return service.list_events(data_mode=data_mode, limit=limit, offset=offset, start=start, end=end)
