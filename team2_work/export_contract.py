"""Export the implemented candidate contract and real stored-reference examples."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_service import CandidateRequest, CandidateResult, create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh contract drop required')
    args.output.mkdir(parents=True)
    app = create_app(args.source, args.output / 'export-state')
    spec = app.openapi()
    (args.output / 'candidate-openapi-v1.json').write_text(json.dumps(spec, indent=2, allow_nan=False), encoding='utf-8')
    routes = {route.path: route.endpoint for route in app.routes if hasattr(route, 'endpoint')}
    select = routes['/api/v1/candidates/jobs']
    scenarios = []
    for number, peak in enumerate((15000., 20000., 30000., 25000.)):
        request = CandidateRequest(request_id='example-reference-' + str(number + 1),
            peak_release_m3s=peak, allow_nearest_stored=peak == 25000.)
        response = CandidateResult.model_validate(select(request))
        scenarios.append({'request': request.model_dump(mode='json'), 'response': response.model_dump(mode='json')})
    payload = {'schema_version': '1.0.0', 'examples_kind': 'actual stored-reference service calls; no new simulation or ML prediction',
        'capabilities': routes['/api/v1/candidates/capabilities'](), 'examples': scenarios}
    (args.output / 'candidate-examples.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    checksums = []
    for path in sorted(args.output.rglob('*')):
        if path.is_file():
            checksums.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(args.output).as_posix())
    (args.output / 'CHECKSUMS.sha256').write_text('\n'.join(checksums) + '\n', encoding='utf-8')
    print(json.dumps({'exported': True, 'routes': list(spec['paths']), 'actual_examples': len(scenarios), 'ml_enabled': False}))


if __name__ == '__main__':
    main()
