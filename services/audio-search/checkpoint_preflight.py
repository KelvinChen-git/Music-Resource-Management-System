#!/usr/bin/env python3
"""Fresh checkpoint compatibility run on the original twenty development recordings.

No new-test data, labels, downloads, database changes or quality metrics are read.
"""
import argparse
from copy import deepcopy
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import time

from checkpoint_model import regular, checked_checkpoint, load_checkpoint, require
import numpy as np
import torch
from corpus import checked_assets, decode_mono, file_hash, window_bounds, unit_vectors, rank_segments, PIPELINE_VERSION
from preprocess import prepare_window, SAMPLE_RATE
from research_probe import private_output, write_json, write_vectors, validate_decode

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
CATALOG_SHA = '33c9d7fdf284aa1f3570ccbb03e79146adcb16e7e2509b823fb6cee7b931e2a5'
QUERY_SHA = 'f6118b2283c2818f0dd2af196c98c770045ff787c32403407eaea2241a313723'
QUERY_IDS = ['exp-02', 'exp-03', 'exp-04', 'exp-07', 'exp-08']
SOURCE_FILES = ['checkpoint_preflight.py', 'checkpoint_model.py', 'test_checkpoint_preflight.py',
    'test_checkpoint_model.py', 'research_probe.py', 'corpus.py', 'preprocess.py', 'probe.py',
    'exploratory_queries.json']


def code_state():
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()
    require(not dirty, 'Committed clean source required before model construction')
    sources = {name: file_hash(regular(SOURCE / name)) for name in SOURCE_FILES}
    for name in SOURCE_FILES:
        raw = subprocess.check_output(['git', 'show', sha + ':services/audio-search/' + name], cwd=ROOT)
        import hashlib
        require(hashlib.sha256(raw).hexdigest() == sources[name], 'Source differs from committed tree')
    return {'code_sha': sha, 'working_tree_dirty': False, 'source_hashes': sources}


def inputs(catalog, catalog_sha256, audio_root):
    require(catalog_sha256 == CATALOG_SHA and file_hash(regular(catalog)) == CATALOG_SHA,
            'Only pinned original20 development catalog is supported')
    query_path = SOURCE / 'exploratory_queries.json'
    require(file_hash(regular(query_path)) == QUERY_SHA, 'Original query fixture changed')
    fixture = json.loads(query_path.read_text())
    require(fixture.get('split') == 'exploratory_unjudged', 'Original development fixture required')
    queries = [q for q in fixture['queries'] if q['query_id'] in QUERY_IDS]
    require([q['query_id'] for q in queries] == QUERY_IDS, 'Exactly five fixed development queries required')
    assets = checked_assets(catalog, audio_root)
    require(len(assets) == 20, 'Exactly original twenty recordings required')
    hashes = {str(Path(catalog).absolute()): CATALOG_SHA, str(query_path): QUERY_SHA}
    for asset in assets:
        asset['source_provider'] = 'jamendo'
        for name in [asset['asset_filename'], asset['source_id'] + '.download.json']:
            path = regular(Path(audio_root) / name)
            hashes[str(path)] = file_hash(path)
    return assets, queries, hashes


def run(*, catalog, catalog_sha256, audio_root, checkpoint, model_id, output):
    target = private_output(output)
    started = time.perf_counter()
    prior_cache = os.environ.get('NUMBA_CACHE_DIR')
    prior_mask = os.umask(0o077)
    cache = target / 'decode-cache'
    cache.mkdir(mode=0o700)
    cache.chmod(0o700)
    os.environ['NUMBA_CACHE_DIR'] = str(cache)
    try:
        git = code_state()
        assets, queries, pins = inputs(catalog, catalog_sha256, audio_root)
        original = deepcopy(assets)
        checkpoint, checkpoint_sha = checked_checkpoint(checkpoint, model_id)
        np.random.seed(0); torch.manual_seed(0)
        torch.set_num_threads(2); torch.set_num_interop_threads(1)
        sdk, model = load_checkpoint(checkpoint, model_id)
        token_lengths = [len(sdk.tokenize(q['text'], truncation=False)['input_ids']) for q in queries]
        require(all(0 < n <= 77 for n in token_lengths), 'Development query would be truncated')
        segments, blocks, whole = [], [], []
        with torch.inference_mode():
            for asset in assets:
                samples, info = decode_mono(Path(audio_root) / asset['asset_filename'])
                validate_decode(samples, info, asset)
                asset.update(info)
                bounds = window_bounds(len(samples)); track_blocks = []
                for offset in range(0, len(bounds), 4):
                    windows = []
                    for start, end in bounds[offset:offset + 4]:
                        window, padding = prepare_window(samples[start:end], SAMPLE_RATE)
                        windows.append(window)
                        segments.append({'segment_id': f"{asset['track_id']}:{start}:{end}",
                            'track_id': asset['track_id'], 'start_sample': start, 'end_sample': end,
                            'start_ms': start * 1000 // SAMPLE_RATE, 'end_ms': end * 1000 // SAMPLE_RATE,
                            'padded_samples': padding['padded_samples']})
                    vectors = unit_vectors(sdk.get_audio_embedding_from_data(np.stack(windows), use_tensor=False))
                    require(vectors.shape == (len(windows), 512), 'Audio embedding must have512 dimensions')
                    track_blocks.append(vectors)
                track_vectors = np.concatenate(track_blocks)
                blocks.append(track_vectors)
                whole.append(unit_vectors(track_vectors.mean(axis=0, keepdims=True))[0])
                print(json.dumps({'decoded_tracks': len(whole), 'segments': len(segments)}), flush=True)
            text_vectors = unit_vectors(sdk.get_text_embedding([q['text'] for q in queries], use_tensor=False))
        require(text_vectors.shape == (5, 512), 'Text embedding must be5x512')
        segment_vectors, whole_vectors = np.concatenate(blocks), np.stack(whole)
        results = []
        for query, vector in zip(queries, text_vectors):
            scores = whole_vectors @ vector
            order = sorted(range(20), key=lambda i: (-float(scores[i]), int(assets[i]['track_id'])))[:5]
            results.append({**query, 'whole_track': [{'track_id': assets[i]['track_id'], 'score': float(scores[i])} for i in order],
                            'segment': rank_segments(segment_vectors @ vector, segments)})
        def recheck():
            again, again_queries, again_pins = inputs(catalog, catalog_sha256, audio_root)
            require(again == original and again_queries == queries and again_pins == pins
                    and code_state() == git and checked_checkpoint(checkpoint, model_id)[1] == checkpoint_sha,
                    'Development inputs/source/checkpoint changed during run')
        recheck()
        write_json(target / 'corpus-manifest.json', {'schema': 'sonora-checkpoint-preflight-corpus-v1',
            'split': 'development_preflight_only', 'tracks': assets, 'pipeline_version': PIPELINE_VERSION})
        write_json(target / 'segments.json', segments)
        write_vectors(target / 'vectors.npz', segment_vectors=segment_vectors, whole_vectors=whole_vectors,
                      text_vectors=text_vectors)
        write_json(target / 'rankings.json', {'schema': 'sonora-checkpoint-preflight-rankings-v1',
            'split': 'development_preflight_only', 'model_id': model_id, 'queries': results})
        write_json(target / 'queries.json', {'split': 'development_preflight_only', 'queries': queries})
        artifact_hashes = {p.name: file_hash(p) for p in target.iterdir() if p.is_file()}
        import soundfile
        report = {'schema': 'sonora-checkpoint-preflight-report-v1', 'status': 'passed_development_compatibility_only',
            **git, 'input_catalog_sha256': catalog_sha256, 'original_query_fixture_sha256': QUERY_SHA,
            'input_sha256': pins, 'artifact_sha256': artifact_hashes, 'model': {**model, 'dimension': 512},
            'pipeline_version': PIPELINE_VERSION, 'counts': {'tracks': 20, 'segments': len(segments),
                'text_queries': 5, 'reference_queries': 0, 'new_test_tracks_or_queries': 0},
            'text_token_lengths': token_lengths, 'environment': {'python': platform.python_version(),
                'system': platform.system(), 'machine': platform.machine(), 'device': 'cpu', 'threads': 2,
                'soundfile_library': soundfile.__libsndfile_version__, 'packages': {n: version(n) for n in
                    ['laion-clap', 'torch', 'numpy', 'librosa', 'soundfile', 'soxr', 'transformers']}},
            'single_run_seconds': time.perf_counter() - started,
            'limits': ['Original twenty development recordings only; no test material, qrels, metrics or model selection.',
                'Fresh full encoding; unchanged old decoder/DSP/ranking; whole normalized window mean, segment maximum.',
                'Compatibility is not held-out quality, P95, safe loading of arbitrary unpinned files, or G2 runner freeze.',
                'No database, model service, dependency, cache, original checkpoint or existing artifacts modified.']}
        recheck()
        write_json(target / 'report.json', report)
        return report
    except Exception as exc:
        write_json(target / 'failure.json', {'status': 'failed_preflight', 'error_type': type(exc).__name__, 'error': str(exc)})
        raise
    finally:
        os.umask(prior_mask)
        if prior_cache is None:
            os.environ.pop('NUMBA_CACHE_DIR', None)
        else:
            os.environ['NUMBA_CACHE_DIR'] = prior_cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['catalog', 'audio_root', 'checkpoint', 'output']:
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--catalog-sha256', required=True)
    parser.add_argument('--model-id', choices=['A', 'B'], required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({'status': report['status'], 'counts': report['counts']}))


if __name__ == '__main__':
    main()
