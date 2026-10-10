"""V1 current status is explicitly demo and uses the persisted reading time."""
from collections.abc import Generator

from fastapi import HTTPException
from pydantic import ValidationError
from services.api.app.api_schemas.status import CurrentStatusResponse
from services.api.app.db.session import SessionLocal
from services.api.app.repositories.status_repository import StatusRepository


class StatusService:
    def __init__(self, repository: StatusRepository):
        self.repository = repository

    def current(self) -> CurrentStatusResponse:
        row = self.repository.latest(data_mode="demo")
        if row is None:
            raise HTTPException(404, "No demo status reading is available.")
        try:
            return CurrentStatusResponse.model_validate(dict(
                reservoir_level_m=row.reservoir_level_m, inflow_m3s=row.inflow_m3s,
                release_m3s=row.release_m3s, timestamp=row.reading_time,
                data_mode=row.data_mode,
            ))
        except ValidationError as error:
            raise HTTPException(503, "The registered demo reading is unavailable.") from error


def get_status_service() -> Generator[StatusService, None, None]:
    session = SessionLocal()
    try:
        yield StatusService(StatusRepository(session))
    finally:
        session.close()
