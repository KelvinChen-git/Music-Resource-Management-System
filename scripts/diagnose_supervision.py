#!/usr/bin/env python3
"""One read-only cached diagnostic, no new learner, encoder, labels or test scoring."""
from pathlib import Path
import argparse
import json
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '2'
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services/audio-search'))
import numpy as np
import holdout_contract as h
import supervision_diagnostic as d
import expanded_pair_features as pairs
import device_feature_cache as features
from train_positive_score import numpy_runtime
from weighted_caption_adapter import recording_weights

SOURCES = ('scripts/diagnose_supervision.py', 'services/audio-search/supervision_diagnostic.py',
           'services/audio-search/expanded_pair_features.py', 'services/audio-search/interval_feature_cache.py',
           'services/audio-search/weighted_caption_adapter.py', 'services/audio-search/device_feature_cache.py',
           'services/audio-search/device_calibration.py', 'services/audio-search/tag_adapter.py',
           'services/audio-search/review_pack.py', 'services/audio-search/holdout_contract.py',
           'scripts/holdout_assets.py', 'scripts/train_positive_score.py')


def validate(c):
    h.require(c['schema'] == 'sonora-supervision-diagnostic-v1' and c['task_directory'] == '.local/a/mus059'
              and c['subsets'] == ['train100', 'original37', 'new63', 'validation20']
              and c['dimension'] == 512 and c['ngram_n'] == 5 and c['common_ngram_min_train_recording_fraction'] == .2
              and c['near_duplicate_jaccard'] == .8 and c['heuristics_only_not_semantic_labels'] is True
              and c['candidate_models'] == ['identity', 'saved37-fulltext-ridge', 'expanded100-fulltext-ridge']
              and c['ridge_attribution'] == 'saved_delta_normal_equation_rhs_mean_centered_decomposition_no_solve'
              and c['alpha'] == 1. and c['label_edits'] == c['fits'] == c['new_encodes'] == c['downloads'] == c['test_inputs'] == 0
              and c['automatic_selection_or_deployment'] is False, 'Fixed descriptive no-learning protocol required')


def bound_human_texts(dataset, original_meta, retrieval_meta):
    dev = {r['source_track_id']: r for r in dataset['selected']['caption_dev']}
    # The MPS retrieval pool is sorted independently; query order stays with the original cache.
    texts = [q['text'] for r in original_meta['rows'] if r['split'] == 'caption_dev'
             for q in dev[r['source_track_id']]['captions']]
    tracks = [r['source_track_id'] for r in original_meta['rows'] if r['split'] == 'caption_dev'
              for q in dev[r['source_track_id']]['captions']]
    h.require(len(texts) == 24 and [h.digest(t.encode()) for t in texts] == retrieval_meta['query_text_sha256']
              == original_meta['query_text_sha256'] and tracks == retrieval_meta['query_tracks']
              == original_meta['query_tracks'], 'Only existing complete24 bound development texts required')
    return texts


def run(*, config, config_sha256, output):
    c = h.assets.document(config, config_sha256); validate(c)
    h.require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Clean committed diagnostic required')
    task = ROOT/c['task_directory']
    h.require(Path(output).absolute().is_relative_to(task.absolute()) and not (task/'diagnostic-started.json').exists(),
              'Task-local diagnostic already attempted or invalid output; no new-directory restart')
    target = h.private_output(output)
    try:
        docs = {}; bound = {str(Path(config).absolute()): config_sha256}
        for k, pin in c.items():
            if isinstance(pin, dict) and set(pin) == {'path', 'sha256'}:
                path = ROOT/pin['path']; bound[str(path.absolute())] = pin['sha256']
                if path.suffix == '.json': docs[k] = h.assets.document(path, pin['sha256'])
        for name in ('expanded_cache', 'retrieval_cache'):
            meta = docs[name]; directory = (ROOT/c[name]['path']).parent
            bound[str(directory/'features.npz')] = meta['feature_sha256']
            bound[str(directory/'result.json')] = meta.get('result_sha256', meta.get('parity_report_sha256'))
        for n, pin in bound.items(): h.require(h.file_hash(n) == pin, 'Bound inputs changed')
        args = {'cache': ROOT/c['expanded_cache']['path'], 'cache_sha256': c['expanded_cache']['sha256'],
                'expected_device': 'mps', 'expected_model_sha256': c['expected_model_sha256']}
        pairs.ready_view(**args, split='train'); pairs.ready_view(**args, split='validation')
        rows = docs['expanded_cache']['rows']
        candidates = sorted(docs['old_candidates']['candidates']+docs['new_candidates']['candidates'],
                            key=lambda r: (int(r['id']), r['start_time'], r['end_time']))
        h.require(len(candidates) == len(rows) == 599 and all(all(r[k] == s[k] for k in
                  ('id', 'start_time', 'end_time', 'raw_line_sha256')) and h.digest(s['caption'].encode()) == r['caption_sha256']
                  for r, s in zip(rows, candidates)), 'Exact599 unchanged captions required')
        texts = [r['caption'] for r in candidates]
        with np.load((ROOT/c['expanded_cache']['path']).parent/'features.npz', allow_pickle=False) as f: audio, text = f['audio'], f['text']
        with np.load(ROOT/c['baseline_adapter']['path'], allow_pickle=False) as f: prior = f['W']
        with np.load(ROOT/c['expanded_adapter']['path'], allow_pickle=False) as f: expanded = f['W']
        h.require(docs['expanded_result']['adapter_sha256'] == c['expanded_adapter']['sha256']
                  and docs['baseline_result']['adapter_sha256'] == c['baseline_adapter']['sha256'], 'Saved model identity differs')
        retrieval = features.ready_view(ROOT/c['retrieval_cache']['path'], c['retrieval_cache']['sha256'],
                         expected_device='mps', expected_model_sha256=c['expected_model_sha256'], view='caption_retrieval')
        human = bound_human_texts(docs['human_dataset'], docs['human_text_metadata'], docs['retrieval_cache'])
        original_ids = {r['id'] for r in docs['old_cache']['rows']}
        subsets = {'train100': [i for i, r in enumerate(rows) if r['split'] == 'train'],
                   'original37': [i for i, r in enumerate(rows) if r['split'] == 'train' and r['id'] in original_ids],
                   'new63': [i for i, r in enumerate(rows) if r['split'] == 'train' and r['id'] not in original_ids],
                   'validation20': [i for i, r in enumerate(rows) if r['split'] == 'validation']}
        h.require([len(v) for v in subsets.values()] == [539, 209, 330, 60], 'Fixed diagnostic subsets required')
        runtime = numpy_runtime(); h.require(runtime == docs['expanded_result']['runtime'], 'Same frozen NumPy runtime required')
        source = {n: h.file_hash(ROOT/n) for n in SOURCES}
        state = {'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                 'source_sha256': source, 'input_sha256': bound, 'config_sha256': config_sha256, 'runtime': runtime, 'created_at_utc': h.now()}
        h.write_json(target/'freeze.json', state)
        h.write_json(task/'diagnostic-started.json', {'source_sha': state['source_sha'], 'config_sha256': config_sha256,
                     'started_at_utc': h.now(), 'maximum_attempts': 1, 'fits': 0})
        lexical, private_lexical, vocabulary = d.text_audit(texts, rows, n=c['ngram_n'],
                     prevalence=c['common_ngram_min_train_recording_fraction'], near=c['near_duplicate_jaccard'])
        geometry = {}; contrasts = {}; language = {}
        for name, ix in subsets.items():
            ids = [rows[i]['id'] for i in ix]
            geometry[name] = {'audio': d.geometry(audio[ix], ids), 'text': d.geometry(text[ix], ids)}
            contrasts[name] = {label: d.score_contrasts(audio[ix], text[ix], ids, w) for label, w in
                              zip(c['candidate_models'], [np.eye(512), prior, expanded])}
            language[name] = d.language_coverage([texts[i] for i in ix], ids, vocabulary,
                                              [docs['expanded_cache']['token_lengths'][i] for i in ix])
        train = subsets['train100']; old = subsets['original37']; new = subsets['new63']
        attribution = {name: d.ridge_attribution(audio[ix], text[ix], [rows[i]['id'] for i in ix], w)
                       for name, ix, w in [('saved37', old, prior), ('expanded100', train, expanded)]}
        h.require(all(v['normal_equation_maxabs'] < 1e-12 for v in attribution.values()), 'Saved training normal equations do not match')
        delta37, delta100 = prior-np.eye(512), expanded-np.eye(512)
        updates = {'delta_difference_frobenius': float(np.linalg.norm(expanded-prior)),
                   'delta_direction_cosine': float(np.sum(delta37*delta100)/np.linalg.norm(delta37)/np.linalg.norm(delta100)),
                   'original37_new63_text_mean_direction_cosine': d.mean_direction_cosine(text[old], [rows[i]['id'] for i in old], text[new], [rows[i]['id'] for i in new])}
        qids = retrieval['query_tracks']; language['human_dev20'] = d.language_coverage(human, qids, vocabulary, docs['human_text_metadata']['caption_token_lengths'])
        changes = d.ranking_changes(retrieval['texts'], retrieval['features'], [r['source_track_id'] for r in docs['retrieval_cache']['rows']], qids, prior, expanded)
        private_ranks = changes.pop('private')
        main = docs['expanded_result']['paired_deltas']['saved37-fulltext-ridge']['human_development']['expanded140']['whole']['MRR']
        coverage = {'human_recordings': len(set(qids)), 'human_queries': len(human), 'candidate_recordings': 140,
                    'unqueried_candidate_recordings': 120, 'known_positive_pair_per_query': 1,
                    'other_pairs_are_human_judged_negatives': False, 'ranking_changes_37_to100': changes,
                    'already_published_MRR_delta': main, 'scope': 'Previously seen human development only; no held-out labels opened.'}
        for n, pin in bound.items(): h.require(h.file_hash(n) == pin, 'Diagnostic inputs changed')
        h.require(runtime == numpy_runtime() and all(h.file_hash(ROOT/n) == pin for n, pin in source.items())
                  and not any(n in sys.modules for n in ('torch', 'laion_clap')), 'Unexpected source/runtime change or encoder import')
        result = {'schema': 'sonora-supervision-diagnostic-result-v1', 'status': 'descriptive_diagnostic_complete',
                  'source_sha': state['source_sha'], 'config_sha256': config_sha256, 'lexical': lexical, 'geometry': geometry,
                  'score_contrasts': contrasts, 'ridge_attribution': attribution, 'saved_updates_comparison': updates,
                  'language_coverage': language, 'evaluation_coverage': coverage, 'fits': 0, 'encodes': 0, 'downloads': 0,
                  'label_edits': 0, 'test_inputs': 0, 'semantic_label_quality_verified': False,
                  'decision': 'retain_identity_no_automatic_data_filtering_or_new_training',
                  'limits': ['Heuristic text repetition and embedding geometry cannot verify audible semantic correctness.',
                             'All alternative song/interval pairs remain unjudged, not labeled negatives.',
                             'Algebra is descriptive of two saved ridge models, not causal proof or a new candidate.',
                             'Same previously seen development; no selection, new learner, encoder or held-out test.']}
        h.write_json(target/'private-details.json', {'lexical': private_lexical, 'human_rank_details': private_ranks})
        h.write_json(target/'result.json', result); return result
    except Exception as exc:
        h.write_json(target/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc)}); raise


def main():
    p = argparse.ArgumentParser()
    for n in ('config', 'output'): p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--config-sha256', required=True)
    print(json.dumps(run(**vars(p.parse_args()))))


if __name__ == '__main__': main()
