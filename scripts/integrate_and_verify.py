"""Run the local DB, real receipt import, HTTP checks and tests in one process tree."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.update(TEMP=str(ROOT/'temp'), TMP=str(ROOT/'temp'), TMPDIR=str(ROOT/'scratch'),
                  OBJECT_STORAGE_ROOT=str(ROOT/'objects'), B2_ENV='local', UKAI_PG_BIN=str(ROOT/'runtime/pgsql/bin'))


def run(*args, log=None):
    if log:
        with (ROOT/'evidence'/log).open('w', encoding='utf-8') as output:
            result = subprocess.run([sys.executable, *map(str,args)], stdout=output, stderr=subprocess.STDOUT)
        print(f'{log}: exit {result.returncode}', flush=True)
        return result.returncode
    subprocess.run([sys.executable, *map(str,args)], check=True)


def main():
    run('scripts/bootstrap_local.py')
    os.environ['DATABASE_URL'] = (ROOT/'runtime/database-url.txt').read_text().strip()
    suffix = time.strftime('%H%M%S')
    receipts = [('h02', Path('part_a'))] + [(code, Path('receipts')/code) for code in ('h01','h03','2006')
        if (ROOT/'receipts'/code/'prototype-manifest.json').is_file()]
    imported=[]
    for code, receipt in receipts:
        output = f'evidence/import-{code}-{suffix}'
        run('scripts/receive_part_a.py', 'integrate', '--receipt', receipt, '--manifest', 'prototype-manifest.json',
            '--output', output, '--target-marker', 'runtime/target-marker.json',
            '--expected-database', 'ukai_b_integration_combined_20261008', '--object-root', 'objects',
            '--delivery-id', 'a01-'+code+'-combined-v1', '--registered-by', 'local-integration',
            '--catalog', receipt/'input-catalog.json', '--database-url-file', 'runtime/database-url.txt')
        imported.append(output+'/report.json')
    from services.api.app.published_contract import PublishedScenarioManifest
    from services.api.app.receiving import canonical_manifest_hash
    manifests=[PublishedScenarioManifest.model_validate_json((ROOT/receipt/'prototype-manifest.json').read_text()) for _,receipt in receipts]
    admission = {'schema_version':'1.0.0','entries':[{'scenario_id':manifest.scenario_id,
                  'run_id':manifest.run_id,'manifest_checksum':canonical_manifest_hash(manifest)} for manifest in manifests]}
    admission_path = ROOT/'runtime/admission.json'
    admission_path.write_text(json.dumps(admission, indent=2), encoding='utf-8')
    api_log = (ROOT/'evidence/api-runtime.log').open('w',encoding='utf-8')
    api = subprocess.Popen([sys.executable,'scripts/start_combined.py','--no-browser'], stdout=api_log, stderr=subprocess.STDOUT,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(60):
            try:
                with build_opener(ProxyHandler({})).open('http://127.0.0.1:8765/api/v1/prototypes/scenarios', timeout=5) as response:
                    if response.status == 200:
                        break
            except OSError:
                if api.poll() is not None:
                    raise RuntimeError('API exited; see api-runtime.log')
                time.sleep(1)
        else:
            raise RuntimeError('API did not become ready')
        for code,receipt in receipts:
            run('scripts/receive_part_a.py','verify-preview','--receipt',receipt,'--manifest','prototype-manifest.json',
                '--output',f'evidence/http-{code}-{suffix}','--base-url','http://127.0.0.1:8765')
        admission_path.write_text(json.dumps({'schema_version':'1.0.0','entries':[]}),encoding='utf-8')
        try:
            for code,receipt in receipts:
                run('scripts/receive_part_a.py','verify-preview','--receipt',receipt,'--manifest','prototype-manifest.json',
                    '--output',f'evidence/hidden-{code}-{suffix}','--base-url','http://127.0.0.1:8765','--expect-unadmitted')
        finally:
            admission_path.write_text(json.dumps(admission,indent=2),encoding='utf-8')
        result = run('-m','pytest',
            '-q','--tb=short','--basetemp',f'temp/integrated-tests-{suffix}',log=f'integrated-tests-{suffix}.log')
        (ROOT/'evidence/latest-run.json').write_text(json.dumps({'import_reports':imported,
            'http_reports':[f'evidence/http-{code}-{suffix}/report.json' for code,_ in receipts],
            'hidden_reports':[f'evidence/hidden-{code}-{suffix}/report.json' for code,_ in receipts],
            'tests_log':f'evidence/integrated-tests-{suffix}.log','tests_exit':result},indent=2))
        print('INTEGRATION AND HTTP VERIFIED. Tests exit: '+str(result),flush=True)
        if '--keep-running' in sys.argv:
            print('API remains available at http://127.0.0.1:8765/docs',flush=True)
            while api.poll() is None:
                time.sleep(5)
    finally:
        api.terminate()
        api_log.close()
        subprocess.run([str(ROOT/'runtime/pgsql/bin/pg_ctl.exe'),'-D',str(ROOT/'runtime/pgdata2'),'-m','fast','-w','stop'])


if __name__ == '__main__':
    main()
