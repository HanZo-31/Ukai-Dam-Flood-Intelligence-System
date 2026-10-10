"""Step 11 regression acceptance, not the deferred cross-team handoff rehearsal."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select

from test_b1_integration import isolated_database, session
from test_gis_catalog import prepared, register
from services.api.app.db.models import ProcessingRun, PublishedBundle, Scenario
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.storage import LocalObjectStore, sha256_file


def assert_hidden(repo, identity, mode):
    assert repo.get(identity, data_mode=mode) is None
    assert repo.list(data_mode=mode) == []
    assert repo.assets(identity, data_mode=mode) == []
    assert repo.summary(identity, data_mode=mode) is None
    assert repo.datasets(identity, data_mode=mode) == []
    assert repo.footprint(identity, data_mode=mode) is None
    assert repo.spatial_assets(identity, data_mode=mode) == []


@pytest.mark.parametrize("gate", ["draft", "rejected", "revoked", "scenario_failed", "run_failed", "quality_failed", "missing_bundle", "wrong_mode"])
def test_all_reads_fail_closed_with_real_gis(session, tmp_path, gate):
    item, store, root = prepared(session, tmp_path)
    register(session, item, store, root)
    repo = PublishedScenarioRepository(session)
    assert repo.get(item.scenario_id, data_mode="demo") is not None
    assert len(repo.assets(item.scenario_id, data_mode="demo")) == 4
    assert repo.summary(item.scenario_id, data_mode="demo") is not None
    assert len(repo.datasets(item.scenario_id, data_mode="demo")) == 1
    assert repo.footprint(item.scenario_id, data_mode="demo") is not None
    assert len(repo.spatial_assets(item.scenario_id, data_mode="demo")) == 4
    scenario = session.scalar(select(Scenario))
    run = session.scalar(select(ProcessingRun))
    if gate in {"draft", "rejected"}:
        scenario.publication_status = gate
    elif gate == "revoked":
        repo.revoke(item.scenario_id, actor="acceptance-test", reason="Synthetic withdrawal")
    elif gate == "scenario_failed":
        scenario.status = "failed"
    elif gate == "run_failed":
        run.status = "failed"
    elif gate == "quality_failed":
        run.validation_status = "fail"
        run.approved_by = None
        run.approved_at = None
    elif gate == "missing_bundle":
        session.delete(session.scalar(select(PublishedBundle)))
    session.flush()
    assert_hidden(repo, item.scenario_id, "production" if gate == "wrong_mode" else "demo")


@pytest.mark.parametrize("mode", [None, "", "unknown"])
@pytest.mark.parametrize("accessor", ["get", "list", "assets", "summary", "datasets", "footprint", "spatial_assets"])
def test_every_public_accessor_requires_explicit_mode(session, mode, accessor):
    method = getattr(PublishedScenarioRepository(session), accessor)
    args = () if accessor == "list" else ("unknown-scenario",)
    with pytest.raises(ValueError, match="explicit"):
        method(*args, data_mode=mode)


@pytest.mark.parametrize("conflicting", [False, True])
def test_concurrent_object_publication_never_overwrites(tmp_path, conflicting):
    store = LocalObjectStore(tmp_path / "objects")
    barrier = Barrier(2)

    def publish(content):
        barrier.wait(timeout=10)
        try:
            return store.put("versions/v1/input.csv", content)
        except ValueError as error:
            return error

    contents = [b"original", b"different" if conflicting else b"original"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(publish, contents))
    successes = [result for result in outcomes if isinstance(result, tuple)]
    assert len(successes) == (1 if conflicting else 2)
    if conflicting:
        assert sum(isinstance(result, ValueError) for result in outcomes) == 1
    path = store.path_for_key("versions/v1/input.csv")
    assert path.read_bytes() in contents
    assert all(checksum == sha256_file(path) for _, checksum in successes)
    assert list(store.root.rglob(".pending-*")) == []


def test_missing_scenario_has_no_public_children(session):
    assert_hidden(PublishedScenarioRepository(session), "missing", "demo")
