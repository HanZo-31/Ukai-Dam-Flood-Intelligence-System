"""Actual packaging/runtime evidence checks without repeating long native solves."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import pytest
import rasterio

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from rapid_engine.native_provider import NativeProvider
from rapid_engine.compute import validate

BASE=Path(os.environ['UKAI_REFERENCE_ROOT'])
REAL=ROOT/'EVIDENCE/genuine-packaging-v01'

def provider():return NativeProvider(BASE)

def test_actual_readiness_bound_input_and_original_driver():
    p=provider();caps=p.verify()
    assert caps['configuration_id']=='ukai-fast-fixedshape-n0025-v1'
    assert set(caps['available_roles'])=={'max_depth_cog','arrival_time_cog','max_velocity_cog','extent_geojson'}
    assert p.config['parameters']['model_duration_seconds']==410400

def test_missing_bound_file_disables(tmp_path):
    p=provider();p.config=copy.deepcopy(p.config)
    p.config['bound_files']['job:missing.dll']='sha256:'+'0'*64
    with pytest.raises(ValueError):p.verify()

def test_repackage_actual_native_outputs(tmp_path):
    shutil.copytree(REAL/'native',tmp_path/'native')
    p=provider();caps=p.verify()
    req=dict(schema_version='2.0.0',input_family='ukai-hyp-fixed-shape-v1',configuration_id=caps['configuration_id'],
        configuration_checksum=caps['configuration_checksum'],request_id='native-test-package',peak_release_m3s=25000)
    report=json.loads((tmp_path/'native/report.json').read_text())
    product=p.package(req,tmp_path,report,time.perf_counter()-report['worker_total_seconds'])
    validate('Result',product.result)
    assert product.result['actual_peak_release_m3s']==25000
    assert product.result['computed'] and not product.result['scientifically_validated']
    assert product.result['velocity_definition'] and 'not velocity-vector magnitude' in product.result['velocity_definition']
    with rasterio.open(tmp_path/'arrival_time.tif') as ds:
        values=ds.read(1);valid=values!=-9999
        assert np.all(values[valid]%60==0)
    with rasterio.open(tmp_path/'max_depth.tif') as ds:
        values=ds.read(1);assert (values==-9999).any() and (values==0).any()

def test_native_bundle_corruption_rejected(tmp_path):
    shutil.copytree(REAL/'native',tmp_path/'native')
    p=provider();req=json.loads((REAL/'result.json').read_text())
    report=json.loads((tmp_path/'native/report.json').read_text());(tmp_path/'native/native-results.npz').write_bytes(b'corrupt')
    with pytest.raises(ValueError):p.package(req,tmp_path,report,time.perf_counter())
