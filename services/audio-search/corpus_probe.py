#!/usr/bin/env python3
"""Read-only real-music feasibility run. All generated artifacts stay ignored."""
import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import time

# No provider or model downloads: reuse the pinned feasibility environment/cache.
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['WANDB_MODE'] = 'disabled'

import numpy as np
import torch
from corpus import checked_assets, decode_mono, file_hash, window_bounds, unit_vectors, rank_segments, PIPELINE_VERSION
from preprocess import prepare_window, SAMPLE_RATE, WINDOW_SAMPLES
from probe import create_pinned_model, CHECKPOINT_SHA256, CHECKPOINT_REVISION, ROBERTA_REVISION


def write_json(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def run(catalog, audio_root, checkpoint, output, queries_path):
    repo = Path(__file__).resolve().parents[2]
    output = output.resolve()
    if not output.is_relative_to(repo / '.local'):
        raise ValueError('Generated corpus artifacts must stay under this checkout .local/')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Refuse to overwrite any previous run, including failures.
    started = time.perf_counter()
    source = Path(__file__).resolve().parent
    try:
        assets = checked_assets(catalog, audio_root)
        query_fixture = json.loads(queries_path.read_text())
        texts = query_fixture['queries']
        if (query_fixture['split'] != 'exploratory_unjudged' or not 1 <= len(texts) <= 20
                or len({item['query_id'] for item in texts}) != len(texts)
                or any(not isinstance(item['text'], str) or not item['text'].strip() for item in texts)):
            raise ValueError('Invalid exploratory query fixture')
        actual_hash = file_hash(checkpoint)
        if actual_hash != CHECKPOINT_SHA256:
            raise ValueError('Checkpoint hash mismatch; no deserialization attempted')
        np.random.seed(0); torch.manual_seed(0)
        torch.set_num_threads(2); torch.set_num_interop_threads(1)
        model_started = time.perf_counter()
        sdk = create_pinned_model()
        with torch.serialization.safe_globals([np.core.multiarray.scalar, np.dtype,
                type(np.dtype(np.float64)), type(np.dtype(np.float32))]):
            loaded_state = torch.load(checkpoint, map_location='cpu', weights_only=True, mmap=True)
        state = {key.removeprefix('module.'): value for key, value in loaded_state.get('state_dict', loaded_state).items()}
        removed = state.pop('text_branch.embeddings.position_ids', None) is not None
        loaded = sdk.model.load_state_dict(state, strict=True)
        del loaded_state, state
        sdk.model.eval()
        model_ms = (time.perf_counter() - model_started) * 1000
        token_lengths = [len(sdk.tokenize(item['text'], truncation=False)['input_ids']) for item in texts]
        if max(token_lengths) > 77:
            raise ValueError('Exploratory text would be silently truncated by the SDK')
        segments, blocks, whole_vectors, references = [], [], [], []
        decode_ms, encode_ms = 0.0, 0.0
        reference_tracks = {0, len(assets) // 2, len(assets) - 1}
        with torch.inference_mode():
            for position, asset in enumerate(assets):
                tick = time.perf_counter()
                samples, info = decode_mono(Path(audio_root) / asset['asset_filename'])
                decode_ms += (time.perf_counter() - tick) * 1000
                asset.update(info)
                bounds = window_bounds(len(samples))
                track_blocks = []
                for offset in range(0, len(bounds), 4):
                    windows = []
                    for start, end in bounds[offset:offset + 4]:
                        window, padding = prepare_window(samples[start:end], SAMPLE_RATE)
                        windows.append(window)
                        segments.append({'segment_id': f"{asset['track_id']}:{start}:{end}",
                            'track_id': asset['track_id'], 'start_sample': start, 'end_sample': end,
                            'start_ms': start * 1000 // SAMPLE_RATE, 'end_ms': end * 1000 // SAMPLE_RATE,
                            'padded_samples': padding['padded_samples']})
                    tick = time.perf_counter()
                    vectors = unit_vectors(sdk.get_audio_embedding_from_data(np.stack(windows), use_tensor=False))
                    encode_ms += (time.perf_counter() - tick) * 1000
                    if vectors.shape[0] != len(windows):
                        raise ValueError('Embedding/window batch mismatch')
                    track_blocks.append(vectors)
                track_vectors = np.concatenate(track_blocks)
                blocks.append(track_vectors)
                whole_vectors.append(unit_vectors(track_vectors.mean(axis=0, keepdims=True))[0])
                if position in reference_tracks:
                    start = len(samples) // 3
                    end = min(start + WINDOW_SAMPLES, len(samples))
                    window, _ = prepare_window(samples[start:end], SAMPLE_RATE)
                    tick = time.perf_counter()
                    vector = unit_vectors(sdk.get_audio_embedding_from_data(window[None, :], use_tensor=False))[0]
                    encode_ms += (time.perf_counter() - tick) * 1000
                    references.append({'query_id': 'reference-' + asset['track_id'],
                        'reference_track_id': asset['track_id'], 'start_ms': start * 1000 // SAMPLE_RATE,
                        'end_ms': end * 1000 // SAMPLE_RATE, 'vector': vector})
                print(json.dumps({'track_id': asset['track_id'], 'decoded_ms': info['duration_ms'], 'segments': len(bounds)}), flush=True)
            tick = time.perf_counter()
            text_vectors = unit_vectors(sdk.get_text_embedding([item['text'] for item in texts], use_tensor=False))
            text_ms = (time.perf_counter() - tick) * 1000
        segment_vectors = np.concatenate(blocks)
        whole_vectors = np.stack(whole_vectors)
        reference_vectors = np.stack([item.pop('vector') for item in references])
        dimension = segment_vectors.shape[1]
        if text_vectors.shape[0] != len(texts):
            raise ValueError('Embedding/text batch mismatch')
        # Detect changed shared input bytes/proofs instead of labeling a mixed run valid.
        rechecked = checked_assets(catalog, audio_root)
        for before, after in zip(assets, rechecked):
            if any(before[key] != value for key, value in after.items()):
                raise ValueError('Shared corpus input changed during encoding')
        if len(rechecked) != len(assets):
            raise ValueError('Shared corpus size changed during encoding')
        for vectors in (whole_vectors, text_vectors, reference_vectors):
            if vectors.shape[1] != dimension:
                raise ValueError('Text/audio/whole embedding dimension mismatch')
        corpus = {'pipeline_version': PIPELINE_VERSION, 'tracks': assets,
            'visibility': 'private owner-scoped offline probe; no shared discovery permission',
            'evidence': 'recorded catalog plus original download proofs; no fresh provider/permission check'}
        write_json(output / 'corpus-manifest.json', corpus)
        write_json(output / 'segments.json', segments)
        np.savez(output / 'vectors.npz', segment_vectors=segment_vectors, whole_vectors=whole_vectors,
                 text_vectors=text_vectors, reference_vectors=reference_vectors)
        results = []
        for kind, queries, vectors in [('text', texts, text_vectors), ('audio', references, reference_vectors)]:
            for query, vector in zip(queries, vectors):
                whole_scores = whole_vectors @ vector
                order = sorted(range(len(assets)), key=lambda i: (-float(whole_scores[i]), int(assets[i]['track_id'])))[:5]
                results.append({'kind': kind, **query,
                    'whole_track': [{'track_id': assets[i]['track_id'], 'score': float(whole_scores[i])} for i in order],
                    'segment': rank_segments(segment_vectors @ vector, segments)})
        write_json(output / 'rankings.json', {'judgments': 'unjudged', 'queries': results})
        write_json(output / 'queries.json', query_fixture)
        artifacts = {path.name: file_hash(path) for path in sorted(output.iterdir()) if path.is_file()}
        report = {
            'status': 'passed_offline_pipeline_only',
            'code_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
            'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip()),
            'source_hashes': {name: file_hash(source / name) for name in ['corpus.py', 'corpus_probe.py', 'preprocess.py', 'probe.py']},
            'input_catalog_sha256': file_hash(catalog), 'artifact_sha256': artifacts,
            'model': {'checkpoint_sha256': actual_hash, 'checkpoint_revision': CHECKPOINT_REVISION,
                'roberta_revision': ROBERTA_REVISION, 'audio_architecture': 'HTSAT-base', 'fusion': False,
                'dimension': dimension, 'strict_missing': loaded.missing_keys, 'strict_unexpected': loaded.unexpected_keys,
                'removed_nonlearned_position_ids': removed},
            'pipeline_version': PIPELINE_VERSION,
            'preprocessing': {'sample_rate_hz': SAMPLE_RATE, 'window_samples': WINDOW_SAMPLES,
                'hop_samples': SAMPLE_RATE * 5, 'downmix': 'channel arithmetic mean',
                'resampler': 'whole-track soxr_hq with integer-ceiling sample count',
                'padding': 'right zeros before SDK', 'sdk_quantization': 'clip [-1,1], float32 -> int16 -> float32'},
            'environment': {'python': platform.python_version(), 'system': platform.system(), 'machine': platform.machine(),
                'device': 'cpu', 'threads': 2, 'soundfile_library': sf_version(),
                'packages': {name: version(name) for name in ['laion-clap', 'torch', 'numpy', 'soundfile', 'librosa', 'soxr', 'transformers']}},
            'counts': {'tracks': len(assets), 'segments': len(segments), 'text_queries': len(texts), 'reference_queries': len(references),
                'padded_tail_segments': sum(item['padded_samples'] > 0 for item in segments),
                'decoded_duration_ms': sum(item['duration_ms'] for item in assets)},
            'text_token_lengths': token_lengths,
            'single_run_timings_ms': {'model_load': model_ms, 'decode_resample': decode_ms,
                'audio_encoding_including_reference': encode_ms, 'text_encoding': text_ms,
                'total': (time.perf_counter() - started) * 1000},
            'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'limits': ['No human relevance labels, held-out test set, localization ground truth or quality metric.',
                'Reference clips come from candidate tracks; self matches are not held-out retrieval evidence.',
                'Whole-track is normalized mean of window embeddings, not a full-song encoder.',
                'Single-process timings are not P95/concurrency/Java/browser latency.',
                'Recorded license declarations were matched, not refreshed or legally revalidated.',
                'No database/permission refresh, API, shared index, service or discovery-v0 freeze.'],
        }
        write_json(output / 'report.json', report)
        return report
    except Exception as exc:
        write_json(output / 'failure.json', {'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)})
        raise


def sf_version():
    import soundfile
    return soundfile.__libsndfile_version__


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--audio-root', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--queries', type=Path, default=Path(__file__).with_name('exploratory_queries.json'))
    args = parser.parse_args()
    result = run(args.catalog, args.audio_root, args.checkpoint, args.output, args.queries)
    print(json.dumps({'status': result['status'], 'counts': result['counts']}, indent=2))
