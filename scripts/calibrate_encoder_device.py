#!/usr/bin/env python3
"""Isolated CPU reference and explicit CPU/MPS/CUDA frozen-CLAP calibration; never rents or downloads."""
from pathlib import Path
import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/audio-search'))
import holdout_contract as h
import device_calibration as calibration
from train_tag_adapter import save_npz

SOURCES = ('scripts/calibrate_encoder_device.py', 'services/audio-search/device_calibration.py',
           'services/audio-search/checkpoint_model.py', 'services/audio-search/probe.py',
           'services/audio-search/preprocess.py', 'services/audio-search/research_corpus.py',
           'services/audio-search/tag_adapter.py', 'scripts/train_tag_adapter.py')


def inventory():
    base = {'system': platform.system(), 'machine': platform.machine()}
    try:
        import torch
    except ImportError:
        return {**base, 'torch_available': False, 'cuda_available': False, 'cuda_count': 0, 'mps_available': False}
    return {**base, 'torch_available': True, 'torch': torch.__version__, 'cuda_build': torch.version.cuda,
            'cuda_available': torch.cuda.is_available(), 'cuda_count': torch.cuda.device_count(),
            'mps_available': bool(hasattr(torch.backends, 'mps') and torch.backends.mps.is_available())}


def sources():
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean committed source required')
    return {'sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'files': {n: h.file_hash(ROOT/n) for n in SOURCES}}



def check_bound_files(bindings):
    """Stream bounded binary bundles; old JSON reader's16MiB ceiling is not a binary limit."""
    for path, expected in bindings.items():
        path = h.assets.regular(path)
        limit = h.PINS['A'][1] if path.suffix == '.pt' else 32*1024*1024 if path.suffix == '.npz' else h.assets.MAX_JSON
        h.require(0 < path.stat().st_size <= limit and h.file_hash(path) == expected, 'Bound calibration file changed')


def setup(torch, device):
    torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    version = tuple(int(x) for x in torch.__version__.split('+')[0].split('.')[:2])
    if version >= (2, 9):
        torch.backends.cuda.matmul.fp32_precision = 'ieee'; torch.backends.cudnn.conv.fp32_precision = 'ieee'
    else:
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    if device == 'cuda:0': torch.cuda.set_device(0)


def synchronize(torch, device):
    if device == 'cuda:0': torch.cuda.synchronize(0)
    elif device == 'mps': torch.mps.synchronize()


def benchmark(sdk, waves, prompts, cfg, torch, device):
    import numpy as np
    def audio():
        return np.concatenate([sdk.get_audio_embedding_from_data(waves[i:i+cfg['batch_audio']], use_tensor=False)
                               for i in range(0, len(waves), cfg['batch_audio'])])
    def text():
        return np.concatenate([sdk.get_text_embedding(prompts[i:i+cfg['batch_text']], use_tensor=False)
                               for i in range(0, len(prompts), cfg['batch_text'])])
    with torch.inference_mode():
        for _ in range(cfg['warmup_repeats']): audio(); text(); synchronize(torch, device)
        if device == 'cuda:0': torch.cuda.reset_peak_memory_stats(0)
        elapsed_a = []; elapsed_t = []; first_a = first_t = None; repeat_delta = 0.
        for _ in range(cfg['timed_repeats']):
            synchronize(torch, device); start = time.perf_counter(); a = audio(); synchronize(torch, device)
            elapsed_a.append((time.perf_counter()-start)*1000)
            start = time.perf_counter(); t = text(); synchronize(torch, device); elapsed_t.append((time.perf_counter()-start)*1000)
            calibration.valid_vectors(a, (cfg['audio_windows'], cfg['dimension']))
            calibration.valid_vectors(t, (cfg['text_prompts'], cfg['dimension']))
            if first_a is None: first_a, first_t = a.copy(), t.copy()
            repeat_delta = max(repeat_delta, float(np.max(np.abs(a-first_a))), float(np.max(np.abs(t-first_t))))
    h.require(repeat_delta <= cfg['atol_vector_maxabs'], 'Device repeated outputs unstable')
    memory = {'cuda_peak_allocated_bytes': int(torch.cuda.max_memory_allocated(0)) if device == 'cuda:0' else None,
              'mps_current_allocated_bytes_after_run': int(torch.mps.current_allocated_memory()) if device == 'mps' else None}
    return first_a, first_t, {'audio_all9_ms': elapsed_a, 'text_all6_ms': elapsed_t,
             'median_audio_ms': statistics.median(elapsed_a), 'median_text_ms': statistics.median(elapsed_t),
             'repeat_max_abs_difference': repeat_delta, **memory,
             'scope': 'warm_SDK_encoding_including_CPU_feature_preparation_and_transfer_no_decode_load_or_training;not_P95'}


def prepare(*, config, config_sha256, output):
    import numpy as np
    import tag_adapter as adapter
    cfg = h.assets.document(config, config_sha256); state = sources(); target = h.private_output(output)
    try:
        h.require(cfg['schema'] == 'sonora-device-calibration-v1' and cfg['audio_tracks'] == 3
                  and cfg['audio_windows'] == 9 and cfg['text_prompts'] == 6, 'Fixed three-track calibration required')
        doc = lambda key: h.assets.document(ROOT/cfg[key]['path'], cfg[key]['sha256'])
        cat, meta, old = (doc(k) for k in ('corpus', 'cache', 'original_cache'))
        original, _ = h.checked_freeze(ROOT/cfg['original_freeze']['path'], cfg['original_freeze']['sha256'], verify_environment=True)
        h.require(old['model'] == original['models']['A']['pin'], 'Original model differs')
        for n, digest in old['source_sha256'].items(): h.require(h.file_hash(ROOT/n) == digest, 'Original feature source changed')
        checked = {str((ROOT/cfg[k]['path']).absolute()): cfg[k]['sha256'] for k in ('corpus', 'cache', 'original_cache', 'original_freeze')}
        feature_path = (ROOT/cfg['cache']['path']).parent/'features.npz'; old_path = (ROOT/cfg['original_cache']['path']).parent/'features.npz'
        checked[str(feature_path)] = meta['feature_sha256']; checked[str(old_path)] = old['feature_sha256']
        checked[str(Path(config).absolute())] = config_sha256
        h.assets.recheck({Path(p): d for p, d in checked.items()})
        rows = sorted((r for r in meta['rows'] if r['split'] == 'train'), key=lambda r: r['source_track_id'])[:3]
        h.require(len(rows) == 3, 'Three train rows required')
        by = {(r['split'], r['source_track_id']): r for r in cat['tracks']}
        import soundfile as sf
        from research_corpus import decode_source_mono
        from preprocess import prepare_window
        waves = []; positions = []; reference_windows = []
        with np.load(feature_path, allow_pickle=False) as f: golden_audio = f['windows']
        with np.load(old_path, allow_pickle=False) as f: golden_text = f['prototypes'][:6]
        for row in rows:
            proof = by[('train', row['source_track_id'])]; receipt = Path(proof['receipt_path'])
            checked[str(receipt)] = proof['receipt_sha256']; checked[str(receipt.parent/'audio.mp3')] = proof['audio_sha256']
            h.assets.recheck({receipt: proof['receipt_sha256'], receipt.parent/'audio.mp3': proof['audio_sha256']})
            with sf.SoundFile(receipt.parent/'audio.mp3') as z:
                head = {'frames': z.frames, 'sample_rate_hz': z.samplerate, 'channels': z.channels,
                        'format': z.format, 'duration_ms': z.frames*1000//z.samplerate}
            audio, _ = decode_source_mono(receipt.parent/'audio.mp3', head)
            h.require(h.digest(audio.astype('<f4', copy=False).tobytes()) == row['pcm_sha256'], 'Source PCM changed')
            audio = audio[:120*48000]; last = len(audio)-480000; starts = sorted({0, last//2, last})
            h.require(starts == row['window_start_samples'] and len(starts) == 3, 'Golden view differs')
            waves.extend(prepare_window(audio[i:i+480000], 48000)[0] for i in starts)
            reference_windows.extend(golden_audio[row['window_indices']]); positions.append({'source_track_id': row['source_track_id'], 'starts': starts})
        prompts = ['Music tagged with '+t.replace('---', ': ', 1)+'.' for t in old['vocabulary'][:6]]
        save_npz(target/'inputs.npz', waves=np.stack(waves).astype(np.float32))
        input_sha = h.file_hash(target/'inputs.npz')
        opening = {'schema': 'sonora-device-calibration-opening-v1', 'created_at_utc': h.now(), 'source': state,
                   'config_sha256': config_sha256, 'input_sha256': input_sha, 'input_bindings': checked,
                   'selected_train_positions': positions, 'model': old['model'], 'environment': original['environment']}
        h.write_json(target/'freeze.json', opening)
        import torch
        from checkpoint_model import load_checkpoint
        setup(torch, 'cpu'); start = time.perf_counter(); sdk, strict = load_checkpoint(old['model']['path'], 'A')
        for p in sdk.model.parameters(): p.requires_grad_(False)
        load_ms = (time.perf_counter()-start)*1000
        vectors_a, vectors_t, timing = benchmark(sdk, np.stack(waves), prompts, cfg, torch, 'cpu')
        control = calibration.compare(np.stack(reference_windows), golden_text, vectors_a, vectors_t, cfg)
        h.require(control['status'] == 'passed', 'CPU reference differs from frozen source features')
        save_npz(target/'reference.npz', audio=vectors_a, text=vectors_t)
        package = {'schema': 'sonora-device-calibration-package-v1', 'source': state, 'config': cfg,
                   'config_sha256': config_sha256, 'input_sha256': input_sha,
                   'reference_sha256': h.file_hash(target/'reference.npz'), 'prompts': prompts,
                   'model_sha256': old['model']['sha256'], 'model_filename': old['model']['filename'],
                   'cpu_environment': original['environment'], 'cpu_timing': timing, 'cpu_load_ms': load_ms,
                   'strict': strict, 'golden_control': control, 'no_caption_or_test_inputs': True}
        package['cache_key_sha256'] = calibration.cache_key(device='cpu', environment=package['cpu_environment'],
                    model_sha256=package['model_sha256'], input_sha256=input_sha, recipe_sha256=config_sha256, source_sha256=state['files'])
        h.assets.recheck({Path(p): d for p, d in checked.items()})
        h.require(all(h.file_hash(ROOT/n) == d for n, d in state['files'].items()) and h.environment() == original['environment'], 'Source/environment changed')
        h.require(h.checkpoint_pin(old['model']['path'], 'A') == old['model'], 'Checkpoint changed')
        h.write_json(target/'package.json', package)
        return {'status': 'passed_cpu_reference', 'counts': {'tracks': 3, 'windows': 9, 'tag_prompts': 6, 'fits': 0, 'test_inputs': 0},
                'package_sha256': h.file_hash(target/'package.json'), 'timing': timing, 'golden_control': control}
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def run(*, package, package_sha256, checkpoint, device, output):
    # Output and availability checks precede input/model deserialization; no silent CPU fallback.
    state = sources(); target = h.private_output(output)
    try:
        hardware = inventory()
        decision = calibration.device_status(device, hardware, mps_fallback=os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1')
        if decision['status'] == 'blocked':
            result = {**decision, 'hardware': hardware, 'model_loads': 0, 'encodes': 0, 'fits': 0}
            h.write_json(target/'result.json', result); return result
        p = h.assets.document(package, package_sha256); cfg = p['config']
        h.require(p['schema'] == 'sonora-device-calibration-package-v1'
                  and h.digest((json.dumps(cfg, indent=2)+'\n').encode()) == p['config_sha256']
                  and p['source']['files'] == state['files'], 'Calibration config/source recipe changed')
        root = Path(package).parent
        inputs = root/'inputs.npz'; reference = root/'reference.npz'
        bound = {Path(package): package_sha256, inputs: p['input_sha256'], reference: p['reference_sha256'], Path(checkpoint): p['model_sha256']}
        check_bound_files(bound)
        from checkpoint_model import checked_checkpoint, load_checkpoint
        checked_checkpoint(checkpoint, 'A')
        h.require(Path(checkpoint).name == p['model_filename'], 'Calibration checkpoint differs')
        env = h.environment(); env['device'] = device
        key = calibration.cache_key(device=device, environment=env, model_sha256=p['model_sha256'],
                    input_sha256=p['input_sha256'], recipe_sha256=p['config_sha256'], source_sha256=state['files'])
        h.require(device == 'cpu' or key != p['cache_key_sha256'], 'GPU must have a separate cache identity')
        h.write_json(target/'freeze.json', {'source': state, 'package_sha256': package_sha256, 'cache_key_sha256': key,
                     'device': device, 'hardware': hardware, 'environment': env, 'created_at_utc': h.now()})
        import torch
        import numpy as np
        setup(torch, device); start = time.perf_counter(); sdk, strict = load_checkpoint(checkpoint, 'A')
        sdk.model.to(torch.device(device)); sdk.device = torch.device(device)
        for param in sdk.model.parameters():
            param.requires_grad_(False)
            h.require(str(param.device) == ('mps:0' if device == 'mps' else device)
                      and (not param.is_floating_point() or param.dtype == torch.float32), 'Model device/dtype differs')
        synchronize(torch, device); load_ms = (time.perf_counter()-start)*1000
        with np.load(inputs, allow_pickle=False) as f: waves = f['waves']
        h.require(waves.shape == (9, 480000) and waves.dtype == np.float32 and np.isfinite(waves).all(), 'Frozen wave shapes/dtype changed')
        with np.load(reference, allow_pickle=False) as f: ra, rt = f['audio'], f['text']
        audio, text, timing = benchmark(sdk, waves, p['prompts'], cfg, torch, device)
        check = calibration.compare(ra, rt, audio, text, cfg)
        save_npz(target/'features.npz', audio=audio, text=text)
        check_bound_files(bound); checked_checkpoint(checkpoint, 'A')
        current_env = h.environment(); current_env['device'] = device
        h.require(current_env == env and all(h.file_hash(ROOT/n) == d for n, d in state['files'].items()), 'Runtime environment/source changed')
        result = {'status': check['status'], 'device': device, 'hardware': hardware, 'source_sha': state['sha'],
                  'cache_key_sha256': key, 'package_sha256': package_sha256, 'strict': strict, 'comparison': check,
                  'timing': timing, 'load_ms': load_ms, 'small_batch_audio_speed_ratio_cpu_over_device': p['cpu_timing']['median_audio_ms']/timing['median_audio_ms'],
                  'model_loads': 1, 'new_fit_runs': 0, 'test_inputs': 0,
                  'limits': ['Device numerical calibration only, not training/model quality or production migration.',
                             'MPS results do not validate CUDA; small warm SDK timing notP95/end-to-end/training speed.']}
        h.write_json(target/'result.json', result); return result
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inventory')
    p = sub.add_parser('prepare')
    for k in ('config', 'output'): p.add_argument('--'+k, type=Path, required=True)
    p.add_argument('--config-sha256', required=True)
    p = sub.add_parser('run')
    for k in ('package', 'checkpoint', 'output'): p.add_argument('--'+k, type=Path, required=True)
    p.add_argument('--package-sha256', required=True); p.add_argument('--device', choices=['cpu', 'mps', 'cuda:0'], required=True)
    args = vars(parser.parse_args()); command = args.pop('command')
    result = inventory() if command == 'inventory' else globals()[command](**args)
    print(json.dumps(result))
    if result.get('status') == 'blocked': raise SystemExit(2)
    if result.get('status') == 'failed': raise SystemExit(1)


if __name__ == '__main__': main()
