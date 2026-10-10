from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_migration_chain_is_linear() -> None:
    versions = ROOT / "database" / "migrations" / "versions"
    newest = (versions / "c01b8f01b101_add_scenario_inputs_and_processing_runs.py").read_text()
    assert 'down_revision = "b52235f9108d"' in newest
    assert "scenario_inputs" in newest
    assert "processing_runs" in newest
