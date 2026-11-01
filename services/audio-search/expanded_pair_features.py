"""Explicit fulltext expanded interval cache; no encoder imports in the consumer."""
from collections import Counter
from pathlib import Path
import numpy as np
import holdout_contract as h
import interval_feature_cache as intervals
import device_calibration as calibration
from device_feature_cache import matrix
from tag_adapter import unit

COUNTS = {'train_recordings': 100, 'train_components': 83, 'train_intervals': 539,
          'validation_recordings': 20, 'validation_components': 19, 'validation_intervals': 60}


def identity(row):
    return row['id'], row['start_time'], row['end_time']


def combine(old_candidates, new_candidates, old_allowlist, old_corpus, recordings, base_rows):
    new = recordings['records']
    h.require(len(new) == len({r['id'] for r in new}) == 76 and not recordings['failures'], 'Exact76 successful new sources required')
    new_ids = {r['id'] for r in new}
    h.require(not new_ids & {r['id'] for r in old_candidates['candidates']}, 'Old/new sources overlap')
    allowed = old_allowlist['records']+new
    proofs = old_corpus['tracks']+[{**r, 'decode': {**r['decode'], 'pcm_sha256': r['pcm_sha256']}} for r in new]
    candidates = {'candidates': old_candidates['candidates']+new_candidates['candidates'],
                  'label_source': 'model_generated', 'training_ready': False}
    rows, texts, unique, by_id, counts = intervals.plan(candidates, {'records': allowed}, {'tracks': proofs}, expected=COUNTS)
    base = {identity(r): (i, r) for i, r in enumerate(base_rows)}
    reused = {}
    for i, r in enumerate(rows):
        if r['id'] in new_ids: continue
        h.require(identity(r) in base, 'Existing row absent from immutable cache')
        j, before = base[identity(r)]
        h.require(all(r[k] == before[k] for k in r if k not in ('weight', 'window_indices')), 'Existing interval metadata changed')
        reused[i] = j
    h.require(len(reused) == len(base) == 232 and len(rows)-len(reused) == 367, 'Exact232 reused and367 new intervals required')
    return rows, texts, unique, by_id, counts, reused


def proof_complete(proof, lengths):
    h.require(len(proof) == len(lengths) == 599 and all(type(n) is int and 2 <= n <= 256 for n in lengths)
              and all(r['untruncated_tokens'] == r['encoded_nonpad_tokens'] == n for r, n in zip(proof, lengths)),
              'All599 full captions must fit256; no truncation or filtering')


def validate_windows(rows, unique):
    canonical = sorted({(r['id'], s) for r in rows for s in r['window_start_samples']}, key=lambda k: (int(k[0]), k[1]))
    h.require([(r['id'], r['start_sample']) for r in unique] == canonical, 'Canonical unique window list required')
    for r in rows:
        h.require(all(i < len(unique) for i in r['window_indices']) and
                  [(unique[i]['id'], unique[i]['start_sample']) for i in r['window_indices']] ==
                  [(r['id'], s) for s in r['window_start_samples']], 'Window/interval binding differs')


def ready_view(cache, cache_sha256, *, expected_device, expected_model_sha256, split):
    h.require(split in ('train', 'validation'), 'Explicit train/validation split required')
    path = Path(cache); meta = h.assets.document(path, cache_sha256)
    h.require(meta['schema'] == 'sonora-expanded-pair-feature-cache-v1' and meta['status'] == 'ready_after_parity'
              and meta['device'] == expected_device and meta['model_sha256'] == expected_model_sha256
              and meta['token_length'] == 256 and meta['recipe'] == intervals.RECIPE
              and meta['key_context']['device'] == expected_device and meta['key_context']['model_sha256'] == expected_model_sha256
              and calibration.cache_key(**meta['key_context']) == meta['cache_key_sha256'], 'Fulltext/model/device/recipe/key differs')
    report = h.assets.document(path.parent/'result.json', meta['result_sha256'])
    h.require(report['status'] == 'passed' and report['ready_cache_written'] is True and report['truncated_captions'] == 0
              and report['cache_key_sha256'] == meta['cache_key_sha256']
              and set(report['vector_parity']) == {'new_windows', 'new_interval_audio', 'new_text256'}
              and all(v['status'] == 'passed' for v in report['vector_parity'].values())
              and report['reused_intervals_exact'] == 232, 'Successful numeric and reuse proof required')
    rows = meta['rows']; intervals.validate_rows(rows, COUNTS); validate_windows(rows, meta['unique_windows'])
    proof = h.assets.document(path.parent/'token-proof.json', meta['token_proof_sha256'])
    proof_complete(proof, meta['token_lengths'])
    h.require(h.file_hash(path.parent/'features.npz') == meta['feature_sha256'], 'Feature bytes differ')
    positions = [i for i, r in enumerate(rows) if r['split'] == split]
    with np.load(h.assets.regular(path.parent/'features.npz'), allow_pickle=False) as f:
        audio = matrix(f['audio'], (599, 512)); text = matrix(f['text'], (599, 512))
        windows = matrix(f['windows'], (len(meta['unique_windows']), 512))
        h.require(np.array_equal(f['weights'], np.array([r['weight'] for r in rows])), 'Recording-equal weights differ')
        aggregated = unit(np.stack([windows[r['window_indices']].mean(axis=0) for r in rows]))
        h.require(np.max(abs(aggregated-audio)) < 1e-12, 'Interval/window aggregate mismatch')
    return {'split': split, 'audio': audio[positions].copy(), 'text': text[positions].copy(),
            'weights': np.array([rows[i]['weight'] for i in positions]),
            'recording_ids': [rows[i]['id'] for i in positions], 'creator_components': [rows[i]['creator_component'] for i in positions],
            'original_indices': positions, 'cache_key_sha256': meta['cache_key_sha256'], 'token_length': 256}
