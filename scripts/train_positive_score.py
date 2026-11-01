#!/usr/bin/env python3
"""One preregistered CPU/NumPy fit from typed GPU features; evaluate only after W is saved."""
from pathlib import Path
import argparse
import json
import os
# Bind BLAS threads before any NumPy import in this standalone process.
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '2'
import platform
import subprocess
import sys
import time
from importlib.metadata import distribution

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'services/audio-search'))
import numpy as np
import holdout_contract as h
import tag_adapter as a
import positive_score_adapter as learner
import expanded_caption_metrics as metrics
from device_feature_cache import ready_view
from train_tag_adapter import save_npz
from evaluate_caption_gate import tag_buckets

SOURCES = ('scripts/train_positive_score.py', 'services/audio-search/positive_score_adapter.py',
           'services/audio-search/device_feature_cache.py', 'services/audio-search/device_calibration.py',
           'services/audio-search/tag_adapter.py', 'services/audio-search/expanded_caption_metrics.py',
           'scripts/train_tag_adapter.py', 'scripts/evaluate_caption_gate.py')


def numpy_runtime():
    dist = distribution('numpy'); hashes = {}
    for entry in dist.files or []:
        if '..' not in entry.parts and entry.suffix in ('.py', '.so', '.dylib', '.json'):
            p = dist.locate_file(entry)
            if p.is_file() and not p.is_symlink(): hashes[str(entry)] = h.file_hash(p)
    return {'python': platform.python_version(), 'numpy': np.__version__, 'numpy_code_sha256': h.digest(h.canonical(hashes)),
            'system': platform.system(), 'machine': platform.machine(), 'device': 'cpu', 'dtype': 'float64',
            'thread_environment': {name: os.environ[name] for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS')}}


def evaluate(models, retrieval, meta, feature_path, validation, support):
    with np.load(feature_path, allow_pickle=False) as f: windows = f['windows']
    rows = meta['rows']; ids = [r['source_track_id'] for r in rows]; x, texts = retrieval['features'], retrieval['texts']
    output = {}
    for name, w in models.items():
        mapped = a.unit(x@w); output[name] = {}
        for pool in ('dev20', 'expanded140'):
            ix = [i for i, r in enumerate(rows) if pool == 'expanded140' or r['split'] == 'caption_dev']
            scores = texts@mapped[ix].T
            segment = np.stack([(texts@a.unit(windows[rows[i]['retrieval_window_indices']]@w).T).max(axis=1) for i in ix], axis=1)
            output[name][pool] = {'whole': metrics.paired(scores, retrieval['query_tracks'], [ids[i] for i in ix]),
                                 'segment': metrics.paired(segment, retrieval['query_tracks'], [ids[i] for i in ix])}
        output[name]['tag_validation'] = tag_buckets(a.unit(validation['features']@w), validation['prototypes'],
                            validation['positive_indices'], meta['vocabulary'], support)
    return output


def run(*, config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256)
    h.require(cfg['schema'] == 'sonora-positive-score-training-v1' and cfg['candidate_fits'] == 1
              and cfg['alpha'] == .01 and cfg['positive_cosine_margin'] == .05 and cfg['max_steps'] == 200
              and cfg['fit_view'] == 'tag_training' and cfg['test_inputs'] == cfg['new_audio_or_model_encoding'] == cfg['new_downloads'] == 0
              and cfg['hyperparameter_search'] is False and cfg['validation_used_for_early_stopping'] is False,
              'One fixed positive-score training protocol required')
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean committed training source required')
    target = h.private_output(output); started = time.perf_counter()
    try:
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        hashes = {p: h.file_hash(ROOT/p) for p in SOURCES}; runtime = numpy_runtime()
        cache = ROOT/cfg['cache']['path']; meta = h.assets.document(cache, cfg['cache']['sha256'])
        prior_path = ROOT/cfg['prior_result']['path']; prior = h.assets.document(prior_path, cfg['prior_result']['sha256'])
        feature_path = cache.parent/'features.npz'
        bound = {str(Path(config).absolute()): config_sha256, str(cache): cfg['cache']['sha256'],
                 str(feature_path): meta['feature_sha256'], str(cache.parent/'result.json'): meta['parity_report_sha256'],
                 str(prior_path): cfg['prior_result']['sha256']}
        for name, digest in meta['key_context']['source_sha256'].items(): h.require(h.file_hash(ROOT/name) == digest, 'Original device feature recipe changed')
        for name, digest in prior['adapter_artifact_sha256'].items():
            path = prior_path.parent/(name+'.npz'); bound[str(path)] = digest
        for p, digest in bound.items(): h.require(h.file_hash(p) == digest, 'Bound source/cache/oldW changed')
        args = {'cache': cache, 'cache_sha256': cfg['cache']['sha256'], 'expected_device': cfg['expected_device'],
                'expected_model_sha256': cfg['expected_model_sha256']}
        train = ready_view(**args, view='tag_training')
        h.require(train['features'].shape == (100, 512) and 'texts' not in train, 'Training-only typed features required')
        h.write_json(target/'freeze.json', {'schema': 'sonora-positive-score-fit-freeze-v1', 'created_at_utc': h.now(),
                     'source_sha': source, 'source_sha256': hashes, 'config_sha256': config_sha256,
                     'input_sha256': bound, 'runtime': runtime, 'fit_input_views': ['tag_training'], 'validation_loaded_for_fit': False,
                     'cache_key_sha256': train['cache_key_sha256'], 'fit_tracks': 100, 'test_inputs': 0})
        np.random.seed(cfg['seed']); fit_started = time.perf_counter()
        settings = {k: cfg[k] for k in ('alpha', 'initial_step', 'max_steps', 'max_backtracks', 'armijo', 'backtrack_factor', 'gradient_max_tol', 'relative_loss_tol')}
        w, diagnostic = learner.fit(train['features'], train['prototypes'], train['positive_indices'], margin=cfg['positive_cosine_margin'], **settings)
        fit_ms = (time.perf_counter()-fit_started)*1000
        save_npz(target/'adapter.npz', W=w)
        h.write_json(target/'fit.json', {'completed_at_utc': h.now(), 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                     'fit_ms': fit_ms, 'diagnostic': diagnostic, 'fit_runs': 1,
                     'validation_or_caption_data_used_for_fit_or_stopping': False})
        # All validation/retrieval views are obtained only after the single W/fit receipt is persisted.
        validation = ready_view(**args, view='tag_validation'); retrieval = ready_view(**args, view='caption_retrieval')
        h.write_json(target/'evaluation-open.json', {'opened_at_utc': h.now(), 'fit_receipt_sha256': h.file_hash(target/'fit.json'),
                     'views': ['tag_validation', 'caption_retrieval'], 'caption_split': 'already_seen_development', 'reserved_test_inputs': 0})
        models = {'identity': np.eye(512)}
        for name in prior['adapter_artifact_sha256']:
            with np.load(prior_path.parent/(name+'.npz'), allow_pickle=False) as f: models[name] = f['W']
        models['positive-score-0.01'] = w
        support = np.zeros(183, dtype=int)
        for positive in train['positive_indices']: support[positive] += 1
        results = evaluate(models, retrieval, meta, feature_path, validation, support)
        paired = {anchor: {pool: {mode: metrics.deltas(results['positive-score-0.01'][pool][mode], results[anchor][pool][mode],
                    cfg['bootstrap_iterations'], cfg['bootstrap_seed']) for mode in ('whole', 'segment')}
                    for pool in ('dev20', 'expanded140')} for anchor in cfg['paired_comparisons']}
        h.require('torch' not in sys.modules and 'laion_clap' not in sys.modules, 'Training must remain CPU NumPy without model imports')
        for p, digest in bound.items(): h.require(h.file_hash(p) == digest, 'Inputs changed during fit/evaluation')
        h.require(numpy_runtime() == runtime and all(h.file_hash(ROOT/p) == digest for p, digest in hashes.items()), 'Runtime/source changed')
        result = {'schema': 'sonora-positive-score-training-result-v1', 'status': 'one_fixed_fit_and_development_evaluation_complete',
                  'source_sha': source, 'config_sha256': config_sha256, 'cache_sha256': cfg['cache']['sha256'],
                  'cache_key_sha256': train['cache_key_sha256'], 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                  'runtime': runtime, 'counts': {'fit_runs': 1, 'fit_tracks': 100, 'tag_validation_tracks': 20,
                  'caption_dev_recordings': 20, 'caption_queries': 24, 'retrieval_candidates': 140, 'new_model_or_audio_encodes': 0,
                  'reserved_test_inputs': 0, 'downloads': 0}, 'fit_ms': fit_ms, 'diagnostic': diagnostic,
                  'results': results, 'paired_deltas': paired, 'training_tag_support': {t: int(c) for t, c in zip(meta['vocabulary'], support)},
                  'decision': 'retain_identity_no_automatic_selection_scale_up_or_deployment',
                  'torch_or_CLAP_imported': False, 'total_ms': (time.perf_counter()-started)*1000,
                  'limits': ['Positive-only uploaded tags are weak labels; unrecorded tags unknown, no complete semantic negatives.',
                             'One preregistered objective/parameter set on previously seen development, not new independent test.',
                             'Step limit without gradient/loss tolerance must not be called converged; loss decrease is not retrieval gain.',
                             'No CLAP fine-tuning, new corpus, full-window localization or production model/cache switch.']}
        h.write_json(target/'result-private.json', result)
        public = json.loads(json.dumps(result))
        for model in public['results'].values():
            for pool in ('dev20', 'expanded140'):
                for mode in ('whole', 'segment'): model[pool][mode].pop('per_recording')
        h.write_json(target/'result-public.json', public)
        return public
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    p = argparse.ArgumentParser(); p.add_argument('--config', type=Path, required=True)
    p.add_argument('--config-sha256', required=True); p.add_argument('--output', type=Path, required=True)
    result = run(**vars(p.parse_args())); print(json.dumps({'status': result['status'], 'counts': result['counts'], 'fit_ms': result['fit_ms']}))


if __name__ == '__main__': main()
