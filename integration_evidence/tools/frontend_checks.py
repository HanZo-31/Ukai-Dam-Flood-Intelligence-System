"""Run bundled build/typecheck/Vitest without fetching dependencies; retain actual logs."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base')
    parser.add_argument('--tests-only', action='store_true')
    args = parser.parse_args()
    root, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    node = root / 'runtime/node/node.exe'
    npm = root / 'runtime/node/node_modules/npm/bin/npm-cli.js'
    env = os.environ.copy()
    env.update(PATH=str(node.parent) + os.pathsep + env['PATH'], npm_config_update_notifier='false',
               npm_config_audit='false', npm_config_fund='false', FORCE_COLOR='0')
    if args.base:
        env['UKAI_CANDIDATE_TEST_BASE'] = args.base
    report = {'started_at': datetime.now().astimezone().isoformat(), 'base': args.base,
              'passed': True, 'commands': [], 'source_hashes': {}}
    for p in (root / 'frontend/src').rglob('*'):
        if p.is_file():
            report['source_hashes'][p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    for task in (['test'] if args.tests_only else ['build', 'test']):
        command = [str(node), str(npm), 'run', task]
        if task == 'test':
            command += ['--', '--maxWorkers=2', '--minWorkers=1']
        with (output / (task + '.log')).open('w', encoding='utf-8') as log:
            run = subprocess.run(command, cwd=root / 'frontend', env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        report['commands'].append({'task': task, 'exit_code': run.returncode,
                'log_sha256': hashlib.sha256((output / (task + '.log')).read_bytes()).hexdigest()})
        print((output / (task + '.log')).read_text(encoding='utf-8', errors='replace'), flush=True)
        if run.returncode:
            report['passed'] = False
            break
    report['finished_at'] = datetime.now().astimezone().isoformat()
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
