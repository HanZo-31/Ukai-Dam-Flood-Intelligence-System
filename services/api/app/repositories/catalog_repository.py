"""Append-only catalog registration. Callers own commit/rollback boundaries."""
from sqlalchemy import select

from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate, HistoricalEventCreate, ValidationMetricCreate
from services.api.app.db.models import Dataset, DatasetVersion, HistoricalEvent, HistoricalEventDataset, ValidationMetric, ProcessingRun, Scenario
from .base import Repository
from .query_filters import time_window


def page(statement, limit, offset):
    if isinstance(limit, bool) or isinstance(offset, bool) or not isinstance(limit, int) or not isinstance(offset, int) or not 1 <= limit <= 1000 or offset < 0:
        raise ValueError("limit must be 1..1000 and offset a nonnegative integer")
    return statement.limit(limit).offset(offset)


class DatasetRepository(Repository):
    def get(self, dataset_id):
        return self.session.scalar(select(Dataset).where(Dataset.dataset_id == dataset_id))

    def get_version(self, dataset_id, version):
        return self.session.scalar(select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id, DatasetVersion.version == version))

    def register(self, data: DatasetCreate):
        data = DatasetCreate.model_validate(data)
        if self.get(data.dataset_id):
            raise ValueError("dataset already exists")
        row = Dataset(**data.model_dump())
        self.session.add(row)
        self.session.flush()
        return row

    def register_version(self, data: DatasetVersionCreate):
        data = DatasetVersionCreate.model_validate(data)
        parent = self.get(data.dataset_id)
        if parent is None:
            raise ValueError("dataset does not exist")
        if parent.data_mode == "production" and data.source_label == "demo":
            raise ValueError("demo source cannot belong to a production dataset")
        if self.get_version(data.dataset_id, data.version):
            raise ValueError("dataset version already exists; register a new version instead")
        values = data.model_dump(exclude={"time_coverage", "source_url"})
        values["source_url"] = str(data.source_url) if data.source_url else None
        values["coverage_start"] = data.time_coverage.start if data.time_coverage else None
        values["coverage_end"] = data.time_coverage.end if data.time_coverage else None
        row = DatasetVersion(**values)
        self.session.add(row)
        self.session.flush()
        return row

    def list(self, *, data_mode=None, limit=100, offset=0):
        statement = select(Dataset).order_by(Dataset.dataset_id)
        if data_mode is not None:
            statement = statement.where(Dataset.data_mode == data_mode)
        return self.session.scalars(page(statement, limit, offset)).all()

    def list_versions(self, dataset_id, *, source_label=None, crs=None, start=None, end=None, limit=100, offset=0):
        start, end = time_window(start, end)
        statement = select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.id)
        for field, value in ((DatasetVersion.source_label, source_label), (DatasetVersion.crs, crs)):
            if value is not None:
                statement = statement.where(field == value)
        if start is not None:
            statement = statement.where(DatasetVersion.coverage_end >= start)
        if end is not None:
            statement = statement.where(DatasetVersion.coverage_start <= end)
        return self.session.scalars(page(statement, limit, offset)).all()


class HistoricalEventRepository(Repository):
    def get(self, event_id):
        return self.session.scalar(select(HistoricalEvent).where(HistoricalEvent.event_id == event_id))

    def register(self, data: HistoricalEventCreate):
        data = HistoricalEventCreate.model_validate(data)
        if self.get(data.event_id):
            raise ValueError("historical event already exists")
        values = data.model_dump(exclude={"time_coverage", "source_urls"})
        row = HistoricalEvent(**values, coverage_start=data.time_coverage.start, coverage_end=data.time_coverage.end, source_urls=[str(url) for url in data.source_urls])
        self.session.add(row)
        self.session.flush()
        return row

    def link_dataset(self, event_id, dataset_id, version):
        event = self.get(event_id)
        datasets = DatasetRepository(self.session)
        source = datasets.get_version(dataset_id, version)
        if event is None or source is None:
            raise ValueError("event and dataset version must exist")
        if event.data_mode != datasets.get(dataset_id).data_mode:
            raise ValueError("event and dataset data modes must match")
        existing = self.session.scalar(select(HistoricalEventDataset).where(HistoricalEventDataset.event_id == event_id, HistoricalEventDataset.dataset_version_id == source.id))
        if existing:
            return existing
        row = HistoricalEventDataset(event_id=event_id, dataset_version_id=source.id)
        self.session.add(row)
        self.session.flush()
        return row

    def datasets(self, event_id):
        return self.session.scalars(select(DatasetVersion).join(HistoricalEventDataset, HistoricalEventDataset.dataset_version_id == DatasetVersion.id).where(HistoricalEventDataset.event_id == event_id).order_by(DatasetVersion.id)).all()

    def list(self, *, data_mode=None, start=None, end=None, limit=100, offset=0):
        start, end = time_window(start, end)
        statement = select(HistoricalEvent).order_by(HistoricalEvent.coverage_start, HistoricalEvent.event_id)
        if data_mode is not None:
            statement = statement.where(HistoricalEvent.data_mode == data_mode)
        if start is not None:
            statement = statement.where(HistoricalEvent.coverage_end >= start)
        if end is not None:
            statement = statement.where(HistoricalEvent.coverage_start <= end)
        return self.session.scalars(page(statement, limit, offset)).all()


class ValidationMetricRepository(Repository):
    def get(self, metric_id):
        return self.session.scalar(select(ValidationMetric).where(ValidationMetric.metric_id == metric_id))

    def register(self, data: ValidationMetricCreate):
        data = ValidationMetricCreate.model_validate(data)
        if self.get(data.metric_id):
            raise ValueError("validation metric already exists")
        events = HistoricalEventRepository(self.session)
        event = events.get(data.event_id)
        source = DatasetRepository(self.session).get_version(data.dataset_id, data.dataset_version)
        if event is None or source is None:
            raise ValueError("event and dataset version must exist")
        linked = self.session.scalar(select(HistoricalEventDataset).where(HistoricalEventDataset.event_id == data.event_id, HistoricalEventDataset.dataset_version_id == source.id))
        if linked is None:
            raise ValueError("observation dataset version must be linked to the event")
        if source.source_label not in {"observed", "demo"}:
            raise ValueError("validation requires observed or explicitly demo reference data")
        if data.run_id:
            run = self.session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == data.run_id))
            if run is None or run.status != "completed":
                raise ValueError("validation run must exist and be completed")
            scenario = self.session.scalar(select(Scenario).where(Scenario.scenario_id == run.scenario_id))
            if scenario.model_version != data.model_version or scenario.data_mode != event.data_mode:
                raise ValueError("validation model version and data mode must match the run")
        values = data.model_dump(exclude={"dataset_id", "dataset_version"})
        row = ValidationMetric(**values, dataset_version_id=source.id)
        self.session.add(row)
        self.session.flush()
        return row

    def list(self, *, event_id=None, station_id=None, model_version=None, metric_name=None,
             data_mode=None, run_id=None, start=None, end=None, limit=100, offset=0):
        start, end = time_window(start, end)
        statement = select(ValidationMetric).order_by(ValidationMetric.computed_at, ValidationMetric.metric_id)
        if data_mode is not None:
            if data_mode not in {"demo", "production"}:
                raise ValueError("unknown data mode")
            statement = statement.join(HistoricalEvent, HistoricalEvent.event_id == ValidationMetric.event_id).where(HistoricalEvent.data_mode == data_mode)
        if run_id is not None:
            statement = statement.where(ValidationMetric.run_id == run_id)
        if start is not None:
            statement = statement.where(ValidationMetric.computed_at >= start)
        if end is not None:
            statement = statement.where(ValidationMetric.computed_at <= end)
        for field, value in ((ValidationMetric.event_id, event_id), (ValidationMetric.station_id, station_id), (ValidationMetric.model_version, model_version), (ValidationMetric.metric_name, metric_name)):
            if value is not None:
                statement = statement.where(field == value)
        return self.session.scalars(page(statement, limit, offset)).all()
