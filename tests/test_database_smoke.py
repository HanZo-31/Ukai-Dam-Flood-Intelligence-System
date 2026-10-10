"""Opt-in integration test: requires a migrated local Postgres instance."""
import os
import uuid
import json
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import text
from test_b1_integration import isolated_database, session

load_dotenv(Path(__file__).parents[1] / ".env")


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not configured")
def test_required_b1_tables_are_available() -> None:
    from services.api.app.db.session import engine

    required = {"scenarios", "result_assets", "impact_summaries", "status_readings", "scenario_inputs", "processing_runs", "datasets", "dataset_versions", "historical_events", "historical_event_datasets", "validation_metrics", "published_bundles", "scenario_dataset_versions", "publication_actions"}
    with engine.connect() as connection:
        actual = set(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'" )).scalars())
    assert required | {"asset_spatial_metadata", "scenario_spatial_metadata"} <= actual


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not configured")
def test_registration_persists_inputs_in_one_transaction(session, isolated_database) -> None:
    from services.api.app.repositories.scenario_repository import ScenarioRepository
    from services.api.app.schemas import ScenarioManifest
    from scripts.backup_db import snapshot

    engine, _ = isolated_database
    before = snapshot(engine)  # Explicit public reads; the writer is isolated.

    fixture = Path(__file__).parent / "fixtures" / "scenario_manifest.json"
    payload = json.loads(fixture.read_text())
    payload["scenario_id"] = f"db-test-{uuid.uuid4().hex[:12]}"
    manifest = ScenarioManifest.model_validate(payload)
    repository = ScenarioRepository(session)
    scenario = repository.register(manifest)
    assert scenario.status == "registered"
    assert len(session.execute(text("SELECT id FROM scenario_inputs WHERE scenario_id = :scenario_id"), {"scenario_id": scenario.scenario_id}).all()) == 1
    session.rollback()
    assert snapshot(engine) == before  # Includes live ID sequences, not only rows.
