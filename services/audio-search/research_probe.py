#!/usr/bin/env python3
"""Fresh two-provider, forty-track development run; no human judgments or downloads."""
import argparse
from copy import deepcopy
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import re
import resource
import subprocess
import time

# Reuse already cached, pinned dependencies. Model construction must not fetch.
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['WANDB_MODE'] = 'disabled'

import numpy as np
import torch
from corpus import decode_mono, file_hash, window_bounds, unit_vectors, rank_segments, PIPELINE_VERSION
from preprocess import prepare_window, SAMPLE_RATE, WINDOW_SAMPLES
from probe import create_pinned_model, CHECKPOINT_SHA256, CHECKPOINT_REVISION, ROBERTA_REVISION

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
INPUT_PINS = {'catalog': 'catalog_sha256', 'source_manifest': 'manifest_sha256',
              'decode_report': 'decode_sha256', 'baseline_catalog': 'baseline_sha256',
              'selection': 'selection_sha256', 'queries': 'queries_sha256'}
SOURCE_FILES = ['research_probe.py', 'test_research_probe.py', 'research_corpus.py',
                'corpus.py', 'preprocess.py', 'probe.py', 'source_review_pack.py',
                'review_pack.py', 'exploratory_queries.json']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
            'Input must be a regular file without symlinks')
    return path


def checked_assets(**arguments):
    from research_corpus import checked_assets as adapter
    return adapter(**arguments)


def source_hashes():
    return {name: file_hash(regular(SOURCE / name)) for name in SOURCE_FILES}


def input_hashes(arguments):
    result = {}
    for name, pin in INPUT_PINS.items():
        expected = arguments[pin]
        require(isinstance(expected, str) and re.fullmatch(r'[a-f0-9]{64}', expected),
                'Six explicit input SHA256 pins are required')
        actual = file_hash(regular(arguments[name]))
        require(actual == expected, 'Pinned research input SHA256 mismatch')
        result[name] = actual
    return result


def query_fixture(path):
    def pairs(items):
        obj = {}
        for key, value in items:
            require(key not in obj, 'Duplicate query JSON key')
            obj[key] = value
        return obj
    value = json.loads(regular(path).read_text(), object_pairs_hook=pairs)
    original = json.loads(regular(SOURCE / 'exploratory_queries.json').read_text(), object_pairs_hook=pairs)
    require(value == original and isinstance(value, dict)
            and value.get('split') == 'exploratory_unjudged'
            and len(value.get('queries', [])) == 8
            and [q['query_id'] for q in value['queries']] == ['exp-%02d' % n for n in range(1, 9)],
            'Expected all eight original exploratory text queries in their original order')
    return value


def private_output(path):
    output = Path(path).absolute()
    local = ROOT / '.local'
    require(local.is_dir() and not local.is_symlink()
            and not any(p.is_symlink() for p in (output, *output.parents)),
            'Output cannot traverse symlinks')
    require(output.resolve().is_relative_to(local.resolve()) and output.resolve() != local.resolve(),
            'Output must stay below this checkout .local')
    require(output.parent.is_dir(), 'Create the private output parent first')
    require(subprocess.run(['git', 'check-ignore', '--quiet', '--no-index', str(output)], cwd=ROOT,
                           capture_output=True).returncode == 0,
            'Output must be ignored by Git')
    output.mkdir(mode=0o700)  # Existing successful, incomplete and failed runs all remain intact.
    return output


def write_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(raw)


def write_vectors(path, **arrays):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        np.savez(output, **arrays)


def code_state():
    return {'code_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())}


def validate_decode(samples, info, asset):
    fields = {'format', 'source_frames', 'source_sample_rate_hz', 'source_channels',
              'sample_rate_hz', 'decoded_samples', 'duration_ms'}
    require(isinstance(info, dict) and set(info) == fields, 'Decoder metadata fields changed')
    frames, rate, channels = info['source_frames'], info['source_sample_rate_hz'], info['source_channels']
    require(type(frames) is int and type(rate) is int and type(channels) is int
            and 8000 <= rate <= 192000 and channels in (1, 2) and 0 < frames <= rate * 600
            and info['format'] == 'MP3', 'Invalid original decode frames/rate/channels/format')
    expected = (frames * SAMPLE_RATE + rate - 1) // rate
    require(isinstance(samples, np.ndarray) and samples.ndim == 1 and samples.dtype == np.float32
            and samples.flags.c_contiguous and len(samples) == expected and np.isfinite(samples).all()
            and type(info['sample_rate_hz']) is int and info['sample_rate_hz'] == SAMPLE_RATE
            and type(info['decoded_samples']) is int and info['decoded_samples'] == expected
            and type(info['duration_ms']) is int and info['duration_ms'] == expected * 1000 // SAMPLE_RATE,
            'Decoded/resampled samples must match the exact integer-ceiling length')
    if asset['source_provider'] == 'incompetech':
        recorded = asset.get('recorded_decode')
        require(isinstance(recorded, dict)
                and set(recorded) == {'frames', 'sample_rate_hz', 'channels', 'format', 'duration_ms'}
                and all(type(recorded[key]) is int for key in ('frames', 'sample_rate_hz', 'channels', 'duration_ms'))
                and recorded == {'frames': frames, 'sample_rate_hz': rate, 'channels': channels,
                                 'format': info['format'], 'duration_ms': frames * 1000 // rate},
                'New source decode differs from its pinned original decode record')


def sf_version():
    import soundfile
    return soundfile.__libsndfile_version__


def run(*, catalog, audio_root, source_manifest, decode_report, baseline_catalog, selection, queries,
        catalog_sha256, manifest_sha256, decode_sha256, baseline_sha256, selection_sha256,
        queries_sha256, checkpoint, output):
    arguments = {'catalog': catalog, 'audio_root': audio_root, 'source_manifest': source_manifest,
        'decode_report': decode_report, 'baseline_catalog': baseline_catalog, 'selection': selection,
        'queries': queries, 'catalog_sha256': catalog_sha256, 'manifest_sha256': manifest_sha256,
        'decode_sha256': decode_sha256, 'baseline_sha256': baseline_sha256,
        'selection_sha256': selection_sha256, 'queries_sha256': queries_sha256}
    output = private_output(output)
    started = time.perf_counter()
    try:
        pins, sources, git = input_hashes(arguments), source_hashes(), code_state()
        require(isinstance(git, dict) and git.get('working_tree_dirty') is False
                and isinstance(git.get('code_sha'), str) and re.fullmatch(r'[a-f0-9]{40}', git['code_sha']),
                'Research pipeline requires a clean committed Git source identity')
        assets = checked_assets(**arguments)
        require(isinstance(assets, list) and len(assets) == 40
                and sum(a.get('source_provider') == 'jamendo' for a in assets) == 20
                and sum(a.get('source_provider') == 'incompetech' for a in assets) == 20,
                'Expected the checked forty-track two-provider corpus')
        original_assets = deepcopy(assets)
        fixture = query_fixture(queries)
        texts = fixture['queries']
        actual_hash = file_hash(regular(checkpoint))
        require(actual_hash == CHECKPOINT_SHA256, 'Checkpoint hash mismatch; no model construction or deserialization attempted')
        np.random.seed(0)
        torch.manual_seed(0)
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        model_started = time.perf_counter()
        sdk = create_pinned_model()
        require(file_hash(regular(checkpoint)) == actual_hash,
                'Checkpoint changed during model construction; no deserialization attempted')
        # Keep the original probe's restricted PyTorch loader and strict CLAP load.
        with torch.serialization.safe_globals([np.core.multiarray.scalar, np.dtype,
                type(np.dtype(np.float64)), type(np.dtype(np.float32))]):
            loaded_state = torch.load(checkpoint, map_location='cpu', weights_only=True, mmap=True)
        state = {key.removeprefix('module.'): value for key, value in loaded_state.get('state_dict', loaded_state).items()}
        removed = state.pop('text_branch.embeddings.position_ids', None) is not None
        loaded = sdk.model.load_state_dict(state, strict=True)
        require(not loaded.missing_keys and not loaded.unexpected_keys, 'Strict model load reported mismatched keys')
        del loaded_state, state
        sdk.model.eval()
        model_ms = (time.perf_counter() - model_started) * 1000
        token_lengths = [len(sdk.tokenize(item['text'], truncation=False)['input_ids']) for item in texts]
        require(all(0 < count <= 77 for count in token_lengths), 'Exploratory text would be truncated or empty')
        segments, blocks, whole = [], [], []
        decode_ms = encode_ms = 0.0
        with torch.inference_mode():
            for original in original_assets:
                asset = deepcopy(original)
                tick = time.perf_counter()
                samples, info = decode_mono(Path(audio_root) / asset['asset_filename'])
                decode_ms += (time.perf_counter() - tick) * 1000
                validate_decode(samples, info, asset)
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
                    require(vectors.shape[0] == len(windows), 'Embedding/window batch mismatch')
                    track_blocks.append(vectors)
                track_vectors = np.concatenate(track_blocks)
                blocks.append(track_vectors)
                whole.append(unit_vectors(track_vectors.mean(axis=0, keepdims=True))[0])
                assets[len(whole) - 1] = asset
                print(json.dumps({'track_id': asset['track_id'], 'decoded_ms': info['duration_ms'],
                                  'segments': len(bounds)}), flush=True)
            tick = time.perf_counter()
            text_vectors = unit_vectors(sdk.get_text_embedding([item['text'] for item in texts], use_tensor=False))
            text_ms = (time.perf_counter() - tick) * 1000
        segment_vectors, whole_vectors = np.concatenate(blocks), np.stack(whole)
        dimension = segment_vectors.shape[1]
        require(dimension == 512, 'Embedding dimension mismatch; pinned checkpoint must produce 512 dimensions')
        require(text_vectors.shape == (8, dimension) and whole_vectors.shape == (40, dimension),
                'Text/audio/whole embedding dimension mismatch')
        require(checked_assets(**arguments) == original_assets, 'Shared corpus input changed during encoding')
        require(input_hashes(arguments) == pins and source_hashes() == sources and code_state() == git
                and file_hash(regular(checkpoint)) == actual_hash,
                'Pinned input/source/Git state changed during encoding')
        corpus = {'schema': 'sonora-research-corpus-v1', 'pipeline_version': PIPELINE_VERSION, 'tracks': assets,
            'visibility': 'private owner-scoped offline probe; no shared discovery permission',
            'evidence': 'pinned two-provider catalog, source/decode records and original download proofs; no fresh permission check'}
        write_json(output / 'corpus-manifest.json', corpus)
        write_json(output / 'segments.json', segments)
        write_vectors(output / 'vectors.npz', segment_vectors=segment_vectors, whole_vectors=whole_vectors,
                      text_vectors=text_vectors, reference_vectors=np.empty((0, dimension), dtype=np.float32))
        results = []
        for query, vector in zip(texts, text_vectors):
            whole_scores = whole_vectors @ vector
            order = sorted(range(len(assets)), key=lambda i: (-float(whole_scores[i]), int(assets[i]['track_id'])))[:5]
            results.append({'kind': 'text', **query,
                'whole_track': [{'track_id': assets[i]['track_id'], 'score': float(whole_scores[i])} for i in order],
                'segment': rank_segments(segment_vectors @ vector, segments)})
        write_json(output / 'rankings.json', {'judgments': 'unjudged', 'queries': results})
        write_json(output / 'queries.json', fixture)
        artifacts = {p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
        report = {'schema': 'sonora-research-probe-v1', 'status': 'passed_private_research_pipeline_only', **git,
            'source_hashes': sources, 'input_catalog_sha256': pins['catalog'], 'input_sha256': pins,
            'artifact_sha256': artifacts,
            'model': {'checkpoint_sha256': actual_hash, 'checkpoint_revision': CHECKPOINT_REVISION,
                'roberta_revision': ROBERTA_REVISION, 'audio_architecture': 'HTSAT-base', 'fusion': False,
                'dimension': dimension, 'strict_missing': loaded.missing_keys, 'strict_unexpected': loaded.unexpected_keys,
                'removed_nonlearned_position_ids': removed}, 'pipeline_version': PIPELINE_VERSION,
            'preprocessing': {'sample_rate_hz': SAMPLE_RATE, 'window_samples': WINDOW_SAMPLES,
                'hop_samples': SAMPLE_RATE * 5, 'downmix': 'channel arithmetic mean',
                'resampler': 'whole-track soxr_hq with integer-ceiling sample count',
                'padding': 'right zeros before SDK', 'sdk_quantization': 'clip [-1,1], float32 -> int16 -> float32'},
            'environment': {'python': platform.python_version(), 'system': platform.system(), 'machine': platform.machine(),
                'device': 'cpu', 'threads': 2, 'soundfile_library': sf_version(),
                'packages': {name: version(name) for name in ['laion-clap', 'torch', 'numpy', 'soundfile', 'librosa', 'soxr', 'transformers']}},
            'counts': {'tracks': 40, 'segments': len(segments), 'text_queries': 8, 'reference_queries': 0,
                'padded_tail_segments': sum(item['padded_samples'] > 0 for item in segments),
                'decoded_duration_ms': sum(item['duration_ms'] for item in assets)},
            'text_token_lengths': token_lengths,
            'single_run_timings_ms': {'model_load': model_ms, 'decode_resample': decode_ms,
                'audio_encoding_including_reference': encode_ms, 'text_encoding': text_ms,
                'total': (time.perf_counter() - started) * 1000},
            'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'limits': ['Fresh forty-track development encoding; no human labels read and no relevance metric computed.',
                'Eight existing text queries only; no new audio reference or held-out test.',
                'New source original decode duration retained; 48k duration follows exact integer-ceiling resampling.',
                'Whole-track is normalized mean of window embeddings, not a full-song encoder.',
                'Single-process timings are not P95/concurrency/Java/browser latency.',
                'Recorded source/license evidence is not fresh permission or legal verification.',
                'No database refresh, public catalog, service, shared index, training or discovery-v0 freeze.']}
        # Check again after writing derived artifacts; a changed source never gets a passed report.
        require(input_hashes(arguments) == pins and source_hashes() == sources and code_state() == git
                and file_hash(regular(checkpoint)) == actual_hash,
                'Pinned input/source/Git state changed while writing artifacts')
        write_json(output / 'report.json', report)
        return report
    except Exception as exc:
        write_json(output / 'failure.json', {'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('catalog', 'audio_root', 'source_manifest', 'decode_report', 'baseline_catalog', 'selection', 'queries', 'checkpoint', 'output'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    for name in INPUT_PINS.values():
        parser.add_argument('--' + name.replace('_', '-'), required=True)
    args = parser.parse_args()
    result = run(**vars(args))
    print(json.dumps({'status': result['status'], 'counts': result['counts']}, indent=2))


if __name__ == '__main__':
    main()
