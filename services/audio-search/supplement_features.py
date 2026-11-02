"""Strict six-source overlay; preserve old140 vectors and full original text."""
from collections import Counter, defaultdict
import csv
import io
from pathlib import Path
import numpy as np

import holdout_contract as h
from human_caption_capacity import identity
from device_feature_cache import matrix
import device_calibration as calibration
from tag_adapter import unit
import expanded_caption_metrics as metrics

COUNTS = {'old_candidates': 140, 'new_candidates': 6, 'combined_candidates': 146,
          'old_queries': 24, 'new_queries': 7, 'old_query_recordings': 20,
          'new_query_recordings': 6, 'old_windows': 624, 'new_windows': 18}


def validate(c):
    h.require(c['schema'] == 'sonora-six-supplement-retrieval-v1' and c['task_directory'] == '.local/a/mus064'
              and c['device'] == 'mps' and c['dimension'] == 512 and c['dtype'] == 'float32'
              and c['autocast'] is c['automatic_fallback'] is False
              and c['audio_batch'] == 3 and c['text_batch'] == 6 and c['token_length'] == 256
              and c['counts'] == COUNTS and c['models'] == ['identity', 'saved100-fulltext-ridge']
              and c['text_policy'] == 'exact_original_UTF8_text_and_untruncated_token_equality_or_fail'
              and c['audio_policy'] == 'canonical65536_EOF48k_mono;first_min120_seconds;first_mid_last10s;unit_mean_unit'
              and c['CPU_controls'] == 'all18_new_audio_windows_all6_aggregates_all7_texts256;short_CPU77_vs256_when_applicable'
              and c['blas_threads'] == 2 and c['seed'] == 0
              and c['primary_metric'] == 'new6_recording_macro_whole_MRR_saved100_minus_identity'
              and c['query_pools'] == ['new6', 'old20_control'] and c['retrieval_modes'] == ['whole', 'segment']
              and c['original140_control_must_reproduce'] is True
              and c['bootstrap_iterations'] == 2000 and c['bootstrap_seed'] == 20261102064
              and c['atol_vector_maxabs'] == c['atol_cosine_distance'] == 1e-4
              and c['operations'] == dict.fromkeys(('downloads', 'fits', 'reserved_test_inputs', 'new_manual_labels'), 0)
              and c['decision'] == 'retain_identity_no_automatic_selection_or_deployment',
              'Fixed fulltext/no-fit six-source comparison required')


def queries(raw, selected):
    """Access caption text only after both selected-ID and valid-flag checks."""
    ids = [r['source_track_id'] for r in selected]
    h.require(len(ids) == len(set(ids)) == 6, 'Fixed six source IDs required')
    grouped = defaultdict(list)
    for row in csv.DictReader(io.StringIO(raw.decode('utf8'))):
        tid = identity(row['track_id'], 'track')
        if tid not in ids or row['is_valid_subset'].lower() not in ('true', '1'): continue
        text = row['caption']
        h.require(isinstance(text, str) and text.strip() and row['caption_id'], 'Nonempty original human caption required')
        grouped[tid].append({'track_id': tid, 'caption_id': row['caption_id'], 'text': text,
                             'text_sha256': h.digest(text.encode('utf8'))})
    result = []
    for row in selected:
        found = grouped[row['source_track_id']]
        h.require(len(found) == row['validated_caption_count'], 'Frozen per-source caption count changed')
        result.extend(found)
    h.require(len(result) == 7 and len({r['caption_id'] for r in result}) == 7, 'Exactly seven original unique captions required')
    return result


def new_rows(corpus):
    rows = []
    for i, source in enumerate(corpus['tracks']):
        n = source['audio_preflight']['retrieval_clip_samples']
        h.require(n == min(source['decode']['decoded_samples'], 120*48000) and n >= 30*48000,
                  'Actual first120 source view required')
        starts = sorted({0, max(0, n-480000)//2, max(0, n-480000)})
        h.require(len(starts) == 3 and all(0 <= x <= n-480000 for x in starts), 'Three bounded10-second windows required')
        rows.append({'source_track_id': source['source_track_id'], 'origin': 'new', 'split': 'supplement_dev',
            'creator_component': source['creator_component'], 'pcm_sha256': source['audio_preflight']['pcm_sha256'],
            'validated_caption_count': source['validated_caption_count'],
            'retrieval_clip_samples': n, 'window_start_samples': starts,
            'retrieval_window_indices': list(range(624+3*i, 624+3*i+3))})
    h.require(len(rows) == len({r['source_track_id'] for r in rows}) == 6
              and len({r['creator_component'] for r in rows}) == 6, 'Six original source components required')
    return rows


def merge(old_meta, old_whole, old_windows, old_text, rows, new_windows, new_text):
    for value, shape in [(old_whole, (140, 512)), (old_windows, (624, 512)), (old_text, (24, 512)),
                         (new_windows, (18, 512)), (new_text, (7, 512))]: matrix(value, shape)
    h.require(old_whole.dtype == old_windows.dtype == old_text.dtype == np.float64,
              'Original cache float64 serialization must be preserved')
    oldrows = [{**r, 'origin': 'old'} for r in old_meta['rows']]
    h.require(len(oldrows) == 140 and len(rows) == 6
              and not {r['source_track_id'] for r in oldrows} & {r['source_track_id'] for r in rows},
              'New sources must not reuse old140')
    new_whole = unit(new_windows.reshape(6, 3, 512).mean(axis=1))
    values = list(zip(oldrows, old_whole)) + list(zip(rows, new_whole))
    values.sort(key=lambda item: item[0]['source_track_id'])
    return {'rows': [r for r, v in values], 'whole': np.stack([v for r, v in values]),
            'windows': np.concatenate([old_windows, new_windows]),
            'old_texts': old_text.copy(), 'new_texts': new_text.copy()}


def ready_view(cache, cache_sha256, *, old_cache, old_sha256, expected_device, expected_model_sha256):
    meta = h.assets.document(cache, cache_sha256)
    h.require(meta['schema'] == 'sonora-six-supplement-feature-cache-v1' and meta['status'] == 'ready_after_parity'
              and meta['counts'] == COUNTS and meta['device'] == expected_device == 'mps'
              and meta['model_sha256'] == expected_model_sha256 and meta['token_length'] == 256
              and meta['key_context']['device'] == expected_device
              and meta['key_context']['model_sha256'] == expected_model_sha256
              and meta['old_cache_sha256'] == old_sha256
              and meta['cache_key_sha256'] == calibration.cache_key(**meta['key_context']),
              'Ready supplement/model/device/cache identity mismatch')
    report = h.assets.document(Path(cache).parent/'result.json', meta['result_sha256'])
    h.require(report['status'] == 'passed' and report['ready_cache_written'] is True
              and set(report['vector_parity']) == {'all18_windows', 'all6_whole', 'all7_texts256', 'short_CPU77_to256'}
              and all(v['status'] in ('passed', 'not_applicable') for v in report['vector_parity'].values())
              and report['cache_key_sha256'] == meta['cache_key_sha256'], 'Successful full parity report required')
    proof = h.assets.document(Path(cache).parent/'token-proof.json', meta['token_proof_sha256'])
    h.require(len(proof) == len(meta['new_query_tracks']) == len(meta['query_text_sha256']) == 7
              and all(p['untruncated_tokens'] == p['encoded_nonpad_tokens'] == n and 2 <= n <= 256
                      for p, n in zip(proof, meta['token_lengths'])), 'Seven complete token proofs required')
    short_count = sum(n <= 77 for n in meta['token_lengths'])
    h.require(report['CPU_controls'] == {'audio_windows': 18, 'whole': 6, 'texts256': 7, 'short_text77': short_count}
              and all(report['vector_parity'][name]['status'] == 'passed'
                      for name in ('all18_windows', 'all6_whole', 'all7_texts256'))
              and report['vector_parity']['short_CPU77_to256']['status'] == ('passed' if short_count else 'not_applicable')
              and all(report['vector_parity'][name]['vectors'] == n for name, n in
                  [('all18_windows', 18), ('all6_whole', 6), ('all7_texts256', 7), ('short_CPU77_to256', short_count)]),
              'All new vectors must be covered by the fixed CPU controls')
    old = h.assets.document(old_cache, old_sha256)
    rows = meta['rows']; ids = [r['source_track_id'] for r in rows]
    h.require(len(ids) == len(set(ids)) == 146 and ids == sorted(ids)
              and Counter(r['origin'] for r in rows) == {'old': 140, 'new': 6}
              and Counter(r['split'] for r in rows) == {'train': 100, 'validation': 20, 'caption_dev': 20, 'supplement_dev': 6}
              and set(meta['new_query_tracks']) == {r['source_track_id'] for r in rows if r['origin'] == 'new'}
              and Counter(meta['new_query_tracks']) == {r['source_track_id']: r['validated_caption_count'] for r in rows if r['origin'] == 'new'}
              and meta['old_query_tracks'] == old['query_tracks'], 'Complete fixed query/candidate bindings required')
    path = Path(cache).parent/'features.npz'
    h.require(h.file_hash(path) == meta['feature_sha256'], 'Supplement feature bytes changed')
    with np.load(h.assets.regular(path), allow_pickle=False) as f:
        values = {k: matrix(f[k], shape) for k, shape in [('whole', (146, 512)), ('windows', (642, 512)),
                  ('old_texts', (24, 512)), ('new_texts', (7, 512))]}
    oldpath = Path(old_cache).parent/'features.npz'
    h.require(h.file_hash(oldpath) == old['feature_sha256'], 'Original140 feature bytes changed')
    positions = [ids.index(r['source_track_id']) for r in old['rows']]
    with np.load(h.assets.regular(oldpath), allow_pickle=False) as f:
        h.require(np.array_equal(values['whole'][positions], f['retrieval_first120'])
                  and np.array_equal(values['windows'][:624], f['windows'])
                  and np.array_equal(values['old_texts'], f['texts']), 'Original140/624/24 must remain elementwise identical')
    oldby = {r['source_track_id']: r for r in old['rows']}
    h.require(sorted(i for r in rows if r['origin'] == 'new' for i in r['retrieval_window_indices']) == list(range(624, 642)),
              'Each of the eighteen new windows must be bound once')
    for row in rows:
        ix = row['retrieval_window_indices']
        h.require(len(ix) == 3 and len(set(ix)) == 3 and all(type(i) is int and 0 <= i < 642 for i in ix),
                  'Three valid source window indices required')
        if row['origin'] == 'old':
            h.require(ix == oldby[row['source_track_id']]['retrieval_window_indices'], 'Old source window binding changed')
        else:
            n = row['retrieval_clip_samples']
            h.require(row['window_start_samples'] == sorted({0, max(0, n-480000)//2, max(0, n-480000)})
                      and 30*48000 <= n <= 120*48000 and all(i >= 624 for i in ix)
                      and np.allclose(values['whole'][ids.index(row['source_track_id'])],
                                      unit(values['windows'][ix].mean(axis=0, keepdims=True))[0], atol=1e-12, rtol=0),
                      'New source aggregation/window binding mismatch')
    return {**values, 'rows': rows, 'old_query_tracks': meta['old_query_tracks'],
            'new_query_tracks': meta['new_query_tracks'], 'cache_key_sha256': meta['cache_key_sha256']}


def evaluate(view, w):
    ids = [r['source_track_id'] for r in view['rows']]
    output = {}
    for pool in ('new6', 'old20_control', 'old20_original140'):
        text, tracks = (view['new_texts'], view['new_query_tracks']) if pool == 'new6' else (view['old_texts'], view['old_query_tracks'])
        positions = [i for i, r in enumerate(view['rows']) if pool != 'old20_original140' or r['origin'] == 'old']
        keys = [ids[i] for i in positions]
        whole = text @ unit(view['whole'][positions] @ w).T
        segment = np.column_stack([(text @ unit(view['windows'][view['rows'][i]['retrieval_window_indices']] @ w).T).max(axis=1)
                                   for i in positions])
        output[pool] = {mode: metrics.paired(scores, tracks, keys) for mode, scores in [('whole', whole), ('segment', segment)]}
    return output
