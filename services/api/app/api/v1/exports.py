from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response
from services.api.app.api_schemas.export import ScenarioExportResponse
from services.api.app.api.v1.responses import ERRORS
from services.api.app.services.scenario_service import ScenarioService, get_scenario_service

router = APIRouter(tags=["exports"])


@router.get("/exports/{scenario_id}", response_model=ScenarioExportResponse,
            responses=ERRORS, summary="Discover a verified registered export",
            description="Returns a safe download link for an approved, existing derivative. "
                        "Does not generate files, substitute map layers, or grant GIS approval.")
def scenario_export(
    scenario_id: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9_-]{2,149}$")],
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
    response: Response,
    format: Annotated[Literal["geojson", "kml"], Query()],
    data_mode: Literal["demo", "production"] = "demo",
) -> ScenarioExportResponse:
    response.headers["Cache-Control"] = "no-store"
    return service.export(scenario_id, format=format, data_mode=data_mode)
