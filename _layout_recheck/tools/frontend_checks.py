"""Build/type-check/test V05 using bundled tools; keep caches/logs within V05."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / '_layout_recheck'


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    output = ROOT / 'layout_cleanup_evidence' / sys.argv[1]
    output.mkdir(exist_ok=False)
    node = ROOT / 'runtime/node/node.exe'
    npm = ROOT / 'runtime/node/node_modules/npm/bin/npm-cli.js'
    temp = CHECK / 'temp'
    temp.mkdir(exist_ok=True)
    env = os.environ | {'PATH': str(node.parent) + os.pathsep + os.environ['PATH'],
        'npm_config_cache': str(CHECK / 'npm-cache'), 'TEMP': str(temp), 'TMP': str(temp),
        'npm_config_update_notifier': 'false', 'npm_config_audit': 'false',
        'npm_config_fund': 'false', 'FORCE_COLOR': '0'}
    if '--live' in sys.argv:
        env['UKAI_CANDIDATE_TEST_BASE'] = 'http://127.0.0.1:5191'
        env['UKAI_COMPUTE_EVIDENCE_PATH'] = str(output / 'COMPUTE_REGRESSION.json')
    else:
        env.pop('UKAI_CANDIDATE_TEST_BASE', None)
    report = {'started_at': datetime.now().astimezone().isoformat(), 'passed': True,
        'live': '--live' in sys.argv, 'commands': [], 'source_hashes': {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / 'frontend/src').rglob('*') if p.is_file()}}
    for task in ['build', 'test']:
        command = [str(node), str(npm), 'run', task]
        if task == 'test':
            command += ['--', '--maxWorkers=2', '--minWorkers=1']
        with (output / (task + '.log')).open('w', encoding='utf-8') as log:
            run = subprocess.run(command, cwd=ROOT / 'frontend', env=env,
                                 stdout=log, stderr=subprocess.STDOUT, timeout=650)
        report['commands'].append({'task': task, 'exit_code': run.returncode})
        print((output / (task + '.log')).read_text(encoding='utf-8', errors='replace'), flush=True)
        if run.returncode:
            report['passed'] = False
            break
    report['finished_at'] = datetime.now().astimezone().isoformat()
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
