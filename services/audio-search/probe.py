#!/usr/bin/env python3
"""CPU-only CLAP feasibility probe. No retrieval service or quality evaluation."""
import argparse
from contextlib import ExitStack
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import time
from unittest.mock import patch

import numpy as np
import torch
import laion_clap
from transformers import RobertaModel, RobertaTokenizer

from preprocess import prepare_window

CHECKPOINT_SHA256 = 'fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd'
CHECKPOINT_REVISION = 'b3708341862f581175dba5c356a4ebf74a9b6651'
ROBERTA_REVISION = 'e2da8e2f811d1448a5b465c236feacd80ffbac7b'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def create_pinned_model():
    # SDK hard-codes roberta-base. Scope the revision override to construction only.
    original_model = RobertaModel.from_pretrained
    original_tokenizer = RobertaTokenizer.from_pretrained

    def pinned(loader):
        def load(name, *args, **kwargs):
            if name != 'roberta-base':
                raise ValueError('Unexpected hidden model dependency: ' + str(name))
            return loader('FacebookAI/roberta-base', *args, revision=ROBERTA_REVISION, **kwargs)
        return load
    with ExitStack() as stack:
        stack.enter_context(patch.object(RobertaModel, 'from_pretrained', side_effect=pinned(original_model)))
        stack.enter_context(patch.object(RobertaTokenizer, 'from_pretrained', side_effect=pinned(original_tokenizer)))
        return laion_clap.CLAP_Module(enable_fusion=False, amodel='HTSAT-base', device='cpu')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError('Refusing to overwrite an existing run report')
    actual_hash = sha256(args.checkpoint)
    if actual_hash != CHECKPOINT_SHA256:
        raise ValueError('Checkpoint SHA256 mismatch; no deserialization attempted')
    np.random.seed(0)
    torch.manual_seed(0)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    started = time.perf_counter()
    sdk = create_pinned_model()
    # Keep PyTorch's restricted loader, rather than SDK weights_only=False.
    numpy_types = [np.core.multiarray.scalar, np.dtype,
                   type(np.dtype(np.float64)), type(np.dtype(np.float32))]
    with torch.serialization.safe_globals(numpy_types):
        checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=True, mmap=True)
    state = checkpoint.get('state_dict', checkpoint)
    state = {key.removeprefix('module.'): value for key, value in state.items()}
    # Transformers >=4.31 no longer persists this nonlearned position-ID buffer.
    removed_position_ids = state.pop('text_branch.embeddings.position_ids', None) is not None
    loaded = sdk.model.load_state_dict(state, strict=True)
    del checkpoint, state
    sdk.model.eval()
    load_ms = (time.perf_counter() - started) * 1000

    windows, preprocessing = [], []
    for seconds, hz in [(4, 220), (10, 440)]:
        times = np.arange(seconds * 44100, dtype=np.float32) / 44100
        mono = 0.1 * np.sin(2 * np.pi * hz * times)
        stereo = np.column_stack((mono, mono))
        window, info = prepare_window(stereo, 44100)
        windows.append(window)
        preprocessing.append(info)
    audio_input = np.stack(windows)
    texts = ['A sustained low electronic tone.', 'A sustained high electronic tone.']
    with torch.inference_mode():
        start = time.perf_counter()
        audio = sdk.get_audio_embedding_from_data(audio_input, use_tensor=False)
        audio_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        text = sdk.get_text_embedding(texts, use_tensor=False)
        text_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        repeat = sdk.get_audio_embedding_from_data(audio_input, use_tensor=False)
        repeat_ms = (time.perf_counter() - start) * 1000
    if audio.shape != text.shape or audio.shape[0] != 2:
        raise ValueError('Incompatible text/audio embedding shapes')
    for vectors in (audio, text):
        if vectors.dtype != np.float32 or not np.isfinite(vectors).all():
            raise ValueError('Invalid vectors')
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
    np.testing.assert_allclose(audio, repeat, atol=1e-6, rtol=1e-6)
    source = Path(__file__).resolve().parent
    packages = ['laion-clap', 'torch', 'torchaudio', 'torchvision', 'transformers',
                'numpy', 'librosa', 'soundfile', 'soxr']
    sdk_root = Path(laion_clap.__file__).parent
    report = {
        'status': 'passed_feasibility_only',
        'code_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip(),
        'source_hashes': {name: sha256(source / name) for name in ['probe.py', 'preprocess.py']},
        'sdk_source_hashes': {name: sha256(sdk_root / name) for name in [
            'hook.py', 'training/data.py', 'clap_module/model.py', 'clap_module/model_configs/HTSAT-base.json']},
        'checkpoint': {'repo': 'lukewys/laion_clap', 'revision': CHECKPOINT_REVISION,
                       'filename': args.checkpoint.name, 'sha256': actual_hash,
                       'bytes': args.checkpoint.stat().st_size},
        'roberta_revision': ROBERTA_REVISION,
        'model': {'audio_architecture': 'HTSAT-base', 'fusion': False,
                  'config': sdk.model_cfg, 'strict_load_missing': loaded.missing_keys,
                  'strict_load_unexpected': loaded.unexpected_keys,
                  'removed_nonlearned_position_ids': removed_position_ids},
        'environment': {'python': platform.python_version(), 'os': platform.system(),
                        'machine': platform.machine(), 'device': 'cpu', 'threads': 2,
                        'packages': {name: version(name) for name in packages}},
        'preprocessing': {'source': 'synthetic stereo sine waves, 44100 Hz',
                          'downmix': 'arithmetic mean', 'resampler': 'soxr_hq',
                          'short_window_padding': 'right zeros before SDK',
                          'sdk_quantization': 'clip [-1,1], float32 -> int16 -> float32',
                          'windows': preprocessing},
        'outputs': {'audio_shape': list(audio.shape), 'text_shape': list(text.shape),
                    'dtype': str(audio.dtype), 'audio_norms': np.linalg.norm(audio, axis=1).tolist(),
                    'text_norms': np.linalg.norm(text, axis=1).tolist(),
                    'repeat_max_abs_difference': float(np.max(np.abs(audio - repeat)))},
        'single_run_timings_ms': {'load_with_backbone_cache': load_ms,
                                  'audio_batch_two_first': audio_ms, 'text_batch_two': text_ms,
                                  'audio_batch_two_repeat': repeat_ms},
        'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'limits': ['Synthetic inputs only; no music retrieval accuracy or localization judgment.',
                   'Single process timings are not P95, concurrency, or end-to-end API latency.',
                   'No MP3/FFmpeg decoding test; generated waveform preprocessing only.',
                   'discovery-v0 is not frozen; no index or online service was built.'],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'outputs': report['outputs']}, indent=2))


if __name__ == '__main__':
    main()
