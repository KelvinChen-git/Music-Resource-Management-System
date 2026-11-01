#!/usr/bin/env python3
"""One immutable, task-budgeted caption ridge fit; frozen CLAP and existing GPU caches."""
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
import weighted_caption_adapter as learner
import interval_feature_cache as intervals
import device_feature_cache as features
import expanded_caption_metrics as metrics
from tag_adapter import unit
from train_tag_adapter import save_npz
from train_positive_score import numpy_runtime

SOURCES = ('scripts/train_caption_adapter.py', 'services/audio-search/weighted_caption_adapter.py',
           'services/audio-search/interval_feature_cache.py', 'services/audio-search/device_feature_cache.py',
           'services/audio-search/device_calibration.py', 'services/audio-search/tag_adapter.py',
           'services/audio-search/expanded_caption_metrics.py', 'services/audio-search/holdout_contract.py',
           'services/audio-search/review_pack.py', 'scripts/holdout_assets.py', 'scripts/train_tag_adapter.py',
           'scripts/train_positive_score.py', 'services/audio-search/positive_score_adapter.py', 'scripts/evaluate_caption_gate.py')


def validate_config(cfg):
    require = h.require
    require(cfg['schema'] == 'sonora-caption-adapter-training-v1' and cfg['task_directory'] == '.local/a/mus054'
            and cfg['candidate_fits'] == 1 and cfg['alpha'] == 1.0 and cfg['fit_view'] == 'train'
            and (cfg['fit_recordings'], cfg['fit_components'], cfg['fit_intervals'], cfg['dimension']) == (37, 33, 209, 512)
            and (cfg['validation_recordings'], cfg['validation_intervals']) == (7, 23)
            and cfg['loss'] == 'sum_i(q_i*||X_i W-T_i||^2)+alpha*||W-I||_F^2'
            and cfg['weights'] == 'each_recording_equal_then_each_interval_equal'
            and cfg['solver'] == 'float64_weighted_dual_ridge_identity_prior'
            and cfg['text_target'] == 'MUS053_fixed_CLAP77token_prefix_all209_no_filter_no_reencode'
            and cfg['hyperparameter_search'] is cfg['validation_used_for_selection'] is False
            and cfg['comparators'] == ['identity', 'caption-ridge-1.0']
            and cfg['primary_development_metric'] == 'expanded140_whole_recording_macro_MRR'
            and cfg['bootstrap_iterations'] == 2000 and cfg['bootstrap_seed'] == 20261101054
            and cfg['blas_threads'] == 2 and cfg['seed'] == 0
            and cfg['new_audio_or_model_encodes'] == cfg['new_downloads'] == cfg['test_inputs'] == cfg['new_human_labels'] == 0
            and cfg['decision'] == 'retain_identity_no_automatic_selection_scale_up_or_deployment', 'One fixed caption training protocol required')


def human_development(w, retrieval, meta, windows):
    output = {}; ids = [r['source_track_id'] for r in meta['rows']]; text = retrieval['texts']
    mapped = unit(retrieval['features']@w)
    for pool in ('dev20', 'expanded140'):
        ix = [i for i, row in enumerate(meta['rows']) if pool == 'expanded140' or row['split'] == 'caption_dev']
        whole = text@mapped[ix].T
        segment = np.stack([(text@unit(windows[meta['rows'][i]['retrieval_window_indices']]@w).T).max(axis=1) for i in ix], axis=1)
        output[pool] = {'whole': metrics.paired(whole, retrieval['query_tracks'], [ids[i] for i in ix]),
                        'segment': metrics.paired(segment, retrieval['query_tracks'], [ids[i] for i in ix])}
    return output


def run(*, config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256); validate_config(cfg)
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean committed fit source required')
    h.require(Path(output).absolute().is_relative_to((ROOT/cfg['task_directory']).absolute()), 'Fit output must remain in fixed task directory')
    target = h.private_output(output); started = time.perf_counter()
    try:
        state = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        source = {n: h.file_hash(ROOT/n) for n in SOURCES}; runtime = numpy_runtime()
        doc = lambda k: h.assets.document(ROOT/cfg[k]['path'], cfg[k]['sha256'])
        interval_meta, retrieval_meta = doc('interval_cache'), doc('retrieval_cache')
        bound = {str(Path(config).absolute()): config_sha256}
        for name, meta in [('interval_cache', interval_meta), ('retrieval_cache', retrieval_meta)]:
            path = ROOT/cfg[name]['path']; bound[str(path)] = cfg[name]['sha256']
            bound[str(path.parent/'features.npz')] = meta['feature_sha256']
            bound[str(path.parent/'result.json')] = meta['result_sha256'] if name == 'interval_cache' else meta['parity_report_sha256']
            for n, digest in meta['key_context']['source_sha256'].items(): h.require(h.file_hash(ROOT/n) == digest, 'Frozen feature recipe changed')
        prior_path = ROOT/cfg['prior_identity']['path']; bound[str(prior_path)] = cfg['prior_identity']['sha256']
        for n, digest in bound.items(): h.require(h.file_hash(n) == digest, 'Bound input changed')
        args = {'cache': ROOT/cfg['interval_cache']['path'], 'cache_sha256': cfg['interval_cache']['sha256'],
                'expected_device': cfg['expected_device'], 'expected_model_sha256': cfg['expected_model_sha256']}
        train = intervals.ready_view(**args, split='train')
        h.require(train['audio'].shape == train['text'].shape == (209, 512) and len(set(train['recording_ids'])) == 37
                  and len(set(train['creator_components'])) == 33, 'Fixed train-only returned pairs required')
        h.write_json(target/'freeze.json', {'schema': 'sonora-caption-adapter-fit-freeze-v1', 'created_at_utc': h.now(),
                     'source_sha': state, 'source_sha256': source, 'input_sha256': bound, 'runtime': runtime,
                     'config_sha256': config_sha256, 'cache_key_sha256': train['cache_key_sha256'],
                     'fit_intervals': 209, 'fit_recordings': 37, 'fit_components': 33,
                     'validation_used_for_fit_or_selection': False,
                     'reader_integrity_loads_shared_npz_but_only_train_returned_for_solver': True})
        # Exclusive persistent claim survives failures and rejects a new-output-directory second fit.
        h.write_json(ROOT/cfg['task_directory']/'fit-started.json', {'source_sha': state, 'config_sha256': config_sha256,
                     'output': str(target), 'started_at_utc': h.now(), 'maximum_fit_attempts': 1})
        np.random.seed(0); fit_start = time.perf_counter()
        w, diagnostic = learner.fit(train['audio'], train['text'], train['weights'], train['recording_ids'], cfg['alpha'])
        fit_ms = (time.perf_counter()-fit_start)*1000
        save_npz(target/'adapter.npz', W=w)
        h.write_json(target/'fit.json', {'completed_at_utc': h.now(), 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                     'fit_ms': fit_ms, 'diagnostic': diagnostic, 'completed_fit_runs': 1, 'validation_used_for_fit_or_selection': False})
        h.write_json(target/'evaluation-open.json', {'opened_at_utc': h.now(), 'fit_receipt_sha256': h.file_hash(target/'fit.json'),
                     'views': ['validation', 'old_caption_retrieval'], 'reserved_test_inputs': 0})
        validation = intervals.ready_view(**args, split='validation')
        h.require(not set(train['recording_ids']) & set(validation['recording_ids'])
                  and not set(train['creator_components']) & set(validation['creator_components']), 'Validation group contamination')
        retrieval = features.ready_view(ROOT/cfg['retrieval_cache']['path'], cfg['retrieval_cache']['sha256'],
                         expected_device=cfg['expected_device'], expected_model_sha256=cfg['expected_model_sha256'], view='caption_retrieval')
        with np.load((ROOT/cfg['retrieval_cache']['path']).parent/'features.npz', allow_pickle=False) as f: windows = f['windows']
        results = {}
        for name, candidate in [('identity', np.eye(512)), ('caption-ridge-1.0', w)]:
            results[name] = {'human_development': human_development(candidate, retrieval, retrieval_meta, windows),
                             'generated_validation': learner.validation_metrics(validation['audio'], validation['text'], validation['recording_ids'], candidate)}
        prior = doc('prior_identity')
        for pool in ('dev20', 'expanded140'):
            for mode in ('whole', 'segment'):
                h.require(all(abs(results['identity']['human_development'][pool][mode]['recording_macro'][k]-prior['results']['identity'][pool][mode]['recording_macro'][k]) < 1e-12 for k in metrics.METRICS), 'Original identity development control changed')
        delta = lambda c, i: metrics.deltas(c, i, cfg['bootstrap_iterations'], cfg['bootstrap_seed'])
        paired = {'human_development': {pool: {mode: delta(results['caption-ridge-1.0']['human_development'][pool][mode], results['identity']['human_development'][pool][mode]) for mode in ('whole', 'segment')} for pool in ('dev20', 'expanded140')},
                  'generated_validation': {kind: delta(results['caption-ridge-1.0']['generated_validation'][kind], results['identity']['generated_validation'][kind]) for kind in ('exact_interval', 'recording_max_interval')}}
        h.require('torch' not in sys.modules and 'laion_clap' not in sys.modules, 'Frozen-feature CPU-only fit required')
        for n, digest in bound.items(): h.require(h.file_hash(n) == digest, 'Bound input changed during fit')
        h.require(numpy_runtime() == runtime and all(h.file_hash(ROOT/n) == digest for n, digest in source.items()), 'Runtime/source changed')
        result = {'schema': 'sonora-caption-adapter-training-result-v1', 'status': 'one_fixed_fit_and_development_evaluation_complete',
                  'source_sha': state, 'config_sha256': config_sha256, 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                  'runtime': runtime, 'counts': {'fit_runs': 1, 'fit_recordings': 37, 'fit_components': 33, 'fit_intervals': 209,
                      'validation_recordings': 7, 'validation_intervals': 23, 'human_dev_recordings': 20, 'human_dev_queries': 24,
                      'retrieval_candidates': 140, 'new_audio_or_model_encodes': 0, 'downloads': 0, 'reserved_test_inputs': 0},
                  'fit_ms': fit_ms, 'diagnostic': diagnostic, 'results': results, 'paired_deltas': paired,
                  'identity_control_matches_prior': True, 'torch_or_CLAP_imported': False, 'decision': cfg['decision'],
                  'total_ms': (time.perf_counter()-started)*1000,
                  'limits': ['Generated captions and only first77 tokens; not human semantic truth.',
                             'Seven validation recordings and previously seen human development; no new independent test.',
                             'Known exact pairs only, other intervals/recordings semantically unjudged.',
                             'One weighted unnormalized ridge objective; no CLAP fine tuning, hyperparameter search or production switch.']}
        h.write_json(target/'result-private.json', result)
        public = json.loads(json.dumps(result))
        for model in public['results'].values():
            for pool in model['human_development'].values():
                for values in pool.values(): values.pop('per_recording')
            for values in model['generated_validation'].values():
                values.pop('per_recording'); values.pop('ranks', None)
        h.write_json(target/'result-public.json', public)
        return public
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--config-sha256', required=True); parser.add_argument('--output', type=Path, required=True)
    result = run(**vars(parser.parse_args())); print(json.dumps({'status': result['status'], 'counts': result['counts'], 'fit_ms': result['fit_ms']}))


if __name__ == '__main__': main()
