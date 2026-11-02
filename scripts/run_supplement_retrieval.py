#!/usr/bin/env python3
"""Immutable fulltext feature build, then CPU-only fixed two-model development comparison."""
from pathlib import Path
import argparse
import json
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '2'
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import numpy as np
import holdout_contract as h
import supplement_features as supplement
import device_feature_cache as features
import device_calibration as calibration
import long_caption_features as fulltext
import expanded_caption_metrics as metrics
from tag_adapter import unit
from train_tag_adapter import save_npz
from train_positive_score import numpy_runtime

SOURCES = ('scripts/run_supplement_retrieval.py', 'services/audio-search/supplement_features.py',
           'services/audio-search/device_feature_cache.py', 'services/audio-search/device_calibration.py',
           'services/audio-search/long_caption_features.py', 'services/audio-search/checkpoint_model.py',
           'services/audio-search/probe.py', 'services/audio-search/research_corpus.py',
           'services/audio-search/preprocess.py', 'services/audio-search/source_review_pack.py',
           'services/audio-search/tag_adapter.py', 'services/audio-search/expanded_caption_metrics.py',
           'services/audio-search/human_caption_capacity.py', 'services/audio-search/mtg_dataset.py',
           'services/audio-search/mtg_plan.py', 'services/audio-search/holdout_contract.py',
           'services/audio-search/review_pack.py', 'scripts/holdout_assets.py',
           'scripts/calibrate_encoder_device.py', 'scripts/preflight_caption_pairs.py',
           'scripts/train_tag_adapter.py', 'scripts/train_positive_score.py')


def initialize(config, config_sha256, output, stage):
    c = h.assets.document(config, config_sha256); supplement.validate(c)
    task = ROOT/c['task_directory']
    h.require(stage in ('encode', 'evaluate') and Path(output).absolute().is_relative_to(task.absolute())
              and not (task/(stage+'-started.json')).exists(), 'Stage already attempted or invalid output; no new-directory retry')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed comparison required')
    target = h.private_output(output)
    docs = {}; bound = {str(Path(config).absolute()): config_sha256}
    for key, pin in c['inputs'].items():
        path = ROOT/pin['path']; bound[str(path.absolute())] = pin['sha256']
        if path.suffix == '.json': docs[key] = h.assets.document(path, pin['sha256'])
    old = docs['old_cache']; olddir = (ROOT/c['inputs']['old_cache']['path']).parent
    bound[str(olddir/'features.npz')] = old['feature_sha256']
    bound[str(olddir/'result.json')] = old['parity_report_sha256']
    for name, pin in old['key_context']['source_sha256'].items(): h.require(h.file_hash(ROOT/name) == pin, 'Original feature source changed')
    for row in docs['corpus']['tracks']:
        bound[str(Path(row['audio_path']).absolute())] = row['audio_sha256']
        bound[str(Path(row['receipt_path']).absolute())] = row['receipt_sha256']
    sdd = docs['source_inputs']['files']['sdd']; bound[str((ROOT/sdd['path']).absolute())] = sdd['sha256']
    h.require(docs['preflight_verification']['catalog_sha256'] == c['inputs']['corpus']['sha256']
              and docs['corpus']['summary']['audio_ready_for_feature_build'] is True,
              'Published complete six-source audio preflight required')
    h.require(docs['plan']['future_comparison'] == docs['plan_config']['future_comparison']
              and docs['plan']['future_comparison']['models'] == c['models']
              and docs['plan']['future_comparison']['primary'] == c['primary_metric'], 'Frozen062 comparison changed')
    state = {'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'source_sha256': {n: h.file_hash(ROOT/n) for n in SOURCES}, 'input_sha256': bound,
             'config_sha256': config_sha256, 'created_at_utc': h.now()}
    recheck(state)
    return c, target, docs, state


def recheck(state):
    for path, pin in state['input_sha256'].items(): h.require(h.file_hash(path) == pin, 'Bound input changed')
    for path, pin in state['source_sha256'].items(): h.require(h.file_hash(ROOT/path) == pin, 'Comparison source changed')


def claim(c, state, target, stage):
    h.write_json(ROOT/c['task_directory']/(stage+'-started.json'), {'started_at_utc': h.now(),
                 'source_sha': state['source_sha'], 'config_sha256': state['config_sha256'],
                 'output': str(target), 'maximum_attempts': 1, 'fits': 0})


def build(config, config_sha256, output):
    c, target, docs, state = initialize(config, config_sha256, output, 'encode'); started = time.perf_counter()
    try:
        oldpin = c['inputs']['old_cache']
        features.ready_view(ROOT/oldpin['path'], oldpin['sha256'], expected_device='mps',
                            expected_model_sha256=c['expected_model_sha256'], view='caption_retrieval')
        h.require([r['source_track_id'] for r in docs['corpus']['tracks']] == [r['source_track_id'] for r in docs['plan']['selected']],
                  'Original six sources/order required')
        rows = supplement.new_rows(docs['corpus'])
        environment = h.environment(); environment['device'] = 'mps'
        h.require(environment == docs['device_freeze']['environment'] == docs['old_cache']['key_context']['environment'],
                  'Calibrated MPS encoder environment changed')
        model = docs['model_cache']['model']
        h.require(model['sha256'] == c['expected_model_sha256'] and h.checkpoint_pin(model['path'], 'A') == model,
                  'Original frozen A checkpoint required')
        state['input_sha256'][model['path']] = model['sha256']
        context = {'device': 'mps', 'environment': environment, 'model_sha256': model['sha256'],
                   'input_sha256': h.digest(h.canonical(state['input_sha256'])), 'recipe_sha256': config_sha256,
                   'source_sha256': state['source_sha256']}
        key = calibration.cache_key(**context)
        h.write_json(target/'freeze.json', {**state, 'key_context': context, 'cache_key_sha256': key,
                     'new_rows': rows, 'CPU_control_scope': c['CPU_controls']})
        claim(c, state, target, 'encode')
        sdd = docs['source_inputs']['files']['sdd']
        queries = supplement.queries(h.assets.read(ROOT/sdd['path']), docs['plan']['selected'])
        texts = [r['text'] for r in queries]; h.write_json(target/'queries-private.json', queries)
        import torch
        from checkpoint_model import load_checkpoint, checked_checkpoint
        from calibrate_encoder_device import setup, synchronize
        from preflight_caption_pairs import decode
        from preprocess import prepare_window
        h.require(torch.backends.mps.is_available() and os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') != '1',
                  'Explicit MPS required; no fallback')
        setup(torch, 'mps'); load_start = time.perf_counter(); sdk, strict = load_checkpoint(model['path'], 'A')
        for parameter in sdk.model.parameters(): parameter.requires_grad_(False)
        load_ms = (time.perf_counter()-load_start)*1000
        h.require(sdk.model.text_branch_type == 'roberta' and sdk.model.text_branch.config.max_position_embeddings >= 258,
                  'RoBERTa256 positional capacity required')
        raw_ids = [sdk.tokenize(t, truncation=False)['input_ids'] for t in texts]
        tokenize = lambda values, length=256: sdk.tokenize(values, padding='max_length', truncation=True,
                                                          max_length=length, return_tensors='pt')
        proof = fulltext.token_proof(tokenize(texts), raw_ids)
        h.write_json(target/'token-proof.json', proof)
        waves = []
        for record, row in zip(docs['corpus']['tracks'], rows):
            audio, info = decode(record['audio_path'])
            h.require(info == record['decode'] and h.digest(audio.astype('<f4', copy=False).tobytes()) == row['pcm_sha256'],
                      'Pinned65536 actual-EOF decoder/PCM differs')
            waves.extend(prepare_window(audio[start:start+480000], 48000)[0] for start in row['window_start_samples'])
        waves = np.stack(waves); save_npz(target/'control-inputs.npz', waves=waves)
        def audio_encode(values):
            return unit(features.matrix(np.concatenate([sdk.get_audio_embedding_from_data(values[i:i+3], use_tensor=False)
                        for i in range(0, len(values), 3)]), (len(values), 512)))
        def text_encode(values, length=256):
            return unit(features.matrix(np.concatenate([sdk.get_text_embedding(values[i:i+6],
                        tokenizer=lambda batch: tokenize(batch, length), use_tensor=False)
                        for i in range(0, len(values), 6)]), (len(values), 512)))
        short = [i for i, ids in enumerate(raw_ids) if len(ids) <= 77]
        with torch.inference_mode():
            start = time.perf_counter(); cpu_windows = audio_encode(waves); cpu_text = text_encode(texts)
            cpu77 = text_encode([texts[i] for i in short], 77) if short else None
            cpu_ms = (time.perf_counter()-start)*1000
            save_npz(target/'cpu-controls.npz', windows=cpu_windows, whole=unit(cpu_windows.reshape(6, 3, 512).mean(axis=1)),
                     text256=cpu_text, short_text77=cpu77 if short else np.empty((0, 512)))
            sdk.model.to(torch.device('mps')); sdk.device = torch.device('mps')
            h.require(all(str(p.device) == 'mps:0' and not p.requires_grad and
                          (not p.is_floating_point() or p.dtype == torch.float32) for p in sdk.model.parameters()),
                      'Frozen FP32 MPS model required')
            audio_encode(waves[:3]); text_encode(texts[:1]); synchronize(torch, 'mps')
            start = time.perf_counter(); new_windows = audio_encode(waves); new_text = text_encode(texts)
            synchronize(torch, 'mps'); mps_ms = (time.perf_counter()-start)*1000
        parity = {'all18_windows': features.vector_parity(cpu_windows, new_windows, c),
                  'all6_whole': features.vector_parity(unit(cpu_windows.reshape(6, 3, 512).mean(axis=1)),
                                                      unit(new_windows.reshape(6, 3, 512).mean(axis=1)), c),
                  'all7_texts256': features.vector_parity(cpu_text, new_text, c),
                  'short_CPU77_to256': features.vector_parity(cpu77, cpu_text[short], c) if short else {'status': 'not_applicable', 'vectors': 0}}
        passed = all(v['status'] in ('passed', 'not_applicable') for v in parity.values())
        olddir = (ROOT/oldpin['path']).parent
        with np.load(olddir/'features.npz', allow_pickle=False) as f:
            merged = supplement.merge(docs['old_cache'], f['retrieval_first120'], f['windows'], f['texts'], rows, new_windows, new_text)
        save_npz(target/'features.npz', **{k: merged[k] for k in ('whole', 'windows', 'old_texts', 'new_texts')})
        recheck(state); checked_checkpoint(model['path'], 'A')
        final = h.environment(); final['device'] = 'mps'; h.require(final == environment, 'Encoder environment changed')
        result = {'status': 'passed' if passed else 'failed', 'source_sha': state['source_sha'], 'config_sha256': config_sha256,
            'cache_key_sha256': key, 'ready_cache_written': passed, 'counts': supplement.COUNTS, 'vector_parity': parity,
            'untruncated_tokens_min': min(map(len, raw_ids)), 'untruncated_tokens_max': max(map(len, raw_ids)),
            'token_length': 256, 'truncated_captions': 0, 'CPU_controls': {'audio_windows': 18, 'whole': 6, 'texts256': 7, 'short_text77': len(short)},
            'reused_exact': {'whole': 140, 'windows': 624, 'texts': 24}, 'strict': strict,
            'operations': c['operations'], 'timing_ms': {'model_load': load_ms, 'CPU_controls': cpu_ms,
            'MPS_audio_and_text': mps_ms, 'total_including_integrity': (time.perf_counter()-started)*1000}}
        h.write_json(target/'result.json', result)
        if passed:
            h.write_json(target/'cache.json', {'schema': 'sonora-six-supplement-feature-cache-v1', 'status': 'ready_after_parity',
                'counts': supplement.COUNTS, 'device': 'mps', 'model_sha256': model['sha256'], 'token_length': 256,
                'key_context': context, 'cache_key_sha256': key, 'old_cache_sha256': oldpin['sha256'], 'rows': merged['rows'],
                'new_query_tracks': [r['track_id'] for r in queries], 'old_query_tracks': docs['old_cache']['query_tracks'],
                'query_text_sha256': [r['text_sha256'] for r in queries], 'token_lengths': list(map(len, raw_ids)),
                'token_proof_sha256': h.file_hash(target/'token-proof.json'), 'feature_sha256': h.file_hash(target/'features.npz'),
                'result_sha256': h.file_hash(target/'result.json')})
        return result
    except Exception as error:
        h.write_json(target/'failure.json', {'error_type': type(error).__name__, 'error': str(error)}); raise


def evaluate(config, config_sha256, output, cache, cache_sha256):
    c, target, docs, state = initialize(config, config_sha256, output, 'evaluate'); started = time.perf_counter()
    try:
        meta = h.assets.document(cache, cache_sha256); directory = Path(cache).parent
        report = h.assets.document(directory/'result.json', meta['result_sha256'])
        h.require(report['source_sha'] == state['source_sha'] and report['config_sha256'] == config_sha256,
                  'Same committed build and evaluation recipe required')
        state['input_sha256'].update({str(Path(cache).absolute()): cache_sha256,
            str((directory/'features.npz').absolute()): meta['feature_sha256'],
            str((directory/'result.json').absolute()): meta['result_sha256'],
            str((directory/'token-proof.json').absolute()): meta['token_proof_sha256']})
        view = supplement.ready_view(cache, cache_sha256, old_cache=ROOT/c['inputs']['old_cache']['path'],
            old_sha256=c['inputs']['old_cache']['sha256'], expected_device='mps', expected_model_sha256=c['expected_model_sha256'])
        runtime = numpy_runtime(); h.require(runtime == docs['saved100_result']['runtime'], 'Original NumPy evaluation runtime changed')
        h.write_json(target/'freeze.json', {**state, 'runtime': runtime, 'supplement_cache_sha256': cache_sha256,
                     'primary_metric': c['primary_metric'], 'models': c['models'], 'new_fits': 0})
        claim(c, state, target, 'evaluate')
        h.write_json(target/'evaluation-open.json', {'opened_at_utc': h.now(), 'feature_sha256': meta['feature_sha256'],
                     'saved100_adapter_sha256': c['inputs']['saved100_adapter']['sha256'], 'new_fits': 0})
        with np.load(ROOT/c['inputs']['saved100_adapter']['path'], allow_pickle=False) as f: w = f['W']
        h.require(w.shape == (512, 512) and np.isfinite(w).all()
                  and docs['saved100_result']['adapter_sha256'] == c['inputs']['saved100_adapter']['sha256'], 'Saved100 identity mismatch')
        results = {name: supplement.evaluate(view, model) for name, model in [('identity', np.eye(512)), ('saved100-fulltext-ridge', w)]}
        for name, original in [('identity', 'identity'), ('saved100-fulltext-ridge', 'expanded100-fulltext-ridge')]:
            for mode in c['retrieval_modes']:
                h.require(results[name]['old20_original140'][mode] == docs['saved100_result']['results'][original]['human_development']['expanded140'][mode],
                          'Original140 known-pair control did not reproduce')
        deltas = {pool: {mode: metrics.deltas(results['saved100-fulltext-ridge'][pool][mode], results['identity'][pool][mode],
                       c['bootstrap_iterations'], c['bootstrap_seed']) for mode in c['retrieval_modes']} for pool in c['query_pools']}
        recheck(state)
        h.require(numpy_runtime() == runtime and 'torch' not in sys.modules and 'laion_clap' not in sys.modules,
                  'Evaluation must remain fixed-feature CPU NumPy only')
        result = {'status': 'fixed_two_model_supplement_comparison_complete', 'source_sha': state['source_sha'],
            'config_sha256': config_sha256, 'supplement_cache_sha256': cache_sha256, 'counts': supplement.COUNTS,
            'runtime': runtime, 'results': results, 'paired_deltas': deltas, 'original140_controls_reproduced': True,
            'operations': c['operations'], 'decision': c['decision'], 'torch_or_CLAP_imported': False,
            'total_ms': (time.perf_counter()-started)*1000,
            'limits': ['Six source components/7 existing human captions, small development supplement, not formal significance or final test.',
                       'Only known paired recording is judged; other tracks are semantically unjudged.',
                       'Old20 is repeatedly seen development; report146 control separately.',
                       'No new fit, parameter selection, corpus replacement or automatic model switch.']}
        h.write_json(target/'result-private.json', result)
        public = json.loads(json.dumps(result))
        for model in public['results'].values():
            for pool in model.values():
                for values in pool.values(): values.pop('per_recording')
        h.write_json(target/'result-public.json', public)
        return public
    except Exception as error:
        h.write_json(target/'failure.json', {'error_type': type(error).__name__, 'error': str(error)}); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('stage', choices=['build', 'evaluate'])
    for name in ('config', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--config-sha256', required=True); parser.add_argument('--cache', type=Path); parser.add_argument('--cache-sha256')
    args = vars(parser.parse_args()); stage = args.pop('stage')
    if stage == 'build': args.pop('cache'); args.pop('cache_sha256')
    result = (build if stage == 'build' else evaluate)(**args)
    print(json.dumps(result))
    if result['status'] == 'failed': raise SystemExit(1)


if __name__ == '__main__': main()
