"""B1 event metadata and approved replay availability, without invented coverage."""
from collections.abc import Generator
from datetime import datetime
import ipaddress
from urllib.parse import urlencode

from pydantic import HttpUrl, TypeAdapter, ValidationError

from services.api.app.api_schemas.historical_event import (
    HistoricalEventListResponse, HistoricalEventSummary, ReplayAvailability,
)
from services.api.app.api_schemas.scenario import DatasetProvenance, OffsetPagination
from services.api.app.db.session import SessionLocal
from services.api.app.repositories.catalog_repository import HistoricalEventRepository
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.services.scenario_service import public_summary


def public_source_urls(values):
    """Return reviewed-shape HTTP(S) links; omit credential/query/local references.

    No URLs are fetched. Omission preserves the original catalogue record while
    keeping signed query values and local-network links out of the public DTO.
    """
    parser = TypeAdapter(HttpUrl)
    result = []
    for value in values:
        try:
            url = parser.validate_python(value)
        except ValidationError:
            continue
        host = (url.host or "").strip("[]").lower()
        if url.username is not None or url.password is not None or url.query or url.fragment:
            continue
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            continue
        try:
            if not ipaddress.ip_address(host).is_global:
                continue
        except ValueError:
            pass  # A public hostname, not an IP literal; no DNS lookup is needed.
        result.append(url)
    return result


class HistoricalEventService:
    def __init__(self, events: HistoricalEventRepository, scenarios: PublishedScenarioRepository):
        self.events = events
        self.scenarios = scenarios

    def list_events(self, *, data_mode: str, limit: int, offset: int,
                    start: datetime | None = None, end: datetime | None = None) -> HistoricalEventListResponse:
        rows = self.events.list(data_mode=data_mode, limit=limit + 1, offset=offset,
                                start=start, end=end)
        items = []
        for row in rows[:limit]:
            datasets = [DatasetProvenance(
                dataset_id=source.dataset_id, version=source.version,
                source_label=source.source_label, license=source.license,
                checksum=source.checksum, crs=source.crs,
                coverage_start=source.coverage_start, coverage_end=source.coverage_end,
            ) for source in self.events.datasets(row.event_id)]
            replays = self.scenarios.list(data_mode=data_mode, scenario_type="historical_replay",
                                          historical_event_id=row.event_id, limit=1)
            url = "/api/v1/scenarios?" + urlencode({
                "data_mode": data_mode, "scenario_type": "historical_replay",
                "historical_event_id": row.event_id,
            })
            items.append(HistoricalEventSummary(
                event_id=row.event_id, name=row.name,
                coverage_start=row.coverage_start, coverage_end=row.coverage_end,
                observed_coverage=row.observed_coverage,
                source_urls=public_source_urls(row.source_urls), data_mode=row.data_mode,
                source_labels=sorted({source.source_label for source in datasets}),
                datasets=datasets,
                replay=ReplayAvailability(available=bool(replays), scenarios_url=url,
                    example=public_summary(replays[0]) if replays else None),
            ))
        return HistoricalEventListResponse(items=items, pagination=OffsetPagination(
            limit=limit, offset=offset, next_offset=offset + limit if len(rows) > limit else None,
        ))


def get_historical_event_service() -> Generator[HistoricalEventService, None, None]:
    session = SessionLocal()
    try:
        yield HistoricalEventService(HistoricalEventRepository(session), PublishedScenarioRepository(session))
    finally:
        session.close()
