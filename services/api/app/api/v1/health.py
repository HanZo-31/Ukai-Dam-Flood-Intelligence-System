from fastapi import APIRouter
from services.api.app.api_schemas.health import HealthResponse
from services.api.app.api.v1.responses import ERRORS

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, responses={500: ERRORS[500]}, summary="Check API availability")
def health() -> HealthResponse:
    return HealthResponse()
