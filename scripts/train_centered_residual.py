#!/usr/bin/env python3
"""One cached-feature centered-residual ablation; no encoder or repeated search."""
from pathlib import Path
import argparse
import json
import os
for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[n] = '2'
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'services/audio-search'))
import numpy as np
import holdout_contract as h
import centered_residual_adapter as learner
import expanded_pair_features as pairs
import device_feature_cache as features
import expanded_caption_metrics as metrics
from weighted_caption_adapter import validation_metrics
from supervision_diagnostic import score_contrasts
from train_caption_adapter import human_development, SOURCES as PRIOR_SOURCES
from train_positive_score import numpy_runtime
from train_tag_adapter import save_npz

SOURCES = tuple(dict.fromkeys(('scripts/train_centered_residual.py', 'services/audio-search/centered_residual_adapter.py',
           'services/audio-search/expanded_pair_features.py', 'services/audio-search/supervision_diagnostic.py', *PRIOR_SOURCES)))


def validate(c):
    h.require(c['schema'] == 'sonora-centered-residual-training-v1' and c['task_directory'] == '.local/a/mus060'
              and c['counts'] == pairs.COUNTS and c['dimension'] == 512 and c['token_length'] == 256
              and c['text_policy'] == 'complete_original_tokens_no_reencoding_no_truncation' and c['alpha'] == 1.
              and c['residual_centering'] == 'mu=sum_train(q*(T-X));Y=(T-X)-mu;X_not_centered;no_inference_mean_subtraction'
              and c['loss'] == 'sum_i(q_i*||X_i*(W-I)-((T_i-X_i)-mu_train)||^2)+alpha*||W-I||_F^2'
              and c['solver'] == 'float64_weighted_primal_ridge_identity_prior'
              and c['weights'] == 'each_recording_equal_then_each_interval_equal' and c['candidate_fits'] == 1
              and c['hyperparameter_search'] is c['validation_used_for_centering_or_selection'] is False
              and c['comparators'] == ['identity', 'saved37-fulltext-ridge', 'saved100-fulltext-ridge', 'centered100-fulltext-ridge']
              and c['primary_metric'] == 'expanded140_whole_recording_macro_MRR_centered100_minus_saved100'
              and c['validation_views'] == ['expanded20', 'original7'] and c['diagnostic_views'] == ['train100', 'validation20']
              and c['bootstrap_iterations'] == 2000 and c['bootstrap_seed'] == 20261102060 and c['blas_threads'] == 2 and c['seed'] == 0
              and c['new_encodes'] == c['downloads'] == c['test_inputs'] == c['label_edits'] == 0
              and c['decision'] == 'retain_identity_no_automatic_selection_or_deployment', 'Fixed one-fit centered-residual protocol required')


def recheck(state):
    for n, pin in state['input_sha256'].items(): h.require(h.file_hash(n) == pin, 'Bound input changed')
    for n, pin in state['source_sha256'].items(): h.require(h.file_hash(ROOT/n) == pin, 'Frozen source changed')


def run(*, config, config_sha256, output):
    c = h.assets.document(config, config_sha256); validate(c)
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed source required')
    task = ROOT/c['task_directory']
    h.require(Path(output).absolute().is_relative_to(task.absolute()) and not (task/'fit-started.json').exists(),
              'Task fit already attempted or output outside task; no implicit retry')
    target = h.private_output(output); started = time.perf_counter()
    try:
        bound = {str(Path(config).absolute()): config_sha256}; docs = {}
        for k, pin in c.items():
            if isinstance(pin, dict) and set(pin) == {'path', 'sha256'}:
                path = ROOT/pin['path']; bound[str(path.absolute())] = pin['sha256']
                if path.suffix == '.json': docs[k] = h.assets.document(path, pin['sha256'])
        for name in ('expanded_cache', 'retrieval_cache'):
            meta = docs[name]; folder = (ROOT/c[name]['path']).parent
            bound[str(folder/'features.npz')] = meta['feature_sha256']
            bound[str(folder/'result.json')] = meta.get('result_sha256', meta.get('parity_report_sha256'))
            for n, pin in meta['key_context']['source_sha256'].items(): h.require(h.file_hash(ROOT/n) == pin, 'Original cache source changed')
        args = {'cache': ROOT/c['expanded_cache']['path'], 'cache_sha256': c['expanded_cache']['sha256'],
                'expected_device': 'mps', 'expected_model_sha256': c['expected_model_sha256']}
        train = pairs.ready_view(**args, split='train'); runtime = numpy_runtime()
        h.require(train['audio'].shape == train['text'].shape == (539, 512) and len(set(train['recording_ids'])) == 100
                  and runtime == docs['uncentered_result']['runtime'] and docs['diagnostic_result']['fits'] == 0,
                  'Frozen original100/539 features/runtime required')
        state = {'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                 'source_sha256': {n: h.file_hash(ROOT/n) for n in SOURCES}, 'input_sha256': bound,
                 'runtime': runtime, 'config_sha256': config_sha256, 'created_at_utc': h.now()}
        recheck(state)
        h.write_json(target/'freeze.json', {**state, 'fit_recordings': 100, 'fit_intervals': 539,
                     'mean_from_train_only': True, 'validation_used_for_fit_or_selection': False,
                     'reader_integrity_loads_shared_NPZ_but_only_train_returned_to_solver': True})
        h.write_json(task/'fit-started.json', {'source_sha': state['source_sha'], 'config_sha256': config_sha256,
                     'output': str(target), 'started_at_utc': h.now(), 'maximum_attempts': 1})
        start = time.perf_counter()
        w, mean, diagnostic = learner.fit(train['audio'], train['text'], train['weights'], train['recording_ids'], 1.)
        fit_ms = (time.perf_counter()-start)*1000; save_npz(target/'adapter.npz', W=w, training_residual_mean=mean)
        h.write_json(target/'fit.json', {'completed_at_utc': h.now(), 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                     'fit_ms': fit_ms, 'diagnostic': diagnostic, 'fit_runs': 1, 'baseline_refit_runs': 0})
        h.write_json(target/'evaluation-open.json', {'opened_at_utc': h.now(), 'fit_receipt_sha256': h.file_hash(target/'fit.json'),
                     'validation_views': c['validation_views'], 'human_queries_unchanged': True, 'test_inputs': 0})
        val = pairs.ready_view(**args, split='validation')
        h.require(not set(train['recording_ids']) & set(val['recording_ids']) and not set(train['creator_components']) & set(val['creator_components']), 'Split contamination')
        old_ids = {r['id'] for r in docs['old_cache']['rows'] if r['split'] == 'validation'}
        ix = [i for i, tid in enumerate(val['recording_ids']) if tid in old_ids]
        oldval = {'audio': val['audio'][ix], 'text': val['text'][ix], 'recording_ids': [val['recording_ids'][i] for i in ix]}
        h.require(len(ix) == 23 and len(old_ids) == 7, 'Original7/23 validation subset required')
        views = {'expanded20': val, 'original7': oldval}
        retrieval = features.ready_view(ROOT/c['retrieval_cache']['path'], c['retrieval_cache']['sha256'],
                         expected_device='mps', expected_model_sha256=c['expected_model_sha256'], view='caption_retrieval')
        human = docs['human_text_metadata']
        h.require(len(human['caption_token_lengths']) == 24 and max(human['caption_token_lengths']) <= 77
                  and human['query_text_sha256'] == docs['retrieval_cache']['query_text_sha256'], 'Complete unchanged human query features required')
        with np.load((ROOT/c['retrieval_cache']['path']).parent/'features.npz', allow_pickle=False) as f: windows = f['windows']
        with np.load(ROOT/c['uncentered_adapter']['path'], allow_pickle=False) as f: w100 = f['W']
        with np.load(ROOT/c['original37_adapter']['path'], allow_pickle=False) as f: w37 = f['W']
        h.require(docs['uncentered_result']['adapter_sha256'] == c['uncentered_adapter']['sha256']
                  and docs['original37_result']['adapter_sha256'] == c['original37_adapter']['sha256'], 'Saved controls changed')
        results = {}; contrasts = {}
        for name, model in zip(c['comparators'], [np.eye(512), w37, w100, w]):
            results[name] = {'human_development': human_development(model, retrieval, docs['retrieval_cache'], windows),
                            'generated_validation': {label: validation_metrics(v['audio'], v['text'], v['recording_ids'], model) for label, v in views.items()}}
            contrasts[name] = {label: score_contrasts(v['audio'], v['text'], v['recording_ids'], model)
                               for label, v in [('train100', train), ('validation20', val)]}
        for name, before in [('identity', 'identity'), ('saved37-fulltext-ridge', 'saved37-fulltext-ridge'), ('saved100-fulltext-ridge', 'expanded100-fulltext-ridge')]:
            h.require(results[name] == docs['uncentered_result']['results'][before], 'Entire saved control evaluation changed')
        delta = lambda x, y: metrics.deltas(x, y, c['bootstrap_iterations'], c['bootstrap_seed'])
        new = results['centered100-fulltext-ridge']; paired = {}
        for anchor in c['comparators'][:-1]:
            paired[anchor] = {'human_development': {pool: {mode: delta(new['human_development'][pool][mode], results[anchor]['human_development'][pool][mode])
                                for mode in ('whole', 'segment')} for pool in ('dev20', 'expanded140')},
                              'generated_validation': {label: {kind: delta(new['generated_validation'][label][kind], results[anchor]['generated_validation'][label][kind])
                                for kind in ('exact_interval', 'recording_max_interval')} for label in c['validation_views']}}
        recheck(state); h.require(runtime == numpy_runtime() and not any(n in sys.modules for n in ('torch', 'laion_clap')), 'Frozen-feature CPU-only training required')
        result = {'schema': 'sonora-centered-residual-result-v1', 'status': 'one_fixed_centered_fit_complete', 'source_sha': state['source_sha'],
                  'config_sha256': config_sha256, 'adapter_sha256': h.file_hash(target/'adapter.npz'), 'runtime': runtime,
                  'counts': {**pairs.COUNTS, 'fit_runs': 1, 'baseline_refit_runs': 0, 'human_queries': 24, 'human_recordings': 20,
                             'human_candidates': 140, 'truncated_texts': 0, 'new_encodes': 0, 'downloads': 0, 'test_inputs': 0},
                  'fit_ms': fit_ms, 'diagnostic': diagnostic, 'results': results, 'paired_deltas': paired, 'score_contrasts': contrasts,
                  'saved_controls_fully_reproduced': True, 'torch_or_CLAP_imported': False, 'decision': c['decision'],
                  'total_ms': (time.perf_counter()-started)*1000,
                  'limits': ['Centered training residual is an ablation, not semantic label cleaning.', 'Original fulltext features remain unchanged; inference uses W only.',
                             'Generated known pairs only; alternatives semantically unjudged, not negatives.',
                             'Repeatedly seen human development, not independent blind test; no search or deployment.']}
        h.write_json(target/'result-private.json', result); public = json.loads(json.dumps(result))
        for model in public['results'].values():
            for pool in model['human_development'].values():
                for values in pool.values(): values.pop('per_recording')
            for view in model['generated_validation'].values():
                for values in view.values(): values.pop('per_recording'); values.pop('ranks', None)
        h.write_json(target/'result-public.json', public); return public
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    p = argparse.ArgumentParser()
    for n in ('config', 'output'): p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--config-sha256', required=True)
    print(json.dumps(run(**vars(p.parse_args()))))


if __name__ == '__main__': main()
