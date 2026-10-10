"""Read-only prototype namespace; exact operator admission and local peers."""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Path, Query, Request, Response
from fastapi.responses import StreamingResponse
from services.api.app.api.v1.responses import ERRORS, problem_spec
from services.api.app.api.v1.scenarios import download_response
from services.api.app.api_schemas.prototype import PrototypeList, PrototypeDetail, PrototypeLayers, PrototypeImpact
from services.api.app.services.prototype_service import PrototypeService, get_prototype_service

router = APIRouter(prefix="/api/v1/prototypes", tags=["prototype-preview"])
Service = Annotated[PrototypeService, Depends(get_prototype_service, scope="function")]
ScenarioID = Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9_-]{2,149}$")]
MapRole = Literal["max_depth_cog", "max_velocity_cog", "arrival_time_cog", "extent_geojson", "duration_cog", "hazard_cog", "exposure_geojson"]


@router.get("/scenarios", response_model=PrototypeList, responses=ERRORS)
def prototypes(service: Service, limit: Annotated[int, Query(ge=1, le=100)] = 20,
               offset: Annotated[int, Query(ge=0)] = 0):
    return service.list(limit=limit, offset=offset)


@router.get("/scenarios/{scenario_id}", response_model=PrototypeDetail, responses=ERRORS)
def detail(scenario_id: ScenarioID, service: Service):
    return service.detail(scenario_id)


@router.get("/scenarios/{scenario_id}/layers", response_model=PrototypeLayers, responses=ERRORS)
def layers(scenario_id: ScenarioID, service: Service):
    return service.layers(scenario_id)


@router.get("/scenarios/{scenario_id}/impact", response_model=PrototypeImpact, responses=ERRORS)
def impact(scenario_id: ScenarioID, service: Service):
    return service.impact(scenario_id)


def preview_download(service, scenario_id, resource, request):
    result = download_response(service.download(scenario_id, resource), request)
    result.headers.update({"X-Ukai-Prototype": "true", "X-Ukai-Scientific-Validation": "not_validated"})
    return result


DOWNLOADS = ERRORS | {
    200: {"description": "Verified stored prototype bytes, not scientific approval", "content": {
        mime: {"schema": {"type": "string", "format": "binary"}}
        for mime in ("image/tiff", "application/geo+json", "application/json", "application/octet-stream")}},
    206: {"description": "Single verified byte range"},
    416: problem_spec("Requested range is not satisfiable"),
}


@router.head("/scenarios/{scenario_id}/assets/{asset_type}", responses=ERRORS)
@router.get("/scenarios/{scenario_id}/assets/{asset_type}", response_class=StreamingResponse, responses=DOWNLOADS)
def asset(scenario_id: ScenarioID, asset_type: MapRole, request: Request, service: Service) -> Response:
    return preview_download(service, scenario_id, asset_type, request)


@router.head("/scenarios/{scenario_id}/assumptions", responses=ERRORS)
@router.get("/scenarios/{scenario_id}/assumptions", response_class=StreamingResponse, responses=DOWNLOADS)
def assumptions(scenario_id: ScenarioID, request: Request, service: Service) -> Response:
    return preview_download(service, scenario_id, "assumptions", request)


@router.head("/scenarios/{scenario_id}/quality-report", responses=ERRORS)
@router.get("/scenarios/{scenario_id}/quality-report", response_class=StreamingResponse, responses=DOWNLOADS)
def quality_report(scenario_id: ScenarioID, request: Request, service: Service) -> Response:
    return preview_download(service, scenario_id, "quality-report", request)
