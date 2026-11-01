#!/usr/bin/env python3
"""One fulltext normalized-pair fit; fixed cached features and saved fulltext-ridge control."""
from pathlib import Path
import argparse
import json
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '2'
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'services/audio-search'))
import numpy as np
import holdout_contract as h
import cosine_caption_adapter as learner
import long_caption_features as fulltext
import device_feature_cache as features
import expanded_caption_metrics as metrics
from weighted_caption_adapter import validation_metrics
from train_caption_adapter import human_development, SOURCES as PRIOR_SOURCES
from train_positive_score import numpy_runtime
from train_tag_adapter import save_npz

SOURCES = tuple(dict.fromkeys(('scripts/train_fulltext_cosine.py', 'services/audio-search/cosine_caption_adapter.py',
                              'services/audio-search/long_caption_features.py', *PRIOR_SOURCES)))
INPUTS = ('interval_cache', 'fulltext_cache', 'retrieval_cache', 'human_text_metadata', 'baseline_result', 'baseline_adapter', 'token_proof')


def validate_config(cfg):
    h.require(cfg['schema'] == 'sonora-fulltext-cosine-training-v1' and cfg['task_directory'] == '.local/a/mus056'
              and cfg['text_policy'] == 'complete_original_token_sequence;overflow_fail_no_truncation' and cfg['token_length'] == 256
              and (cfg['fit_recordings'], cfg['fit_components'], cfg['fit_intervals'], cfg['validation_recordings'], cfg['validation_intervals'], cfg['dimension']) == (37, 33, 209, 7, 23, 512)
              and type(cfg['alpha']) is float and cfg['alpha'] == 1.0
              and cfg['loss'] == 'sum_i(q_i*||unit(X_i W)-T_i||^2)+alpha*||W-I||_F^2'
              and cfg['weights'] == 'each_recording_equal_then_each_interval_equal'
              and cfg['optimizer'] == 'float64_full_batch_gradient_descent_Armijo_from_identity'
              and cfg['initial_step'] == 1.0 and cfg['max_steps'] == 200 and cfg['max_backtracks'] == 20
              and cfg['armijo'] == 1e-4 and cfg['backtrack_factor'] == .5 and cfg['gradient_max_tol'] == 1e-8 and cfg['relative_loss_tol'] == 1e-12
              and cfg['candidate_fits'] == 1 and cfg['hyperparameter_search'] is cfg['validation_used_for_stopping_or_selection'] is False
              and cfg['comparators'] == ['identity', 'fulltext-ridge', 'fulltext-cosine']
              and cfg['primary_metric'] == 'expanded140_whole_recording_macro_MRR_new_cosine_minus_saved_fulltext_ridge'
              and cfg['human_query_features'] == 'unchanged_complete_11_to30_token_queries' and cfg['validation_query_features'] == 'fulltext256_only'
              and cfg['bootstrap_iterations'] == 2000 and cfg['bootstrap_seed'] == 20261101056 and cfg['blas_threads'] == 2 and cfg['seed'] == 0
              and cfg['new_model_or_audio_encodes'] == cfg['new_downloads'] == cfg['new_test_inputs'] == cfg['new_human_labels'] == 0
              and cfg['decision'] == 'retain_identity_no_automatic_selection_scale_up_or_deployment', 'One complete-text normalized-pair protocol required')


def verify_fulltext(proof, lengths):
    h.require(len(proof) == len(lengths) == 232 and all(type(n) is int and 2 <= n <= 256 for n in lengths)
              and all(item['untruncated_tokens'] == item['encoded_nonpad_tokens'] == n for item, n in zip(proof, lengths)),
              'Complete original tokens required; overflow or truncation must fail')


def run(*, config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256); validate_config(cfg)
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean committed fulltext fit source required')
    h.require(Path(output).absolute().is_relative_to((ROOT/cfg['task_directory']).absolute()), 'Fixed private task directory required')
    target = h.private_output(output); started = time.perf_counter()
    try:
        state = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        hashes = {n: h.file_hash(ROOT/n) for n in SOURCES}; runtime = numpy_runtime()
        doc = lambda key: h.assets.document(ROOT/cfg[key]['path'], cfg[key]['sha256'])
        base, overlay, retrieval_meta, human_meta = (doc(k) for k in ('interval_cache', 'fulltext_cache', 'retrieval_cache', 'human_text_metadata'))
        bound = {str(Path(config).absolute()): config_sha256}
        bound.update({str((ROOT/cfg[k]['path']).absolute()): cfg[k]['sha256'] for k in INPUTS})
        for name, meta in [('interval_cache', base), ('fulltext_cache', overlay), ('retrieval_cache', retrieval_meta)]:
            path = ROOT/cfg[name]['path']; bound[str(path.parent/'features.npz')] = meta['feature_sha256']
            bound[str(path.parent/'result.json')] = meta.get('result_sha256', meta.get('parity_report_sha256'))
            for n, digest in meta['key_context']['source_sha256'].items(): h.require(h.file_hash(ROOT/n) == digest, 'Frozen feature source changed')
        verify_fulltext(doc('token_proof'), overlay['token_lengths'])
        h.require(len(human_meta['caption_token_lengths']) == 24 and all(0 < n <= 77 for n in human_meta['caption_token_lengths'])
                  and human_meta['query_text_sha256'] == retrieval_meta['query_text_sha256'], 'Original human features must already represent complete queries')
        for n, digest in bound.items(): h.require(h.file_hash(n) == digest, 'Bound fulltext inputs changed')
        args = {'base_cache': ROOT/cfg['interval_cache']['path'], 'base_sha256': cfg['interval_cache']['sha256'],
                'text_cache': ROOT/cfg['fulltext_cache']['path'], 'text_sha256': cfg['fulltext_cache']['sha256'],
                'expected_device': cfg['expected_device'], 'expected_model_sha256': cfg['expected_model_sha256']}
        train = fulltext.ready_view(**args, split='train')
        h.require(train['audio'].shape == train['text'].shape == (209, 512) and len(set(train['recording_ids'])) == 37
                  and len(set(train['creator_components'])) == 33, 'Only fixed209 complete-text train pairs required')
        h.write_json(target/'freeze.json', {'created_at_utc': h.now(), 'source_sha': state, 'source_sha256': hashes,
                     'config_sha256': config_sha256, 'input_sha256': bound, 'runtime': runtime,
                     'fulltext_cache_key_sha256': train['cache_key_sha256'], 'fit_intervals': 209, 'fit_recordings': 37,
                     'text_policy': cfg['text_policy'], 'validation_used_for_fit_or_stopping': False,
                     'reader_integrity_loads_shared_npz_but_only_train_returned_for_solver': True})
        h.write_json(ROOT/cfg['task_directory']/'fit-started.json', {'source_sha': state, 'config_sha256': config_sha256,
                     'output': str(target), 'started_at_utc': h.now(), 'maximum_fit_attempts': 1})
        np.random.seed(0); start = time.perf_counter()
        settings = {k: cfg[k] for k in ('alpha', 'initial_step', 'max_steps', 'max_backtracks', 'armijo', 'backtrack_factor', 'gradient_max_tol', 'relative_loss_tol')}
        w, diagnostic = learner.fit(train['audio'], train['text'], train['weights'], train['recording_ids'], **settings)
        fit_ms = (time.perf_counter()-start)*1000; save_npz(target/'adapter.npz', W=w)
        h.write_json(target/'fit.json', {'completed_at_utc': h.now(), 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                     'fit_ms': fit_ms, 'diagnostic': diagnostic, 'fit_runs': 1, 'baseline_refit_runs': 0})
        h.write_json(target/'evaluation-open.json', {'opened_at_utc': h.now(), 'fit_receipt_sha256': h.file_hash(target/'fit.json'),
                     'validation_text': 'fulltext256', 'human_query_features_unchanged_and_complete': True, 'reserved_test_inputs': 0})
        val = fulltext.ready_view(**args, split='validation')
        h.require(not set(train['recording_ids']) & set(val['recording_ids']) and not set(train['creator_components']) & set(val['creator_components']), 'Validation group contamination')
        retrieval = features.ready_view(ROOT/cfg['retrieval_cache']['path'], cfg['retrieval_cache']['sha256'],
                         expected_device=cfg['expected_device'], expected_model_sha256=cfg['expected_model_sha256'], view='caption_retrieval')
        with np.load((ROOT/cfg['retrieval_cache']['path']).parent/'features.npz', allow_pickle=False) as f: windows = f['windows']
        baseline = doc('baseline_result')
        h.require(baseline['adapter_sha256'] == cfg['baseline_adapter']['sha256'] and baseline['runtime'] == runtime, 'Fulltext ridge baseline/runtime changed')
        with np.load(ROOT/cfg['baseline_adapter']['path'], allow_pickle=False) as f: ridge = f['W']
        results = {}
        for name, candidate in [('identity', np.eye(512)), ('fulltext-ridge', ridge), ('fulltext-cosine', w)]:
            results[name] = {'human_development': human_development(candidate, retrieval, retrieval_meta, windows),
                             'generated_validation': validation_metrics(val['audio'], val['text'], val['recording_ids'], candidate)}
        for name, oldname in [('identity', 'identity'), ('fulltext-ridge', 'caption256')]:
            h.require(results[name]['human_development'] == baseline['results'][oldname]['human_development']
                      and results[name]['generated_validation'] == baseline['results'][oldname]['generated_validation']['query256'], 'Fulltext baseline controls did not reproduce')
        delta = lambda c, b: metrics.deltas(c, b, cfg['bootstrap_iterations'], cfg['bootstrap_seed'])
        paired = {anchor: {'human_development': {pool: {mode: delta(results['fulltext-cosine']['human_development'][pool][mode], results[anchor]['human_development'][pool][mode])
                            for mode in ('whole', 'segment')} for pool in ('dev20', 'expanded140')},
                          'generated_validation': {kind: delta(results['fulltext-cosine']['generated_validation'][kind], results[anchor]['generated_validation'][kind])
                            for kind in ('exact_interval', 'recording_max_interval')}} for anchor in ('identity', 'fulltext-ridge')}
        h.require('torch' not in sys.modules and 'laion_clap' not in sys.modules, 'Cached-feature CPU fit must not import encoder')
        for n, digest in bound.items(): h.require(h.file_hash(n) == digest, 'Bound inputs changed during fit')
        h.require(numpy_runtime() == runtime and all(h.file_hash(ROOT/n) == digest for n, digest in hashes.items()), 'Runtime/source changed')
        result = {'schema': 'sonora-fulltext-cosine-result-v1', 'status': 'one_fixed_fit_and_development_evaluation_complete',
                  'source_sha': state, 'config_sha256': config_sha256, 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                  'runtime': runtime, 'counts': {'fit_runs': 1, 'baseline_refit_runs': 0, 'train_recordings': 37, 'train_components': 33, 'train_intervals': 209,
                      'validation_recordings': 7, 'validation_intervals': 23, 'human_dev_recordings': 20, 'human_dev_queries': 24, 'retrieval_candidates': 140,
                      'truncated_texts': 0, 'new_model_or_audio_encodes': 0, 'downloads': 0, 'test_inputs': 0},
                  'text_policy': cfg['text_policy'], 'fit_ms': fit_ms, 'diagnostic': diagnostic, 'results': results, 'paired_deltas': paired,
                  'fulltext_baseline_controls_reproduced': True, 'torch_or_CLAP_imported': False, 'decision': cfg['decision'],
                  'total_ms': (time.perf_counter()-started)*1000,
                  'limits': ['Generated full captions are weak supervision, not human semantic truth.',
                             'Normalized positive-pair objective remains nonconvex and is not a ranking loss; no global optimum claim.',
                             'Fixed one-run comparison on previously seen development and seven validation recordings, not new blind test.',
                             'No new negatives, original CLAP fine tuning, hyperparameter search or deployment.']}
        h.write_json(target/'result-private.json', result); public = json.loads(json.dumps(result))
        for model in public['results'].values():
            for pool in model['human_development'].values():
                for values in pool.values(): values.pop('per_recording')
            for values in model['generated_validation'].values(): values.pop('per_recording'); values.pop('ranks', None)
        h.write_json(target/'result-public.json', public); return public
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    p = argparse.ArgumentParser(); p.add_argument('--config', type=Path, required=True)
    p.add_argument('--config-sha256', required=True); p.add_argument('--output', type=Path, required=True)
    result = run(**vars(p.parse_args())); print(json.dumps({'status': result['status'], 'counts': result['counts'], 'fit_ms': result['fit_ms'], 'stop_reason': result['diagnostic']['stop_reason']}))


if __name__ == '__main__': main()
