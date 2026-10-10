"""Strict, disabled-by-default asynchronous compute-v2 infrastructure.

Provider injection is an internal Python interface, never a request executable/path.
No operational provider exists until original native solver/input gates are verified.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import threading
import time
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
import jsonschema

PREFIX = '/api/v1/candidates/compute-v2'
FAMILY = 'ukai-hyp-fixed-shape-v1'
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{2,99}$')
ROLES = ['max_depth_cog','arrival_time_cog','max_velocity_cog','extent_geojson']
SCHEMA = json.loads((Path(__file__).parent/'contract/compute-v2.schema.json').read_text())

def now():
    return datetime.now(timezone.utc).isoformat()

def storage_id(wire_id):
    # Valid contract IDs can still be Windows device names. A leading underscore
    # cannot be a valid wire-ID prefix, so this mapping has no namespace collision.
    return '_'+wire_id if re.fullmatch(r'con|prn|aux|nul|com[1-9]|lpt[1-9]',wire_id) else wire_id

def digest(path):
    with path.open('rb') as stream:
        return 'sha256:'+hashlib.file_digest(stream,'sha256').hexdigest()

def strict_json(path):
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))

def validate(kind, doc):
    jsonschema.Draft202012Validator({**SCHEMA,'oneOf':[{'$ref':'#/$defs/'+kind}]},
        format_checker=jsonschema.FormatChecker()).validate(doc)
    if kind=='Request' and (isinstance(doc['peak_release_m3s'],bool) or not math.isfinite(doc['peak_release_m3s'])):
        raise ValueError('Finite numeric release required')
    if kind=='Job':
        if datetime.fromisoformat(doc['updated_at'])<datetime.fromisoformat(doc['created_at']):raise ValueError('Timestamp order')
        if doc['status']=='completed' and doc['result_url']!=PREFIX+'/jobs/'+doc['job_id']+'/result':raise ValueError('Job result URL mismatch')

def atomic(path, value):
    temporary=path.with_suffix('.pending')
    try:
        with temporary.open('x',encoding='utf-8') as stream:
            json.dump(value,stream,allow_nan=False,sort_keys=True)
            stream.flush();os.fsync(stream.fileno())
        for attempt in range(20):
            try:
                os.replace(temporary,path);break
            except PermissionError:
                if attempt==19:raise
                time.sleep(.025)
    finally:
        temporary.unlink(missing_ok=True)

def safe_file(root, relative):
    if not isinstance(relative,str) or '\\' in relative or '\x00' in relative:
        raise ValueError('Unsafe file reference')
    candidate=Path(relative)
    if candidate.is_absolute() or '..' in candidate.parts or not candidate.parts:raise ValueError('Unsafe file reference')
    root=root.resolve();target=root/candidate
    if not target.resolve().is_relative_to(root):raise ValueError('File escapes root')
    for component in [target,*target.parents]:
        if component==root:break
        if component.is_symlink() or component.is_junction():raise ValueError('Linked path')
    if not target.is_file():raise ValueError('Missing product')
    return target

@dataclass
class Produced:
    result: dict
    asset_files: dict
    native_file: str
    diagnostics_file: str

class ComputeManager:
    def __init__(self, source, state, provider=None, *, test_only=False, max_bytes=1024**3, shutdown_seconds=5):
        self.source=Path(source).resolve();self.state=Path(state).resolve()
        if self.state.is_relative_to(self.source) or self.source.is_relative_to(self.state):raise ValueError('Separate state required')
        if provider is not None and getattr(provider,'synthetic',False) and not test_only:raise ValueError('Synthetic provider forbidden operationally')
        self.provider=provider;self.test_only=test_only;self.max_bytes=max_bytes;self.shutdown_seconds=shutdown_seconds
        self.lock=threading.RLock();self.cancel=threading.Event();self.thread=None;self.active=None;self.closed=False;self.owner=None

    def start(self):
        self.state.mkdir(parents=True,exist_ok=True)
        if self.state.is_symlink() or self.state.is_junction():raise ValueError('Linked state')
        self.owner=(self.state/'compute-owner.lock').open('a+b')
        try:
            if os.name=='nt':
                import msvcrt
                self.owner.seek(0);self.owner.write(b'0');self.owner.flush();self.owner.seek(0)
                msvcrt.locking(self.owner.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.owner.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.owner.close();self.owner=None;raise ValueError('Compute state already owned') from None
        try:
            for path in self.state.glob('*.pending'):path.unlink()
            for path in self.state.glob('*.json'):
                record=strict_json(path);validate('Request',record['request']);validate('Job',record['job'])
                if path.name!=storage_id(record['job']['job_id'])+'.json':raise ValueError('Persisted identity mismatch')
                self.match(record['job'],record['request'])
                if record['job']['status'] in ['queued','running']:
                    self.fail(record,'interrupted','The previous computation was interrupted.')
        except Exception:
            self.stop();raise

    def stop(self):
        self.closed=True;self.cancel.set()
        if self.thread is not None:self.thread.join(self.shutdown_seconds)
        # Keep ownership until a noncooperative worker exits; never permit concurrent restart.
        if self.thread is not None and self.thread.is_alive():return
        self.release_owner()

    def release_owner(self):
        if self.owner is not None:
            if os.name=='nt':
                import msvcrt
                self.owner.seek(0);msvcrt.locking(self.owner.fileno(),msvcrt.LK_UNLCK,1)
            self.owner.close();self.owner=None

    def capability(self):
        config=None;reason='The native solver and its complete inputs have not been verified.'
        if self.provider is not None and not self.closed:
            try:config=self.provider.verify()
            except Exception:reason='The native solver configuration is unavailable.'
        doc=dict(schema_version='2.0.0',input_family=FAMILY,configuration_id=config['configuration_id'] if config else None,
            configuration_checksum=config['configuration_checksum'] if config else None,enabled=bool(config),reason=None if config else reason,
            peak_range_m3s=[15000,30000],available_roles=config['available_roles'] if config else [],scientifically_validated=False)
        validate('Capabilities',doc)
        return doc

    def match(self, job, req):
        for key in ['schema_version','input_family','configuration_id','configuration_checksum','request_id']:
            if job[key]!=req[key]:raise ValueError('Request identity mismatch')
        if job['requested_peak_release_m3s']!=req['peak_release_m3s'] or job['job_id']!=req['request_id']:raise ValueError('Request/job mismatch')

    def read(self, job_id):
        with self.lock:return self.read_locked(job_id)

    def read_locked(self, job_id):
        if not ID.fullmatch(job_id):raise HTTPException(404,detail='unknown_job')
        filename=storage_id(job_id)+'.json';path=self.state/filename
        if not path.is_file():raise HTTPException(404,detail='unknown_job')
        record=strict_json(safe_file(self.state,filename))
        validate('Request',record['request']);validate('Job',record['job']);self.match(record['job'],record['request'])
        if record['job']['status']=='completed':self.checked_product(record)
        return record

    def save(self, record):
        with self.lock:
            validate('Job',record['job']);atomic(self.state/(storage_id(record['job']['job_id'])+'.json'),record)

    def fail(self, record, code, message):
        record['job'].update(status='failed',result_url=None,error=dict(code=code,message=message),updated_at=now())
        record.pop('product',None);self.save(record)

    def checked_product(self, record):
        if not self.test_only and self.provider is not None:self.provider.verify()
        product=record['product'];root=safe_file(self.state,product['result_file']).parent
        result=strict_json(root/'result.json');validate('Result',result)
        job=record['job'];req=record['request']
        for key in ['job_id','request_id','configuration_id','configuration_checksum','input_family']:
            if result[key]!=job[key]:raise ValueError('Result identity mismatch')
        if result['actual_peak_release_m3s']!=req['peak_release_m3s'] or result['requested_peak_release_m3s']!=req['peak_release_m3s']:
            raise ValueError('Actual/requested peak mismatch')
        if result['cache_hit']!=job['cache_hit']:raise ValueError('Cache identity mismatch')
        if not self.test_only:
            import rasterio
            with rasterio.open(self.source/'part_a/assets/max_depth.tif') as reference:
                grid=result['derived_grid']
                if (grid['width'],grid['height'],grid['transform'])!=(reference.width,reference.height,list(reference.transform)[:6]):
                    raise ValueError('Not exact reference grid')
            source_ids={strict_json(path)['scenario_id'] for path in [self.source/'part_a/prototype-manifest.json',
                *self.source.glob('receipts/*/prototype-manifest.json')]}
            source_runs={strict_json(path)['run_id'] for path in [self.source/'part_a/prototype-manifest.json',
                *self.source.glob('receipts/*/prototype-manifest.json')]}
            if result['scenario_id'] in source_ids or result['run_id'] in source_runs:raise ValueError('Reused reference identity')
            if result['derived_grid']['target_reference_scenario_id']!=strict_json(self.source/'part_a/prototype-manifest.json')['scenario_id']:
                raise ValueError('Wrong target reference identity')
        for role,asset in result['assets'].items():
            reason=result['unavailable_reasons'][role]
            if asset is None:
                if not reason:raise ValueError('Missing product reason')
                continue
            if reason is not None or asset['url']!=PREFIX+'/jobs/'+job['job_id']+'/assets/'+role:raise ValueError('Asset identity mismatch')
            path=safe_file(root,product['asset_files'][role])
            if path.stat().st_size!=asset['bytes'] or digest(path)!=asset['sha256']:raise ValueError('Asset integrity failure')
        if result['assets']['arrival_time_cog'] and result['arrival_definition'] is None:raise ValueError('Arrival definition absent')
        if result['assets']['max_velocity_cog'] and result['velocity_definition'] is None:raise ValueError('Velocity definition absent')
        for field,key in [('native_results_checksum','native_file'),('numerical_diagnostics_checksum','diagnostics_file')]:
            if digest(safe_file(root,product[key]))!=result[field]:raise ValueError('Native/diagnostic checksum mismatch')
        if digest(root/'result.json')!=product['result_checksum']:raise ValueError('Result manifest changed')
        return result,root

    def submit(self, request):
        submitted=time.perf_counter()
        validate('Request',request)
        with self.lock:
            disk_id=storage_id(request['request_id']);path=self.state/(disk_id+'.json')
            if path.exists():
                record=self.read(request['request_id'])
                if record['request']!=request:raise HTTPException(409,detail='request_conflict')
                return record['job']
            caps=self.capability()
            if not caps['enabled']:raise HTTPException(503,detail='native_solver_unavailable')
            if any(request[k]!=caps[k] for k in ['configuration_id','configuration_checksum']):raise HTTPException(409,detail='configuration_changed')
            if self.active is not None:raise HTTPException(409,detail='compute_busy')
            if sum(p.stat().st_size for p in self.state.rglob('*') if p.is_file())>=self.max_bytes:
                raise HTTPException(503,detail='storage_budget_exceeded')
            stamp=now();job={k:request[k] for k in ['schema_version','input_family','configuration_id','configuration_checksum','request_id']}
            job.update(job_id=request['request_id'],requested_peak_release_m3s=request['peak_release_m3s'],status='queued',
                created_at=stamp,updated_at=stamp,elapsed_wall_seconds=0,cache_hit=False,result_url=None,error=None)
            record={'request':copy.deepcopy(request),'job':job}
            # Cross-request cache reuses verified generated bytes/run identity, not a synthetic calculation.
            for saved in self.state.glob('*.json'):
                previous=self.read(strict_json(saved)['job']['job_id'])
                old=previous['request']
                if previous['job']['status']=='completed' and all(old[k]==request[k] for k in
                    ['configuration_id','configuration_checksum','input_family','peak_release_m3s']):
                    result,root=self.checked_product(previous)
                    target=self.state/disk_id;target.mkdir(exist_ok=False)
                    try:
                        product=previous['product']
                        for relative in set(product['asset_files'].values())|{product['native_file'],product['diagnostics_file']}:
                            source_file=safe_file(root,relative);destination=target/relative
                            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source_file,destination)
                        result=copy.deepcopy(result);result.update(job_id=job['job_id'],request_id=job['request_id'],cache_hit=True)
                        for role,asset in result['assets'].items():
                            if asset:asset['url']=PREFIX+'/jobs/'+job['job_id']+'/assets/'+role
                        atomic(target/'result.json',result)
                        record['product']=copy.deepcopy(product)
                        record['product'].update(result_file=disk_id+'/result.json',result_checksum=digest(target/'result.json'))
                        job.update(status='completed',cache_hit=True,updated_at=now(),result_url=PREFIX+'/jobs/'+job['job_id']+'/result',
                            elapsed_wall_seconds=time.perf_counter()-submitted)
                        self.checked_product(record)
                        if sum(p.stat().st_size for p in self.state.rglob('*') if p.is_file())>self.max_bytes:raise ValueError('Storage budget exceeded')
                        self.save(record);return copy.deepcopy(job)
                    except Exception:
                        self.fail(record,'cache_unavailable','The checked cached result could not be reused.')
                        raise
            self.save(record);self.active=job['job_id']
            self.thread=threading.Thread(target=self.work,args=(record,submitted),daemon=False);self.thread.start()
            return copy.deepcopy(job)

    def work(self, record, started):
        job=record['job'];disk_id=storage_id(job['job_id']);folder=self.state/disk_id
        try:
            job.update(status='running',updated_at=now());self.save(record)
            folder.mkdir(exist_ok=False)
            verified=self.provider.verify()
            if any(verified[key]!=record['request'][key] for key in ['configuration_id','configuration_checksum']):
                raise ValueError('Configuration changed before execution')
            produced=self.provider.compute(copy.deepcopy(record['request']),folder,self.cancel)
            if self.cancel.is_set():raise InterruptedError()
            if sum(p.stat().st_size for p in self.state.rglob('*') if p.is_file())>self.max_bytes:raise ValueError('Storage budget exceeded')
            result=produced.result;validate('Result',result)
            measured=time.perf_counter()-started
            result['timings']['request_to_assets_seconds']=measured
            result['timings']['availability_seconds']=max(0,measured-result['timings']['prepare_seconds']
                -result['timings']['solver_seconds']-result['timings']['package_check_seconds'])
            atomic(folder/'result.json',result)
            record['product']=dict(result_file=disk_id+'/result.json',asset_files=produced.asset_files,
                native_file=produced.native_file,diagnostics_file=produced.diagnostics_file,result_checksum=digest(folder/'result.json'))
            job.update(status='completed',updated_at=now(),elapsed_wall_seconds=time.perf_counter()-started,
                result_url=PREFIX+'/jobs/'+job['job_id']+'/result')
            self.checked_product(record)
            with self.lock:
                if self.cancel.is_set():raise InterruptedError()
                self.save(record)
        except Exception as exc:
            job['elapsed_wall_seconds']=time.perf_counter()-started
            self.fail(record,'interrupted' if isinstance(exc,InterruptedError) else 'computation_failed',
                'The computation was interrupted.' if isinstance(exc,InterruptedError) else 'The computation or product checks failed.')
        finally:
            with self.lock:
                self.active=None
                if self.closed:self.release_owner()

def install(app, source, state, provider=None, **options):
    manager=ComputeManager(source,state,provider,**options)
    previous_lifespan=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with previous_lifespan(application):
            manager.start()
            try:yield
            finally:manager.stop()
    app.router.lifespan_context=lifespan
    app.state.compute_manager=manager
    router=APIRouter(prefix=PREFIX)

    def guarded(call):
        try:return call()
        except HTTPException:raise
        except (ValueError,OSError,KeyError,TypeError,jsonschema.ValidationError):
            raise HTTPException(503,detail='compute_evidence_unavailable') from None

    @router.get('/capabilities')
    def caps():return guarded(manager.capability)

    @router.post('/jobs')
    async def submit(req: Request):
        # Strict JSON duplicates/nonfinite/large payloads are rejected before execution.
        body=bytearray()
        async for chunk in req.stream():
            body.extend(chunk)
            if len(body)>16384:raise HTTPException(413,detail='request_too_large')
        try:
            pairs=lambda entries: dict(entries) if len(dict(entries))==len(entries) else (_ for _ in ()).throw(ValueError())
            doc=json.loads(body,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            validate('Request',doc)
        except (ValueError,TypeError,jsonschema.ValidationError):raise HTTPException(422,detail='invalid_compute_request') from None
        job=guarded(lambda:manager.submit(doc))
        return JSONResponse(job,status_code=202 if job['status'] in ['queued','running'] else 200)

    @router.get('/jobs/{job_id}')
    def job(job_id: str):return guarded(lambda:manager.read(job_id)['job'])

    @router.get('/jobs/{job_id}/result')
    def result(job_id: str):
        def get():
            record=manager.read(job_id)
            if record['job']['status']!='completed':raise HTTPException(409,detail='result_not_ready')
            return manager.checked_product(record)[0]
        return guarded(get)

    @router.get('/jobs/{job_id}/assets/{role}',operation_id='compute_v2_asset_get')
    @router.head('/jobs/{job_id}/assets/{role}',operation_id='compute_v2_asset_head')
    def asset(job_id: str,role: str,request: Request):
        def get():
            if role not in ROLES:raise HTTPException(404,detail='unknown_asset')
            record=manager.read(job_id)
            if record['job']['status']!='completed':raise HTTPException(409,detail='result_not_ready')
            result,root=manager.checked_product(record);metadata=result['assets'][role]
            if metadata is None:raise HTTPException(404,detail='asset_unavailable')
            path=safe_file(root,record['product']['asset_files'][role]);stream=path.open('rb')
            # Hash the same descriptor that will be streamed, not a reopened path.
            if 'sha256:'+hashlib.file_digest(stream,'sha256').hexdigest()!=metadata['sha256']:
                stream.close();raise ValueError('Asset changed')
            size=metadata['bytes'];etag='"'+metadata['sha256']+'"'
            headers={'ETag':etag,'Accept-Ranges':'bytes','X-Content-Type-Options':'nosniff','Content-Length':str(size)}
            if request.headers.get('if-none-match')==etag:
                stream.close();return Response(status_code=304,headers={'ETag':etag})
            start,end,status=0,size-1,200
            value=request.headers.get('range')
            if value and request.headers.get('if-range',etag)==etag:
                match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
                if not match or not any(match.groups()):
                    stream.close();return Response(status_code=416,headers={'Content-Range':f'bytes */{size}'})
                left,right=match.groups()
                if left:start=int(left);end=min(int(right),size-1) if right else size-1
                else:start=max(0,size-int(right));end=size-1
                if start>=size or end<start or (not left and int(right)==0):
                    stream.close();return Response(status_code=416,headers={'Content-Range':f'bytes */{size}'})
                status=206;headers.update({'Content-Range':f'bytes {start}-{end}/{size}','Content-Length':str(end-start+1)})
            mime='application/geo+json' if role=='extent_geojson' else 'image/tiff'
            if request.method=='HEAD':stream.close();return Response(status_code=status,headers=headers,media_type=mime)
            def chunks():
                try:
                    stream.seek(start);remaining=end-start+1
                    while remaining:
                        chunk=stream.read(min(65536,remaining))
                        if not chunk:raise OSError('Asset truncated')
                        remaining-=len(chunk);yield chunk
                finally:stream.close()
            return StreamingResponse(chunks(),status_code=status,headers=headers,media_type=mime)
        return guarded(get)

    app.include_router(router)
    return manager

def create_app(source,state,provider=None,**options):
    app=FastAPI(title='Ukai computed candidate infrastructure',docs_url=None,redoc_url=None)
    install(app,source,state,provider,**options)
    return app
