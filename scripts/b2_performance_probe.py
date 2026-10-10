"""Bounded closed-loop local HTTP load and read-only cgroup measurements."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]

METRICS_CODE = r'''
import json,os,select,shutil,sys,time
from pathlib import Path
root=Path('/sys/fs/cgroup')
def pairs(name):
    return {k:int(v) for k,v in (line.split() for line in (root/name).read_text().splitlines())}
while True:
    usage=shutil.disk_usage('/tmp')
    fds=rss=0
    for proc in Path('/proc').glob('[0-9]*'):
        if proc.name==str(os.getpid()): continue
        try:
            fds+=len(list((proc/'fd').iterdir()))
            for line in (proc/'status').read_text().splitlines():
                if line.startswith('VmRSS:'): rss+=int(line.split()[1])*1024
        except (OSError,ValueError): pass
    print(json.dumps({'memory_current':int((root/'memory.current').read_text()),
        'memory_peak_since_start':int((root/'memory.peak').read_text()),
        'memory_events':pairs('memory.events'),'cpu':pairs('cpu.stat'),
        'scratch_free':usage.free,'scratch_total':usage.total,'process_rss_sum':rss,
        'process_fd_sum':fds,'pids_current':int((root/'pids.current').read_text())}),flush=True)
    if select.select([sys.stdin],[],[],1)[0]:
        sys.stdin.readline()
        break
'''


def read_profile(path):
    raw = Path(path).read_bytes()
    if len(raw) > 65536:
        raise ValueError('Profile is too large')
    profile = json.loads(raw)
    required = {'schema_version','profile_id','approval','catalogue_extra_scenarios','json_concurrency',
        'artifact_concurrency','json_duration_seconds','artifact_duration_seconds','mixed_duration_seconds',
        'max_phase_seconds','json_min_samples_per_route','artifact_min_samples','http_timeout_seconds',
        'targets','cache_conditions','load_model','fixture_scope'}
    if set(profile) != required or profile['schema_version'] != 1:
        raise ValueError('Unsupported performance profile')
    bounds = {'catalogue_extra_scenarios':(1,500),'json_concurrency':(1,16),'artifact_concurrency':(1,2),
        'json_duration_seconds':(10,300),'artifact_duration_seconds':(10,300),'mixed_duration_seconds':(10,300),
        'max_phase_seconds':(30,600),'json_min_samples_per_route':(20,1000),'artifact_min_samples':(20,200),
        'http_timeout_seconds':(10,120)}
    if any(type(profile[k]) is not int or not lo <= profile[k] <= hi for k,(lo,hi) in bounds.items()):
        raise ValueError('Unsafe performance profile bounds')
    if profile['max_phase_seconds'] <= max(profile[k] for k in ('json_duration_seconds','artifact_duration_seconds','mixed_duration_seconds')):
        raise ValueError('Maximum phase duration must allow the minimum duration')
    targets = profile['targets']
    if set(targets) != {'json_p95_ms','full_transfer_p95_ms','head_range_p95_ms','unexpected_errors','oom_events',
                        'max_memory_fraction','scratch_reserve_bytes','scratch_recovery_tolerance_bytes'}:
        raise ValueError('Incomplete performance targets')
    for key in ('json_p95_ms','full_transfer_p95_ms','head_range_p95_ms'):
        if type(targets[key]) not in (int,float) or not math.isfinite(targets[key]) or targets[key] <= 0:
            raise ValueError('Invalid latency target')
    if (targets['unexpected_errors'] != 0 or targets['oom_events'] != 0
            or not 0 < targets['max_memory_fraction'] < 1
            or type(targets['scratch_reserve_bytes']) is not int or targets['scratch_reserve_bytes'] < 1024**2
            or type(targets['scratch_recovery_tolerance_bytes']) is not int
            or not 0 <= targets['scratch_recovery_tolerance_bytes'] <= 8*1024**2):
        raise ValueError('Invalid safety targets')
    if profile['approval']['status'] not in {'proposed','delegated_local_provisional'}:
        raise ValueError('Unsupported approval scope')
    if profile['approval'].get('team_a_final_sla_approved') is not False:
        raise ValueError('This synthetic probe cannot establish Team A acceptance')
    return profile


def percentiles(values):
    if not values or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid latency samples')
    ordered = sorted(values)
    rank = lambda p: ordered[max(0,math.ceil(p*len(ordered))-1)]
    return {'samples':len(values),'p50_ms':round(rank(.5),3),'p95_ms':round(rank(.95),3),
            'p99_ms':round(rank(.99),3),'max_ms':round(ordered[-1],3)}


class Sampler:
    def __init__(self, container):
        if not re.fullmatch(r'[0-9a-f]{12,64}',container):
            raise ValueError('Owned container ID required')
        self.process = subprocess.Popen(['docker','exec','-i',container,'python','-u','-c',METRICS_CODE],
            stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.samples=[]
        self.error=False
        self.stopped=False
        def consume():
            try:
                for line in self.process.stdout:
                    row=json.loads(line); row['host_monotonic']=time.monotonic(); self.samples.append(row)
            except Exception:
                self.error=True
        self.thread=threading.Thread(target=consume,daemon=True); self.thread.start()
        deadline=time.monotonic()+15
        while not self.samples:
            if self.error or self.process.poll() is not None or time.monotonic()>=deadline:
                self.close(); raise ValueError('Resource sampler unavailable')
            time.sleep(.05)

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.stdin.write('stop\n'); self.process.stdin.flush(); self.process.stdin.close()
            self.process.wait(timeout=10)
            self.thread.join(5)
            self.stopped=self.process.returncode==0 and not self.thread.is_alive() and not self.error
        except (OSError,subprocess.TimeoutExpired):
            self.process.terminate()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=5)
        finally:
            for stream in (self.process.stdout,self.process.stderr): stream.close()


def json_routes(identity):
    base='/api/v1/scenarios/'+identity
    return [('health','/api/v1/health','status'),('catalogue','/api/v1/scenarios?data_mode=demo&limit=20','items'),
        ('detail',base+'?data_mode=demo','scenario_id'),('layers',base+'/layers?data_mode=demo','layers'),
        ('impact',base+'/impact?data_mode=demo','max_depth_m'),('events','/api/v1/historical-events?data_mode=demo','items'),
        ('status','/api/v1/status/current','is_live'),('export_discovery','/api/v1/exports/'+identity+'?format=geojson&data_mode=demo','download_url')]


def request_sample(client, workload, fixture, route=None):
    start=time.perf_counter()
    status=None; count=0; headers_ms=None; error=None
    try:
        if route is not None:
            response=client.get(route[1]); status=response.status_code
            elapsed=(time.perf_counter()-start)*1000
            body=response.json()
            if status!=200 or route[2] not in body: raise ValueError('invalid metadata response')
            if route[0]=='status' and (body['is_live'] is not False or body['data_mode']!='demo'):
                raise ValueError('invalid demo status')
            count=len(response.content)
        else:
            method='HEAD' if workload=='head' else 'GET'
            headers={}
            facts=fixture['large']
            expected_size=facts['size_bytes']
            expected_hash=facts['checksum'].removeprefix('sha256:')
            if workload=='range':
                bounds=fixture['range']; first=bounds['start']; expected_size=bounds['length']
                headers={'Range':f'bytes={first}-{first+expected_size-1}'}
                expected_hash=bounds['sha256']
            with client.stream(method,fixture['large_url'],headers=headers) as response:
                status=response.status_code; headers_ms=(time.perf_counter()-start)*1000
                if status!=(206 if workload=='range' else 200): raise ValueError('unexpected artifact status')
                if response.headers.get('etag')!='"'+facts['checksum']+'"': raise ValueError('ETag mismatch')
                if int(response.headers['content-length'])!=expected_size: raise ValueError('length mismatch')
                if workload=='range' and response.headers.get('content-range')!=f'bytes {first}-{first+expected_size-1}/{facts["size_bytes"]}':
                    raise ValueError('range mismatch')
                digest=hashlib.sha256()
                for chunk in response.iter_bytes(chunk_size=1024**2):
                    digest.update(chunk); count+=len(chunk)
                if workload=='head':
                    if count: raise ValueError('HEAD body')
                elif count!=expected_size or digest.hexdigest()!=expected_hash:
                    raise ValueError('checksum mismatch')
            elapsed=(time.perf_counter()-start)*1000
    except Exception as failure:
        elapsed=(time.perf_counter()-start)*1000
        error=type(failure).__name__  # Never persist response bodies, private paths or exception text.
    return {'workload':route[0] if route else workload,'total_ms':elapsed,'headers_ms':headers_ms,
            'status':status,'bytes':count,'error':error}


def run_phase(base, fixture, profile, name, sampler):
    routes=json_routes(fixture['small_scenario_id'])
    has_json=name in {'json','mixed'}
    has_artifact=name!='json'
    artifact='full' if name=='mixed' else name
    workers=(profile['json_concurrency'] if has_json else 0)+(profile['artifact_concurrency'] if has_artifact else 0)
    minimum={r[0]:profile['json_min_samples_per_route'] for r in routes} if has_json else {}
    if has_artifact: minimum[artifact]=profile['artifact_min_samples']
    duration=profile['mixed_duration_seconds'] if name=='mixed' else profile['json_duration_seconds'] if name=='json' else profile['artifact_duration_seconds']
    records=[]; lock=threading.Lock(); start=time.monotonic(); barrier=threading.Barrier(workers)
    counts=Counter()
    def one_worker(index):
        is_json=has_json and index<profile['json_concurrency']
        cycle=index
        with httpx.Client(base_url=base,trust_env=False,timeout=profile['http_timeout_seconds']) as client:
            barrier.wait(timeout=15)
            while True:
                with lock:
                    elapsed=time.monotonic()-start
                    if elapsed>=profile['max_phase_seconds'] or len(records)>=100000:
                        break
                    if elapsed>=duration and all(counts[k]>=n for k,n in minimum.items()):
                        break
                route=routes[cycle%len(routes)] if is_json else None; cycle+=1
                sample=request_sample(client,artifact,fixture,route)
                sample['ended_host_monotonic']=time.monotonic()
                with lock:
                    records.append(sample); counts[sample['workload']]+=1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one_worker,range(workers)))
    end=time.monotonic()
    grouped=defaultdict(list)
    for row in records: grouped[row['workload']].append(row)
    resource_rows=[s for s in sampler.samples if start<=s['host_monotonic']<=end]
    workloads={}
    for label,rows in grouped.items():
        result=percentiles([r['total_ms'] for r in rows])
        result.update(unexpected_errors=sum(r['error'] is not None for r in rows),
                      status_counts=dict(Counter(str(r['status']) for r in rows)),bytes_received=sum(r['bytes'] for r in rows))
        head_values=[r['headers_ms'] for r in rows if r['headers_ms'] is not None]
        if head_values: result['time_to_headers']=percentiles(head_values)
        workloads[label]=result
    summary={'name':name,'elapsed_seconds':round(end-start,3),'minimum_duration_seconds':duration,
        'json_clients':profile['json_concurrency'] if has_json else 0,
        'artifact_clients':profile['artifact_concurrency'] if has_artifact else 0,
        'minimum_samples':minimum,'workloads':workloads,'requests_per_second':round(len(records)/(end-start),3),
        'resources':resource_summary(resource_rows,end-start)}
    return summary,records


def resource_summary(rows,elapsed):
    if len(rows)<2: return {'complete':False,'samples':len(rows)}
    first,last=rows[0],rows[-1]
    gaps=[b['host_monotonic']-a['host_monotonic'] for a,b in zip(rows,rows[1:])]
    maximum_gap=max(gaps)
    return {'complete':len(rows)>=3 and maximum_gap<=3 and last['host_monotonic']-first['host_monotonic']>=elapsed-3,
        'samples':len(rows),'maximum_sampling_gap_seconds':round(maximum_gap,3),
        'sampled_max_memory_bytes':max(r['memory_current'] for r in rows),
        'cgroup_peak_since_container_start_bytes':max(r['memory_peak_since_start'] for r in rows),
        'sampled_min_scratch_free_bytes':min(r['scratch_free'] for r in rows),
        'sampled_max_rss_sum_bytes':max(r['process_rss_sum'] for r in rows),
        'sampled_max_fd_sum':max(r['process_fd_sum'] for r in rows),
        'sampled_max_pids':max(r['pids_current'] for r in rows),
        'cpu_core_equivalents':round((last['cpu']['usage_usec']-first['cpu']['usage_usec'])/1e6/elapsed,3),
        'throttled_usec_delta':last['cpu'].get('throttled_usec',0)-first['cpu'].get('throttled_usec',0),
        'throttled_periods_delta':last['cpu'].get('nr_throttled',0)-first['cpu'].get('nr_throttled',0),
        'oom_delta':last['memory_events']['oom']-first['memory_events']['oom'],
        'oom_kill_delta':last['memory_events']['oom_kill']-first['memory_events']['oom_kill']}


def evaluate(profile,phases,memory_limit,recovery):
    failures=[]; targets=profile['targets']
    expected={'json','full','head','range','mixed'}
    if {p['name'] for p in phases}!=expected or len(phases)!=5: failures.append('missing/duplicate phase')
    for phase in phases:
        name=phase['name']
        if name not in expected: failures.append('unrecognized phase'); continue
        expected_minimum={r[0]:profile['json_min_samples_per_route'] for r in json_routes('fixture')} if name in {'json','mixed'} else {}
        if name!='json': expected_minimum['full' if name=='mixed' else name]=profile['artifact_min_samples']
        expected_duration=profile['mixed_duration_seconds'] if name=='mixed' else profile['json_duration_seconds'] if name=='json' else profile['artifact_duration_seconds']
        if (phase['minimum_samples']!=expected_minimum or phase['minimum_duration_seconds']!=expected_duration
                or set(phase['workloads'])!=set(expected_minimum)
                or phase['json_clients']!=(profile['json_concurrency'] if name in {'json','mixed'} else 0)
                or phase['artifact_clients']!=(0 if name=='json' else profile['artifact_concurrency'])):
            failures.append(name+': workload profile mismatch')
        if phase['elapsed_seconds']<phase['minimum_duration_seconds']: failures.append(phase['name']+': duration incomplete')
        for label,minimum in phase['minimum_samples'].items():
            row=phase['workloads'].get(label)
            if not row or row['samples']<minimum: failures.append(phase['name']+': insufficient '+label+' samples'); continue
            target=targets['full_transfer_p95_ms'] if label=='full' else targets['head_range_p95_ms'] if label in {'head','range'} else targets['json_p95_ms']
            if row['p95_ms']>target: failures.append(phase['name']+': '+label+' p95 target missed')
            if row['unexpected_errors']!=0: failures.append(phase['name']+': '+label+' unexpected errors')
            if row['status_counts']!={str(206 if label=='range' else 200):row['samples']}:
                failures.append(phase['name']+': '+label+' unexpected status inventory')
        resources=phase['resources']
        if not resources.get('complete'): failures.append(phase['name']+': resource samples incomplete'); continue
        if resources['sampled_max_memory_bytes']>memory_limit*targets['max_memory_fraction']: failures.append(phase['name']+': memory budget missed')
        if resources['cgroup_peak_since_container_start_bytes']>memory_limit*targets['max_memory_fraction']: failures.append(phase['name']+': cumulative kernel memory peak budget missed')
        if resources['sampled_min_scratch_free_bytes']<targets['scratch_reserve_bytes']: failures.append(phase['name']+': scratch reserve missed')
        if resources['oom_delta'] or resources['oom_kill_delta']: failures.append(phase['name']+': OOM observed')
    if not recovery.get('scratch_recovered') or not recovery.get('health_ready') or not recovery.get('sampler_stopped'):
        failures.append('recovery/telemetry cleanup incomplete')
    if recovery.get('oom_delta',1) or recovery.get('oom_kill_delta',1): failures.append('overall OOM observed')
    passed=not failures
    return {'local_targets_met':passed,'local_provisional_acceptance':passed and profile['approval']['status']=='delegated_local_provisional',
            'team_a_final_performance_accepted':False,'failures':failures}


def probe(base,container,fixture,profile,output,memory_limit):
    parsed=urlsplit(base)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.path or parsed.query or parsed.username:
        raise ValueError('Owned loopback endpoint required')
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to((ROOT/'data/handoff').resolve()):
        raise ValueError('New owned rehearsal evidence path required')
    if not fixture.get('synthetic') or fixture.get('scientific_approval') is not False or fixture['large']['size_bytes']<300*1024**2:
        raise ValueError('Explicit real synthetic large COG fixture required')
    report={'scope':'provisional synthetic local closed-loop performance/resource testing',
        'profile':profile,'fixture':fixture,'memory_limit_bytes':memory_limit,
        'result':'failed','team_a_final_performance_accepted':False,'phases':[],
        'measurement_notes':['Warm caches, host Windows loopback to hardened Linux API',
            'Total artifact latency includes client streaming SHA256 validation',
            'One-second read-only cgroup observer runs inside API cgroup; its small overhead is included',
            'Closed-loop client model can understate fixed-arrival queueing; no open-loop or production capacity claim',
            'memory.peak is cumulative since container start, not an isolated phase peak',
            'Sampled memory/RSS/FD/scratch values may miss sub-second spikes; kernel peak is retained']}
    sampler=Sampler(container); all_records=[]
    before=sampler.samples[0]
    try:
        print('Performance: warmup (discarded from percentiles)',flush=True)
        with httpx.Client(base_url=base,trust_env=False,timeout=profile['http_timeout_seconds']) as client:
            warmups=[request_sample(client,'json',fixture,route) for route in json_routes(fixture['small_scenario_id']) for _ in range(3)]
            warmups += [request_sample(client,name,fixture) for name in ('full','head','range')]
        if any(r['error'] for r in warmups): raise ValueError('Warmup functional failures')
        report['warmup_requests']=len(warmups)
        for name in ('json','full','head','range','mixed'):
            print('Performance: '+name+' phase',flush=True)
            phase,rows=run_phase(base,fixture,profile,name,sampler)
            report['phases'].append(phase); all_records.extend([dict(r,phase=name) for r in rows])
            print('Performance: '+name+' phase recorded ('+str(sum(w['samples'] for w in phase['workloads'].values()))+' requests)',flush=True)
        time.sleep(5)  # bounded cooldown after all clients have closed
        after=sampler.samples[-1]
        with httpx.Client(base_url=base,trust_env=False,timeout=10) as client:
            health_ready=client.get('/api/v1/health').status_code==200 and client.get('/readyz').status_code==200
        recovery={'scratch_recovered':after['scratch_free']>=before['scratch_free']-profile['targets']['scratch_recovery_tolerance_bytes'],
            'scratch_before':before['scratch_free'],'scratch_after':after['scratch_free'],'health_ready':health_ready,
            'fd_sum_before_warmup':before['process_fd_sum'],'fd_sum_after_cooldown':after['process_fd_sum'],
            'oom_delta':after['memory_events']['oom']-before['memory_events']['oom'],
            'oom_kill_delta':after['memory_events']['oom_kill']-before['memory_events']['oom_kill']}
        report['recovery']=recovery
        report['result']='measured'
    finally:
        sampler.close()
        report['telemetry_samples']=sampler.samples
        report.setdefault('recovery',{})['sampler_stopped']=sampler.stopped
        if report['result']=='measured':
            report['gate']=evaluate(profile,report['phases'],memory_limit,report['recovery'])
            report['result']='passed_local_targets' if report['gate']['local_provisional_acceptance'] else 'targets_failed_or_not_approved'
        report['raw_request_samples']=all_records
        output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return report
