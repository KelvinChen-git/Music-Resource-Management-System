#!/usr/bin/env python3
"""Immutable new fulltext features, then one fixed data-size ridge comparison."""
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
import expanded_pair_features as pairs
import interval_feature_cache as intervals
import long_caption_features as fulltext
import device_calibration as calibration
import device_feature_cache as features
import weighted_caption_adapter as learner
import expanded_caption_metrics as metrics
from tag_adapter import unit
from train_tag_adapter import save_npz
from train_positive_score import numpy_runtime
from train_caption_adapter import human_development, SOURCES as PRIOR_SOURCES

SOURCES = tuple(dict.fromkeys(('scripts/run_expanded_caption_training.py', 'services/audio-search/expanded_pair_features.py',
           'services/audio-search/long_caption_features.py', 'services/audio-search/checkpoint_model.py',
           'services/audio-search/probe.py', 'services/audio-search/research_corpus.py',
           'services/audio-search/preprocess.py', 'scripts/calibrate_encoder_device.py', *PRIOR_SOURCES)))


def validate_config(c):
    h.require(c['schema'] == 'sonora-expanded-fulltext-training-v1' and c['task_directory'] == '.local/a/mus058'
              and c['counts'] == pairs.COUNTS and c['device'] == 'mps' and c['dimension'] == 512
              and c['token_length'] == 256 and c['text_policy'] == 'complete_original_tokens_overflow_fail_no_truncation'
              and c['dtype'] == 'float32' and c['autocast'] is c['automatic_fallback'] is False
              and c['audio_batch'] == 3 and c['text_batch'] == 6 and c['audio_control_intervals'] == 3
              and c['text_controls'] == {'short': 3, 'long': 3} and c['alpha'] == 1.0
              and c['new_intervals'] == 367 and c['reused_intervals'] == 232 and c['expected_new_recordings'] == 76
              and c['weights'] == 'each_recording_equal_then_each_interval_equal'
              and c['loss'] == 'sum_i(q_i*||X_i W-T_i||^2)+alpha*||W-I||_F^2'
              and c['solver'] == 'float64_weighted_dual_ridge_identity_prior' and c['candidate_fits'] == 1
              and c['hyperparameter_search'] is c['validation_used_for_selection'] is False
              and c['comparators'] == ['identity', 'saved37-fulltext-ridge', 'expanded100-fulltext-ridge']
              and c['primary_metric'] == 'expanded140_whole_recording_macro_MRR_expanded100_minus_saved37'
              and c['validation_views'] == ['expanded20', 'original7']
              and c['bootstrap_iterations'] == 2000 and c['bootstrap_seed'] == 20261101058
              and c['atol_vector_maxabs'] == c['atol_cosine_distance'] == 1e-4
              and c['new_downloads'] == c['test_inputs'] == c['new_human_labels'] == 0
              and c['seed'] == 0 and c['blas_threads'] == 2
              and c['decision'] == 'retain_identity_no_automatic_selection_or_deployment', 'Fixed no-search data-size protocol required')


def initialize(config, config_sha256, output, stage):
    c = h.assets.document(config, config_sha256); validate_config(c)
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed source required')
    task = ROOT/c['task_directory']
    h.require(Path(output).absolute().is_relative_to(task.absolute()) and stage in ('encode', 'fit'), 'Task-local stage required')
    h.require(not (task/(stage+'-started.json')).exists(), 'Stage already attempted; no new-output retry')
    target = h.private_output(output)
    bound = {str(Path(config).absolute()): config_sha256}
    docs = {}
    for key, pin in c.items():
        if isinstance(pin, dict) and set(pin) == {'path', 'sha256'}:
            path = ROOT/pin['path']; bound[str(path.absolute())] = pin['sha256']
            if path.suffix == '.json': docs[key] = h.assets.document(path, pin['sha256'])
    for key in ('interval_cache', 'fulltext_cache', 'retrieval_cache'):
        meta = docs[key]; directory = (ROOT/c[key]['path']).parent
        bound[str(directory/'features.npz')] = meta['feature_sha256']
        bound[str(directory/'result.json')] = meta.get('result_sha256', meta.get('parity_report_sha256'))
        for path, pin in meta['key_context']['source_sha256'].items(): h.require(h.file_hash(ROOT/path) == pin, 'Frozen feature source changed')
    source = {n: h.file_hash(ROOT/n) for n in SOURCES}
    state = {'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'source_sha256': source, 'input_sha256': bound, 'config_sha256': config_sha256, 'created_at_utc': h.now()}
    recheck(state)
    return c, target, docs, state


def recheck(state):
    for n, pin in state['input_sha256'].items(): h.require(h.file_hash(n) == pin, 'Bound input changed')
    for n, pin in state['source_sha256'].items(): h.require(h.file_hash(ROOT/n) == pin, 'Source changed')


def claim(c, state, target, stage):
    h.write_json(ROOT/c['task_directory']/(stage+'-started.json'), {'source_sha': state['source_sha'],
                 'config_sha256': state['config_sha256'], 'output': str(target), 'started_at_utc': h.now(), 'maximum_attempts': 1})


def old_view(c, split):
    return fulltext.ready_view(base_cache=ROOT/c['interval_cache']['path'], base_sha256=c['interval_cache']['sha256'],
             text_cache=ROOT/c['fulltext_cache']['path'], text_sha256=c['fulltext_cache']['sha256'], expected_device='mps',
             expected_model_sha256=c['expected_model_sha256'], split=split)


def build(*, config, config_sha256, output):
    c, target, docs, state = initialize(config, config_sha256, output, 'encode'); started = time.perf_counter()
    try:
        h.require(docs['expansion_result']['reference_preflight_passed'] and docs['expansion_audit']['status'] == 'passed'
                  and docs['expansion_result']['combined_interval_counts'] == {'train': 539, 'validation': 60}, 'Verified expansion required')
        old_view(c, 'train'); old_view(c, 'validation')
        rows, texts, unique, proofs, counts, reused = pairs.combine(*(docs[k] for k in
            ('old_candidates', 'new_candidates', 'old_allowlist', 'old_corpus', 'new_recordings')), docs['interval_cache']['rows'])
        pairs.validate_windows(rows, unique)
        new_indices = [i for i in range(len(rows)) if i not in reused]
        local_controls = intervals.control_indices([rows[i] for i in new_indices], c['audio_control_seed'])
        audio_controls = [new_indices[i] for i in local_controls]
        environment = h.environment(); environment['device'] = 'mps'
        h.require(environment == docs['device_freeze']['environment'] == docs['interval_cache']['key_context']['environment'], 'Calibrated environment changed')
        model = docs['model_cache']['model']
        h.require(h.checkpoint_pin(model['path'], 'A') == model and model['sha256'] == c['expected_model_sha256'], 'Original model changed')
        state['input_sha256'][model['path']] = model['sha256']
        new_ids = {rows[i]['id'] for i in new_indices}
        for tid in new_ids:
            r = proofs[tid]; path = Path(r['audio_path'])
            state['input_sha256'].update({str(path.absolute()): r['audio_sha256'], str(Path(r['receipt_path']).absolute()): r['receipt_sha256']})
        recheck(state)
        context = {'device': 'mps', 'environment': environment, 'model_sha256': model['sha256'],
                   'input_sha256': h.digest(h.canonical(state['input_sha256'])), 'recipe_sha256': config_sha256,
                   'source_sha256': state['source_sha256']}
        key = calibration.cache_key(**context)
        h.write_json(target/'freeze.json', {**state, 'key_context': context, 'cache_key_sha256': key,
                     'rows_sha256': h.digest(h.canonical(rows)), 'audio_control_indices': audio_controls,
                     'text_control_policy': {'seed': c['text_control_seed'], 'counts': c['text_controls'],
                                             'scope': 'new train only; indices fixed after raw tokenization before encoding'}})
        claim(c, state, target, 'encode')
        import torch
        from checkpoint_model import load_checkpoint, checked_checkpoint
        from calibrate_encoder_device import setup, synchronize
        from preflight_caption_pairs import decode
        from preprocess import prepare_window
        h.require(torch.backends.mps.is_available() and os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') != '1', 'MPS required; no fallback')
        setup(torch, 'mps'); load_start = time.perf_counter(); sdk, strict = load_checkpoint(model['path'], 'A')
        for p in sdk.model.parameters(): p.requires_grad_(False)
        load_ms = (time.perf_counter()-load_start)*1000
        h.require(sdk.model.text_branch_type == 'roberta' and sdk.model.text_branch.config.max_position_embeddings >= 258, 'RoBERTa256 capacity required')
        raw_ids = [sdk.tokenize(t, truncation=False)['input_ids'] for t in texts]
        lengths = [len(v) for v in raw_ids]
        tokenize = lambda values: sdk.tokenize(values, padding='max_length', truncation=True, max_length=256, return_tensors='pt')
        token_proof = fulltext.token_proof(tokenize(texts), raw_ids)
        pairs.proof_complete(token_proof, lengths)
        old_proof = docs['token_proof']
        h.require(all(token_proof[i] == old_proof[j] for i, j in reused.items()), 'Old token sequence changed')
        controls = fulltext.controls([rows[i] for i in new_indices], [lengths[i] for i in new_indices], seed=c['text_control_seed'])
        text_controls = [new_indices[i] for kind in ('short', 'long') for i in controls[kind]]
        h.write_json(target/'token-proof.json', token_proof)
        h.write_json(target/'encoding-plan.json', {'text_control_indices': text_controls, 'audio_control_indices': audio_controls,
                     'new_indices': new_indices, 'reused_to_base_index': reused, 'token_lengths': lengths})
        def waves_for(tid, ix):
            record = proofs[tid]; wave, info = decode(record['audio_path'])
            h.require(info['decoded_samples'] == record['decode']['decoded_samples']
                      and h.digest(wave.astype('<f4', copy=False).tobytes()) == record['pcm_sha256'], 'Actual audio EOF/PCM changed')
            return np.stack([prepare_window(wave[unique[j]['start_sample']:unique[j]['start_sample']+480000], 48000)[0] for j in ix])
        control_windows = [j for i in audio_controls for j in rows[i]['window_indices']]
        control_waves = np.concatenate([waves_for(rows[i]['id'], rows[i]['window_indices']) for i in audio_controls])
        save_npz(target/'control-inputs.npz', waves=control_waves)
        audio_encode = lambda waves: unit(features.matrix(np.concatenate([sdk.get_audio_embedding_from_data(waves[i:i+3], use_tensor=False)
                                             for i in range(0, len(waves), 3)]), (len(waves), 512)))
        text_encode = lambda values: unit(features.matrix(np.concatenate([sdk.get_text_embedding(values[i:i+6], tokenizer=tokenize, use_tensor=False)
                                             for i in range(0, len(values), 6)]), (len(values), 512)))
        base = docs['interval_cache']; before_windows = base['unique_windows']
        with np.load((ROOT/c['interval_cache']['path']).parent/'features.npz', allow_pickle=False) as f:
            old_audio, old_windows = f['audio'], f['windows']
        with np.load((ROOT/c['fulltext_cache']['path']).parent/'features.npz', allow_pickle=False) as f: old_text = f['text256']
        audio = np.empty((599, 512)); text = np.empty((599, 512)); windows = np.empty((len(unique), 512))
        old_lookup = {(r['id'], r['start_sample']): i for i, r in enumerate(before_windows)}
        for i, j in reused.items(): audio[i] = old_audio[j]; text[i] = old_text[j]
        for i, r in enumerate(unique):
            if r['id'] not in new_ids: windows[i] = old_windows[old_lookup[(r['id'], r['start_sample'])]]
        with torch.inference_mode():
            start = time.perf_counter(); cpu_windows = audio_encode(control_waves); cpu_text = text_encode([texts[i] for i in text_controls])
            cpu_audio = unit(cpu_windows.reshape(3, 3, 512).mean(axis=1)); cpu_ms = (time.perf_counter()-start)*1000
            save_npz(target/'cpu-controls.npz', windows=cpu_windows, audio=cpu_audio, text=cpu_text)
            sdk.model.to(torch.device('mps')); sdk.device = torch.device('mps')
            h.require(all(str(p.device) == 'mps:0' and not p.requires_grad and (not p.is_floating_point() or p.dtype == torch.float32)
                          for p in sdk.model.parameters()), 'Frozen FP32 MPS required')
            audio_encode(control_waves[:3]); text_encode([texts[text_controls[0]]]); synchronize(torch, 'mps')
            start = time.perf_counter()
            for n, tid in enumerate(sorted(new_ids, key=int), 1):
                ix = [i for i, r in enumerate(unique) if r['id'] == tid]
                windows[ix] = audio_encode(waves_for(tid, ix))
                if n % 5 == 0 or n == len(new_ids): print(json.dumps({'encoded_new_recordings': n, 'total': len(new_ids)}), flush=True)
            synchronize(torch, 'mps'); audio_ms = (time.perf_counter()-start)*1000
            start = time.perf_counter(); text[new_indices] = text_encode([texts[i] for i in new_indices]); synchronize(torch, 'mps')
            text_ms = (time.perf_counter()-start)*1000
        for i in new_indices: audio[i] = unit(windows[rows[i]['window_indices']].mean(axis=0, keepdims=True))[0]
        h.require(all(np.array_equal(audio[i], old_audio[j]) and np.array_equal(text[i], old_text[j]) for i, j in reused.items()), 'Reused interval vectors changed')
        features.matrix(windows, (len(unique), 512)); features.matrix(audio, (599, 512)); features.matrix(text, (599, 512))
        parity = {'new_windows': features.vector_parity(cpu_windows, windows[control_windows], c),
                  'new_interval_audio': features.vector_parity(cpu_audio, audio[audio_controls], c),
                  'new_text256': features.vector_parity(cpu_text, text[text_controls], c)}
        passed = all(v['status'] == 'passed' for v in parity.values())
        save_npz(target/'features.npz', audio=audio, text=text, windows=windows, weights=np.array([r['weight'] for r in rows]))
        recheck(state); checked_checkpoint(model['path'], 'A')
        final = h.environment(); final['device'] = 'mps'; h.require(final == environment, 'ML environment changed')
        result = {'status': 'passed' if passed else 'failed', 'source_sha': state['source_sha'], 'config_sha256': config_sha256,
                  'cache_key_sha256': key, 'ready_cache_written': passed, 'counts': counts, 'reused_intervals_exact': len(reused),
                  'new_intervals': len(new_indices), 'new_recordings': len(new_ids), 'unique_audio_windows': len(unique),
                  'new_audio_windows': sum(r['id'] in new_ids for r in unique), 'new_texts': len(new_indices),
                  'truncated_captions': 0, 'min_tokens': min(lengths), 'max_tokens': max(lengths),
                  'over_77_tokens': sum(n > 77 for n in lengths), 'vector_parity': parity,
                  'audio_control_intervals': 3, 'text_control_intervals': 6, 'strict': strict, 'fits': 0, 'downloads': 0, 'test_inputs': 0,
                  'timing_ms': {'model_load': load_ms, 'CPU_controls': cpu_ms, 'MPS_audio_including_decode': audio_ms,
                                'MPS_text': text_ms, 'total_including_integrity': (time.perf_counter()-started)*1000}}
        h.write_json(target/'result.json', result)
        if passed:
            h.write_json(target/'cache.json', {'schema': 'sonora-expanded-pair-feature-cache-v1', 'status': 'ready_after_parity',
                         'device': 'mps', 'model_sha256': model['sha256'], 'recipe': intervals.RECIPE, 'token_length': 256,
                         'key_context': context, 'cache_key_sha256': key, 'rows': rows, 'unique_windows': unique, 'token_lengths': lengths,
                         'token_proof_sha256': h.file_hash(target/'token-proof.json'), 'feature_sha256': h.file_hash(target/'features.npz'),
                         'result_sha256': h.file_hash(target/'result.json')})
        return result
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def fit(*, config, config_sha256, output, cache, cache_sha256):
    c, target, docs, state = initialize(config, config_sha256, output, 'fit'); started = time.perf_counter()
    try:
        meta = h.assets.document(cache, cache_sha256); directory = Path(cache).parent
        report = h.assets.document(directory/'result.json', meta['result_sha256'])
        h.require(report['source_sha'] == state['source_sha'] and report['config_sha256'] == config_sha256, 'Same committed build and fit protocol required')
        state['input_sha256'].update({str(Path(cache).absolute()): cache_sha256, str((directory/'features.npz').absolute()): meta['feature_sha256'],
                     str((directory/'token-proof.json').absolute()): meta['token_proof_sha256'], str((directory/'result.json').absolute()): meta['result_sha256']})
        args = {'cache': cache, 'cache_sha256': cache_sha256, 'expected_device': 'mps', 'expected_model_sha256': c['expected_model_sha256']}
        train = pairs.ready_view(**args, split='train'); runtime = numpy_runtime(); recheck(state)
        h.require(train['audio'].shape == train['text'].shape == (539, 512) and len(set(train['recording_ids'])) == 100, 'Only expanded train rows may fit')
        h.write_json(target/'freeze.json', {**state, 'runtime': runtime, 'expanded_cache_sha256': cache_sha256,
                     'fit_recordings': 100, 'fit_intervals': 539, 'alpha': 1.0, 'validation_used_for_fit_or_selection': False,
                     'shared_NPZ_physically_integrity_checked_but_only_train_returned': True})
        claim(c, state, target, 'fit'); start = time.perf_counter()
        w, diagnostic = learner.fit(train['audio'], train['text'], train['weights'], train['recording_ids'], 1.0)
        fit_ms = (time.perf_counter()-start)*1000; save_npz(target/'adapter.npz', W=w)
        h.write_json(target/'fit.json', {'completed_at_utc': h.now(), 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                     'fit_ms': fit_ms, 'diagnostic': diagnostic, 'fit_runs': 1, 'baseline_refit_runs': 0})
        h.write_json(target/'evaluation-open.json', {'opened_at_utc': h.now(), 'fit_receipt_sha256': h.file_hash(target/'fit.json'),
                     'validation_views': c['validation_views'], 'human_queries_unchanged': True, 'test_inputs': 0})
        val = pairs.ready_view(**args, split='validation')
        h.require(not set(train['recording_ids']) & set(val['recording_ids']) and not set(train['creator_components']) & set(val['creator_components']), 'Split leakage')
        oldval = old_view(c, 'validation'); old_ids = set(oldval['recording_ids'])
        old_ix = [i for i, tid in enumerate(val['recording_ids']) if tid in old_ids]
        h.require(np.array_equal(val['audio'][old_ix], oldval['audio']) and np.array_equal(val['text'][old_ix], oldval['text']), 'Original7/23 subset changed')
        views = {'expanded20': val, 'original7': oldval}
        retrieval = features.ready_view(ROOT/c['retrieval_cache']['path'], c['retrieval_cache']['sha256'], expected_device='mps',
                                       expected_model_sha256=c['expected_model_sha256'], view='caption_retrieval')
        human = docs['human_text_metadata']
        h.require(len(human['caption_token_lengths']) == 24 and max(human['caption_token_lengths']) <= 77
                  and human['query_text_sha256'] == docs['retrieval_cache']['query_text_sha256'], 'Human queries must already be complete and unchanged')
        with np.load((ROOT/c['retrieval_cache']['path']).parent/'features.npz', allow_pickle=False) as f: windows = f['windows']
        with np.load(ROOT/c['baseline_adapter']['path'], allow_pickle=False) as f: prior_w = f['W']
        baseline = docs['baseline_result']
        h.require(baseline['adapter_sha256'] == c['baseline_adapter']['sha256'] and baseline['runtime'] == runtime, 'Fixed saved37 baseline/runtime changed')
        results = {}
        for name, candidate in zip(c['comparators'], [np.eye(512), prior_w, w]):
            results[name] = {'human_development': human_development(candidate, retrieval, docs['retrieval_cache'], windows),
                  'generated_validation': {label: learner.validation_metrics(v['audio'], v['text'], v['recording_ids'], candidate) for label, v in views.items()}}
        for name, oldname in [('identity', 'identity'), ('saved37-fulltext-ridge', 'caption256')]:
            h.require(results[name]['human_development'] == baseline['results'][oldname]['human_development']
                      and results[name]['generated_validation']['original7'] == baseline['results'][oldname]['generated_validation']['query256'], 'Original control results changed')
        delta = lambda x, y: metrics.deltas(x, y, c['bootstrap_iterations'], c['bootstrap_seed'])
        new = results['expanded100-fulltext-ridge']
        paired = {anchor: {'human_development': {pool: {mode: delta(new['human_development'][pool][mode], results[anchor]['human_development'][pool][mode])
                               for mode in ('whole', 'segment')} for pool in ('dev20', 'expanded140')},
                           'generated_validation': {label: {kind: delta(new['generated_validation'][label][kind], results[anchor]['generated_validation'][label][kind])
                               for kind in ('exact_interval', 'recording_max_interval')} for label in c['validation_views']}}
                  for anchor in ('identity', 'saved37-fulltext-ridge')}
        recheck(state); h.require(runtime == numpy_runtime() and 'torch' not in sys.modules and 'laion_clap' not in sys.modules, 'Frozen-feature CPU-only fit required')
        result = {'status': 'one_fixed_expanded_fit_complete', 'source_sha': state['source_sha'], 'config_sha256': config_sha256,
                  'adapter_sha256': h.file_hash(target/'adapter.npz'), 'counts': {**pairs.COUNTS, 'fit_runs': 1, 'baseline_refit_runs': 0,
                      'human_dev_queries': 24, 'human_dev_recordings': 20, 'human_candidates': 140, 'truncated_captions': 0, 'test_inputs': 0, 'downloads': 0},
                  'fit_ms': fit_ms, 'diagnostic': diagnostic, 'runtime': runtime, 'results': results, 'paired_deltas': paired,
                  'baseline_controls_reproduced': True, 'torch_or_CLAP_imported': False, 'decision': c['decision'],
                  'total_ms': (time.perf_counter()-started)*1000,
                  'limits': ['Generated captions are weak labels, not human relevance truth.',
                             'Known-pair retrieval; other songs and intervals remain semantically unjudged.',
                             'Previously seen20-recording human development, not independent blind test.',
                             'Single fixed ridge comparison; no CLAP fine tuning, parameter search or deployment.']}
        h.write_json(target/'result-private.json', result); public = json.loads(json.dumps(result))
        for m in public['results'].values():
            for pool in m['human_development'].values():
                for values in pool.values(): values.pop('per_recording')
            for view in m['generated_validation'].values():
                for values in view.values(): values.pop('per_recording'); values.pop('ranks', None)
        h.write_json(target/'result-public.json', public); return public
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    p = argparse.ArgumentParser(); p.add_argument('stage', choices=['build', 'fit'])
    for name in ('config', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--config-sha256', required=True); p.add_argument('--cache', type=Path); p.add_argument('--cache-sha256')
    args = vars(p.parse_args()); stage = args.pop('stage')
    if stage == 'build': args.pop('cache'); args.pop('cache_sha256')
    r = (build if stage == 'build' else fit)(**args); print(json.dumps(r))
    if r['status'] == 'failed': raise SystemExit(1)


if __name__ == '__main__': main()
