"""Seal an allowlisted Team2 engineering overlay; never copy private runtime state."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_delivery import digest, safe_file, verify  # noqa: E402 -- bundled Python local bootstrap


TEAM2_FILES = [
    'START_HERE.md', 'DELIVERY.md', 'WORK_CHECKLIST.md', 'WORK_EVIDENCE.md',
    'ASSEMBLY_AND_RUN_GUIDE.md', 'TEAM1_CANDIDATE_CONTRACT.md', 'DEMO_AND_ACCEPTANCE.md',
    'START_TEAM2.cmd', 'STOP_TEAM2.cmd', 'candidate_service.py', 'combined_runtime.py',
    'run_candidate_service.py', 'audit_four_scenarios.py', 'fit_diagnostic_model.py',
    'export_contract.py', 'reconcile_contract.py', 'run_focused_checks.py',
    'run_final_regression.py', 'check_quality.py', 'probe_local_service.py',
    'probe_assembly_proxy.py', 'probe_combined_runtime.py', 'package_first_delivery.py',
    'package_delivery.py', 'verify_delivery.py', 'test_delivery.py',
    'run_packaging_checks.py', 'test_candidate_service.py', 'test_combined_runtime.py',
    'quality-ruff.toml', 'quality-mypy.ini', 'assembly/simulation_web_server.cjs',
    'AUDIT_FIXES_AND_INTEGRATION_STATUS.md', 'DELIVERY_EVIDENCE.json',
    'contract-drop-v02/candidate-openapi-v1.json', 'contract-drop-v02/candidate-examples.json',
    'diagnostic-v01/evaluation.json', 'diagnostic-v01/diagnostic-model.npz',
    'evidence/four-scenario-audit-v01.json', 'evidence/combined-runtime-v01/report.json',
    'evidence/combined-focused-v01/report.json', 'evidence/loopback-probe-v01/report.json',
    'evidence/candidate-check-v05/report.json', 'evidence/candidate-check-v08/report.json',
    'evidence/assembly-proxy-v02/report.json', 'evidence/contract-reconciliation-v03/report.json',
    'evidence/final-regression-v03/report.json', 'evidence/final-regression-v03/tests.log',
    'evidence/final-quality-v03/report.json', 'evidence/final-quality-v07/report.json',
    'evidence/packaging-check-v04/report.json', 'evidence/packaging-check-v04/tests.log',
    'evidence/audit-fixes-focused-v01/report.json', 'evidence/audit-fixes-focused-v01/tests.log',
] + ['evidence/final-quality-v07/' + key + '.log' for key in
     ('dependency-consistency', 'correctness-lint', 'gradual-types', 'proxy-syntax', 'openapi-conformance')]
BASELINE_FILES = ['SIMULATION_PACKAGE_ID.txt', 'SIMULATION_PACKAGE_REPORT.json', 'docs/HACKATHON_20_HOUR_PLAN.md',
    'docs/SIMULATION_SETUP_AND_WORK_GUIDE.md', 'evidence/SSD_FINAL_VERIFICATION.md',
    'requirements.txt', 'requirements-checker.txt', 'services/api/requirements-quality.txt',
    'services/api/requirements-dev.txt', 'services/api/requirements-container.lock',
    'frontend/package.json', 'frontend/package-lock.json']


def seal(target, ownership):
    files = sorted(path for path in target.rglob('*') if path.is_file())
    inventory = target / 'FILE_INVENTORY.csv'
    if inventory.exists() or (target / 'CHECKSUMS.sha256').exists():
        raise ValueError('Never reseal an existing delivery')
    with inventory.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['relative_path', 'source_relative_path', 'bytes', 'sha256', 'owner'])
        for path in files:
            key = path.relative_to(target).as_posix()
            safe_file(target, key)
            writer.writerow([key, ownership.get(key, 'generated delivery entry'), path.stat().st_size,
                             digest(path), 'Team2' if key.startswith('team2_work/') else 'Baseline context/Team2 entry'])
    files.append(inventory)
    checksum = target / 'CHECKSUMS.sha256'
    checksum.write_text(''.join(digest(path) + '  ' + path.relative_to(target).as_posix() + '\n'
                               for path in sorted(files)), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true', help='Seal and inspect a separate receiving rehearsal folder first')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    target = root / ('evidence/receiver-preflight-v04' if args.preflight else 'deliveries/TEAM2_ENGINEERING_DELIVERY_V04')
    if target.exists():
        raise ValueError('Delivery already exists; preserve and publish a new version for corrections')
    entries = {('team2_work/' + key): (root, key) for key in TEAM2_FILES}
    entries |= {('reference/' + key): (args.source.resolve(), key) for key in BASELINE_FILES}
    # Validate all sources before creating any incomplete outgoing directory.
    for source_root, key in entries.values():
        safe_file(source_root, key)
    target.mkdir(parents=True)
    ownership = {}
    for destination, (source_root, key) in entries.items():
        source = source_root / key
        copy = target / destination
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, copy)
        if digest(source) != digest(copy):
            raise ValueError('Copy hash mismatch')
        ownership[destination] = ('team2_work/' if source_root == root else 'baseline/') + key
    for name in ('START_HERE.md', 'DELIVERY.md'):
        (target / name).write_text('# Team 2 engineering overlay v04\n\n'
            + 'Read [the complete ' + name + '](team2_work/' + name + ').\n\n'
            + 'The complete verified Ukai_SSD_Ready baseline must accompany this overlay. '
            + 'No private state or credentials are supplied. Start from team2_work/START_TEAM2.cmd with the baseline path.\n', encoding='utf-8')
    seal(target, ownership)
    report = verify(target, args.source.resolve())
    report['sealed_at'] = datetime.now(ZoneInfo('Asia/Calcutta')).isoformat()
    report['all_team2_copy_hashes_match'] = all(digest(root / key) == digest(target / ('team2_work/' + key)) for key in TEAM2_FILES)
    if not report['all_team2_copy_hashes_match']:
        raise ValueError('Working source changed during packaging')
    receipt = 'receiver-preflight-v04-verification.json' if args.preflight else 'v04-delivery-verification.json'
    (root / ('evidence/' + receipt)).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
