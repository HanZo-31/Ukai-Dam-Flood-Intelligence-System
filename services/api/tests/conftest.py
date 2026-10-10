"""B2 HTTP tests use B1's disposable schema and real synthetic GIS assets."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Reuse the B1 migration/cleanup fixture, not its working database session.
# pytest.ini exposes the existing root tests directory for standalone B2 runs.
from test_b1_integration import isolated_database as isolated_database
from scripts.gis_fixture import build_fixture
from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate, HistoricalEventCreate
from services.api.app.gis_validation import GISInspector
from services.api.app.main import app
from services.api.app.published_registry import register_published_bundle
from services.api.app.repositories.catalog_repository import DatasetRepository, HistoricalEventRepository
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.services.scenario_service import ScenarioService, get_scenario_service
from services.api.app.repositories.status_repository import StatusRepository
from services.api.app.services.historical_event_service import HistoricalEventService, get_historical_event_service
from services.api.app.services.status_service import StatusService, get_status_service
from services.api.app.storage import LocalObjectStore


def pytest_addoption(parser):
    parser.addoption("--b2-examples-output", default=None,
                     help="Explicitly regenerate synthetic HTTP documentation examples at this path.")


@pytest.fixture
def b2_session(isolated_database):
    engine, _ = isolated_database
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.rollback()


@pytest.fixture
def scenario_store(tmp_path):
    return LocalObjectStore(tmp_path / "objects")


@pytest.fixture
def scenario_factory(b2_session, scenario_store):
    """Generate GIS files in pytest temp storage; approval exists only in tests."""
    store = scenario_store
    draft, root, _ = build_fixture(store, prefix="b2-tests/synthetic-gis/")
    datasets = DatasetRepository(b2_session)
    for source in draft.datasets:
        datasets.register(DatasetCreate(
            dataset_id=source.dataset_id,
            name="B2 synthetic integration fixture",
            description="Invented input for HTTP contract testing; no observations.",
            data_mode="demo",
        ))
        values = source.model_dump()
        values["source_reference"] = store.resolve_uri(root + source.source_reference).as_uri()
        datasets.register_version(DatasetVersionCreate.model_validate(values))

    def create(scenario_id="b2-approved-001", *, status="approved", historical_event_id=None,
               summary_updates=None, exports=False):
        if status not in {"approved", "draft", "rejected", "revoked"}:
            raise ValueError("Unsupported fixture status")
        item = draft.model_copy(deep=True)
        item.scenario_id = scenario_id
        item.run_id = scenario_id + "-run"
        if exports:
            # Explicit synthetic derivative, not an API-generated/relabelled
            # extent. B1 inspects this actual registered GeoJSON too.
            reference = "results/export.geojson"
            content = store.resolve_uri(root + item.assets["extent_geojson"]).read_bytes()
            _, checksum = store.put("b2-tests/synthetic-gis/" + reference, content)
            item.assets["export_geojson"] = reference
            item.asset_metadata["export_geojson"] = item.asset_metadata["extent_geojson"].model_copy(
                update={"checksum": checksum}, deep=True)
        if summary_updates is not None:
            from services.api.app.published_contract import ImpactSummary
            item.summary = ImpactSummary.model_validate(item.summary.model_dump() | summary_updates)
        if historical_event_id is not None:
            item.scenario_type = "historical_replay"
            item.historical_event_id = historical_event_id
            events = HistoricalEventRepository(b2_session)
            if events.get(historical_event_id) is None:
                events.register(HistoricalEventCreate(
                    event_id=historical_event_id, name="Synthetic B2 replay event",
                    time_coverage=item.time_coverage,
                    observed_coverage="Synthetic test coverage only",
                    quality_notes="No historical observation or scientific approval claimed",
                    source_urls=["https://example.org/b2-synthetic-fixture"], data_mode="demo",
                ))
                for source in item.datasets:
                    events.link_dataset(historical_event_id, source.dataset_id, source.version)
        if status in {"approved", "revoked"}:
            item.status = "approved"
            item.quality.validation_status = "pass"
            item.quality.approved_by = "synthetic-fixture-reviewer"
            item.quality.approved_at = item.run_timestamp + timedelta(minutes=15)
        elif status == "rejected":
            item.status = "rejected"
            item.quality.validation_status = "fail"
        register_published_bundle(
            b2_session, item, store, bundle_root_uri=root,
            registered_by="b2-test-operator",
            trusted_approvers={"synthetic-fixture-reviewer"},
            asset_inspector=GISInspector(),
        )
        if status == "revoked":
            PublishedScenarioRepository(b2_session).revoke(
                scenario_id, actor="b2-test-operator", reason="Synthetic test withdrawal",
            )
        return item

    return create


@pytest.fixture
def b2_client(b2_session, scenario_store):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_scenario_service] = lambda: ScenarioService(
        PublishedScenarioRepository(b2_session), store=scenario_store
    )
    app.dependency_overrides[get_historical_event_service] = lambda: HistoricalEventService(
        HistoricalEventRepository(b2_session), PublishedScenarioRepository(b2_session),
    )
    app.dependency_overrides[get_status_service] = lambda: StatusService(StatusRepository(b2_session))
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
