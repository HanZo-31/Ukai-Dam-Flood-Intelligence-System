"""Start the separate local Team2 fallback service without database initialization."""
import argparse
from pathlib import Path
import sys
import uvicorn
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from candidate_service import create_app
from rapid_engine.compute import install


def build_app(source, state, enable_compute=True):
    app = create_app(source, state)
    provider = None
    if enable_compute and (Path(__file__).resolve().parents[1] / 'rapid_engine/native_configuration.json').is_file():
        from rapid_engine.native_provider import NativeProvider
        try:
            provider = NativeProvider(source)
        except (OSError, ValueError, KeyError, TypeError):
            print('Native configuration unavailable; reference lookup remains available.', file=sys.stderr)
    install(app, source, state.parent / (state.name + '-compute-v2'), provider)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--disable-compute', action='store_true', help='Explicit stored-only fallback')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        raise ValueError('Valid local port required')
    app = build_app(args.source, args.state, enable_compute=not args.disable_compute)
    uvicorn.run(app, host='127.0.0.1', port=args.port,
                proxy_headers=False, access_log=False, workers=1)


if __name__ == '__main__':
    main()
