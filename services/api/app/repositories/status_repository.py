from datetime import datetime

from sqlalchemy import select

from services.api.app.db.models import StatusReading
from services.api.app.repositories.base import Repository
from .catalog_repository import page
from .query_filters import time_window


class StatusRepository(Repository):
    def latest(self, *, data_mode=None) -> StatusReading | None:
        rows = self.list(data_mode=data_mode, limit=1)
        return rows[0] if rows else None

    def list(self, *, data_mode=None, start=None, end=None, limit=100, offset=0):
        start, end = time_window(start, end)
        statement = select(StatusReading).order_by(StatusReading.reading_time.desc(), StatusReading.id.desc())
        if data_mode is not None:
            if data_mode not in {"demo", "production"}:
                raise ValueError("unknown data mode")
            statement = statement.where(StatusReading.data_mode == data_mode)
        if start is not None:
            statement = statement.where(StatusReading.reading_time >= start)
        if end is not None:
            statement = statement.where(StatusReading.reading_time <= end)
        return self.session.scalars(page(statement, limit, offset)).all()

    def add(self, *, reading_time: datetime, **values) -> StatusReading:
        reading = StatusReading(reading_time=reading_time, **values)
        self.session.add(reading)
        self.session.flush()
        return reading
