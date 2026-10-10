"""Bundled frontend checks; no dependency installations or external project writes."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'simulation_polish_evidence'


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    output = OUT / sys.argv[1]
    output.mkdir(exist_ok=False)
    temp = OUT / '_temporary'; temp.mkdir(exist_ok=True)
    node = ROOT / 'runtime/node/node.exe'
    env = os.environ | {'PATH': str(node.parent) + os.pathsep + os.environ['PATH'], 'TEMP': str(temp), 'TMP': str(temp),
        'npm_config_cache': str(temp / 'npm-cache'), 'npm_config_update_notifier': 'false', 'npm_config_audit': 'false', 'npm_config_fund': 'false', 'FORCE_COLOR': '0'}
    env.pop('UKAI_CANDIDATE_TEST_BASE', None)
    if '--read-only-http' in sys.argv:
        env['UKAI_POINT_TEST_BASE'] = 'http://127.0.0.1:5176'
        transport = output / 'range-http'; transport.mkdir()
        env['UKAI_POINT_EVIDENCE_DIR'] = str(transport)
    else:
        env.pop('UKAI_POINT_TEST_BASE', None)
    report = {'started_at': datetime.now().astimezone().isoformat(), 'passed': True, 'commands': [], 'source_hashes': {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'frontend/src').rglob('*') if p.is_file()}}
    for task in ['build', 'test']:
        command = [str(node), str(ROOT / 'runtime/node/node_modules/npm/bin/npm-cli.js'), 'run', task]
        if task == 'test': command += ['--', '--maxWorkers=2', '--minWorkers=1']
        with (output / (task + '.log')).open('w', encoding='utf-8') as log:
            run = subprocess.run(command, cwd=ROOT / 'frontend', env=env, stdout=log, stderr=subprocess.STDOUT, timeout=650)
        report['commands'].append({'task': task, 'exit_code': run.returncode})
        print((output / (task + '.log')).read_text(encoding='utf-8', errors='replace'), flush=True)
        if run.returncode: report['passed'] = False; break
    report['finished_at'] = datetime.now().astimezone().isoformat()
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__': main()
