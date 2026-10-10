"""Read-only check that public schema/examples still match implemented Team2 contracts."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_service import CandidateRequest, CandidateResult, Capabilities, create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh contract check directory required')
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent
    spec_path = root / 'contract-drop-v02/candidate-openapi-v1.json'
    examples_path = root / 'contract-drop-v02/candidate-examples.json'
    app = create_app(args.source, args.output / 'documentation-state')
    spec = json.loads(spec_path.read_text())
    examples = json.loads(examples_path.read_text())
    if app.openapi() != spec:
        raise ValueError('Actual public schema changed from frozen contract')
    Capabilities.model_validate(examples['capabilities'])
    for pair in examples['examples']:
        request = CandidateRequest.model_validate(pair['request'])
        result = CandidateResult.model_validate(pair['response'])
        if request.request_id != result.request_id or request.peak_release_m3s != result.requested_peak_release_m3s:
            raise ValueError('Example request/result mismatch')
    report = {'passed': True, 'schema_version': '1.0.0', 'examples': len(examples['examples']),
        'checked_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
        'spec_sha256': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        'examples_sha256': hashlib.sha256(examples_path.read_bytes()).hexdigest(),
        'service_sha256': hashlib.sha256((root / 'candidate_service.py').read_bytes()).hexdigest()}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
