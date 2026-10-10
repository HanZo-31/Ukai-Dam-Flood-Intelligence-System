"""Unknown producing timezone must remain unknown and never reach publication."""
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from services.api.app.published_contract import PublishedScenarioManifest, require_publishable, published_json_schema

ROOT = Path(__file__).resolve().parents[1]


def payload():
    return json.loads((ROOT / 'part_a/prototype-manifest.json').read_text())


def test_real_draft_retains_unknown_timestamp_and_reason():
    item = PublishedScenarioManifest.model_validate(payload())
    assert item.run_timestamp is None
    assert 'timezone' in item.run_timestamp_unknown_reason
    assert all(d.license.startswith('UNKNOWN:') for d in item.datasets)
    with pytest.raises(ValueError):
        require_publishable(item)


@pytest.mark.parametrize('change', [
    {'schema_version': '1.0.0'}, {'run_timestamp_unknown_reason': None},
    {'status': 'approved'}, {'run_timestamp': '2026-10-07T08:34:11Z'},
])
def test_incomplete_or_misrepresented_draft_rejected(change):
    with pytest.raises(ValidationError):
        PublishedScenarioManifest.model_validate(payload() | change)


def test_legacy_canonical_snapshot_has_no_new_null_field():
    old = json.loads((ROOT / 'docs/contracts/examples/prototype-manifest.synthetic.json').read_text())
    saved = PublishedScenarioManifest.model_validate(old).model_dump(mode='json')
    assert 'run_timestamp_unknown_reason' not in saved


def test_unverified_historical_draft_does_not_invent_observed_event():
    values = payload() | {'scenario_type': 'historical_replay', 'historical_event_id': None}
    item = PublishedScenarioManifest.model_validate(values)
    assert item.historical_event_id is None
    with pytest.raises(ValueError):
        require_publishable(item)
    values['schema_version'] = '1.0.0'
    values['run_timestamp'] = '2026-10-07T08:34:11Z'
    values.pop('run_timestamp_unknown_reason')
    with pytest.raises(ValidationError, match='historical_event_id'):
        PublishedScenarioManifest.model_validate(values)


@pytest.mark.parametrize('change', [{'schema_version': '1.0.0'},
    {'run_timestamp_unknown_reason': None}, {'status': 'approved'}])
def test_json_schema_enforces_the_same_draft_boundary(change):
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(published_json_schema())
    assert not list(validator.iter_errors(payload()))
    assert list(validator.iter_errors(payload() | change))
