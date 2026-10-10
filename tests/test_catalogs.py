"""Disposable-schema tests with synthetic demo records, not scientific results."""
from datetime import datetime, timezone
import pytest
from alembic import command
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_b1_integration import isolated_database, session, manifest
from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate, HistoricalEventCreate, ValidationMetricCreate
from services.api.app.db.models import Dataset, DatasetVersion, HistoricalEvent, HistoricalEventDataset, ValidationMetric
from services.api.app.repositories.catalog_repository import DatasetRepository, HistoricalEventRepository, ValidationMetricRepository
from services.api.app.repositories.scenario_repository import ScenarioRepository
from services.api.app.repositories.run_repository import RunRepository

START, END = "2000-01-01T00:00:00Z", "2000-01-02T00:00:00Z"
CHECKSUM = "sha256:" + "a" * 64  # Placeholder for metadata testing only.


def dataset(**changes):
    values = dict(dataset_id="demo-gauge", name="Synthetic gauge", description="Test data only")
    return DatasetCreate.model_validate(dict(values, **changes))


def version(**changes):
    values = dict(dataset_id="demo-gauge", version="v1", source_reference="datasets/demo-gauge/v1/gauge.csv", source_url="https://example.org/demo", source_label="demo", license="Synthetic fixture", checksum=CHECKSUM, crs=None, time_coverage={"start": START, "end": END}, quality_notes="Not observed data", units={"stage": "m"})
    values.update(changes)
    return DatasetVersionCreate.model_validate(values)


def event(**changes):
    values = dict(event_id="demo-event", name="Synthetic event", time_coverage={"start": START, "end": END}, observed_coverage="Synthetic station only", quality_notes="Demo only", source_urls=["https://example.org/demo"])
    values.update(changes)
    return HistoricalEventCreate.model_validate(values)


def metric(**changes):
    values = dict(metric_id="demo-rmse", event_id="demo-event", dataset_id="demo-gauge", dataset_version="v1", model_version="demo-model-v1", station_id="demo-station", metric_name="rmse", value=0.5, unit="m", sample_count=24, computed_at=END, calculation_config={"formula": "sqrt(mean(error**2))", "demo": True}, report_reference="validation/demo-event/report.json", report_checksum=CHECKSUM)
    values.update(changes)
    return ValidationMetricCreate.model_validate(values)


def catalog(session, *, link=True, source_label="demo"):
    datasets = DatasetRepository(session)
    datasets.register(dataset())
    source = datasets.register_version(version(source_label=source_label))
    events = HistoricalEventRepository(session)
    item = events.register(event())
    if link:
        events.link_dataset(item.event_id, source.dataset_id, source.version)
    return datasets, source, events, item


@pytest.mark.parametrize("changes", [
    {"checksum": "invalid"}, {"source_label": "unknown"}, {"crs": "WGS84"},
    {"source_reference": "../gauge.csv"}, {"source_reference": "https://example.org/file"},
    {"time_coverage": {"start": END, "end": START}},
    {"time_coverage": {"start": "2000-01-01T00:00:00", "end": END}},
    {"license": ""}, {"quality_notes": ""}, {"unexpected": 1},
])
def test_invalid_dataset_provenance(changes):
    with pytest.raises(ValidationError):
        version(**changes)


@pytest.mark.parametrize("changes", [
    {"value": float("nan")}, {"value": float("inf")}, {"value": -0.1},
    {"metric_name": "iou", "value": 1.1, "unit": "fraction"},
    {"metric_name": "iou", "value": 0.2, "unit": "percent"},
    {"sample_count": 0}, {"sample_count": True}, {"computed_at": "2000-01-02"},
    {"calculation_config": {}}, {"calculation_config": {"threshold": float("inf")}},
    {"report_checksum": "bad"}, {"metric_name": "made-up"},
])
def test_invalid_metric_metadata(changes):
    with pytest.raises(ValidationError):
        metric(**changes)


@pytest.mark.parametrize("name", ["peak_stage_error", "timing_error"])
def test_signed_errors_are_valid(name):
    assert metric(metric_name=name, value=-1.0).value == -1.0


def test_source_urls_do_not_accept_credentials():
    with pytest.raises(ValidationError):
        version(source_url="https://user:password@example.org/data")
    with pytest.raises(ValidationError):
        event(source_urls=["https://user:password@example.org/event"])


@pytest.mark.parametrize("changes", [{"source_urls": []}, {"source_urls": ["file:///tmp/event"]}, {"time_coverage": {"start": END, "end": START}}])
def test_invalid_event_metadata(changes):
    with pytest.raises(ValidationError):
        event(**changes)


def test_catalog_roundtrip_and_rollback(session):
    datasets, source, events, item = catalog(session)
    assert datasets.get_version("demo-gauge", "v1").checksum == CHECKSUM
    assert source.coverage_start.tzinfo is not None
    assert source.units == {"stage": "m"}
    assert events.datasets("demo-event")[0].id == source.id
    assert events.link_dataset("demo-event", "demo-gauge", "v1").dataset_version_id == source.id
    metrics = ValidationMetricRepository(session)
    row = metrics.register(metric())
    assert metrics.get("demo-rmse").dataset_version_id == source.id
    assert metrics.list(event_id=item.event_id, station_id="demo-station", model_version="demo-model-v1")[0].id == row.id
    assert metrics.list(station_id="missing") == []
    session.rollback()
    for model in (Dataset, DatasetVersion, HistoricalEvent, HistoricalEventDataset, ValidationMetric):
        assert session.scalars(select(model)).all() == []


def test_append_only_registration_and_pagination(session):
    datasets, source, events, item = catalog(session)
    for call in (lambda: datasets.register(dataset()), lambda: datasets.register_version(version(checksum="sha256:" + "b" * 64)), lambda: events.register(event())):
        with pytest.raises(ValueError, match="already exists"):
            call()
    assert source.checksum == CHECKSUM
    second = datasets.register_version(version(version="v2"))
    assert datasets.list_versions("demo-gauge", limit=1, offset=1)[0].id == second.id
    assert datasets.list(data_mode="production") == []
    assert events.list(start=datetime(2001, 1, 1, tzinfo=timezone.utc)) == []
    assert events.list(end=datetime(1999, 1, 1, tzinfo=timezone.utc)) == []
    metrics = ValidationMetricRepository(session)
    metrics.register(metric())
    with pytest.raises(ValueError, match="already exists"):
        metrics.register(metric())


@pytest.mark.parametrize("limit,offset", [(0, 0), (1001, 0), (1, -1), (True, 0), (1, 1.1)])
def test_invalid_pagination(session, limit, offset):
    for repo in (DatasetRepository(session), HistoricalEventRepository(session), ValidationMetricRepository(session)):
        with pytest.raises(ValueError, match="limit"):
            repo.list(limit=limit, offset=offset)


def test_missing_parents_and_unlinked_observations(session):
    with pytest.raises(ValueError, match="does not exist"):
        DatasetRepository(session).register_version(version())
    with pytest.raises(ValueError, match="must exist"):
        HistoricalEventRepository(session).link_dataset("missing", "missing", "v1")
    with pytest.raises(ValueError, match="must exist"):
        ValidationMetricRepository(session).register(metric())
    catalog(session, link=False)
    with pytest.raises(ValueError, match="linked"):
        ValidationMetricRepository(session).register(metric())


def test_demo_production_separation(session):
    datasets = DatasetRepository(session)
    datasets.register(dataset(data_mode="production"))
    with pytest.raises(ValueError, match="production"):
        datasets.register_version(version())
    datasets.register_version(version(source_label="observed"))
    events = HistoricalEventRepository(session)
    events.register(event())
    with pytest.raises(ValueError, match="modes"):
        events.link_dataset("demo-event", "demo-gauge", "v1")


def test_simulated_reference_is_not_an_observation(session):
    catalog(session, source_label="simulated")
    with pytest.raises(ValueError, match="observed"):
        ValidationMetricRepository(session).register(metric())


def test_mutated_dto_is_revalidated(session):
    datasets, *_ = catalog(session)
    data = version(version="v2")
    data.checksum = "bad"
    with pytest.raises(ValidationError):
        datasets.register_version(data)


@pytest.mark.parametrize("field,value", [("value", float("nan")), ("value", float("inf")), ("value", -1.0), ("sample_count", 0), ("report_checksum", "bad")])
def test_database_rejects_invalid_metric_even_without_repository(session, field, value):
    _, source, *_ = catalog(session)
    values = metric().model_dump(exclude={"dataset_id", "dataset_version"})
    values[field] = value
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(ValidationMetric(**values, dataset_version_id=source.id))
            session.flush()


def test_database_enforces_event_dataset_link(session):
    _, source, *_ = catalog(session, link=False)
    values = metric().model_dump(exclude={"dataset_id", "dataset_version"})
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(ValidationMetric(**values, dataset_version_id=source.id))
            session.flush()


@pytest.mark.parametrize("table", ["datasets", "dataset_versions", "historical_events", "historical_event_datasets"])
def test_provenance_cannot_be_deleted_while_referenced(session, table):
    catalog(session)
    ValidationMetricRepository(session).register(metric())
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(text(f'DELETE FROM "{table}"'))


def test_metrics_with_processing_run(session):
    catalog(session)
    scenario = ScenarioRepository(session).register(manifest())
    runs = RunRepository(session)
    run = runs.start(scenario_id=scenario.scenario_id, run_id="catalog-run", stage="model")
    metrics = ValidationMetricRepository(session)
    with pytest.raises(ValueError, match="completed"):
        metrics.register(metric(run_id=run.run_id))
    runs.finish(run, status="completed", metadata_json={})
    with pytest.raises(ValueError, match="model version"):
        metrics.register(metric(run_id=run.run_id, model_version="wrong"))
    metrics.register(metric(run_id=run.run_id, model_version=scenario.model_version))
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.delete(run)
            session.flush()


def test_committed_catalog_can_be_read_in_new_session(isolated_database):
    engine, _ = isolated_database
    try:
        with Session(engine) as writer, writer.begin():
            catalog(writer)
            ValidationMetricRepository(writer).register(metric())
        with Session(engine) as reader:
            assert DatasetRepository(reader).get_version("demo-gauge", "v1").checksum == CHECKSUM
            assert HistoricalEventRepository(reader).datasets("demo-event")[0].version == "v1"
            assert ValidationMetricRepository(reader).get("demo-rmse").calculation_config["demo"] is True
    finally:
        # Only this module's disposable schema; never the working public DB.
        with engine.begin() as connection:
            for table in ("validation_metrics", "historical_event_datasets", "historical_events", "dataset_versions", "datasets"):
                connection.execute(text(f'DELETE FROM "{table}"'))


def test_additive_upgrade_preserves_existing_rows(isolated_database):
    engine, config = isolated_database
    command.downgrade(config, "c01b8f01b101")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO scenarios (scenario_id,scenario_type,status,model_version,input_dataset_version,crs,parameters,data_mode) VALUES ('preservation-test','demo','registered','v1','v1','EPSG:4326','{}','demo')"))
        before = connection.execute(text("SELECT row_to_json(s) FROM scenarios s WHERE scenario_id='preservation-test'")).scalar_one()
    try:
        command.upgrade(config, "head")
        command.check(config)
        with engine.connect() as connection:
            after = connection.execute(text("SELECT row_to_json(s) FROM scenarios s WHERE scenario_id='preservation-test'")).scalar_one()
            assert {key: after[key] for key in before} == before
        command.downgrade(config, "c01b8f01b101")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT row_to_json(s) FROM scenarios s WHERE scenario_id='preservation-test'")).scalar_one() == before
        command.upgrade(config, "head")
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM scenarios WHERE scenario_id='preservation-test'"))
