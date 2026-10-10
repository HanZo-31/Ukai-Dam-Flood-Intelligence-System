"""Assemble a plain code/contract/evidence delivery, excluding runtime jobs and secrets."""
import csv
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v01', 'v02'], default='v01')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    target = root / ('deliveries/TEAM2_FIRST_DELIVERY_' + args.version.upper() + '/team2_work')
    if target.exists():
        raise ValueError('Delivery already exists; never overwrite')
    files = ['START_HERE.md', 'WORK_CHECKLIST.md', 'WORK_EVIDENCE.md', 'TEAM1_CANDIDATE_CONTRACT.md',
        'candidate_service.py', 'run_candidate_service.py', 'test_candidate_service.py',
        'audit_four_scenarios.py', 'fit_diagnostic_model.py', 'export_contract.py',
        'run_focused_checks.py', 'probe_local_service.py', 'package_first_delivery.py',
        'contract-drop-v02/candidate-openapi-v1.json', 'contract-drop-v02/candidate-examples.json',
        'evidence/four-scenario-audit-v01.json', 'diagnostic-v01/evaluation.json',
        'diagnostic-v01/diagnostic-model.npz', 'evidence/candidate-check-v05/report.json',
        'evidence/candidate-check-v05/tests.log', 'evidence/loopback-probe-v01/report.json',
        'evidence/loopback-probe-v01/service.log']
    if args.version == 'v02':
        files += ['ASSEMBLY_AND_RUN_GUIDE.md', 'assembly/ssd_web_server.cjs', 'probe_assembly_proxy.py',
            'evidence/assembly-proxy-v02/report.json', 'evidence/assembly-proxy-v02/candidate.log',
            'evidence/assembly-proxy-v02/web.log', 'evidence/candidate-check-v08/report.json',
            'evidence/candidate-check-v08/tests.log']
    for key in files:
        destination = target / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / key, destination)
        if digest(destination) != digest(root / key):
            raise ValueError('Copy hash mismatch')
    # Exact matching contract/examples are delivered; mutable export job records are excluded.
    inventory = target / 'FILE_INVENTORY.csv'
    with inventory.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['relative_path', 'source_relative_path', 'bytes', 'sha256', 'purpose'])
        for key in files:
            writer.writerow([key, 'team2_work/' + key, (target / key).stat().st_size,
                             digest(target / key), 'Team2 code, contract or explicitly scoped evidence'])
    expected = {key: digest(target / key) for key in [*files, 'FILE_INVENTORY.csv']}
    checksum = target / 'CHECKSUMS.sha256'
    checksum.write_text(''.join(value + '  ' + key + '\n' for key, value in sorted(expected.items())), encoding='utf-8')
    actual = {path.relative_to(target).as_posix() for path in target.rglob('*') if path.is_file() and path != checksum}
    if actual != set(expected) or any(digest(target / key) != value for key, value in expected.items()):
        raise ValueError('Final delivery inventory/hash check failed')
    report = {'delivery': str(target.parent), 'files': len(expected) + 1,
        'verified_checksums': len(expected), 'passed': True,
        'baseline_runtime_and_four_receipts_required': True, 'new_ml_prediction_enabled': False,
        'checksum_file_sha256': digest(checksum)}
    report_path = 'first-delivery-verification.json' if args.version == 'v01' else 'second-delivery-verification.json'
    (root / 'evidence' / report_path).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
