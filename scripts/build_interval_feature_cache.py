#!/usr/bin/env python3
"""One immutable, offline MPS feature build for the fixed MUS-052 interval subset."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import holdout_contract as h
import interval_feature_cache as intervals
import device_calibration as calibration
from device_feature_cache import matrix, vector_parity
from tag_adapter import unit
from calibrate_encoder_device import setup, synchronize
from train_tag_adapter import save_npz

SOURCES = ('scripts/build_interval_feature_cache.py', 'services/audio-search/interval_feature_cache.py',
           'services/audio-search/holdout_contract.py', 'scripts/holdout_assets.py',
           'services/audio-search/device_feature_cache.py', 'services/audio-search/device_calibration.py',
           'scripts/calibrate_encoder_device.py', 'services/audio-search/checkpoint_model.py',
           'services/audio-search/probe.py', 'services/audio-search/research_corpus.py',
           'services/audio-search/preprocess.py', 'services/audio-search/tag_adapter.py',
           'services/audio-search/review_pack.py', 'scripts/train_tag_adapter.py')
INPUTS = ('corpus', 'legacy_cache', 'preflight', 'preflight_freeze', 'original_freeze',
          'candidates', 'allowlist', 'pair_result')


def validate_config(cfg):
    h.require(cfg['schema'] == 'sonora-interval-feature-config-v1' and cfg['device'] == 'mps'
              and cfg['counts'] == intervals.COUNTS and cfg['sample_rate_hz'] == intervals.RATE
              and cfg['dimension'] == 512 and cfg['window_samples'] == intervals.WINDOW
              and cfg['interval_duration_seconds'] == [15, 30] and cfg['window_recipe'] == intervals.RECIPE
              and cfg['weight_recipe'] == 'each_split_recording_equal_then_each_recording_interval_equal'
              and cfg['text_policy'] == 'exact_raw_caption_CLAP77tokens_truncate_report_not_filter'
              and cfg['dtype'] == 'float32' and cfg['autocast'] is False and cfg['automatic_fallback'] is False
              and cfg['audio_batch'] == 3 and cfg['text_batch'] == 6
              and cfg['cpu_controls'] == {'count': 3, 'seed': 'MUS-053-fixed-train-controls-v1',
                                          'selection': 'hash interval, distinct train creator components, no score selection'}
              and cfg['atol_vector_maxabs'] == cfg['atol_cosine_distance'] == 1e-4
              and cfg['fit_runs'] == cfg['new_downloads'] == cfg['test_inputs'] == 0
              and cfg['selection_or_deployment'] is False, 'Fixed bounded no-fit interval configuration required')


def run(*, config, config_sha256, output):
    import numpy as np
    cfg = h.assets.document(config, config_sha256); validate_config(cfg)
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean committed builder required')
    target = h.private_output(output); started = time.perf_counter()
    try:
        docs = {k: h.assets.document(ROOT/cfg[k]['path'], cfg[k]['sha256']) for k in INPUTS}
        old, preflight, prefreeze, original = (docs[k] for k in ('legacy_cache', 'preflight', 'preflight_freeze', 'original_freeze'))
        h.require(preflight['status'] == 'passed' and preflight['device'] == 'mps'
                  and preflight['cache_key_sha256'] == prefreeze['cache_key_sha256'], 'Successful MPS calibration required')
        pair = docs['pair_result']
        h.require(pair['schema'] == 'sonora-caption-pair-preflight-result-v1' and pair['metadata_complete'] is True
                  and pair['reference_preflight_passed'] is True and pair['reference_statuses'] == {'passed': 3}
                  and pair['eligible_recordings'] == 44 and pair['eligible_intervals'] == 232
                  and pair['training_ready'] is False, 'Successful bounded pair preflight required')
        environment = h.environment(); environment['device'] = 'mps'
        h.require(environment == prefreeze['environment'] and old['model'] == original['models']['A']['pin'], 'Calibrated environment/model changed')
        for files in (prefreeze['source']['files'], original['source']['source_sha256'], old['source_sha256']):
            for n, digest in files.items(): h.require(h.file_hash(ROOT/n) == digest, 'Frozen prior source changed')
        h.require(h.checkpoint_pin(old['model']['path'], 'A') == old['model'], 'Checkpoint changed')
        rows, captions, unique, proofs, counts = intervals.plan(docs['candidates'], docs['allowlist'], docs['corpus'])
        controls = intervals.control_indices(rows, cfg['cpu_controls']['seed'])
        control_windows = [i for j in controls for i in rows[j]['window_indices']]
        bound = {str(Path(config).absolute()): config_sha256}
        bound.update({str((ROOT/cfg[k]['path']).absolute()): cfg[k]['sha256'] for k in INPUTS})
        for tid in {r['id'] for r in rows}:
            proof = proofs[tid]
            for path, digest in [(Path(proof['receipt_path']), proof['receipt_sha256']),
                                 (Path(proof['receipt_path']).parent/'audio.mp3', proof['audio_sha256'])]:
                bound[str(path.absolute())] = digest
        for path, digest in bound.items(): h.require(h.file_hash(path) == digest, 'Bound input changed')
        source = {n: h.file_hash(ROOT/n) for n in SOURCES}
        context = {'device': 'mps', 'environment': environment, 'model_sha256': old['model']['sha256'],
                   'input_sha256': h.digest(h.canonical(bound)), 'recipe_sha256': config_sha256, 'source_sha256': source}
        key = calibration.cache_key(**context)
        state = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        h.write_json(target/'freeze.json', {'source_sha': state, 'key_context': context, 'cache_key_sha256': key,
                     'input_sha256': bound, 'control_indices': controls, 'rows_sha256': h.digest(h.canonical(rows)), 'created_at_utc': h.now()})
        # Freeze precedes any torch/SDK import, device probing, decode, or checkpoint load.
        import torch
        import soundfile as sf
        from checkpoint_model import load_checkpoint, checked_checkpoint
        from research_corpus import decode_source_mono
        from preprocess import prepare_window
        decision = calibration.device_status('mps', {'torch_available': True, 'mps_available': torch.backends.mps.is_available()},
                                             mps_fallback=os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1')
        if decision['status'] != 'ready':
            result = {**decision, 'model_loads': 0, 'encodes': 0}; h.write_json(target/'result.json', result); return result
        setup(torch, 'mps')
        decode_ms = 0.; decoded = set()

        def waves_for(tid, indices):
            nonlocal decode_ms
            start = time.perf_counter(); proof = proofs[tid]; path = Path(proof['receipt_path']).parent/'audio.mp3'
            with sf.SoundFile(path) as z:
                head = {'frames': z.frames, 'sample_rate_hz': z.samplerate, 'channels': z.channels,
                        'format': z.format, 'duration_ms': z.frames*1000//z.samplerate}
            audio, info = decode_source_mono(path, head)
            h.require(info['decoded_samples'] == proof['decode']['decoded_samples']
                      and h.digest(audio.astype('<f4', copy=False).tobytes()) == proof['decode']['pcm_sha256'], 'Actual EOF/PCM changed')
            decoded.add(tid)
            waves = np.stack([prepare_window(audio[unique[i]['start_sample']:unique[i]['start_sample']+intervals.WINDOW], intervals.RATE)[0] for i in indices])
            h.require(waves.shape == (len(indices), intervals.WINDOW) and np.isfinite(waves).all(), 'Exact interval windows required')
            decode_ms += (time.perf_counter()-start)*1000
            return waves

        control_waves = np.concatenate([waves_for(rows[j]['id'], rows[j]['window_indices']) for j in controls])
        save_npz(target/'control-inputs.npz', waves=control_waves)
        load_start = time.perf_counter(); sdk, strict = load_checkpoint(old['model']['path'], 'A')
        for param in sdk.model.parameters(): param.requires_grad_(False)
        load_ms = (time.perf_counter()-load_start)*1000
        lengths = [len(sdk.tokenize(t, truncation=False)['input_ids']) for t in captions]
        tokens = intervals.token_summary(lengths)

        def audio_encode(waves):
            raw = np.concatenate([sdk.get_audio_embedding_from_data(waves[i:i+cfg['audio_batch']], use_tensor=False)
                                  for i in range(0, len(waves), cfg['audio_batch'])])
            return unit(matrix(raw, (len(waves), 512)))

        def text_encode(texts):
            raw = np.concatenate([sdk.get_text_embedding(texts[i:i+cfg['text_batch']], use_tensor=False)
                                  for i in range(0, len(texts), cfg['text_batch'])])
            return unit(matrix(raw, (len(texts), 512)))

        with torch.inference_mode():
            start = time.perf_counter(); cpu_windows = audio_encode(control_waves); cpu_text = text_encode([captions[j] for j in controls])
            cpu_ms = (time.perf_counter()-start)*1000
            cpu_audio = unit(cpu_windows.reshape(3, 3, 512).mean(axis=1))
            save_npz(target/'cpu-controls.npz', windows=cpu_windows, audio=cpu_audio, text=cpu_text)
            sdk.model.to(torch.device('mps')); sdk.device = torch.device('mps')
            h.require(all(str(p.device) == 'mps:0' and not p.requires_grad and (not p.is_floating_point() or p.dtype == torch.float32)
                          for p in sdk.model.parameters()), 'Frozen FP32 MPS model required')
            # Fixed warmup is excluded from measured SDK calls; no feature/score-based choices.
            audio_encode(control_waves[:3]); text_encode([captions[controls[0]]]); synchronize(torch, 'mps')
            gpu_windows = np.empty((len(unique), 512), dtype=np.float64); audio_ms = 0.
            tids = sorted({r['id'] for r in rows}, key=int)
            for n, tid in enumerate(tids, 1):
                ix = [i for i, w in enumerate(unique) if w['id'] == tid]; waves = waves_for(tid, ix)
                synchronize(torch, 'mps'); start = time.perf_counter(); gpu_windows[ix] = audio_encode(waves); synchronize(torch, 'mps')
                audio_ms += (time.perf_counter()-start)*1000
                if n % 5 == 0 or n == len(tids): print(json.dumps({'encoded_recordings': n, 'total': len(tids)}), flush=True)
            synchronize(torch, 'mps'); start = time.perf_counter(); text = text_encode(captions); synchronize(torch, 'mps')
            text_ms = (time.perf_counter()-start)*1000
        audio = unit(np.stack([gpu_windows[r['window_indices']].mean(axis=0) for r in rows]))
        matrix(audio, (232, 512)); matrix(text, (232, 512)); matrix(gpu_windows, (len(unique), 512))
        parity = {'windows': vector_parity(cpu_windows, gpu_windows[control_windows], cfg),
                  'interval_audio': vector_parity(cpu_audio, audio[controls], cfg),
                  'caption_text': vector_parity(cpu_text, text[controls], cfg)}
        passed = all(v['status'] == 'passed' for v in parity.values())
        h.require(decoded == set(tids), 'Complete recording PCM verification required')
        save_npz(target/'features.npz', audio=audio, text=text, windows=gpu_windows, weights=np.array([r['weight'] for r in rows]))
        for path, digest in bound.items(): h.require(h.file_hash(path) == digest, 'Bound input changed during build')
        checked_checkpoint(old['model']['path'], 'A')
        final = h.environment(); final['device'] = 'mps'
        h.require(final == environment and all(h.file_hash(ROOT/n) == digest for n, digest in source.items()), 'Source/environment changed')
        result = {'schema': 'sonora-interval-feature-result-v1', 'status': 'passed' if passed else 'failed',
                  'source_sha': state, 'device': 'mps', 'cache_key_sha256': key, 'config_sha256': config_sha256, 'strict': strict,
                  'counts': {**counts, 'intervals': len(rows), 'unique_audio_windows': len(unique),
                             'window_references': sum(len(r['window_indices']) for r in rows), 'caption_texts': len(captions),
                             'fits': 0, 'downloads': 0, 'test_inputs': 0},
                  'tokenization': tokens, 'CPU_control_intervals': 3, 'vector_parity': parity,
                  'ready_cache_written': passed, 'training_protocol_frozen': False,
                  'timing_ms': {'model_load': load_ms, 'decode_including_control_redecode': decode_ms, 'CPU_control_SDK': cpu_ms,
                                'MPS_audio_SDK': audio_ms, 'MPS_text_SDK': text_ms, 'total_including_integrity': (time.perf_counter()-started)*1000},
                  'limits': ['Generated captions, not human semantic or localization truth.',
                             'CPU parity checked on3 fixed train intervals, not all232.',
                             'Teacher exact cached audio unavailable; MUS052 only3 reference snapshots.',
                             'Three10s windows may overlap; not exhaustive frame encoding.', 'No fit, quality score, deployment or P95.']}
        h.write_json(target/'result.json', result)
        if passed:
            h.write_json(target/'cache.json', {'schema': 'sonora-interval-feature-cache-v1', 'status': 'ready_for_bounded_pilot',
                         'device': 'mps', 'model_sha256': old['model']['sha256'], 'key_context': context, 'cache_key_sha256': key,
                         'recipe': intervals.RECIPE, 'rows': rows, 'unique_windows': unique, 'token_lengths': lengths,
                         'control_indices': controls, 'feature_sha256': h.file_hash(target/'features.npz'), 'result_sha256': h.file_hash(target/'result.json')})
        return result
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    p = argparse.ArgumentParser(); p.add_argument('--config', type=Path, required=True)
    p.add_argument('--config-sha256', required=True); p.add_argument('--output', type=Path, required=True)
    r = run(**vars(p.parse_args())); print(json.dumps({'status': r['status'], 'counts': r.get('counts')}))
    if r['status'] != 'passed': raise SystemExit(2 if r['status'] == 'blocked' else 1)


if __name__ == '__main__': main()
