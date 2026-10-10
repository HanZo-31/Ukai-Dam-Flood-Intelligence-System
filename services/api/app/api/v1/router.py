from fastapi import APIRouter
from .health import router as health_router
from .scenarios import router as scenarios_router
from .historical_events import router as historical_events_router
from .status import router as status_router
from .exports import router as exports_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(scenarios_router)
router.include_router(historical_events_router)
router.include_router(status_router)
router.include_router(exports_router)
