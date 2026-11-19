#!/usr/bin/env python3
"""Build a real CLAP index from explicit private source/content proofs; no downloads."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/audio-search'))
from discovery_build import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], default='b')
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--audio-root', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--offline-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--index-version', required=True)
    parser.add_argument('--batch-size', type=int, default=2)
    args = parser.parse_args()
    try:
        print(json.dumps(build(**vars(args)), allow_nan=False))
    except Exception as error:
        # Operators inspect the retained private failure; never print source paths/URLs.
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
