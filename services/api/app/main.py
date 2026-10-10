"""Ukai Dam Flood Intelligence public API entry point."""
import os
from services.api.app.settings import production_settings, business_database_url
from services.api.app.security import SecurityBoundary, security_settings
from services.api.app.services.download_policy import download_policy
from services.api.app.prototype_settings import prototype_settings

# Must precede router/B1 DB imports: production never uses the development .env
# or B1's built-in fallback. The ordinary local test/runtime path is unchanged.
settings = production_settings()
preview_settings = prototype_settings()
download_policy()
security = security_settings() if settings is not None else None
if settings is not None:
    os.environ["DATABASE_URL"] = business_database_url(settings)
    os.environ.pop("DATABASE_URL_FILE", None)

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from services.api.app.api_schemas.problem import Problem
from services.api.app.api.v1.router import router as v1_router
from services.api.app.openapi import build_openapi
from services.api.app.readiness import Readiness
from services.api.app.prototype_runtime import install_preview, build_preview_openapi

app: FastAPI | SecurityBoundary = FastAPI(title="Ukai Dam Flood Intelligence API", version="1.0.0",
              docs_url=None if settings is not None else "/docs",
              redoc_url=None if settings is not None else "/redoc",
              openapi_url=None if settings is not None else "/openapi.json",
              description="Read-only access to approved, precomputed flood scenarios.")
app.include_router(v1_router)
install_preview(app, preview_settings)
# FastAPI's custom-schema hook is a dynamic method replacement.
setattr(app, "openapi", lambda: build_openapi(app) if preview_settings is None else build_preview_openapi(app))
app.state.readiness = Readiness(settings)


@app.get("/readyz", include_in_schema=False)
async def ready(request: Request):
    if not await app.state.readiness.check():
        return problem_response(request, 503, "Service unavailable",
                                "The service is not ready to receive traffic.", {"Retry-After": "1"})
    return JSONResponse({"status": "ready"}, headers={"Cache-Control": "no-store",
                                                     "X-Content-Type-Options": "nosniff"})


def problem_response(request, status: int, title: str, detail: str, headers=None):
    # Exclude query parameters and rejected input values from error envelopes.
    problem = Problem(title=title, status=status, detail=detail, instance=request.scope["path"])
    return JSONResponse(problem.model_dump(), status_code=status,
                        media_type="application/problem+json",
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"} | (headers or {}))


@app.exception_handler(HTTPException)
async def http_error(request, error):
    titles = {404: "Not found", 405: "Method not allowed", 416: "Range not satisfiable",
              422: "Invalid request", 503: "Service unavailable"}
    return problem_response(request, error.status_code,
        titles.get(error.status_code, "Request failed"), str(error.detail), error.headers)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    return problem_response(request, 422, "Invalid request", "The request parameters are invalid.")


@app.exception_handler(SQLAlchemyError)
async def database_error(request, error):
    return problem_response(request, 503, "Service unavailable", "The catalogue is temporarily unavailable.")


@app.exception_handler(ValidationError)
@app.exception_handler(ResponseValidationError)
async def invalid_registered_data(request, error):
    return problem_response(request, 503, "Service unavailable", "The registered response data is unavailable.")


@app.exception_handler(Exception)
async def unexpected_error(request, error):
    return problem_response(request, 500, "Internal server error", "The request could not be completed.")


if security is not None:
    app = SecurityBoundary(app, security)
