"""Start the separate local Team2 fallback service without database initialization."""
import argparse
from pathlib import Path
import sys
import uvicorn
sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_service import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8770)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        raise ValueError('Valid local port required')
    uvicorn.run(create_app(args.source, args.state), host='127.0.0.1', port=args.port,
                proxy_headers=False, access_log=False, workers=1)


if __name__ == '__main__':
    main()
