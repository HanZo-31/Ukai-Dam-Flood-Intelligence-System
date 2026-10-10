import importlib.util
import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
BASE=Path(os.environ['UKAI_REFERENCE_ROOT'])
spec=importlib.util.spec_from_file_location('new_runner',ROOT/'team2_work/run_candidate_service.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_real_v1_and_disabled_v2_share_app(tmp_path):
    with TestClient(module.build_app(BASE,tmp_path/'jobs',enable_compute=False),client=('127.0.0.1',1234)) as client:
        v1=client.get('/api/v1/candidates/capabilities').json()
        assert v1['schema_version']=='1.0.0' and v1['supported_modes']==['stored_reference']
        v2=client.get('/api/v1/candidates/compute-v2/capabilities').json()
        assert v2['schema_version']=='2.0.0' and not v2['enabled']
        req=dict(schema_version='1.0.0',request_id='runner-test-001',mode='stored_reference',
            input_family='ukai-hyp-fixed-shape-v1',peak_release_m3s=20000,allow_nearest_stored=False)
        result=client.post('/api/v1/candidates/jobs',json=req).json()
        assert result['actual_peak_release_m3s']==20000 and not result['computed']
        assert result['source_scenario_id']==json.loads((BASE/'part_a/prototype-manifest.json').read_text())['scenario_id']
        assert (tmp_path/'jobs-compute-v2').is_dir()

def test_v1_openapi_unchanged(tmp_path):
    old=module.create_app(BASE,tmp_path/'old').openapi()
    new=module.build_app(BASE,tmp_path/'new').openapi()
    for path,value in old['paths'].items():assert new['paths'][path]==value
    assert old['components']==new['components']

def test_bad_native_configuration_keeps_v1_working(tmp_path):
    with patch('rapid_engine.native_provider.NativeProvider',side_effect=ValueError('bad native config')):
        with TestClient(module.build_app(BASE,tmp_path/'jobs'),client=('127.0.0.1',1234)) as client:
            assert client.get('/api/v1/candidates/capabilities').status_code==200
            assert not client.get('/api/v1/candidates/compute-v2/capabilities').json()['enabled']
