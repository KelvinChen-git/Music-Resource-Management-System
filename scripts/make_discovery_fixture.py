#!/usr/bin/env python3
"""Explicit synthetic retrieval fixture for self-generated local audio; not a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/audio-search'))
import numpy as np
from discovery_index import DiscoveryIndex


def write_fixture(output, tracks, index_version='mus067-synthetic-v1'):
    output = Path(output)
    output.mkdir(mode=0o700)
    output.chmod(0o700)
    try:
        assert 1 <= len(tracks) <= 3
        segments, vectors, whole, queries = [], [], [], {}
        for i, track in enumerate(tracks):
            vector = np.eye(1, 512, i, dtype=np.float32)[0]
            whole.append(vector)
            queries['synthetic tone ' + str((440, 660, 880)[i])] = vector.tolist()
            for start in range(0, track['duration_ms'], 5000):
                segments.append({'track_id': track['track_id'], 'segment_id': track['track_id'] + ':' + str(start),
                                 'start_ms': start, 'end_ms': min(start + 10000, track['duration_ms'])})
                vectors.append(vector)
        prior = os.umask(0o077)
        try:
            np.savez(output / 'features.npz', segments=np.stack(vectors), whole=np.stack(whole))
            meta = {'schema': 'sonora-discovery-index-v1', 'index_version': index_version,
                    'model_version': 'synthetic-text-v1', 'engine_kind': 'synthetic_fixture', 'dimension': 512,
                    'feature_sha256': hashlib.sha256((output / 'features.npz').read_bytes()).hexdigest(),
                    'tracks': tracks, 'segments': segments, 'fixture_queries': queries}
            (output / 'manifest.json').write_text(json.dumps(meta, indent=2) + '\n')
        finally:
            os.umask(prior)
        DiscoveryIndex(output / 'manifest.json')
        return meta
    except Exception:
        # Failed output remains intact, never reused or overwritten.
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', type=Path, required=True, help='Synthetic track IDs/content bindings only')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if not output.resolve().is_relative_to((ROOT / '.local').resolve()) or any(p.is_symlink() for p in (output, *output.parents)):
        raise SystemExit('Output must be a fresh private directory below this checkout .local')
    subprocess.run(['git', 'check-ignore', '--quiet', '--no-index', str(output)], cwd=ROOT, check=True)
    meta = write_fixture(output, json.loads(args.catalog.read_text()))
    print(json.dumps({'engine_kind': meta['engine_kind'], 'index_version': meta['index_version'],
                      'model_version': meta['model_version'], 'fixture_queries': list(meta['fixture_queries'])}))


if __name__ == '__main__':
    main()
