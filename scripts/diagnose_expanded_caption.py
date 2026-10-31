#!/usr/bin/env python3
"""Fixed 140-candidate development diagnostic, zero fits and zero downloads."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/audio-search'))
import holdout_contract as h
import tag_adapter as a
import expanded_caption_metrics as metrics
from train_tag_adapter import save_npz

SOURCES = ('scripts/diagnose_expanded_caption.py', 'services/audio-search/expanded_caption_metrics.py',
           'services/audio-search/tag_adapter.py', 'scripts/train_tag_adapter.py',
           'services/audio-search/checkpoint_model.py', 'services/audio-search/research_corpus.py',
           'services/audio-search/preprocess.py')
MODEL_NAMES = ['identity', 'alpha-0.1', 'alpha-1.0', 'alpha-5.0']


def checked_document(entry):
    return h.assets.document(ROOT / entry['path'], entry['sha256'])


def validate_rows(meta, corpus):
    from collections import Counter
    rows = meta['rows']
    h.require(Counter(r['split'] for r in rows) == {'train': 100, 'validation': 20, 'caption_dev': 20}
              and len({r['source_track_id'] for r in rows}) == 140, 'Frozen 140 unique rows required')
    by = {(r['split'], r['source_track_id']): r for r in corpus['tracks']}
    h.require(len(by) == 140, 'Complete corpus required')
    for r in rows:
        key = (r['split'], r['source_track_id'])
        h.require(key in by and by[key]['audio_sha256'] == r['audio_sha256']
                  and by[key]['decode']['pcm_sha256'] == r['pcm_sha256'], 'Row/corpus binding changed')
    dev = {r['source_track_id'] for r in rows if r['split'] == 'caption_dev'}
    h.require(set(meta['query_tracks']) == dev and len(meta['query_tracks']) == 24
              and len(meta['query_text_sha256']) == 24, 'Exactly original20 paired recordings/24 queries required')
    return by


def evaluate(whole, windows, row_windows, texts, ids, splits, query_tracks, models, cfg):
    import numpy as np
    results = {}
    for name, w in models.items():
        mapped = a.unit(whole @ w)
        for pool, positions in [('dev20', [i for i, s in enumerate(splits) if s == 'caption_dev']),
                                ('expanded140', list(range(len(ids))))]:
            candidate_ids = [ids[i] for i in positions]
            scores = texts @ mapped[positions].T
            segment = np.stack([np.max(texts @ a.unit(windows[row_windows[i]] @ w).T, axis=1)
                                for i in positions], axis=1)
            results.setdefault(pool, {})[name] = {'whole': metrics.paired(scores, query_tracks, candidate_ids),
                                                 'segment': metrics.paired(segment, query_tracks, candidate_ids)}
    differences = {pool: {name: {mode: metrics.deltas(value[mode], candidates['identity'][mode],
                        cfg['bootstrap_iterations'], cfg['bootstrap_seed']) for mode in ('whole', 'segment')}
                        for name, value in candidates.items() if name != 'identity'}
                   for pool, candidates in results.items()}
    return results, differences


def run(*, config, config_sha256, output):
    import numpy as np
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-expanded-caption-diagnostic-v1'
              and cfg['candidate_models'] == MODEL_NAMES and cfg['candidate_tracks'] == 140
              and cfg['paired_recordings'] == 20 and cfg['caption_queries'] == 24
              and cfg['test_model_inputs'] == cfg['new_fit_runs'] == cfg['new_audio_downloads'] == 0,
              'Fixed diagnostic-only protocol required')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(),
              'Committed clean diagnostic source required')
    # Exclusive output fails before environment/model inspection, loading or inference on repeat.
    target = h.private_output(output)
    try:
        bound = {str(Path(config).absolute()): config_sha256}
        for key in ('cache', 'corpus', 'prior_result', 'original_freeze'):
            entry = cfg[key]; bound[str((ROOT / entry['path']).absolute())] = entry['sha256']
        meta, corpus, prior = (checked_document(cfg[k]) for k in ('cache', 'corpus', 'prior_result'))
        h.require(prior['cache_sha256'] == cfg['cache']['sha256'] and prior['selected'] == 'identity'
                  and prior['feature_sha256'] == meta['feature_sha256']
                  and prior['config_sha256'] == corpus['config_sha256'] == meta['config_sha256']
                  and meta['corpus_sha256'] == cfg['corpus']['sha256'], 'Original gate/cache/corpus context differs')
        by = validate_rows(meta, corpus)
        for name, digest in meta['source_sha256'].items():
            h.require(h.file_hash(ROOT / name) == digest, 'Original feature recipe source changed')
            bound[str((ROOT / name).absolute())] = digest
        features = (ROOT / cfg['cache']['path']).parent / 'features.npz'
        bound[str(features.absolute())] = meta['feature_sha256']
        h.require(h.file_hash(features) == meta['feature_sha256'], 'Original features changed')
        with np.load(h.assets.regular(features), allow_pickle=False) as f:
            oldwhole, oldwindows, prototypes, texts = (f[k] for k in ('whole', 'windows', 'prototypes', 'texts'))
        h.require(oldwhole.shape == (140, 512) and oldwindows.shape == (420, 512)
                  and prototypes.shape == (183, 512) and texts.shape == (24, 512), 'Feature shape mismatch')
        for z in (oldwhole, oldwindows, prototypes, texts): a.unit(z)
        models = {'identity': np.eye(512)}
        for name in MODEL_NAMES[1:]:
            p = ROOT / cfg['adapter_directory'] / (name + '.npz')
            bound[str(p.absolute())] = prior['adapter_artifact_sha256'][name]
            h.require(h.file_hash(p) == bound[str(p.absolute())], 'Original adapter changed')
            with np.load(h.assets.regular(p), allow_pickle=False) as f: w = f['W']
            h.require(w.shape == (512, 512) and np.isfinite(w).all(), 'Invalid adapter matrix')
            models[name] = w
        for proof in corpus['tracks']:
            p = h.assets.regular(proof['receipt_path'])
            bound[str(p)] = proof['receipt_sha256']; bound[str(p.parent / 'audio.mp3')] = proof['audio_sha256']
        h.assets.recheck({Path(p): digest for p, digest in bound.items()})
        print(json.dumps({'stage': 'verify_original_environment_and_frozen_inputs'}), flush=True)
        original, _ = h.checked_freeze(ROOT / cfg['original_freeze']['path'], cfg['original_freeze']['sha256'], verify_environment=True)
        h.require(original['models']['A']['pin'] == meta['model'] and original['environment'] == meta['environment'],
                  'Original model/environment cache binding changed')
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        context = {'schema': 'sonora-expanded-caption-freeze-v1', 'created_at_utc': h.now(),
                   'source_sha': source, 'source_sha256': {p: h.file_hash(ROOT / p) for p in SOURCES},
                   'config_sha256': config_sha256, 'input_sha256': bound,
                   'model': meta['model'], 'environment': original['environment'],
                   'candidate_view': cfg['candidate_view'], 'planned_model_loads': 1, 'fit_runs': 0,
                   'new_text_encodes': 0, 'test_inputs': 0}
        h.write_json(target / 'freeze.json', context)
        import torch
        import soundfile as sf
        from checkpoint_model import load_checkpoint
        from research_corpus import decode_source_mono
        from preprocess import prepare_window
        torch.set_num_threads(2); torch.set_num_interop_threads(1)
        torch.manual_seed(0); np.random.seed(0)
        sdk, strict = load_checkpoint(meta['model']['path'], 'A')
        for param in sdk.model.parameters(): param.requires_grad_(False)
        order = sorted(range(len(meta['rows'])), key=lambda i: meta['rows'][i]['source_track_id'])
        whole, windows, row_windows, rows = [], [], [], []
        encoded = reused = 0
        with torch.inference_mode():
            for index in order:
                row = meta['rows'][index]; proof = by[(row['split'], row['source_track_id'])]
                if row['split'] == 'caption_dev':
                    v = oldwindows[row['window_indices']]
                    h.require(row['view_samples'] <= 120 * 48000, 'Original dev view not first120')
                    starts = row['window_start_samples']; n_samples = row['view_samples']; reused += 1
                else:
                    audio_path = Path(proof['receipt_path']).parent / 'audio.mp3'
                    with sf.SoundFile(audio_path) as z:
                        header = {'frames': z.frames, 'sample_rate_hz': z.samplerate, 'channels': z.channels,
                                  'format': z.format, 'duration_ms': z.frames * 1000 // z.samplerate}
                    audio, info = decode_source_mono(audio_path, header)
                    h.require(h.digest(audio.astype('<f4', copy=False).tobytes()) == row['pcm_sha256'], 'PCM changed')
                    audio = audio[:120 * 48000]; n_samples = len(audio)
                    last = max(0, n_samples - 480000); starts = sorted({0, last // 2, last})
                    v = a.unit(sdk.get_audio_embedding_from_data(np.stack([
                        prepare_window(audio[i:i + 480000], 48000)[0] for i in starts]), use_tensor=False)); encoded += 1
                offset = len(windows); windows.extend(v); row_windows.append(list(range(offset, offset + len(v))))
                pooled = a.unit(v.mean(axis=0, keepdims=True))[0]
                if row['split'] == 'caption_dev':
                    h.require(np.array_equal(pooled, oldwhole[index]), 'Reused dev whole changed')
                whole.append(pooled); rows.append({**row, 'window_indices': row_windows[-1],
                                                  'window_start_samples': starts, 'view_samples': n_samples})
                if (encoded + reused) % 10 == 0:
                    print(json.dumps({'ready_candidates': encoded + reused, 'newly_encoded': encoded, 'reused': reused}), flush=True)
        whole, windows = np.stack(whole), np.stack(windows)
        h.require(encoded == 120 and reused == 20 and windows.shape == (420, 512), 'Unexpected view encoding counts')
        save_npz(target / 'features.npz', whole=whole, windows=windows, texts=texts)
        h.write_json(target / 'cache.json', {'source_freeze_sha256': h.file_hash(target / 'freeze.json'),
                     'feature_sha256': h.file_hash(target / 'features.npz'), 'rows': rows,
                     'query_tracks': meta['query_tracks'], 'query_text_sha256': meta['query_text_sha256']})
        ids = [r['source_track_id'] for r in rows]; splits = [r['split'] for r in rows]
        results, differences = evaluate(whole, windows, row_windows, texts, ids, splits, meta['query_tracks'], models, cfg)
        for name in MODEL_NAMES:
            for mode in ('whole', 'segment'):
                for key in metrics.METRICS:
                    h.require(abs(results['dev20'][name][mode]['recording_macro'][key]
                                  - prior['results'][name][mode]['recording_macro'][key]) < 1e-12, 'Original20 control not reproduced')
        train = [i for i, r in enumerate(meta['rows']) if r['split'] == 'train']
        dev = [i for i, r in enumerate(meta['rows']) if r['split'] == 'caption_dev']
        train_y = a.targets(prototypes, [meta['rows'][i]['positive_indices'] for i in train])
        dev_y = a.targets(prototypes, [meta['rows'][i]['positive_indices'] for i in dev])
        geometry = {'train_audio_mean_pair_cosine': metrics.mean_pair_cosine(oldwhole[train]),
                    'train_tag_centroid_mean_pair_cosine': metrics.mean_pair_cosine(train_y),
                    'dev_recording_macro_caption_original_audio_cosine': metrics.paired_cosine_mean(texts, oldwhole[dev], meta['query_tracks'], [meta['rows'][i]['source_track_id'] for i in dev]),
                    'dev_recording_macro_caption_tag_centroid_cosine': metrics.paired_cosine_mean(texts, dev_y, meta['query_tracks'], [meta['rows'][i]['source_track_id'] for i in dev]),
                    'scope': 'aggregate_geometry_not_causal_or_new_training_supervision'}
        h.assets.recheck({Path(p): digest for p, digest in bound.items()})
        h.require(all(h.file_hash(ROOT / p) == digest for p, digest in context['source_sha256'].items()), 'Diagnostic source changed')
        h.require(h.environment() == original['environment'], 'Environment/cache changed during diagnostic')
        h.require(h.checkpoint_pin(meta['model']['path'], 'A') == meta['model'], 'Checkpoint changed during diagnostic')
        result = {'schema': 'sonora-expanded-caption-diagnostic-result-v1', 'status': 'development_diagnostic_complete',
                  'source_sha': source, 'created_at_utc': h.now(), 'config_sha256': config_sha256,
                  'freeze_sha256': h.file_hash(target / 'freeze.json'), 'features_sha256': h.file_hash(target / 'features.npz'),
                  'counts': {'candidate_tracks': 140, 'paired_dev_recordings': 20, 'caption_queries': 24,
                             'newly_encoded_audio': encoded, 'reused_dev_audio': reused, 'new_text_encodes': 0,
                             'new_downloads': 0, 'fit_runs': 0, 'test_inputs': 0},
                  'strict': strict, 'results': results, 'paired_deltas': differences, 'geometry': geometry,
                  'model_decision': 'retain_identity_no_selection_or_scale_up_from_this_diagnostic', 'limits': cfg['limits']}
        h.write_json(target / 'result-private.json', result)
        public = json.loads(json.dumps(result))
        for candidates in public['results'].values():
            for value in candidates.values():
                for mode in ('whole', 'segment'): value[mode].pop('per_recording')
        h.write_json(target / 'result-public.json', public)
        return public
    except Exception as exc:
        h.write_json(target / 'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)})
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--config-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    result = run(**vars(p.parse_args()))
    print(json.dumps({'status': result['status'], 'counts': result['counts'], 'model_decision': result['model_decision']}))


if __name__ == '__main__': main()
