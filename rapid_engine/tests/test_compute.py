"""Synthetic infrastructure acceptance; never treated as real Ukai solver evidence."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from fastapi.testclient import TestClient
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rapid_engine.compute import create_app,Produced,PREFIX,digest,atomic,safe_file

PACKET=Path(os.environ.get('UKAI_CONTRACT_PACKET',str(Path(__file__).resolve().parents[2]/'computed_contract')))
EXAMPLES=json.loads((PACKET/'contract/examples.json').read_text())

class FixtureProvider:
    synthetic=True
    def __init__(self, gate=None,fail=False):self.gate=gate;self.fail=fail;self.calls=0
    def verify(self):return EXAMPLES['capabilities_enabled']
    def compute(self,request,folder,cancel):
        self.calls+=1
        while self.gate is not None and not self.gate.is_set():
            if cancel.wait(.01):raise InterruptedError()
        if self.fail:raise ValueError('PRIVATE SECRET C:/private/path')
        result=copy.deepcopy(EXAMPLES['result'])
        for key in ['request_id','configuration_id','configuration_checksum']:result[key]=request[key]
        result.update(job_id=request['request_id'],requested_peak_release_m3s=request['peak_release_m3s'],actual_peak_release_m3s=request['peak_release_m3s'])
        files={}
        for role,name in [('max_depth_cog','candidate-depth.tif'),('arrival_time_cog','candidate-arrival.tif'),('extent_geojson','extent.geojson')]:
            shutil.copyfile(PACKET/'fixtures'/name,folder/name);files[role]=name
            result['assets'][role]['url']=PREFIX+'/jobs/'+request['request_id']+'/assets/'+role
        (folder/'native.bin').write_bytes(b'SYNTHETIC NATIVE TEST BYTES')
        (folder/'diagnostics.json').write_text('{"synthetic":true}')
        result.update(native_results_checksum=digest(folder/'native.bin'),numerical_diagnostics_checksum=digest(folder/'diagnostics.json'))
        return Produced(result,files,'native.bin','diagnostics.json')

def request(identity='compute-test-001',**changes):
    return {**EXAMPLES['request'],'request_id':identity,**changes}

def client(tmp_path,provider=None,**options):
    return TestClient(create_app(tmp_path/'base',tmp_path/'state',provider,test_only=True,**options))

def wait_done(c,identity='compute-test-001'):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        response=c.get(PREFIX+'/jobs/'+identity)
        if response.status_code!=200:return response
        if response.json()['status'] in ['completed','failed']:return response
        time.sleep(.01)
    raise AssertionError('Worker did not finish')

def test_default_disabled(tmp_path):
    with client(tmp_path) as c:
        caps=c.get(PREFIX+'/capabilities').json()
        assert not caps['enabled'] and caps['configuration_checksum'] is None
        assert c.post(PREFIX+'/jobs',json=request()).status_code==503

@pytest.mark.parametrize('changes',[{'peak_release_m3s':31000},{'peak_release_m3s':14999},{'peak_release_m3s':True},
    {'path':'C:/private'},{'schema_version':'1.0.0'},{'request_id':'../evil'},{'input_family':'2006'}, {'allow_nearest_stored':True}])
def test_invalid(tmp_path,changes):
    with client(tmp_path,FixtureProvider()) as c:assert c.post(PREFIX+'/jobs',json=request(**changes)).status_code==422

@pytest.mark.parametrize('payload',['{"request_id":"one","request_id":"two"}','{"peak_release_m3s":NaN}','[]','bad json'])
def test_strict_json(tmp_path,payload):
    with client(tmp_path) as c:assert c.post(PREFIX+'/jobs',content=payload).status_code==422

def test_too_large(tmp_path):
    with client(tmp_path) as c:assert c.post(PREFIX+'/jobs',content=' '*17000).status_code==413

def test_provider_forbidden_operationally(tmp_path):
    with pytest.raises(ValueError):create_app(tmp_path/'base',tmp_path/'state',FixtureProvider())

def test_separate_state(tmp_path):
    with pytest.raises(ValueError):create_app(tmp_path,tmp_path/'state')

def test_completed_cache_identity_and_assets(tmp_path):
    provider=FixtureProvider()
    with client(tmp_path,provider) as c:
        assert c.post(PREFIX+'/jobs',json=request()).status_code==202
        assert wait_done(c).json()['status']=='completed'
        first=c.get(PREFIX+'/jobs/compute-test-001/result').json()
        assert first['actual_peak_release_m3s']==25000 and first['computed'] and not first['scientifically_validated']
        assert c.post(PREFIX+'/jobs',json=request()).status_code==200
        assert c.post(PREFIX+'/jobs',json=request(peak_release_m3s=26000)).status_code==409
        second=c.post(PREFIX+'/jobs',json=request('compute-test-002')).json()
        assert second['status']=='completed' and second['cache_hit'] and provider.calls==1
        reused=c.get(PREFIX+'/jobs/compute-test-002/result').json()
        assert reused['run_id']==first['run_id'] and reused['cache_hit']
        assert reused['assets']['max_depth_cog']['url'].endswith('/compute-test-002/assets/max_depth_cog')

def test_busy_and_partial_resources(tmp_path):
    gate=threading.Event()
    with client(tmp_path,FixtureProvider(gate)) as c:
        c.post(PREFIX+'/jobs',json=request())
        assert c.get(PREFIX+'/jobs/compute-test-001/result').status_code==409
        assert c.get(PREFIX+'/jobs/compute-test-001/assets/max_depth_cog').status_code==409
        assert c.post(PREFIX+'/jobs',json=request('compute-test-002')).status_code==409
        assert c.post(PREFIX+'/jobs',json=request()).status_code==202
        gate.set();assert wait_done(c).json()['status']=='completed'

def test_safe_failure(tmp_path):
    with client(tmp_path,FixtureProvider(fail=True)) as c:
        c.post(PREFIX+'/jobs',json=request());job=wait_done(c).json()
        assert job['status']=='failed' and 'PRIVATE' not in json.dumps(job)
        assert c.get(PREFIX+'/jobs/compute-test-001/result').status_code==409

def test_config_conflict(tmp_path):
    with client(tmp_path,FixtureProvider()) as c:assert c.post(PREFIX+'/jobs',json=request(configuration_id='wrong-config')).status_code==409

def test_unknown_job_role(tmp_path):
    with client(tmp_path) as c:
        assert c.get(PREFIX+'/jobs/no-such-job').status_code==404
        assert c.get(PREFIX+'/jobs/no-such-job/assets/private').status_code==404

@pytest.mark.parametrize('range_header,status',[('bytes=0-9',206),('bytes=-10',206),('bytes=10-',206),('bytes=999999-',416),
    ('bytes=1-0',416),('bytes=-0',416),('bytes=0-1,3-4',416),('potato',416)])
def test_ranges(tmp_path,range_header,status):
    with client(tmp_path,FixtureProvider()) as c:
        c.post(PREFIX+'/jobs',json=request());wait_done(c)
        url=PREFIX+'/jobs/compute-test-001/assets/max_depth_cog'
        full=c.get(url);part=c.get(url,headers={'Range':range_header})
        assert part.status_code==status
        if range_header=='bytes=0-9':assert part.content==full.content[:10]
        if range_header=='bytes=-10':assert part.content==full.content[-10:]
        assert c.head(url).headers['content-length']==str(len(full.content))
        assert not c.head(url).content
        assert c.get(url,headers={'Range':'bytes=0-9','If-Range':'wrong'}).content==full.content
        assert c.get(url,headers={'If-None-Match':full.headers['etag']}).status_code==304

@pytest.mark.parametrize('target',['candidate-depth.tif','native.bin','diagnostics.json','result.json'])
def test_corruption(tmp_path,target):
    with client(tmp_path,FixtureProvider()) as c:
        c.post(PREFIX+'/jobs',json=request());wait_done(c)
        (tmp_path/'state/compute-test-001'/target).write_bytes(b'corrupt')
        assert c.get(PREFIX+'/jobs/compute-test-001/result').status_code==503
        assert c.post(PREFIX+'/jobs',json=request('compute-test-002')).status_code==503

def test_budget(tmp_path):
    with client(tmp_path,FixtureProvider(),max_bytes=1) as c:
        assert c.post(PREFIX+'/jobs',json=request()).status_code==503

def test_restart_interrupt(tmp_path):
    gate=threading.Event()
    with client(tmp_path,FixtureProvider(gate)) as c:c.post(PREFIX+'/jobs',json=request())
    with client(tmp_path,FixtureProvider()) as c:
        assert c.get(PREFIX+'/jobs/compute-test-001').json()['status']=='failed'
        assert c.post(PREFIX+'/jobs',json=request()).status_code==200

def test_recovery_of_saved_running(tmp_path):
    with client(tmp_path,FixtureProvider()) as c:
        c.post(PREFIX+'/jobs',json=request());wait_done(c)
    path=tmp_path/'state/compute-test-001.json';record=json.loads(path.read_text());record['job'].update(status='running',result_url=None)
    atomic(path,record)
    with client(tmp_path) as c:assert c.get(PREFIX+'/jobs/compute-test-001').json()['error']['code']=='interrupted'

def test_state_exclusive(tmp_path):
    with client(tmp_path):
        with pytest.raises(ValueError):
            with client(tmp_path):pass

def test_completed_restart(tmp_path):
    with client(tmp_path,FixtureProvider()) as c:c.post(PREFIX+'/jobs',json=request());wait_done(c)
    with client(tmp_path) as c:assert c.get(PREFIX+'/jobs/compute-test-001/result').status_code==200

@pytest.mark.parametrize('name',['../outside','/outside','C:/outside','x\\y','\x00bad'])
def test_unsafe_local_product_path(tmp_path,name):
    with pytest.raises(ValueError):safe_file(tmp_path,name)

def test_storage_failure_after_generation(tmp_path):
    with client(tmp_path,FixtureProvider(),max_bytes=1000) as c:
        c.post(PREFIX+'/jobs',json=request())
        assert wait_done(c).json()['status']=='failed'
        assert c.get(PREFIX+'/jobs/compute-test-001/assets/max_depth_cog').status_code==409

def test_config_changes_before_worker(tmp_path):
    class Changing(FixtureProvider):
        def __init__(self):super().__init__();self.checks=0
        def verify(self):
            self.checks+=1
            doc=copy.deepcopy(super().verify())
            if self.checks>1:doc['configuration_id']='changed-config'
            return doc
    with client(tmp_path,Changing()) as c:
        c.post(PREFIX+'/jobs',json=request())
        assert wait_done(c).json()['status']=='failed'

def test_metadata_and_cross_job_tampering(tmp_path):
    class Bad(FixtureProvider):
        def compute(self,*args):
            product=super().compute(*args)
            product.result['assets']['max_depth_cog']['url']=PREFIX+'/jobs/foreign-job/assets/max_depth_cog'
            return product
    with client(tmp_path,Bad()) as c:
        c.post(PREFIX+'/jobs',json=request());assert wait_done(c).json()['status']=='failed'

def test_big_job_remains_async(tmp_path):
    gate=threading.Event()
    with client(tmp_path,FixtureProvider(gate)) as c:
        start=time.monotonic();reply=c.post(PREFIX+'/jobs',json=request())
        assert reply.status_code==202 and time.monotonic()-start<2
        assert c.get(PREFIX+'/jobs/compute-test-001').json()['status'] in ['queued','running']
        gate.set();wait_done(c)

@pytest.mark.parametrize('identity',['con','nul','prn','aux','com1','lpt9'])
def test_windows_device_identifiers_are_safe_contract_ids(tmp_path,identity):
    with client(tmp_path,FixtureProvider()) as c:
        assert c.post(PREFIX+'/jobs',json=request(identity)).status_code==202
        assert wait_done(c,identity).json()['status']=='completed'
        assert c.get(PREFIX+'/jobs/'+identity+'/result').status_code==200
        assert (tmp_path/'state'/('_'+identity+'.json')).is_file()
        reused=c.post(PREFIX+'/jobs',json=request('ordinary-next-request')).json()
        assert reused['cache_hit'] and reused['status']=='completed'
