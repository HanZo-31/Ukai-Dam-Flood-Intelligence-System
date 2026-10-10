from typing import Annotated, Literal
import anyio
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from services.api.app.api_schemas.scenario import ScenarioDetail, ScenarioListResponse
from services.api.app.api_schemas.layer import ScenarioLayersResponse
from services.api.app.api_schemas.impact import ScenarioImpactResponse
from services.api.app.api.v1.responses import ERRORS, problem_spec
from services.api.app.published_contract import AssetRole, Timestamp
from services.api.app.repositories.query_filters import bbox_values, time_window
from services.api.app.services.asset_service import byte_range
from services.api.app.services.scenario_service import ScenarioService, get_scenario_service

router = APIRouter(tags=["scenarios"])
Service = Annotated[ScenarioService, Depends(get_scenario_service, scope="function")]
ScenarioID = Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9_-]{2,149}$")]
DataMode = Literal["demo", "production"]


class VerifiedStreamingResponse(StreamingResponse):
    """Close snapshots even if send fails before the generator starts."""
    def __init__(self, download, *args, **kwargs):
        self.download = download
        super().__init__(*args, **kwargs)

    async def __call__(self, scope, receive, send):
        try:
            with anyio.fail_after(self.download.stream_seconds):
                await super().__call__(scope, receive, send)
        finally:
            self.download.handle.close()


@router.get("/scenarios", response_model=ScenarioListResponse, summary="List approved scenarios",
            responses={code: ERRORS[code] for code in (422, 500, 503)},
            description="Returns only B1-approved, completed scenarios for the selected data mode.")
def list_scenarios(service: Service,
    data_mode: Literal["demo", "production"] = "demo",
    limit: Annotated[int, Query(ge=1, le=999)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    scenario_type: Literal["hypothetical", "historical_replay"] | None = None,
    historical_event_id: str | None = None, model_version: str | None = None,
    dataset_id: str | None = None, dataset_version: str | None = None,
    data_kind: Literal["demo", "observed", "simulated", "assumed"] | None = None,
    start: Timestamp | None = None, end: Timestamp | None = None,
    bbox: Annotated[str | None, Query(max_length=100, description="WGS84 west,south,east,north")] = None) -> ScenarioListResponse:
    try:
        bounds = bbox_values(tuple(float(value) for value in bbox.split(","))) if bbox is not None else None
        start, end = time_window(start, end)
        if dataset_version is not None and dataset_id is None:
            raise ValueError("dataset_version requires dataset_id")
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Invalid scenario query.") from error
    # Stored-data validation failures must not be mistaken for bad client input.
    return service.list_scenarios(data_mode=data_mode, limit=limit, offset=offset,
        scenario_type=scenario_type, historical_event_id=historical_event_id,
        model_version=model_version, dataset_id=dataset_id, dataset_version=dataset_version,
        data_kind=data_kind, start=start, end=end, bbox=bounds)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetail,
            responses=ERRORS, summary="Read an approved scenario")
def scenario_detail(scenario_id: ScenarioID, service: Service,
                    data_mode: DataMode = "demo") -> ScenarioDetail:
    return service.detail(scenario_id, data_mode=data_mode)


@router.get("/scenarios/{scenario_id}/layers", response_model=ScenarioLayersResponse,
            responses=ERRORS, summary="Discover approved map layers")
def scenario_layers(scenario_id: ScenarioID, service: Service,
                    data_mode: DataMode = "demo") -> ScenarioLayersResponse:
    return service.layers(scenario_id, data_mode=data_mode)


@router.get("/scenarios/{scenario_id}/impact", response_model=ScenarioImpactResponse,
            responses=ERRORS, summary="Read registered scenario impacts",
            description="Serves B1-registered exposure/hazard summary measurements; unavailable values remain null.")
def scenario_impact(scenario_id: ScenarioID, service: Service,
                    data_mode: DataMode = "demo") -> ScenarioImpactResponse:
    return service.impact(scenario_id, data_mode=data_mode)


def download_response(download, request: Request) -> Response:
    headers = {
        "Accept-Ranges": "bytes",
        "ETag": '"' + download.checksum + '"',
        "Content-Disposition": f'attachment; filename="{download.filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if request.method == "HEAD":
        download.handle.close()
        headers["Content-Length"] = str(download.size)
        return Response(headers=headers, media_type=download.media_type)
    try:
        # If-Range mismatch requests the whole current verified representation.
        requested_range = request.headers.get("range")
        if request.headers.get("if-range") not in {None, headers["ETag"]}:
            requested_range = None
        start, length, status = byte_range(requested_range, download.size)
        headers["Content-Length"] = str(length)
        if status == 206:
            headers["Content-Range"] = f"bytes {start}-{start + length - 1}/{download.size}"
        return VerifiedStreamingResponse(download, download.chunks(start, length), status_code=status,
            media_type=download.media_type, headers=headers,
            background=BackgroundTask(download.handle.close))
    except Exception:
        download.handle.close()
        raise


DOWNLOAD_RESPONSES = ERRORS | {
    200: {"description": "Verified artifact bytes", "content": {
        media: {"schema": {"type": "string", "format": "binary"}}
        for media in ("image/tiff", "application/geo+json", "application/vnd.google-earth.kml+xml", "text/plain")
    }},
    206: {"description": "Single byte range"},
    416: problem_spec("Requested range is not satisfiable"),
}


@router.head("/scenarios/{scenario_id}/assets/{asset_type}", responses=ERRORS)
@router.get("/scenarios/{scenario_id}/assets/{asset_type}",
            response_class=StreamingResponse, responses=DOWNLOAD_RESPONSES,
            summary="Download a checksum-verified approved asset")
def scenario_asset(scenario_id: ScenarioID, asset_type: AssetRole, request: Request,
                   service: Service, data_mode: DataMode = "demo") -> Response:
    return download_response(service.asset_download(scenario_id, asset_type, data_mode=data_mode), request)


@router.head("/scenarios/{scenario_id}/assumptions", responses=ERRORS)
@router.get("/scenarios/{scenario_id}/assumptions", response_class=StreamingResponse,
            responses=DOWNLOAD_RESPONSES, summary="Download approved assumptions")
def scenario_assumptions(scenario_id: ScenarioID, request: Request,
                         service: Service, data_mode: DataMode = "demo") -> Response:
    return download_response(service.assumptions_download(scenario_id, data_mode=data_mode), request)
