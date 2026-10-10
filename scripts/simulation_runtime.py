"""Run the self-contained Simulation app; receiving-machine state is kept on local disk."""
import argparse
import hashlib
import json
import msvcrt
import os
import re
import secrets
import socket
import subprocess
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = 'ukai_b_integration_ssd'
DB_PORT, API_PORT, WEB_PORT = 55433, 8766, 5174
RECEIPTS = [('h02',ROOT/'part_a'), *[(name,ROOT/'receipts'/name) for name in ('h01','h03','2006')]]
HIDDEN = getattr(subprocess,'CREATE_NO_WINDOW',0)
OPENER = build_opener(ProxyHandler({}))


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def verify_copy():
    lines=(ROOT/'SIMULATION_CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines()
    if not lines:
        raise RuntimeError('The copy checksum inventory is empty')
    keys=[]
    for line in lines:
        matched=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        if not matched:
            raise RuntimeError('The copy checksum inventory is malformed')
        key=matched[2]
        parts=PurePosixPath(key)
        if (parts.is_absolute() or str(parts)!=key or '\\' in key or ':' in key
                or '..' in parts.parts or key=='SIMULATION_CHECKSUMS.sha256'):
            raise RuntimeError('Unsafe path in copy checksum inventory')
        keys.append(key)
    if len({key.casefold() for key in keys})!=len(keys):
        raise RuntimeError('Duplicate path in copy checksum inventory')
    ignored={'__pycache__','.vite','.pytest_cache'}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
            if p.is_file() and p.name!='SIMULATION_CHECKSUMS.sha256' and not ignored.intersection(p.parts)}
    if actual!=set(keys):
        raise RuntimeError('Copy file inventory differs from the checksum list')
    print(f'Checking {len(lines)} transferred files...',flush=True)
    def check(line):
        digest,key=line.split('  ',1)
        file=(ROOT/key).resolve()
        if not file.is_relative_to(ROOT) or not file.is_file() or checksum(file)!=digest:
            raise RuntimeError('Copy verification failed: '+key)
        return True
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,_ in enumerate(pool.map(check,lines)):
            if (i+1)%3000==0:
                print(f'  {i+1} files verified',flush=True)
    print('Copy checksums match.',flush=True)


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def take_lock(state):
    handle=(state/'instance.lock').open('a+b')
    handle.seek(0,2)
    if not handle.tell():
        handle.write(b'0')
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        handle.close()
        raise RuntimeError('This Simulation copy is already starting/running in another window') from None
    return handle


def stop_database(binaries,data,log):
    if not (data/'postmaster.pid').exists():
        return
    pg(binaries,'-D',data,'-m','fast','-w','stop',log=log)
    result=subprocess.run([str(binaries/'pg_ctl.exe'),'-D',str(data),'status'],capture_output=True,check=False)
    if result.returncode==0:
        raise RuntimeError('The database is still running; do not disconnect the drive yet')


def json_get(path,timeout=3):
    with OPENER.open(f'http://127.0.0.1:{WEB_PORT}'+path,timeout=timeout) as response:
        return json.load(response)


def py(*args, log=None):
    with log.open('a',encoding='utf-8') if log else open(os.devnull,'w') as output:
        subprocess.run([sys.executable,'-B',*map(str,args)],cwd=ROOT,check=True,
                       stdout=output,stderr=subprocess.STDOUT,creationflags=HIDDEN)


def pg(bin_dir,*args,log=None):
    with log.open('a',encoding='utf-8') if log else open(os.devnull,'w') as output:
        subprocess.run([str(bin_dir/'pg_ctl.exe'),*map(str,args)],check=True,
                       stdout=output,stderr=subprocess.STDOUT,creationflags=HIDDEN)


def configure(state,log):
    for folder in ('objects','scratch','protected-unused','evidence'):
        (state/folder).mkdir(parents=True,exist_ok=True)
    os.environ.update(TEMP=str(state/'scratch'),TMP=str(state/'scratch'),TMPDIR=str(state/'scratch'),
        OBJECT_STORAGE_ROOT=str(state/'objects'),B2_ENV='local',PYTHONDONTWRITEBYTECODE='1',
        UKAI_PG_BIN=str(ROOT/'runtime/pgsql/bin'))
    password_file=state/'db-password.txt'
    if not password_file.exists():
        password_file.write_text(secrets.token_urlsafe(32),encoding='ascii')
    password=password_file.read_text().strip()
    binaries=ROOT/'runtime/pgsql/bin'
    data=state/'pgdata'
    if not (data/'pg_hba.conf').exists():
        if data.exists():
            raise RuntimeError('An incomplete database folder exists. See the local setup log; no files were deleted.')
        print('Creating this laptop\'s local database (first run)...',flush=True)
        with log.open('a',encoding='utf-8') as output:
            subprocess.run([str(binaries/'initdb.exe'),'-D',str(data),'-U','ukai_ssd','-A','scram-sha-256',
                '--pwfile='+str(password_file),'--encoding=UTF8','--locale=C',
                '-c','max_connections=25','-c','shared_buffers=1MB'],check=True,
                stdout=output,stderr=subprocess.STDOUT,creationflags=HIDDEN)
        with (data/'postgresql.conf').open('a') as output:
            output.write(f"\nlisten_addresses = '127.0.0.1'\nport = {DB_PORT}\ntimezone = 'UTC'\n")
    status=subprocess.run([str(binaries/'pg_ctl.exe'),'-D',str(data),'status'],capture_output=True,check=False)
    if status.returncode:
        pg(binaries,'-D',data,'-l',state/'postgresql.log','-w','start',log=log)
    import psycopg
    from psycopg import sql
    with psycopg.connect(host='127.0.0.1',port=DB_PORT,dbname='postgres',user='ukai_ssd',
                        password=password,autocommit=True,connect_timeout=5) as conn:
        if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB,)).fetchone():
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB)))
        conn.execute(sql.SQL("ALTER DATABASE {} SET timezone = 'UTC'").format(sql.Identifier(DB)))
    url=f'postgresql+psycopg://ukai_ssd:{password}@127.0.0.1:{DB_PORT}/{DB}'
    os.environ['DATABASE_URL']=url
    url_file=state/'database-url.txt'
    url_file.write_text(url,encoding='utf-8')
    with psycopg.connect(host='127.0.0.1',port=DB_PORT,dbname=DB,user='ukai_ssd',password=password,
                        autocommit=True,connect_timeout=5) as conn:
        conn.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    py('-m','alembic','upgrade','head',log=log)
    marker=state/'target-marker.json'
    write(marker,{'database':DB,'project':'Ukai SSD','version':'1','state':'created','protected_database':'ukai',
        'protected_object_root':str(state/'protected-unused'),'objects_root':str(state/'objects'),'scratch_root':str(state/'scratch')})
    prepared=state/'import-complete.json'
    entries=[]
    from services.api.app.published_contract import PublishedScenarioManifest
    from services.api.app.receiving import canonical_manifest_hash
    for code,receipt in RECEIPTS:
        manifest=PublishedScenarioManifest.model_validate_json((receipt/'prototype-manifest.json').read_text())
        entries.append({'scenario_id':manifest.scenario_id,'run_id':manifest.run_id,
                        'manifest_checksum':canonical_manifest_hash(manifest)})
        if not prepared.exists():
            print('Importing verified '+code+' assets...',flush=True)
            suffix=str(time.time_ns())
            py('scripts/receive_part_a.py','integrate','--receipt',receipt,'--manifest','prototype-manifest.json',
                '--output',state/'evidence'/('import-'+code+'-'+suffix),'--target-marker',marker,
                '--expected-database',DB,'--object-root',state/'objects','--delivery-id','a01-'+code+'-ssd-v1',
                '--registered-by','ssd-local-import','--catalog',receipt/'input-catalog.json',
                '--database-url-file',url_file,log=log)
    if not prepared.exists():
        write(prepared,{'source_root':str(ROOT),'scenario_ids':[item['scenario_id'] for item in entries]})
    admission=state/'admission.json'
    write(admission,{'schema_version':'1.0.0','entries':entries})
    return binaries,data,admission,entries


def check_download_ranges(receipt,report):
    from services.api.app.receiving_http import request
    manifest=json.loads((receipt/'prototype-manifest.json').read_text())
    base=f'http://127.0.0.1:{WEB_PORT}'
    prefix='/api/v1/prototypes/scenarios/'+manifest['scenario_id']
    for download in report['download_results']:
        suffix=download['resource']
        if suffix.startswith('/assets/'):
            key=manifest['assets'][suffix.removeprefix('/assets/')]
        elif suffix=='/assumptions':
            key=manifest['assumptions_url']
        else:
            key=manifest['quality']['report_reference']
        with (receipt/key).open('rb') as stream:
            first=stream.read(1)
        total=download['bytes']
        path=prefix+suffix
        head=request(base,path,method='HEAD',max_bytes=0)
        etag=head['headers'].get('etag')
        if not etag:
            raise RuntimeError('Simulation download has no ETag: '+suffix)
        for headers in ({'Range':'bytes=0-0'},{'Range':'bytes=0-0','If-Range':etag}):
            response=request(base,path,headers=headers,max_bytes=1)
            if (response['status']!=206 or response['body']!=first
                    or response['headers'].get('content-range')!=f'bytes 0-0/{total}'
                    or response['headers'].get('content-length')!='1'
                    or response['headers'].get('etag')!=etag):
                raise RuntimeError('Simulation range bytes/headers differ: '+suffix)
        invalid=request(base,path,headers={'Range':f'bytes={total}-'})
        if invalid['status']!=416 or invalid['headers'].get('content-range')!=f'bytes */{total}':
            raise RuntimeError('Simulation unsatisfiable range header differs: '+suffix)
        download['exact_range_bytes_and_headers_verified']=True
        download['matching_if_range_verified']=True


def check_roundtrip(state,entries):
    from services.api.app.receiving import preflight
    from services.api.app.receiving_http import verify_preview
    reports=[]
    for code,receipt in RECEIPTS:
        print('Verifying '+code+' through the Simulation frontend proxy...',flush=True)
        report=preflight(receipt,'prototype-manifest.json')
        report=verify_preview(report,'prototype-manifest.json',base_url=f'http://127.0.0.1:{WEB_PORT}')
        if not report['passed']:
            raise RuntimeError('Simulation roundtrip failed for '+code)
        check_download_ranges(receipt,report)
        reports.append({'scenario':code,'passed':True,'steps':report['steps'],
                        'download_results':report['download_results']})
    index=OPENER.open(f'http://127.0.0.1:{WEB_PORT}',timeout=5).read().decode()
    if '<div id="root"></div>' not in index:
        raise RuntimeError('The built frontend was not served.')
    import re
    resources=re.findall(r'(?:src|href)="(/assets/[^"]+)"',index)
    for resource in resources:
        with OPENER.open(f'http://127.0.0.1:{WEB_PORT}'+resource,timeout=5) as response:
            if response.status!=200:
                raise RuntimeError('Frontend resource unavailable.')
    with OPENER.open(f'http://127.0.0.1:{WEB_PORT}/api/v1/prototypes/scenarios/'+entries[0]['scenario_id']+
                    '/assets/max_depth_cog',timeout=10) as response:
        if response.headers.get('X-Ukai-Scientific-Validation')!='not_validated':
            raise RuntimeError('Prototype download headers missing.')
    result={'four_scenarios':reports,'built_frontend_served':True,'frontend_resources':resources,
        'source_root':str(ROOT),'local_state':str(state),'visual_browser_checks_performed':False}
    write(state/'SIMULATION_SMOKE_RESULT.json',result)
    print('Simulation API/assets/frontend-resource checks passed.',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--state-dir',type=Path)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--stop',action='store_true')
    parser.add_argument('--verify-copy',action='store_true')
    args=parser.parse_args()
    # Resolve a caller-supplied test state before switching to the package folder.
    requested_state=args.state_dir.resolve() if args.state_dir else None
    os.chdir(ROOT)
    package=(ROOT/'SIMULATION_PACKAGE_ID.txt').read_text().strip()
    instance=hashlib.sha256((package+'|'+str(ROOT).casefold()).encode()).hexdigest()[:16]
    default=Path(os.environ.get('LOCALAPPDATA',str(ROOT.parent)))/'UkaiSSD'/instance
    state=(requested_state or default).resolve()
    if args.stop:
        if state.is_dir():
            (state/'stop.request').write_text('stop',encoding='ascii')
            print('Stop requested. Wait for the server window to say Stopped before disconnecting the drive.')
        return
    if args.verify_copy:
        verify_copy()
        return
    try:
        if json_get('/__ukai_instance').get('instance')==instance:
            if args.check_only:
                raise RuntimeError('Stop the Simulation server before running CHECK_SIMULATION.cmd')
            expected={(json.loads((receipt/'prototype-manifest.json').read_text())['scenario_id'],
                       json.loads((receipt/'prototype-manifest.json').read_text())['run_id']) for _,receipt in RECEIPTS}
            actual={(item['scenario_id'],item['run_id']) for item in json_get('/api/v1/prototypes/scenarios')['items']}
            if actual!=expected:
                raise RuntimeError('The running Simulation instance does not show all four expected scenarios')
            print('This Simulation copy is already running.',flush=True)
            if not args.no_browser:
                webbrowser.open(f'http://127.0.0.1:{WEB_PORT}')
            return
    except (OSError,ValueError):
        pass
    for port in (API_PORT,WEB_PORT):
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1',port))
            except OSError:
                raise RuntimeError(f'Simulation port {port} is already in use; stop the other Simulation copy first.') from None
    if not (state/'copy-verified.txt').exists():
        verify_copy()
    state.mkdir(parents=True,exist_ok=True)
    lock=take_lock(state)
    (state/'copy-verified.txt').write_text(package,encoding='ascii')
    (state/'stop.request').unlink(missing_ok=True)
    log=state/'setup.log'
    print('Local state: '+str(state),flush=True)
    processes=[]
    handles=[]
    data=state/'pgdata'
    binaries=ROOT/'runtime/pgsql/bin'
    try:
        binaries,data,admission,entries=configure(state,log)
        for role,command in [('api',[sys.executable,'-B','scripts/run_prototype_preview.py',
             '--admission',str(admission),'--expected-database',DB,'--port',str(API_PORT)]),
             ('frontend',[str(ROOT/'runtime/node/node.exe'),'scripts/simulation_web_server.cjs'])]:
            output=(state/(role+'.log')).open('a',encoding='utf-8')
            handles.append(output)
            environment=dict(os.environ,UKAI_INSTANCE=instance,UKAI_API_PORT=str(API_PORT),UKAI_WEB_PORT=str(WEB_PORT))
            processes.append(subprocess.Popen(command,cwd=ROOT,env=environment,stdout=output,
                                              stderr=subprocess.STDOUT,creationflags=HIDDEN))
        expected={(item['scenario_id'],item['run_id']) for item in entries}
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError('A service exited. Check api.log or frontend.log in the local state folder.')
            try:
                values=json_get('/api/v1/prototypes/scenarios')['items']
                if {(item['scenario_id'],item['run_id']) for item in values}==expected:
                    break
            except (OSError,ValueError,KeyError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError('The Simulation frontend/API did not become ready.')
        if args.check_only:
            check_roundtrip(state,entries)
            return
        print(f'READY: 4 scenarios verified. http://127.0.0.1:{WEB_PORT}',flush=True)
        print('Keep this window open. Ctrl+C stops all services. Use STOP_SIMULATION.cmd before disconnecting the drive.',flush=True)
        if not args.no_browser:
            webbrowser.open(f'http://127.0.0.1:{WEB_PORT}')
        while not (state/'stop.request').exists():
            if any(process.poll() is not None for process in processes):
                raise RuntimeError('A service stopped unexpectedly. Check the local logs.')
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nStopping...',flush=True)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for handle in handles:
            handle.close()
        try:
            stop_database(binaries,data,log)
        finally:
            lock.close()
        print('Stopped.',flush=True)


if __name__=='__main__':
    try:
        main()
    except Exception as error:  # noqa: BLE001 -- CLI boundary reports failure after guaranteed cleanup.
        detail=str(error) if isinstance(error,RuntimeError) else type(error).__name__
        print('Simulation START FAILED: '+detail+'. See the local setup/service logs.',file=sys.stderr)
        raise SystemExit(1)
