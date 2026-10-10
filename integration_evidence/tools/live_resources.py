"""Verify all real reference resources against an already-running owned assembly."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, state, output = [p.resolve() for p in (args.source, args.state, args.output)]
    sys.path.insert(0, str(root / 'team2_work'))
    from combined_runtime import Config, baseline_module, get_json, load_owner
    marker = json.loads((state / 'combined-owner.json').read_text())
    ports = marker['ports']
    config = Config(root, state, ports['database'], ports['api'], ports['web'], ports['candidate'])
    owner = load_owner(config)
    if get_json(config.web_port, '/__ukai_instance')['instance'] != owner['instance']:
        raise ValueError('Not the owned integrated application')
    before = hashlib.sha256((state / 'import-complete.json').read_bytes()).hexdigest()
    module = baseline_module(config, owner)
    entries = [json.loads((receipt / 'prototype-manifest.json').read_text()) for _, receipt in module.RECEIPTS]
    module.check_roundtrip(state, entries)
    smoke = json.loads((state / 'SSD_SMOKE_RESULT.json').read_text())
    downloads = [r for s in smoke['four_scenarios'] for r in s['download_results']]
    cap = get_json(config.web_port, '/api/v1/candidates/capabilities')
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': len(downloads) == 24,
              'download_count': len(downloads), 'download_results': smoke['four_scenarios'],
              'frontend_resources': smoke['frontend_resources'], 'instance': owner['instance'],
              'stored_only': cap['supported_modes'] == ['stored_reference'] and not cap['experimental_ml_enabled'],
              'no_reimports': before == hashlib.sha256((state / 'import-complete.json').read_bytes()).hexdigest(),
              'source': str(root), 'baseline_database_used': False}
    report['passed'] = report['passed'] and report['stored_only'] and report['no_reimports'] and all(
        d.get('exact_range_bytes_and_headers_verified') and d.get('matching_if_range_verified') for d in downloads)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['passed', 'download_count', 'stored_only', 'no_reimports']}))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
