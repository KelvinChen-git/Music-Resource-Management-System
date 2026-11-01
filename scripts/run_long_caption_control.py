#!/usr/bin/env python3
"""Two immutable stages: explicit256 text encoding, then one CPU caption fit."""
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
import long_caption_features as longtext
import device_calibration as calibration
import device_feature_cache as features
import expanded_caption_metrics as metrics
import weighted_caption_adapter as learner
from tag_adapter import unit
from train_tag_adapter import save_npz
from train_caption_adapter import human_development, SOURCES as FIT_SOURCES
from train_positive_score import numpy_runtime

SOURCES = tuple(dict.fromkeys(('scripts/run_long_caption_control.py', 'services/audio-search/long_caption_features.py',
           'services/audio-search/checkpoint_model.py', 'services/audio-search/probe.py',
           'services/audio-search/preprocess.py', 'scripts/calibrate_encoder_device.py', *FIT_SOURCES)))
INPUTS = ('interval_cache', 'candidates', 'model_cache', 'retrieval_cache', 'baseline_result', 'baseline_adapter')


def validate_config(cfg):
    h.require(cfg['schema'] == 'sonora-long-caption-control-v1' and cfg['task_directory'] == '.local/a/mus055'
              and cfg['device'] == 'mps' and cfg['dimension'] == 512 and cfg['token_length'] == 256
              and cfg['baseline_token_length'] == 77 and cfg['text_batch'] == 6 and cfg['dtype'] == 'float32'
              and cfg['automatic_fallback'] is cfg['autocast'] is False
              and cfg['control_seed'] == longtext.SEED and cfg['controls'] == {'short_train': 3, 'long_train': 3, 'distinct_creator_components': 6}
              and cfg['atol_vector_maxabs'] == cfg['atol_cosine_distance'] == 1e-4
              and cfg['alpha'] == 1.0 and cfg['candidate_fits'] == 1 and cfg['weights'] == 'each_recording_equal_then_each_interval_equal'
              and cfg['primary_metric'] == 'expanded140_whole_recording_macro_MRR_new256_minus_saved77'
              and cfg['human_query_text_features'] == 'unchanged_MUS048_24texts' and cfg['validation_query_lengths'] == [77, 256]
              and cfg['bootstrap_iterations'] == 2000 and cfg['bootstrap_seed'] == 20261101055 and cfg['hyperparameter_search'] is False
              and (cfg['fit_recordings'], cfg['fit_intervals'], cfg['validation_recordings'], cfg['validation_intervals']) == (37, 209, 7, 23)
              and cfg['new_audio_encodes'] == cfg['new_downloads'] == cfg['new_test_inputs'] == cfg['new_human_labels'] == 0
              and cfg['decision'] == 'retain_identity_no_automatic_selection_scale_up_or_deployment', 'Fixed256 no-search paired control required')


def open_run(config, config_sha256, output):
    cfg = h.assets.document(config, config_sha256); validate_config(cfg)
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(), 'Clean committed control source required')
    h.require(Path(output).absolute().is_relative_to((ROOT/cfg['task_directory']).absolute()), 'Fixed task directory required')
    target = h.private_output(output)
    bound = {str(Path(config).absolute()): config_sha256}
    bound.update({str((ROOT/cfg[k]['path']).absolute()): cfg[k]['sha256'] for k in INPUTS})
    docs = {k: h.assets.document(ROOT/cfg[k]['path'], cfg[k]['sha256']) for k in ('interval_cache', 'model_cache', 'retrieval_cache')}
    for name in ('interval_cache', 'retrieval_cache'):
        meta = docs[name]; path = ROOT/cfg[name]['path']
        bound[str(path.parent/'features.npz')] = meta['feature_sha256']
        bound[str(path.parent/'result.json')] = meta.get('result_sha256', meta.get('parity_report_sha256'))
        for n, digest in meta['key_context']['source_sha256'].items(): h.require(h.file_hash(ROOT/n) == digest, 'Original feature source changed')
    for n, digest in bound.items(): h.require(h.file_hash(n) == digest, 'Bound input changed')
    state = {'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'source_sha256': {n: h.file_hash(ROOT/n) for n in SOURCES}, 'input_sha256': bound,
             'config_sha256': config_sha256, 'created_at_utc': h.now()}
    return cfg, target, docs, state


def recheck(state):
    for n, digest in state['input_sha256'].items(): h.require(h.file_hash(n) == digest, 'Bound input changed during control')
    h.require(all(h.file_hash(ROOT/n) == digest for n, digest in state['source_sha256'].items()), 'Source changed during control')


def build(*, config, config_sha256, output):
    cfg, target, docs, state = open_run(config, config_sha256, output); started = time.perf_counter()
    try:
        base, old = docs['interval_cache'], docs['model_cache']; rows = base['rows']
        texts = longtext.captions_for(h.assets.document(ROOT/cfg['candidates']['path'], cfg['candidates']['sha256']), rows)
        lengths = base['token_lengths']; controls = longtext.controls(rows, lengths); ix = controls['short']+controls['long']
        environment = h.environment(); environment['device'] = 'mps'
        h.require(environment == base['key_context']['environment'] and old['model']['sha256'] == base['model_sha256'], 'Frozen model/environment differs')
        h.require(h.checkpoint_pin(old['model']['path'], 'A') == old['model'], 'Original checkpoint changed')
        state['input_sha256'][old['model']['path']] = old['model']['sha256']
        context = {'device': 'mps', 'environment': environment, 'model_sha256': old['model']['sha256'],
                   'input_sha256': h.digest(h.canonical(state['input_sha256'])), 'recipe_sha256': config_sha256, 'source_sha256': state['source_sha256']}
        key = calibration.cache_key(**context)
        h.write_json(target/'freeze.json', {**state, 'key_context': context, 'cache_key_sha256': key,
                     'control_indices': controls, 'rows_sha256': h.digest(h.canonical(rows))})
        h.write_json(ROOT/cfg['task_directory']/'encode-started.json', {'source_sha': state['source_sha'],
                     'config_sha256': config_sha256, 'output': str(target), 'started_at_utc': h.now()})
        import torch
        from checkpoint_model import load_checkpoint, checked_checkpoint
        from calibrate_encoder_device import setup, synchronize
        decision = calibration.device_status('mps', {'torch_available': True, 'mps_available': torch.backends.mps.is_available()},
                                             mps_fallback=os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1')
        h.require(decision['status'] == 'ready', 'Explicit MPS unavailable; no CPU fallback')
        setup(torch, 'mps'); start = time.perf_counter(); sdk, strict = load_checkpoint(old['model']['path'], 'A')
        for param in sdk.model.parameters(): param.requires_grad_(False)
        model_load_ms = (time.perf_counter()-start)*1000
        h.require(sdk.model.text_branch_type == 'roberta' and sdk.model.text_branch.config.max_position_embeddings >= 258, 'RoBERTa256 positional capacity required')
        raw_ids = [sdk.tokenize(text, truncation=False)['input_ids'] for text in texts]
        h.require([len(ids) for ids in raw_ids] == lengths, 'Original token lengths changed')
        tokenizer = lambda values, length: sdk.tokenize(values, padding='max_length', truncation=True, max_length=length, return_tensors='pt')
        proof = longtext.token_proof(tokenizer(texts, 256), raw_ids)
        h.write_json(target/'token-proof.json', proof)
        encode = lambda values, length: unit(features.matrix(np.concatenate([
            sdk.get_text_embedding(values[i:i+6], tokenizer=lambda batch: tokenizer(batch, length), use_tensor=False)
            for i in range(0, len(values), 6)]), (len(values), 512)))
        with np.load((ROOT/cfg['interval_cache']['path']).parent/'features.npz', allow_pickle=False) as f: text77 = f['text']
        with torch.inference_mode():
            start = time.perf_counter(); cpu77 = encode([texts[i] for i in ix], 77); cpu256 = encode([texts[i] for i in ix], 256)
            cpu_ms = (time.perf_counter()-start)*1000
            save_npz(target/'cpu-controls.npz', text77=cpu77, text256=cpu256)
            sdk.model.to(torch.device('mps')); sdk.device = torch.device('mps')
            h.require(all(str(p.device) == 'mps:0' and not p.requires_grad and (not p.is_floating_point() or p.dtype == torch.float32)
                          for p in sdk.model.parameters()), 'Frozen FP32 MPS required')
            synchronize(torch, 'mps'); start = time.perf_counter(); text256 = encode(texts, 256); synchronize(torch, 'mps')
            mps_ms = (time.perf_counter()-start)*1000
        short = [i for i, n in enumerate(lengths) if n <= 77]
        parity = {'CPU77_to_old77_controls': features.vector_parity(cpu77, text77[ix], cfg),
                  'CPU256_to_MPS256_controls': features.vector_parity(cpu256, text256[ix], cfg),
                  'all_short256_to_old77': features.vector_parity(text77[short], text256[short], cfg)}
        passed = all(v['status'] == 'passed' for v in parity.values())
        save_npz(target/'features.npz', text256=text256)
        recheck(state); checked_checkpoint(old['model']['path'], 'A')
        final = h.environment(); final['device'] = 'mps'; h.require(final == environment, 'Encoding environment changed')
        long_ix = [i for i, n in enumerate(lengths) if n > 77]; cosine = np.sum(unit(text77[long_ix])*unit(text256[long_ix]), axis=1)
        result = {'schema': 'sonora-long-caption-build-result-v1', 'status': 'passed' if passed else 'failed',
                  'source_sha': state['source_sha'], 'config_sha256': config_sha256, 'cache_key_sha256': key,
                  'captions': 232, 'truncated_captions': 0, 'previously_truncated_captions': len(long_ix),
                  'untruncated_tokens_min': min(lengths), 'untruncated_tokens_max': max(lengths), 'encoded_length': 256,
                  'vector_parity': parity, 'strict': strict, 'ready_cache_written': passed,
                  'long_caption_cosine_to_prefix': {'min': float(cosine.min()), 'median': float(np.median(cosine)), 'max': float(cosine.max())},
                  'timing_ms': {'model_load': model_load_ms, 'CPU_controls77_and256': cpu_ms, 'MPS_all232_text256': mps_ms,
                                'total_including_integrity': (time.perf_counter()-started)*1000},
                  'new_audio_encodes': 0, 'downloads': 0, 'fit_runs': 0, 'test_inputs': 0,
                  'limits': ['Text encoding correctness only, not improved semantics or retrieval.', 'Six fixed train CPU controls, not full232 CPU parity.']}
        h.write_json(target/'result.json', result)
        if passed:
            h.write_json(target/'cache.json', {'schema': 'sonora-long-caption-text-cache-v1', 'status': 'ready_after_parity',
                         'device': 'mps', 'model_sha256': old['model']['sha256'], 'policy': longtext.POLICY, 'token_length': 256,
                         'base_cache_sha256': cfg['interval_cache']['sha256'], 'rows_sha256': h.digest(h.canonical(rows)),
                         'token_lengths': lengths, 'control_indices': controls, 'key_context': context, 'cache_key_sha256': key,
                         'feature_sha256': h.file_hash(target/'features.npz'), 'result_sha256': h.file_hash(target/'result.json')})
        return result
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def fit(*, config, config_sha256, output, text_cache, text_sha256):
    cfg, target, docs, state = open_run(config, config_sha256, output); started = time.perf_counter()
    try:
        overlay = h.assets.document(text_cache, text_sha256); report = h.assets.document(Path(text_cache).parent/'result.json', overlay['result_sha256'])
        h.require(report['config_sha256'] == config_sha256 and report['source_sha'] == state['source_sha'], 'Same committed build recipe required')
        state['input_sha256'].update({str(Path(text_cache).absolute()): text_sha256,
                   str((Path(text_cache).parent/'features.npz').absolute()): overlay['feature_sha256'],
                   str((Path(text_cache).parent/'result.json').absolute()): overlay['result_sha256']})
        args = {'base_cache': ROOT/cfg['interval_cache']['path'], 'base_sha256': cfg['interval_cache']['sha256'],
                'text_cache': text_cache, 'text_sha256': text_sha256, 'expected_device': 'mps', 'expected_model_sha256': overlay['model_sha256']}
        train = longtext.ready_view(**args, split='train'); runtime = numpy_runtime()
        h.require(train['audio'].shape == train['text'].shape == (209, 512) and len(set(train['recording_ids'])) == 37, 'Fixed209/37 train only required')
        h.write_json(target/'freeze.json', {**state, 'runtime': runtime, 'text_cache_sha256': text_sha256,
                     'fit_recordings': 37, 'fit_intervals': 209, 'alpha': 1.0, 'validation_used_for_fit_or_selection': False})
        h.write_json(ROOT/cfg['task_directory']/'fit-started.json', {'source_sha': state['source_sha'], 'config_sha256': config_sha256,
                     'output': str(target), 'started_at_utc': h.now(), 'maximum_fit_attempts': 1})
        start = time.perf_counter(); w, diagnostic = learner.fit(train['audio'], train['text'], train['weights'], train['recording_ids'], 1.0)
        fit_ms = (time.perf_counter()-start)*1000; save_npz(target/'adapter.npz', W=w)
        h.write_json(target/'fit.json', {'completed_at_utc': h.now(), 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                     'diagnostic': diagnostic, 'fit_ms': fit_ms, 'fit_runs': 1, 'baseline77_refit_runs': 0})
        h.write_json(target/'evaluation-open.json', {'opened_at_utc': h.now(), 'fit_receipt_sha256': h.file_hash(target/'fit.json'),
                     'human_query_features_unchanged': True, 'validation_query_lengths': [77, 256], 'reserved_test_inputs': 0})
        val = longtext.ready_view(**args, split='validation')
        h.require(not set(train['recording_ids']) & set(val['recording_ids']) and not set(train['creator_components']) & set(val['creator_components']), 'Split contamination')
        retrieval = features.ready_view(ROOT/cfg['retrieval_cache']['path'], cfg['retrieval_cache']['sha256'], expected_device='mps',
                                       expected_model_sha256=overlay['model_sha256'], view='caption_retrieval')
        with np.load((ROOT/cfg['retrieval_cache']['path']).parent/'features.npz', allow_pickle=False) as f: windows = f['windows']
        baseline = h.assets.document(ROOT/cfg['baseline_result']['path'], cfg['baseline_result']['sha256'])
        h.require(baseline['adapter_sha256'] == cfg['baseline_adapter']['sha256'], 'Saved77 adapter identity differs')
        with np.load(ROOT/cfg['baseline_adapter']['path'], allow_pickle=False) as f: w77 = f['W']
        results = {}
        for name, candidate in [('identity', np.eye(512)), ('caption77', w77), ('caption256', w)]:
            results[name] = {'human_development': human_development(candidate, retrieval, docs['retrieval_cache'], windows),
                  'generated_validation': {label: learner.validation_metrics(val['audio'], text, val['recording_ids'], candidate)
                                           for label, text in [('query77', val['text77']), ('query256', val['text'])]}}
        for name, oldname in [('identity', 'identity'), ('caption77', 'caption-ridge-1.0')]:
            h.require(results[name]['human_development'] == baseline['results'][oldname]['human_development']
                      and results[name]['generated_validation']['query77'] == baseline['results'][oldname]['generated_validation'], 'Original77 controls did not reproduce')
        delta = lambda c, b: metrics.deltas(c, b, cfg['bootstrap_iterations'], cfg['bootstrap_seed'])
        paired = {anchor: {'human_development': {pool: {mode: delta(results['caption256']['human_development'][pool][mode], results[anchor]['human_development'][pool][mode])
                            for mode in ('whole', 'segment')} for pool in ('dev20', 'expanded140')},
                          'generated_validation': {query: {kind: delta(results['caption256']['generated_validation'][query][kind], results[anchor]['generated_validation'][query][kind])
                            for kind in ('exact_interval', 'recording_max_interval')} for query in ('query77', 'query256')}} for anchor in ('identity', 'caption77')}
        h.require('torch' not in sys.modules and 'laion_clap' not in sys.modules, 'Fit process must remain CPU NumPy only')
        recheck(state); h.require(numpy_runtime() == runtime, 'CPU runtime changed')
        result = {'schema': 'sonora-long-caption-fit-result-v1', 'status': 'one_fixed_fit_and_control_complete', 'source_sha': state['source_sha'],
                  'config_sha256': config_sha256, 'text_cache_sha256': text_sha256, 'adapter_sha256': h.file_hash(target/'adapter.npz'),
                  'counts': {'fit_runs': 1, 'baseline77_refit_runs': 0, 'train_recordings': 37, 'train_intervals': 209, 'validation_recordings': 7,
                             'validation_intervals': 23, 'human_dev_recordings': 20, 'human_dev_queries': 24, 'retrieval_candidates': 140,
                             'new_audio_encodes': 0, 'downloads': 0, 'test_inputs': 0},
                  'runtime': runtime, 'fit_ms': fit_ms, 'diagnostic': diagnostic, 'results': results, 'paired_deltas': paired,
                  'original77_controls_reproduced': True, 'torch_or_CLAP_imported': False, 'decision': cfg['decision'],
                  'total_ms': (time.perf_counter()-started)*1000,
                  'limits': ['Full generated text remains weak supervision, not human semantic truth.',
                             'Previously seen development and seven validation recordings, not a new blind test.',
                             'Query length crossed separately; primary human query features held fixed.',
                             'No original CLAP fine tuning, hyperparameter search or deployment.']}
        h.write_json(target/'result-private.json', result); public = json.loads(json.dumps(result))
        for model in public['results'].values():
            for pool in model['human_development'].values():
                for values in pool.values(): values.pop('per_recording')
            for query in model['generated_validation'].values():
                for values in query.values(): values.pop('per_recording'); values.pop('ranks', None)
        h.write_json(target/'result-public.json', public); return public
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    p = argparse.ArgumentParser(); commands = p.add_subparsers(dest='stage', required=True)
    for stage in ('build', 'fit'):
        sub = commands.add_parser(stage); sub.add_argument('--config', type=Path, required=True); sub.add_argument('--config-sha256', required=True)
        sub.add_argument('--output', type=Path, required=True)
        if stage == 'fit': sub.add_argument('--text-cache', type=Path, required=True); sub.add_argument('--text-sha256', required=True)
    values = vars(p.parse_args()); stage = values.pop('stage'); result = (build if stage == 'build' else fit)(**values)
    print(json.dumps({'status': result['status'], 'captions': result.get('captions'), 'counts': result.get('counts'), 'fit_ms': result.get('fit_ms')}))
    if stage == 'build' and result['status'] != 'passed': raise SystemExit(1)


if __name__ == '__main__': main()
