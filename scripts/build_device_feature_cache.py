#!/usr/bin/env python3
"""Rebuild existing140 frozen-CLAP features on a calibrated device, preserving typed views."""
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
import tag_adapter as a
import device_calibration as calibration
import device_feature_cache as cachetools
import expanded_caption_metrics as metrics
from calibrate_encoder_device import inventory, setup, synchronize
from train_tag_adapter import save_npz

SOURCES = ('scripts/build_device_feature_cache.py', 'services/audio-search/device_feature_cache.py',
           'scripts/calibrate_encoder_device.py', 'services/audio-search/device_calibration.py',
           'services/audio-search/checkpoint_model.py', 'services/audio-search/probe.py',
           'services/audio-search/research_corpus.py', 'services/audio-search/preprocess.py',
           'services/audio-search/tag_adapter.py', 'services/audio-search/expanded_caption_metrics.py',
           'scripts/train_tag_adapter.py')


def compare_retrieval(cpu_whole, cpu_windows, gpu_whole, gpu_windows, cpu_text, gpu_text,
                      cpu_positions, gpu_positions, rows, query_tracks, models, cfg):
    import numpy as np
    ids = [r['source_track_id'] for r in rows]; result = {}
    for pool in ('dev20', 'expanded140'):
        ix = [i for i, r in enumerate(rows) if pool == 'expanded140' or r['split'] == 'caption_dev']
        candidate_ids = [ids[i] for i in ix]; result[pool] = {}
        for name, w in models.items():
            result[pool][name] = {}
            for mode in ('whole', 'segment'):
                def scores(whole, windows, text, positions):
                    if mode == 'whole': return text @ a.unit(whole[ix]@w).T
                    return np.stack([np.max(text@a.unit(windows[positions[i]]@w).T, axis=1) for i in ix], axis=1)
                c, g = scores(cpu_whole, cpu_windows, cpu_text, cpu_positions), scores(gpu_whole, gpu_windows, gpu_text, gpu_positions)
                numerical = cachetools.score_parity(c, g, cfg)
                cm = metrics.paired(c, query_tracks, candidate_ids)['recording_macro']
                gm = metrics.paired(g, query_tracks, candidate_ids)['recording_macro']
                same = all(abs(cm[k]-gm[k]) <= cfg['metric_atol'] for k in metrics.METRICS)
                result[pool][name][mode] = {**numerical, 'recording_macro_CPU': cm, 'recording_macro_device': gm,
                                             'macro_metrics_unchanged': same,
                                             'status': 'passed' if numerical['status'] == 'passed' and same else 'failed'}
    return result


def run(*, config, config_sha256, output):
    import numpy as np
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-bounded-device-feature-cache-v1' and cfg['device'] == 'mps'
              and cfg['counts'] == {'train': 100, 'validation': 20, 'caption_dev': 20, 'caption_queries': 24, 'prototypes': 183}
              and cfg['fit_runs'] == cfg['new_downloads'] == cfg['test_inputs'] == 0, 'Fixed bounded no-fit cache config required')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean committed builder required')
    target = h.private_output(output); started = time.perf_counter()
    try:
        hardware = inventory(); decision = calibration.device_status(cfg['device'], hardware, mps_fallback=os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1')
        if decision['status'] != 'ready':
            result = {**decision, 'model_loads': 0, 'encodes': 0}; h.write_json(target/'result.json', result); return result
        doc = lambda key: h.assets.document(ROOT/cfg[key]['path'], cfg[key]['sha256'])
        corpus, dataset, old, ref, prior, preflight, prefreeze = (doc(k) for k in ('corpus', 'dataset', 'legacy_cache', 'retrieval_cache', 'prior_result', 'preflight', 'preflight_freeze'))
        h.require(preflight['status'] == 'passed' and preflight['device'] == cfg['device']
                  and preflight['cache_key_sha256'] == prefreeze['cache_key_sha256'], 'Matching successful device calibration required')
        original, _ = h.checked_freeze(ROOT/cfg['original_freeze']['path'], cfg['original_freeze']['sha256'], verify_environment=True)
        environment = h.environment(); environment['device'] = cfg['device']
        h.require(environment == prefreeze['environment'] and old['model'] == original['models']['A']['pin'], 'Calibrated environment or model changed')
        for files in (old['source_sha256'], prefreeze['source']['files']):
            for n, digest in files.items(): h.require(h.file_hash(ROOT/n) == digest, 'Prior calibrated source changed')
        bound = {str(Path(config).absolute()): config_sha256}
        for key in ('corpus', 'dataset', 'legacy_cache', 'retrieval_cache', 'prior_result', 'preflight', 'preflight_freeze', 'original_freeze'):
            bound[str((ROOT/cfg[key]['path']).absolute())] = cfg[key]['sha256']
        legacy_path = (ROOT/cfg['legacy_cache']['path']).parent/'features.npz'
        retrieval_path = (ROOT/cfg['retrieval_cache']['path']).parent/'features.npz'
        bound[str(legacy_path)] = old['feature_sha256']; bound[str(retrieval_path)] = ref['feature_sha256']
        for path, digest in bound.items(): h.require(h.file_hash(path) == digest, 'Bound cache context changed')
        with np.load(legacy_path, allow_pickle=False) as f: cpu_old, cpu_old_windows, cpu_p, cpu_t = (f[k] for k in ('whole', 'windows', 'prototypes', 'texts'))
        with np.load(retrieval_path, allow_pickle=False) as f: cpu_r, cpu_r_windows = f['whole'], f['windows']
        rows = ref['rows']; h.require(len(rows) == 140 and [r['source_track_id'] for r in rows] == sorted({r['source_track_id'] for r in rows}), 'Fixed sorted140 IDs required')
        oldby = {r['source_track_id']: i for i, r in enumerate(old['rows'])}; proofs = {r['source_track_id']: r for r in corpus['tracks']}
        h.require(len(oldby) == len(proofs) == 140 and set(oldby) == set(proofs) == {r['source_track_id'] for r in rows}, 'CPU/corpus source identity set differs')
        lookup = {r['source_track_id']: r for r in dataset['selected']['caption_dev']}
        queries = [q['text'] for row in old['rows'] if row['split'] == 'caption_dev' for q in lookup[row['source_track_id']]['captions']]
        h.require(len(queries) == 24 and [h.digest(q.encode()) for q in queries] == old['query_text_sha256']
                  and ref['query_tracks'] == old['query_tracks'], 'Original dev query order/text differs')
        prompts = ['Music tagged with '+tag.replace('---', ': ', 1)+'.' for tag in old['vocabulary']]
        h.require(len(prompts) == 183, 'Original vocabulary required')
        models = {'identity': np.eye(512)}
        for name, digest in prior['adapter_artifact_sha256'].items():
            path = (ROOT/cfg['prior_result']['path']).parent/(name+'.npz'); bound[str(path)] = digest
            h.require(h.file_hash(path) == digest, 'Original adapter changed')
            with np.load(path, allow_pickle=False) as f: models[name] = f['W']
        h.require(set(models) == {'identity', 'alpha-0.1', 'alpha-1.0', 'alpha-5.0'}, 'Exactly original three adapters required')
        for row in rows:
            proof = proofs[row['source_track_id']]; legacy = old['rows'][oldby[row['source_track_id']]]
            h.require(row['split'] == proof['split'] == legacy['split'] and row['pcm_sha256'] == legacy['pcm_sha256'] == proof['decode']['pcm_sha256'], 'Split/PCM identity changed')
            for path, digest in [(proof['receipt_path'], proof['receipt_sha256']), (str(Path(proof['receipt_path']).parent/'audio.mp3'), proof['audio_sha256'])]:
                bound[str(Path(path).absolute())] = digest; h.require(h.file_hash(path) == digest, 'Audio/receipt changed')
        sources = {p: h.file_hash(ROOT/p) for p in SOURCES}
        key_context = {'device': cfg['device'], 'environment': environment, 'model_sha256': old['model']['sha256'],
                       'input_sha256': h.digest(h.canonical(bound)), 'recipe_sha256': config_sha256, 'source_sha256': sources}
        key = calibration.cache_key(**key_context)
        h.write_json(target/'freeze.json', {'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                     'source_sha256': sources, 'key_context': key_context, 'cache_key_sha256': key, 'input_sha256': bound, 'created_at_utc': h.now()})
        import torch
        import soundfile as sf
        from checkpoint_model import load_checkpoint, checked_checkpoint
        from research_corpus import decode_source_mono
        from preprocess import prepare_window
        setup(torch, cfg['device']); load_start = time.perf_counter(); sdk, strict = load_checkpoint(old['model']['path'], 'A')
        sdk.model.to(torch.device(cfg['device'])); sdk.device = torch.device(cfg['device'])
        for param in sdk.model.parameters():
            param.requires_grad_(False)
            h.require(str(param.device) == 'mps:0' and (not param.is_floating_point() or param.dtype == torch.float32), 'Frozen FP32 MPS model required')
        synchronize(torch, cfg['device']); load_ms = (time.perf_counter()-load_start)*1000
        unique_windows = []; gpu_r = []; gpu_legacy = []; bindings = []; decode_ms = audio_ms = text_ms = 0.; warm = False
        with torch.inference_mode():
            for number, row in enumerate(rows, 1):
                proof = proofs[row['source_track_id']]; path = Path(proof['receipt_path']).parent/'audio.mp3'; start = time.perf_counter()
                with sf.SoundFile(path) as z:
                    head = {'frames': z.frames, 'sample_rate_hz': z.samplerate, 'channels': z.channels, 'format': z.format, 'duration_ms': z.frames*1000//z.samplerate}
                audio, _ = decode_source_mono(path, head)
                h.require(h.digest(audio.astype('<f4', copy=False).tobytes()) == row['pcm_sha256'], 'Decoded PCM differs')
                decode_ms += (time.perf_counter()-start)*1000
                legacy = old['rows'][oldby[row['source_track_id']]]
                n_first = min(len(audio), 120*48000); n_legacy = len(audio) if row['split'] != 'caption_dev' else n_first
                starts = lambda n: sorted({0, max(0, n-480000)//2, max(0, n-480000)})
                first_starts, legacy_starts = starts(n_first), starts(n_legacy)
                h.require(first_starts == row['window_start_samples'] and legacy_starts == legacy['window_start_samples'], 'Original view positions changed')
                all_starts = sorted(set(first_starts+legacy_starts)); waves = np.stack([prepare_window(audio[i:i+480000], 48000)[0] for i in all_starts])
                if not warm:
                    sdk.get_audio_embedding_from_data(waves[:3], use_tensor=False); sdk.get_text_embedding(prompts[:6], use_tensor=False)
                    synchronize(torch, cfg['device']); warm = True
                synchronize(torch, cfg['device']); start = time.perf_counter()
                encoded = np.concatenate([sdk.get_audio_embedding_from_data(waves[i:i+cfg['audio_batch']], use_tensor=False) for i in range(0, len(waves), cfg['audio_batch'])])
                synchronize(torch, cfg['device']); audio_ms += (time.perf_counter()-start)*1000
                v = a.unit(cachetools.matrix(encoded, (len(all_starts), 512))); offset = len(unique_windows); unique_windows.extend(v)
                first_ix = [offset+all_starts.index(i) for i in first_starts]; legacy_ix = [offset+all_starts.index(i) for i in legacy_starts]
                gpu_r.append(a.unit(v[[all_starts.index(i) for i in first_starts]].mean(axis=0, keepdims=True))[0])
                gpu_legacy.append(a.unit(v[[all_starts.index(i) for i in legacy_starts]].mean(axis=0, keepdims=True))[0])
                bindings.append({**row, 'positive_indices': legacy['positive_indices'], 'retrieval_window_indices': first_ix,
                                 'legacy_window_indices': legacy_ix, 'unique_start_samples': all_starts})
                if number % 10 == 0: print(json.dumps({'encoded_tracks': number, 'total': 140, 'unique_windows_so_far': len(unique_windows)}), flush=True)
            synchronize(torch, cfg['device']); start = time.perf_counter()
            text_encode = lambda values: np.concatenate([sdk.get_text_embedding(values[i:i+cfg['text_batch']], use_tensor=False) for i in range(0, len(values), cfg['text_batch'])])
            p_raw, t_raw = text_encode(prompts), text_encode(queries)
            synchronize(torch, cfg['device']); text_ms = (time.perf_counter()-start)*1000
        p = a.unit(cachetools.matrix(p_raw, (183, 512))); t = a.unit(cachetools.matrix(t_raw, (24, 512)))
        gpu_r = np.stack(gpu_r); gpu_legacy = np.stack(gpu_legacy); windows = np.stack(unique_windows)
        train = [i for i, row in enumerate(rows) if row['split'] == 'train']; val = [i for i, row in enumerate(rows) if row['split'] == 'validation']
        oldorder = [oldby[row['source_track_id']] for row in rows]
        parity = {'retrieval_whole': cachetools.vector_parity(cpu_r, gpu_r, cfg),
                  'legacy_whole': cachetools.vector_parity(cpu_old[oldorder], gpu_legacy, cfg),
                  'prototypes': cachetools.vector_parity(cpu_p, p, cfg), 'dev_texts': cachetools.vector_parity(cpu_t, t, cfg)}
        cpu_first_ix = [row['window_indices'] for row in rows]; gpu_first_ix = [row['retrieval_window_indices'] for row in bindings]
        cpu_legacy_ix = [old['rows'][i]['window_indices'] for i in oldorder]; gpu_legacy_ix = [row['legacy_window_indices'] for row in bindings]
        parity['retrieval_windows'] = cachetools.vector_parity(cpu_r_windows[np.array(cpu_first_ix).ravel()], windows[np.array(gpu_first_ix).ravel()], cfg)
        parity['legacy_windows'] = cachetools.vector_parity(cpu_old_windows[np.array(cpu_legacy_ix).ravel()], windows[np.array(gpu_legacy_ix).ravel()], cfg)
        retrieval = compare_retrieval(cpu_r, cpu_r_windows, gpu_r, windows, cpu_t, t,
                                     cpu_first_ix, gpu_first_ix, rows, old['query_tracks'], models, cfg)
        passed = all(v['status'] == 'passed' for v in parity.values()) and all(v['status'] == 'passed' for pool in retrieval.values() for model in pool.values() for v in model.values())
        save_npz(target/'features.npz', train_fullsong=gpu_legacy[train], validation_fullsong=gpu_legacy[val],
                 retrieval_first120=gpu_r, windows=windows, prototypes=p, texts=t)
        for path, digest in bound.items(): h.require(h.file_hash(path) == digest, 'Bound input changed during build')
        checked_checkpoint(old['model']['path'], 'A')
        final_env = h.environment(); final_env['device'] = cfg['device']
        h.require(final_env == environment and all(h.file_hash(ROOT/n) == digest for n, digest in sources.items()), 'Environment/source changed')
        result = {'schema': 'sonora-device-feature-build-result-v1', 'status': 'passed' if passed else 'failed',
                  'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'device': cfg['device'],
                  'cache_key_sha256': key, 'config_sha256': config_sha256, 'strict': strict,
                  'counts': {'tracks': 140, 'train': len(train), 'validation': len(val), 'caption_dev': 20,
                             'unique_audio_windows': len(windows), 'view_window_references': 780, 'tag_prototypes': 183,
                             'dev_texts': 24, 'test_inputs': 0, 'fit_runs': 0, 'downloads': 0},
                  'vector_parity': parity, 'retrieval_parity': retrieval,
                  'timing_ms': {'model_load': load_ms, 'decode': decode_ms, 'audio_SDK': audio_ms, 'text_SDK': text_ms,
                                'total_including_integrity_and_parity': (time.perf_counter()-started)*1000},
                  'ready_cache_written': passed, 'limits': ['Device parity only, not new model quality/training or P95.', 'No matched full-corpus CPU timing, no full-run speed ratio.']}
        h.write_json(target/'result.json', result)
        if passed:
            views = {}
            for view, (npz_key, recipe, split, count) in cachetools.VIEWS.items():
                views[view] = {'npz_key': npz_key, 'recipe': recipe, 'row_indices': [i for i, row in enumerate(rows) if split is None or row['split'] == split]}
            meta = {'schema': 'sonora-typed-device-feature-cache-v1', 'status': 'ready_after_parity', 'device': cfg['device'],
                    'model_sha256': old['model']['sha256'], 'key_context': key_context, 'cache_key_sha256': key,
                    'feature_sha256': h.file_hash(target/'features.npz'), 'parity_report_sha256': h.file_hash(target/'result.json'),
                    'views': views, 'rows': bindings, 'query_tracks': old['query_tracks'],
                    'query_text_sha256': old['query_text_sha256'], 'vocabulary': old['vocabulary']}
            h.write_json(target/'cache.json', meta)
        return result
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    p = argparse.ArgumentParser(); p.add_argument('--config', type=Path, required=True)
    p.add_argument('--config-sha256', required=True); p.add_argument('--output', type=Path, required=True)
    r = run(**vars(p.parse_args())); print(json.dumps({'status': r['status'], 'counts': r.get('counts'), 'ready_cache_written': r.get('ready_cache_written')}))
    if r['status'] != 'passed': raise SystemExit(2 if r['status'] == 'blocked' else 1)


if __name__ == '__main__': main()
